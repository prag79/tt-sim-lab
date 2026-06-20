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

Look for log lines such as `[PASS] All N receivers received correct tensor data`
and **`Test Passed`**.

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

## Read the source

```bash
ls $TT_METAL_HOME/ttnn/examples/lab_multicast/
```

Focus on:

1. Host — core grid, four semaphores, which kernel runs on which core.
2. Sender reader — DRAM read + multicast write + semaphore signal.
3. Receiver kernels — semaphore wait + consume tile from L1.

API pointers: [`MATMUL_GUIDE.md` §9.7](../MATMUL_GUIDE.md#97-kernel--multicast--semaphores-lab-03-only)
(multicast APIs; section number kept for anchor — applies to this lab too).

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
