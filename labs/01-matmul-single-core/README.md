# Lab 01 — Single-core matrix multiplication

**Time:** ~45–60 min · **Backend:** library-direct ttsim (virtual Wormhole)
· **Difficulty:** intermediate

This is the first kernel-programming lab. You will run and study a **real
TT-Metalium matrix-multiplication program** on a single Tensix core —
against a *virtual* Wormhole chip, with no QEMU, no driver, and no guest VM
in the way. The simulator (`libttsim_wh.so`) is loaded directly by tt-metal
via `TT_METAL_SIMULATOR`, so kernels execute on the simulated Tensix
RISC-V/compute engines with results **bit-exact to silicon**.

> This lab mirrors the upstream
> [TT-Metalium Lab 1: Single Core Matrix Multiplication](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/labs/matmul/lab1/lab1.html)
> and the
> [Matmul (Single Core)](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/examples/matmul_single_core.html)
> programming example. Read those for the full theory; this README is the
> "run it on the virtual chip" recipe plus the concepts to focus on.
>
> **Deep dive:** [`MATMUL_GUIDE.md`](../MATMUL_GUIDE.md) — source walkthrough
> for all three labs and what the test output means (`409600`, PCC, Test Passed).

## Concepts this lab teaches

- **Tiles, not scalars.** Tensix hardware operates on `32×32` tiles. Matrix
  dimensions `M, K, N` are translated into tile counts `Mt, Kt, Nt`, and the
  host *tilizes* row-major input into the tiled layout the hardware expects.
- **Three kernels per core.** A **reader** kernel streams input tiles from
  DRAM into L1, a **compute** kernel runs the matrix engine (FPU), and a
  **writer** kernel streams the result back to DRAM.
- **Circular buffers (CBs).** The three kernels never call each other; they
  hand tiles off through CBs in L1, forming a producer/consumer pipeline.
- **The matmul compute API.** `mm_init` configures the FPU for matmul (not
  `binary_op_init_common`, which is for elementwise ops), and `matmul_tiles`
  multiply-accumulates a tile pair into the destination register.

## Run it

If you opened the **FULL** Codespace (`tt-sim Lab (FULL — tt-metal prebuilt)`),
tt-metal is already at `/opt/tt-metal` — go straight to the run command.
Confirm with:

```bash
tt-sim status       # should say "built" and point at /opt/tt-metal
```

Run the single-core matmul example on the virtual Wormhole:

```bash
tt-sim run metal_example_matmul_single_core
```

`tt-sim run` exports the library-direct env for you
(`TT_METAL_SIMULATOR`, `TT_METAL_RUNTIME_ROOT`, `TT_METAL_SLOW_DISPATCH_MODE=1`,
`TT_METAL_DISABLE_SFPLOADMACRO=1`) and launches the binary. A successful run
computes `C = A × B` on the simulated Tensix core and verifies it against a
CPU golden reference — you should see **Test Passed**.

Want the raw env to experiment by hand? `tt-sim env` prints the exports, and
`tt-sim shell` drops you into a shell with them already set.

<details>
<summary>Light image only — one-time tt-metal build (skip on FULL)</summary>

If you used the default badge / **light (`:latest`)** image, tt-metal is not
prebuilt. Run this once before any kernel lab (later labs reuse it):

```bash
tt-sim setup        # clone/build tt-metal, wire up the virtual chip
tt-sim status       # confirm "built"
```

*Building* tt-metal is heavy (tens of GB, long compile). *Running* kernels
afterward is light. On a free Codespace, use a larger machine type for the
first build; the result persists in `~/work/tt-metal` across stop/start.

</details>

## Read the source

```bash
ls $TT_METAL_HOME/tt_metal/programming_examples/matmul/matmul_single_core/
```

Focus on, in order:

1. **Host program** — device open, `Mt/Kt/Nt`, DRAM buffer allocation,
   tilization, CB config, kernel creation, and result verification.
2. **`kernels/compute/mm.cpp`** — `mm_init`, the `matmul_tiles`
   multiply-accumulate loop, `tile_regs_*` lifecycle.
3. **Reader / writer kernels** — how tiles move DRAM ⇄ L1 through CBs.

