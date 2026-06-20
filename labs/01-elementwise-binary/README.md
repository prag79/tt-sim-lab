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

Expect **`Test Passed`** and an output size line from the host log.

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
