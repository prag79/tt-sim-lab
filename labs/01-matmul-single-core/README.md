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
