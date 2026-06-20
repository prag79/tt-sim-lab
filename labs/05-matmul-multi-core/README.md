# Lab 05 — Multi-core matrix multiplication

**Time:** ~45–60 min · **Backend:** library-direct ttsim (virtual Wormhole)
· **Difficulty:** intermediate

Lab 04 ran matmul on a single Tensix core. A Wormhole has a **grid** of
them. In this lab you scale the same computation across the grid and learn
the data-parallel (SPMD) programming model that makes Tenstorrent hardware
fast.

> Mirrors the upstream
> [TT-Metalium Lab 2: Multi Core Matrix Multiplication](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/index.html)
> and the `matmul_multi_core` programming example.
>
> **Deep dive:** [`MATMUL_GUIDE.md`](../MATMUL_GUIDE.md) — §4 multi-core SPMD.

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
  point of Lab 06.

## Run it

On the **FULL** image, tt-metal is already built — run the example directly:

```bash
tt-sim run metal_example_matmul_multi_core
```

Same library-direct path as Lab 04 — slow-dispatch, results verified against
a CPU golden reference. Expect it to be **slow** (the whole grid is
simulated in software), but **correct**.

See [Lab 04 — Understanding the output](../04-matmul-single-core/README.md#understanding-the-output)
for how to read sample **C[i]**, `409600`, PCC, and **Test Passed**.

> Exact binary names can drift between tt-metal versions. List what your
> build produced with:
> `ls $TT_METAL_HOME/build/programming_examples/ | grep matmul`

<details>
<summary>Light image only — run tt-sim setup first (skip on FULL)</summary>

```bash
tt-sim setup        # once, if not already done (see Lab 04)
tt-sim run metal_example_matmul_multi_core
```

</details>

## Read the source

```bash
ls $TT_METAL_HOME/tt_metal/programming_examples/matmul/matmul_multi_core/
```

Compare it against the single-core version from Lab 04 and find the deltas:

1. **Core range.** A `CoreRange`/`CoreRangeSet` instead of a single
   `CoreCoord{0,0}`.
2. **Work split.** Where the host decides which output tiles each core owns.
3. **Runtime args.** How per-core args parameterize the (shared) kernels.
4. **Kernels.** They barely change — the parallelism lives in the *host*
   orchestration, not the kernel code. That is a key takeaway.

## Edit & rebuild

Source tree (same layout as Lab 04, different example):

```bash
$TT_METAL_HOME/tt_metal/programming_examples/matmul/matmul_multi_core/
```

Focus your edits on the **host** file — that is where core ranges, work
splitting, and per-core runtime args live. Kernel changes under `kernels/`
are re-JITed on the next run; host changes need a rebuild (see
[Lab 04 — Edit & rebuild](../04-matmul-single-core/README.md#edit--rebuild)):

```bash
cd $TT_METAL_HOME
./build_metal.sh --build-programming-examples
tt-sim run metal_example_matmul_multi_core
```

## Exercise

- Shrink/grow the core grid the work is split over and re-run. How does the
  output partitioning change?
- Identify the redundant DRAM reads: for a given input tile of `A`, how many
  different cores read it from DRAM? Keep this number in mind for Lab 06.

## What you just learned

- Scaling on Tensix is mostly a *host-side* concern: split the output over a
  core grid and feed each core the right runtime args.
- The kernel binary is written once and reused across all cores (SPMD).
- Naive multi-core matmul re-reads input data from DRAM many times — a
  bottleneck Lab 06 fixes with multicast.

Next: [`ttlab 06`](../06-matmul-multicast/README.md) — reuse data with
multicast to kill the redundant DRAM traffic.
