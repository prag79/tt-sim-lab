#!/usr/bin/env python3
# Inject student-friendly result lines into tt-metal lab examples (tt-sim-lab).
# Idempotent: each patch checks for its own marker before editing.

from __future__ import annotations

import sys
from pathlib import Path

# --- Lab 01: elementwise add -------------------------------------------------

ELTWISE_MARKER = "tt-sim-lab: eltwise sample results"
ELTWISE_REL = "ttnn/examples/lab_eltwise_binary/lab_eltwise_binary.cpp"
ELTWISE_ANCHOR = '        log_info(tt::LogAlways, "Output vector of size {}", result_vec.size());'
ELTWISE_BLOCK = """
        // tt-sim-lab: eltwise sample results
        log_info(tt::LogAlways, "Matrix shape: {} x {} (elementwise a + b)", M, N);
        log_info(
            tt::LogAlways,
            "Sample results (a[i] + b[i] = device; golden = CPU reference):");
        constexpr size_t tt_sim_sample_n = 4;
        const size_t tt_sim_n = std::min<size_t>(tt_sim_sample_n, result_vec.size());
        for (size_t i = 0; i < tt_sim_n; ++i) {
            log_info(
                tt::LogAlways,
                "  [{}] {:.6f} + {:.6f} = {:.6f}  (golden {:.6f})",
                i,
                static_cast<float>(src0_vec[i]),
                static_cast<float>(src1_vec[i]),
                static_cast<float>(result_vec[i]),
                static_cast<float>(reference_result[i]));
        }

        log_info(tt::LogAlways, "Output vector of size {}", result_vec.size());"""

# --- Lab 02: multicast -------------------------------------------------------

MCAST_MARKER = "tt-sim-lab: multicast sample results"
MCAST_REL = "ttnn/examples/lab_multicast/lab_multicast.cpp"
MCAST_ANCHOR = "    bool all_pass = true;\n\n    // Check each receiver's copy of the tensor"
MCAST_BLOCK = """    // tt-sim-lab: multicast sample results
    constexpr size_t tt_sim_sample_n = 4;
    log_info(tt::LogAlways, "Sample source tensor (first {} elements):", tt_sim_sample_n);
    for (size_t i = 0; i < tt_sim_sample_n && i < reference.size(); ++i) {
        log_info(tt::LogAlways, "  input[{}] = {:.6f}", i, static_cast<float>(reference[i]));
    }
    for (uint32_t receiver = 0; receiver < num_receivers; ++receiver) {
        log_info(tt::LogAlways, "  receiver {} first {} elements:", receiver + 1, tt_sim_sample_n);
        for (size_t i = 0; i < tt_sim_sample_n && i < total_elements; ++i) {
            const uint32_t idx = static_cast<uint32_t>(receiver * total_elements + i);
            log_info(
                tt::LogAlways,
                "    [{}] = {:.6f}",
                i,
                static_cast<float>(received[idx]));
        }
    }

    bool all_pass = true;

    // Check each receiver's copy of the tensor"""

# --- Lab 03: TTNN add ----------------------------------------------------------

ADD_MARKER = "tt-sim-lab: ttnn add sample results"
ADD_REL = "ttnn/examples/add/add.cpp"
ADD_ANCHOR = "    const auto output_tensor = input_tensor + scalar;\n\n    return 0;"
ADD_INCLUDES = """#include <algorithm>
#include <cmath>
#include <fmt/format.h>
#include <tt-metalium/bfloat16.hpp>
#include "ttnn/tensor/tensor.hpp"

"""
ADD_BLOCK = """
    const auto output_tensor = input_tensor + scalar;

    // tt-sim-lab: ttnn add sample results
    fmt::print("TTNN add: zeros({} x {}) + {:.1f} on device\\n", h, w, scalar);
    const ttnn::Tensor output_host = output_tensor.cpu(true);
    const std::vector<bfloat16> values = output_host.to_vector<bfloat16>();
    fmt::print("Output tensor: {} elements (expected all {:.1f})\\n", values.size(), scalar);
    constexpr size_t tt_sim_sample_n = 4;
    const size_t tt_sim_n = std::min(tt_sim_sample_n, values.size());
    for (size_t i = 0; i < tt_sim_n; ++i) {
        fmt::print("  out[{}] = {:.6f}\\n", i, static_cast<float>(values[i]));
    }
    bool tt_sim_ok = true;
    for (const bfloat16 v : values) {
        if (std::abs(static_cast<float>(v) - scalar) > 0.1f) {
            tt_sim_ok = false;
            break;
        }
    }
    fmt::print("{}\\n", tt_sim_ok ? "Test Passed" : "Test Failed");
    return tt_sim_ok ? 0 : 1;"""