## Edit & rebuild

All source for this lab lives under `$TT_METAL_HOME` (on the FULL image that
is `/opt/tt-metal`):

```
$TT_METAL_HOME/tt_metal/programming_examples/matmul/matmul_single_core/
├── matmul_single_core.cpp       # host: device setup, CBs, launch, verify
└── kernels/
    ├── compute/mm.cpp           # FPU matmul (mm_init, matmul_tiles)
    └── dataflow/                # reader + writer kernels (DRAM ⇄ L1)
```

Open a file in VS Code:

```bash
code $TT_METAL_HOME/tt_metal/programming_examples/matmul/matmul_single_core/kernels/compute/mm.cpp
```

On the FULL image you can edit in place (`/opt/tt-metal` is owned by the
`student` user). To keep the prebuilt tree pristine, copy the example first:

```bash
cp -r $TT_METAL_HOME/tt_metal/programming_examples/matmul/matmul_single_core \
      ~/work/my-matmul-single-core
```

**What needs a rebuild?**

| You changed | Rebuild needed? | Command |
|---|---|---|
| Kernel `.cpp` under `kernels/` | No — re-JITed on next run | `tt-sim run metal_example_matmul_single_core` |
| Host `.cpp` (dimensions, CB config, core grid) | Yes | see below |

After host changes:

```bash
cd $TT_METAL_HOME
./build_metal.sh --build-programming-examples
tt-sim run metal_example_matmul_single_core
```

Look for **Test Passed** and a PCC line near 1.0.

## Understanding the output

A successful run looks like this:

```
Timing — CPU golden: 842.315 ms | Metalium device: 45123.008 ms | device/CPU 53.57x
Output vector of size 409600
Metalium vs Golden -- PCC = 0.981743
Test Passed
```

| Line | What it means |
|---|---|
| **Timing — CPU golden** | Wall-clock time for the reference matmul on the **host CPU** (plain nested loops in fp32, then cast to bfloat16). |
| **Metalium device** | Wall-clock time for the **device path**: upload A/B to simulated DRAM, run reader/compute/writer kernels on the virtual Wormhole, read C back. |
| **device/CPU …x** | How many times **slower** (or faster) the device path was vs CPU golden on *this* host. Under **ttsim** you usually see a large number (often 20–100×): the virtual chip is **software-emulated**, so it is not representative of real silicon speed. On real hardware the ratio is typically inverted (Metalium much faster). |
| **Output vector of size 409600** | Result matrix C is **640 × 640 = 409,600** bfloat16 values (row-major after untilize). |
| **PCC = 0.981743** | **Pearson correlation** between device output and CPU golden. Pass threshold is **> 0.97**. ~0.98 is strong agreement; not exactly 1.0 because of bfloat16 rounding and tiled accumulation order. |
| **Test Passed** | Program finished cleanly and PCC exceeded the threshold. |

The timing lines are injected by the lab environment (`tt-sim` applies a small
patch to the upstream examples at build time). If you do not see them on an
older FULL image, run once:

```bash
tt-sim patch-timing
tt-sim run metal_example_matmul_single_core
```

Fresh **light**-image builds via `tt-sim setup` include timing automatically.

## Exercise

Modify the compute kernel / dimensions and re-run:

- Change `M`, `K`, `N` (keep them multiples of 32) and confirm the golden
  check still passes.
- Trace one output tile: which input tiles feed it, and how many
  `matmul_tiles` accumulations produce it (hint: `Kt`)?

## What you just learned

- A tt-metal program is a host orchestrator plus reader/compute/writer
  kernels communicating via circular buffers.
- The matrix engine consumes `32×32` tiles; tiling and tilization are not
  optional.
- The library-direct ttsim flow lets you iterate on kernels with no
  driver/PCIe/boot overhead — ideal for learning.

Next: [`ttlab 02`](../02-matmul-multi-core/README.md) — spread this work
across the Tensix grid.

---

*Want to see how the device actually appears to an OS — PCIe, BARs, the
`tt-kmd` driver, `/dev/tenstorrent/0`? That's the optional advanced track,
[`ttlab 10`](../10-boot-guest/README.md) onward.*
