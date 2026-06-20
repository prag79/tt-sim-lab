# Lab 01 — Elementwise add (TT-Metalium intro)

**Time:** ~45–60 min · **Backend:** library-direct ttsim (virtual Wormhole)
· **Difficulty:** beginner

Start here after Lab 00. This lab runs Tenstorrent's official **elementwise
add** example — the same program the upstream
[Lab 1 tutorial](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/labs/matmul/lab1/lab1.html)
uses to teach the TT-Metalium programming model *before* matrix multiplication.

Source lives in tt-metal under
[`ttnn/examples/lab_eltwise_binary/`](https://github.com/tenstorrent/tt-metal/tree/main/ttnn/examples/lab_eltwise_binary)
(not under `programming_examples/matmul/`).

## Concepts this lab teaches

- **Host vs device** — the host `.cpp` orchestrates; kernels run on Tensix.
- **Three kernels per core** — **reader** (DRAM → L1), **compute** (`add_tiles`),
  **writer** (L1 → DRAM).
- **Circular buffers (CBs)** — FIFO queues connecting the three kernels.
- **Compile-time vs runtime args** — what gets baked into the kernel binary
  vs passed each launch.
- **Tiled tensors** — data in `32×32` tiles via `ttnn::Tensor` / tilized layout.
- **Verification** — CPU reference vs device output (`Test Passed`).

Matmul (Labs 04–06) reuses this exact pattern with `matmul_tiles` instead of
`add_tiles`. Understanding this lab first makes matmul much easier.

## Run it

On the **FULL** image:

```bash
tt-sim run example_lab_eltwise_binary
```

Expect **`Test Passed`** and an output size line. `tt-sim run` filters out
bring-up noise and prints a **`==> Result`** block at the end; set
`TT_LOGGER_TYPES=All` if you want the full Metal/UMD log stream.

List built ttnn examples if the name differs on your tree:

```bash
ls $TT_METAL_HOME/build/ttnn/examples/
```

<details>
<summary>Light image — run tt-sim setup first</summary>

```bash
tt-sim setup
tt-sim run example_lab_eltwise_binary
```

</details>

## Understanding the output

With the default log filter, a successful run looks like:

```
==> Result
Matrix shape: 640 x 640 (elementwise a + b)
Sample results (a[i] + b[i] = device; golden = CPU reference):
  [0] 0.374540 + 0.950714 = 1.325254  (golden 1.325254)
  [1] 0.731994 + 0.598659 = 1.330653  (golden 1.330653)
  [2] 0.156019 + 0.155994 = 0.312013  (golden 0.312013)
  [3] 0.058084 + 0.866176 = 0.924260  (golden 0.924260)
Output vector of size 409600
Test Passed
```

(Exact floats depend on the fixed RNG seed in the host program; yours will match
this pattern if unmodified.)

| Line | What it means |
|---|---|
| **Matrix shape: 640 x 640** | Two random **640×640** bfloat16 matrices are added element-wise. |
| **Sample results …** | First four elements: **a[i] + b[i]** on device vs CPU golden. Values should match within bfloat16 rounding. |
| **Output vector of size 409600** | Full result flattened: **640 × 640 = 409,600** values (not all printed — that would flood the terminal). |
| **Test Passed** | All 409,600 elements matched the CPU reference within tolerance (4% relative error per element). |

On an older FULL image without the sample patch, run once:

```bash
tt-sim patch-output
tt-sim run example_lab_eltwise_binary
```

If you see **`Test Failed`** or **`Mismatch at index`**, the device result diverged
from the CPU reference — check kernel edits or dimensions (M/N must be multiples of 32).

## Read the source

```bash
ls $TT_METAL_HOME/ttnn/examples/lab_eltwise_binary/
```

Focus on, in order:

1. **`lab_eltwise_binary.cpp`** — `init_program()`, `eltwise_add_tensix()`, golden
   reference, verification loop.
2. **`kernels/dataflow/read_tiles.cpp`** — `noc_async_read_page`, CB reserve/push.
3. **`kernels/compute/tiles_add.cpp`** — `add_tiles_init`, `add_tiles`, CB wait/pop.
4. **`kernels/dataflow/write_tiles.cpp`** — read from CB, write to DRAM.

Compare with the walkthrough in upstream
[lab1.rst §Example TT-Metalium Program](https://github.com/tenstorrent/tt-metal/blob/main/docs/source/tt-metalium/tt_metal/labs/matmul/lab1/lab1.rst).

## Edit & rebuild

| You changed | Rebuild? |
|---|---|
| Kernel `.cpp` under `kernels/` | No — re-JITed on next run |
| Host `lab_eltwise_binary.cpp` | Yes — see below |

```bash
cd $TT_METAL_HOME
./build_metal.sh    # ttnn examples rebuild with the main tree
tt-sim run example_lab_eltwise_binary
```

## Exercise

- Set `TT_METAL_DPRINT_CORES=all` and add a `DPRINT` in the writer kernel
  (see lab1.rst §Exercise 4). Observe JIT compile-on-run for kernel edits.
- Change `M`/`N` (keep multiples of 32) and confirm `Test Passed` still holds.

## What you just learned

- The reader → CB → compute → CB → writer pipeline that every Metalium kernel
  lab uses.
- Why matmul uses `mm_init` / `matmul_tiles` instead of `add_tiles_init` /
  `add_tiles`.

Next: [`ttlab 02`](../02-multicast-intro/README.md) — multicast on the NoC
(without matmul).
