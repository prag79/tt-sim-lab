# Lab 03 — TTNN high-level add (optional)

**Time:** ~15–20 min · **Backend:** library-direct ttsim (virtual Wormhole)
· **Difficulty:** beginner

**Optional.** Labs 01–02 use **TT-Metalium** (you write reader/compute/writer
kernels). This lab shows the other end of the stack: **TTNN** — a higher-level
C++ API where tensor ops are one-liners and kernels are hidden inside the
library.

Source:
[`ttnn/examples/add/`](https://github.com/tenstorrent/tt-metal/tree/main/ttnn/examples/add)

Skip this lab if you are eager to start matmul; it does not teach custom kernels.

## Run it

```bash
tt-sim run example_add
```

This program creates a **`32×64`** bfloat16 tensor of zeros, adds **`3.0`** on
device, reads the result back, and prints sample values plus **`Test Passed`**.

On an older FULL image: `tt-sim patch-output` once, then re-run.

## Understanding the output

```
TTNN add: zeros(32 x 64) + 3.0 on device
Output tensor: 2048 elements (expected all 3.0)
  out[0] = 3.000000
  out[1] = 3.000000
  out[2] = 3.000000
  out[3] = 3.000000
Test Passed
```

| Line | What it means |
|---|---|
| **zeros(32 x 64) + 3.0** | High-level TTNN: create tensor on device, add scalar in one expression. |
| **2048 elements** | **32 × 64** bfloat16 values after readback from simulated device. |
| **out[i] = 3.0** | Every element should be **0 + 3**; sample shows first four. |
| **Test Passed** | All elements within tolerance of 3.0 (smoke test for the TTNN API path). |

Upstream `add.cpp` prints nothing; the lab patch adds this readback for teaching.

## Read the source

```bash
cat $TT_METAL_HOME/ttnn/examples/add/add.cpp
```

Notice: `open_mesh_device`, `zeros`, `input_tensor + scalar` — no `CreateKernel`,
no circular buffers, no JIT kernels.

## Why include it?

Tenstorrent software has two layers students eventually meet:

| Layer | You write | Labs |
|---|---|---|
| **TT-Metalium** | Kernels + host orchestration | 01, 02, 04–06 |
| **TTNN** | Python/C++ calls to prebuilt ops | 03 (this), models/demos upstream |

Matmul in production often uses TTNN internally; these labs teach the Metalium
foundation underneath.

## What you just learned

- TTNN is the convenience layer; Metalium is the control layer.
- Labs 04–06 stay in Metalium because that is where you learn the hardware.

Next (main path): [`ttlab 04`](../04-matmul-single-core/README.md) — single-core
matrix multiplication.