# --- Labs 04–06: matmul sample C[i] -------------------------------------------

MATMUL_SAMPLE_MARKER = "tt-sim-lab: matmul sample results"
MATMUL_SAMPLE_ANCHOR = "        result_vec = untilize_nfaces(result_vec, M, N);\n"
MATMUL_SAMPLE_BLOCK = """
        result_vec = untilize_nfaces(result_vec, M, N);

        // tt-sim-lab: matmul sample results
        fmt::print("Matrix multiply C = A x B: {} x {} * {} x {} = {} x {}\\n", M, K, K, N, M, N);
        fmt::print("Sample C[i] (device vs CPU golden):\\n");
        constexpr size_t tt_sim_sample_n = 4;
        for (size_t i = 0; i < tt_sim_sample_n && i < result_vec.size(); ++i) {
            fmt::print(
                "  C[{}] device {:.6f}  golden {:.6f}\\n",
                i,
                static_cast<float>(result_vec[i]),
                static_cast<float>(golden_vec[i]));
        }
"""

MATMUL_FILES = (
    "tt_metal/programming_examples/matmul/matmul_single_core/matmul_single_core.cpp",
    "tt_metal/programming_examples/matmul/matmul_multi_core/matmul_multi_core.cpp",
    "tt_metal/programming_examples/matmul/matmul_multicore_reuse_mcast/matmul_multicore_reuse_mcast.cpp",
)


def patch_once(path: Path, marker: str, anchor: str, block: str, *, replace: bool = True) -> str:
    if not path.is_file():
        return f"skip (missing): {path}"
    text = path.read_text()
    if marker in text:
        return f"already patched: {path}"
    if anchor not in text:
        return f"ERROR: anchor not found in {path}"
    if replace:
        text = text.replace(anchor, block, 1)
    else:
        text = text.replace(anchor, anchor + block, 1)
    path.write_text(text)
    return f"patched: {path}"


def patch_add(path: Path) -> str:
    if not path.is_file():
        return f"skip (missing): {path}"
    text = path.read_text()
    if ADD_MARKER in text:
        return f"already patched: {path}"
    if ADD_ANCHOR not in text:
        return f"ERROR: anchor not found in {path}"
    if ADD_INCLUDES.strip() not in text.replace("\r\n", "\n"):
        anchor_inc = "using namespace ttnn;\n"
        if anchor_inc not in text:
            return f"ERROR: include anchor not found in {path}"
        text = text.replace(anchor_inc, ADD_INCLUDES + anchor_inc, 1)
    text = text.replace(ADD_ANCHOR, ADD_BLOCK, 1)
    path.write_text(text)
    return f"patched: {path}"


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <tt-metal-root>", file=sys.stderr)
        return 2

    root = Path(sys.argv[1])
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 1

    errors = 0
    for msg in (
        patch_once(
            root / ELTWISE_REL,
            ELTWISE_MARKER,
            ELTWISE_ANCHOR,
            ELTWISE_BLOCK,
        ),
        patch_once(
            root / MCAST_REL,
            MCAST_MARKER,
            MCAST_ANCHOR,
            MCAST_BLOCK,
        ),
        patch_add(root / ADD_REL),
    ):
        print(msg)
        if msg.startswith("ERROR"):
            errors += 1

    for rel in MATMUL_FILES:
        msg = patch_once(
            root / rel,
            MATMUL_SAMPLE_MARKER,
            MATMUL_SAMPLE_ANCHOR,
            MATMUL_SAMPLE_BLOCK,
        )
        print(msg)
        if msg.startswith("ERROR"):
            errors += 1

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
