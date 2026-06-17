# Lab 02 — Multi-core matrix multiplication

**Time:** ~45–60 min · **Backend:** library-direct ttsim (virtual Wormhole)
· **Difficulty:** intermediate

Lab 01 ran matmul on a single Tensix core. A Wormhole has a **grid** of
them. In this lab you scale the same computation across the grid and learn
the data-parallel (SPMD) programming model that makes Tenstorrent hardware
fast.

> Mirrors the upstream
> [TT-Metalium Lab 2: Multi Core Matrix Multiplication](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/index.html)
> and the `matmul_multi_core` programming example.

## Concepts this lab teaches

- **SPMD across the grid.** The *same* kernels run on many cores; each core
  works on a different slice of the output. The output tiles are partitioned
  over the core grid, typically with
  `tt::tt_metal::split_work_to_cores`.
- **Per-core runtime arguments.** Each core needs to know *which* output
  tiles it owns. The host sets per-core runtime args (start tile index,
  count, the DRAM addresses to read/write) so one kernel binary behaves
  differently per core.
- **DRAM as the shared source.** In this first multi-core version every core
  independently reads the input tiles it needs from DRAM. That works and is
  simple — but notice the redundant DRAM traffic. Removing it is the whole
  point of Lab 03.

## Run it

If you have not provisioned tt-metal yet, do it once (see Lab 01):

```bash
tt-sim setup
```

Then run the multi-core example on the virtual Wormhole:

```bash
tt-sim run metal_example_matmul_multi_core
```

Same library-direct path as Lab 01 — slow-dispatch, results verified against
a CPU golden reference. Expect it to be **slow** (the whole grid is
simulated in software), but **correct**.

> Exact binary names can drift between tt-metal versions. List what your
> build produced with:
> `ls $TT_METAL_HOME/build/programming_examples/ | grep matmul`

## Read the source

```bash
ls $TT_METAL_HOME/tt_metal/programming_examples/matmul/matmul_multi_core/
```

Compare it against the single-core version from Lab 01 and find the deltas:

1. **Core range.** A `CoreRange`/`CoreRangeSet` instead of a single
   `CoreCoord{0,0}`.
2. **Work split.** Where the host decides which output tiles each core owns.
3. **Runtime args.** How per-core args parameterize the (shared) kernels.
4. **Kernels.** They barely change — the parallelism lives in the *host*
   orchestration, not the kernel code. That is a key takeaway.

## Exercise

- Shrink/grow the core grid the work is split over and re-run. How does the
  output partitioning change?
- Identify the redundant DRAM reads: for a given input tile of `A`, how many
  different cores read it from DRAM? Keep this number in mind for Lab 03.

## What you just learned

- Scaling on Tensix is mostly a *host-side* concern: split the output over a
  core grid and feed each core the right runtime args.
- The kernel binary is written once and reused across all cores (SPMD).
- Naive multi-core matmul re-reads input data from DRAM many times — a
  bottleneck Lab 03 fixes with multicast.

Next: [`ttlab 03`](../03-matmul-multicast/README.md) — reuse data with
multicast to kill the redundant DRAM traffic.
