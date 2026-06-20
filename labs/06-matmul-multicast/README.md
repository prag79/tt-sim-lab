# Lab 06 — Multicast for data reuse in multi-core matmul

**Time:** ~60–90 min · **Backend:** library-direct ttsim (virtual Wormhole)
· **Difficulty:** advanced

Lab 05 split matmul across the grid but had every core re-read its inputs
from DRAM. In a tiled matmul, whole **rows of A** and **columns of B** are
shared by many output tiles — so that DRAM traffic is mostly redundant. This
lab uses the NoC (network-on-chip) to **read once and multicast** shared
tiles to the cores that need them, the key optimization that makes
multi-core matmul actually fast.

**Prerequisite:** [`ttlab 02`](../02-multicast-intro/README.md) introduces the
same multicast/semaphore ideas in a smaller example.

> Mirrors the upstream
> [TT-Metalium Lab 3: Multicast for Improved Data Reuse](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/index.html)
> and the `matmul_multicore_reuse_mcast` programming example.
>
> **Deep dive:** [`MATMUL_GUIDE.md`](../MATMUL_GUIDE.md) — §5 multicast.

## Concepts this lab teaches

- **Why reuse matters.** Output tile `C[i][j]` needs row-block `i` of A and
  column-block `j` of B. Across a row of the output grid, every core shares
  the *same* A tiles; down a column, they share the *same* B tiles. Reading
  those from DRAM per-core is wasteful.
- **Multicast on the NoC.** One core (or edge of the grid) reads a shared
  tile from DRAM once, then **multicasts** it over the NoC to all the cores
  in its row/column. Far cheaper than N independent DRAM reads.
- **Sender/receiver coordination.** Multicast needs semaphores so receivers
  wait until the data has actually landed in their L1, and the sender knows
  when buffers are free to reuse. This is the trickiest part of the lab.
- **NoC congestion.** Reducing DRAM reads and using multicast also reduces
  NoC congestion — a real performance limiter on the grid.

## Run it

On the **FULL** image, run directly:

```bash
tt-sim run metal_example_matmul_multicore_reuse_mcast
```

> Names vary by tt-metal version (there are usually both a `reuse` and a
> `reuse_mcast` variant). List them:
> `ls $TT_METAL_HOME/build/programming_examples/ | grep matmul`
> Try the plain `reuse` variant first, then the `mcast` one, and compare.

Functionally correct under ttsim (bit-exact golden check); performance is
not meaningful under software simulation — you are here to learn the
*technique*, not to benchmark. Compare **PCC** across Lab 05 and Lab 06.

See [Lab 04 — Understanding the output](../04-matmul-single-core/README.md#understanding-the-output).

<details>
<summary>Light image only — run tt-sim setup first (skip on FULL)</summary>

```bash
tt-sim setup        # once, if not already done (see Lab 04)
tt-sim run metal_example_matmul_multicore_reuse_mcast
```

</details>

## Read the source

```bash
ls $TT_METAL_HOME/tt_metal/programming_examples/matmul/matmul_multicore_reuse_mcast/
```

Focus on:

1. **The multicast grid geometry** — which cores are senders, which are
   receivers, and the row/column they serve.
2. **Semaphores** — how `CreateSemaphore` + the reader/writer kernels
   synchronize sender and receivers around each multicast.
3. **The reader kernel** — the `noc_async_write_multicast` (and matching
   wait) calls that replace per-core DRAM reads.
4. **DRAM read count** — confirm each input tile is now read from DRAM far
   fewer times than in Lab 05.

## Edit & rebuild

Source tree:

```bash
$TT_METAL_HOME/tt_metal/programming_examples/matmul/matmul_multicore_reuse_mcast/
```

The interesting edits are in the **reader kernels** (multicast / semaphores).
Compare against Lab 05's reader while you work. Rebuild/run workflow is the
same as Lab 04 — see
[Edit & rebuild](../04-matmul-single-core/README.md#edit--rebuild):

```bash
cd $TT_METAL_HOME
./build_metal.sh --build-programming-examples   # only if you changed host code
tt-sim run metal_example_matmul_multicore_reuse_mcast
```

## Exercise

- Diff the reader kernel against Lab 05's. Where did the per-core DRAM reads
  go, and what replaced them?
- Trace one multicast: which core reads the tile, which cores receive it,
  and which semaphore tells the receivers it is safe to consume?

## What you just learned

- Tiled matmul has heavy data reuse; exploiting it is the difference between
  a correct kernel and a *fast* one.
- Multicast over the NoC turns N redundant DRAM reads into one read plus a
  broadcast, cutting both DRAM traffic and NoC congestion.
- Multicast requires explicit semaphore-based sender/receiver
  synchronization.

## Where to go next

You have now walked the full single-core → multi-core → multicast matmul
progression on a virtual Tenstorrent chip.

- For deeper kernel work, explore the other programming examples:
  `ls $TT_METAL_HOME/tt_metal/programming_examples/`.
- Curious how the virtual chip is presented to a real OS as a PCIe device
  (BARs, config space, the `tt-kmd` driver, `/dev/tenstorrent/0`)? That is
  the **optional advanced track**, [`ttlab 10`](../10-boot-guest/README.md)
  → [`ttlab 16`](../16-the-qemu-patch/README.md), including running tt-metal
  through the *full* QEMU + driver path in
  [`ttlab 14`](../14-tt-metal-qemu/README.md).
