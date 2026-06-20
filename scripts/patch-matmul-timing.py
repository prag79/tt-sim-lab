#!/usr/bin/env python3
# Patch tt-metal matmul programming examples to print CPU vs device wall-clock timing.
# Idempotent: skips files that already contain the tt-sim-lab timing marker.

from __future__ import annotations

import sys
from pathlib import Path

MARKER = "tt-sim-lab: matmul timing"
CHRONO_INCLUDE = "#include <chrono>\n"

TIMING_PRINT = """
        // tt-sim-lab: matmul timing (host wall clock; device path includes DMA + simulated kernels)
        fmt::print(
            "Timing — CPU golden: {:.3f} ms | Metalium device: {:.3f} ms | device/CPU {:.2f}x\\n",
            tt_sim_cpu_ms,
            tt_sim_dev_ms,
            tt_sim_dev_ms / tt_sim_cpu_ms);
"""

EXAMPLES = (
    {
        "rel": "tt_metal/programming_examples/matmul/matmul_single_core/matmul_single_core.cpp",
        "golden": "        golden_matmul(src0_vec, src1_vec, golden_vec, M, N, K);",
        "device": "        matmul_single_core(src0_vec, src1_vec, result_vec, false, M, N, K, mesh_device);",
    },
    {
        "rel": "tt_metal/programming_examples/matmul/matmul_multi_core/matmul_multi_core.cpp",
        "golden": "        golden_matmul(src0_vec, src1_vec, golden_vec, M, N, K);",
        "device": "        matmul_multi_core(src0_vec, src1_vec, result_vec, M, N, K, mesh_device);",
    },
    {
        "rel": "tt_metal/programming_examples/matmul/matmul_multicore_reuse_mcast/matmul_multicore_reuse_mcast.cpp",
        "golden": "        golden_matmul(src0_vec, src1_vec, golden_vec, M, N, K, B);",
        "device": (
            "        matmul_multicore_reuse_mcast("
            "src0_vec, src1_vec, result_vec, false, M, N, K, B, mesh_device);"
        ),
    },
)


def patch_file(path: Path, golden_line: str, device_line: str) -> bool:
    text = path.read_text()
    if MARKER in text:
        return False

    if "#include <chrono>" not in text:
        anchor = '#include "tt-metalium/core_coord.hpp"\n'
        if anchor in text:
            text = text.replace(anchor, anchor + CHRONO_INCLUDE, 1)
        else:
            # multi_core / mcast omit core_coord.hpp
            anchor = "#include <tt-metalium/host_api.hpp>\n"
            if anchor not in text:
                raise SystemExit(f"{path}: could not find include anchor")
            text = text.replace(anchor, anchor + CHRONO_INCLUDE, 1)

    if golden_line not in text:
        raise SystemExit(f"{path}: golden_matmul call not found")
    text = text.replace(
        golden_line,
        "\n".join(
            (
                "        const auto tt_sim_cpu_t0 = std::chrono::steady_clock::now();",
                golden_line,
                "        const auto tt_sim_cpu_t1 = std::chrono::steady_clock::now();",
                "        const double tt_sim_cpu_ms =",
                "            std::chrono::duration<double, std::milli>(tt_sim_cpu_t1 - tt_sim_cpu_t0).count();",
            )
        ),
        1,
    )

    if device_line not in text:
        raise SystemExit(f"{path}: device matmul call not found")
    text = text.replace(
        device_line,
        "\n".join(
            (
                "        const auto tt_sim_dev_t0 = std::chrono::steady_clock::now();",
                device_line,
                "        const auto tt_sim_dev_t1 = std::chrono::steady_clock::now();",
                "        const double tt_sim_dev_ms =",
                "            std::chrono::duration<double, std::milli>(tt_sim_dev_t1 - tt_sim_dev_t0).count();",
            )
        ),
        1,
    )

    output_line = '        fmt::print("Output vector of size {}\\n", result_vec.size());'
    if output_line not in text:
        raise SystemExit(f"{path}: output print not found")
    text = text.replace(output_line, TIMING_PRINT + output_line, 1)

    path.write_text(text)
    return True


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <TT_METAL_HOME>", file=sys.stderr)
        return 2

    home = Path(sys.argv[1])
    if not home.is_dir():
        print(f"not a directory: {home}", file=sys.stderr)
        return 1

    patched = 0
    for spec in EXAMPLES:
        path = home / spec["rel"]
        if not path.is_file():
            print(f"skip (missing): {path}", file=sys.stderr)
            continue
        if patch_file(path, spec["golden"], spec["device"]):
            print(f"patched: {path}")
            patched += 1
        else:
            print(f"already patched: {path}")

    return 0 if patched >= 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
