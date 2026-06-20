# Lab 02 — Multicast intro (NoC broadcast)

**Time:** ~45–60 min · **Backend:** library-direct ttsim (virtual Wormhole)
· **Difficulty:** intermediate

Lab 01 used one Tensix core. This lab introduces **multicast**: one core reads
data from DRAM and **broadcasts** it over the network-on-chip (NoC) to several
receiver cores — the same idea Lab 06 applies inside matmul, but in a small,
standalone example.

Source:
[`ttnn/examples/lab_multicast/`](https://github.com/tenstorrent/tt-metal/tree/main/ttnn/examples/lab_multicast)

## Concepts this lab teaches

- **Sender vs receiver cores** — default grid: `(0,0)` sends; `(1,0)`, `(2,0)`,
  `(3,0)` receive (configurable in host code).
- **Semaphores** — host `CreateSemaphore`; kernels `noc_semaphore_set/wait`.
- **`noc_async_write_multicast`** — one L1 tile copied to many cores' L1.
- **Double buffering** — overlap movement with synchronization.

You do not need to master every line of this example; the goal is to recognize
these patterns when you see them again in [`ttlab 06`](../06-matmul-multicast/README.md).

## Run it

```bash
tt-sim run example_lab_multicast
```

`tt-sim run` prints a **`==> Result`** summary (filters bring-up noise). Look for
multicast shape, per-receiver **`[PASS]`** lines, and **`Test Passed`**.

On an older FULL image: `tt-sim patch-output` once, then re-run.

```bash
ls $TT_METAL_HOME/build/ttnn/examples/ | grep -i multicast
```

<details>
<summary>Light image — tt-sim setup first</summary>

```bash
tt-sim setup
tt-sim run example_lab_multicast
```

</details>

## Understanding the output

```
Multicast example: 640x640 tensor (400 tiles) to 3 receivers
Launching multicast of 400 tiles to 3 receivers
Multicast complete
Output vector size: 1228800 elements
=========== MULTICAST TENSOR VERIFICATION ===========
Sample source tensor (first 4 elements):
  input[0] = 0.374540
  ...
  receiver 1 first 4 elements:
    [0] = 0.374540
  ...
[PASS] Receiver 1 received correct tensor (400 tiles)
[PASS] Receiver 2 received correct tensor (400 tiles)
[PASS] Receiver 3 received correct tensor (400 tiles)
[PASS] All 3 receivers received correct tensor data
Test Passed
```

| Line | What it means |
|---|---|
| **640x640 … 3 receivers** | Sender core `(0,0)` broadcasts one tensor to receivers `(1,0)`, `(2,0)`, `(3,0)`. |
| **1228800 elements** | Three full copies: **409,600 × 3** bfloat16 values read back from DRAM. |
| **Sample source / receiver** | First four elements of the source tensor and each receiver's copy (should match). |
| **`[PASS] Receiver N`** | That core's copy matches the source bit-for-bit. |
| **Test Passed** | All receivers got the correct multicast data. |

## Read the source

```bash
ls $TT_METAL_HOME/ttnn/examples/lab_multicast/
```

Focus on:

1. Host — core grid, four semaphores, which kernel runs on which core.
2. Sender reader — DRAM read + multicast write + semaphore signal.
3. Receiver kernels — semaphore wait + consume tile from L1.

API pointers: [`MATMUL_GUIDE.md` §9.7](../MATMUL_GUIDE.md#97-kernel--multicast--semaphores-labs-02--06)

## Exercise

- Trace one tile from sender DRAM read to a receiver's L1 — which semaphore
  fires when it is safe to read?
- Compare this host layout to Lab 06's `matmul_multicore_reuse_mcast` — same
  multicast primitives, harder geometry.

## What you just learned

- Multicast is a **data-movement** optimization on the NoC, not a compute opcode.
- Semaphores coordinate sender/receiver when buffers are ready.

Next: [`ttlab 03`](../03-ttnn-add/README.md) — optional TTNN high-level API,
or skip to [`ttlab 04`](../04-matmul-single-core/README.md) for matmul.
