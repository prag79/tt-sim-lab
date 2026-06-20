# Lab 00 — Orientation: what's in the box?

**Time:** ~5–10 minutes · **Backend:** none yet (just a self-test)

Welcome. This lab teaches **kernel programming on Tenstorrent hardware**
using [TT-Metalium](https://github.com/tenstorrent/tt-metal) — without any
physical silicon. Everything runs against a **virtual Wormhole** provided by
[ttsim](https://github.com/tenstorrent/ttsim) (`libttsim_wh.so`).

There are two ways to use that virtual chip, and this repo has a track for
each:

| Track | Backend | What it's for | Labs |
|---|---|---|---|
| **Primary — kernel programming** | **library-direct** (`TT_METAL_SIMULATOR`) | Learn Metalium via [ttnn/examples](https://github.com/tenstorrent/tt-metal/tree/main/ttnn/examples), then matmul. No QEMU, no driver, no guest VM. Fast and light. | **01 → 06** |
| Advanced — bring-up | QEMU + `tt-kmd` | See how the chip appears to a real OS as a PCIe device. Boots Linux under the ttsim QEMU fork, loads the real driver, surfaces `/dev/tenstorrent/0`. Heavy. | 10 → 16 |

You are starting the **primary track**. Do labs **in order**:

1. **01** — elementwise add ([`ttnn/examples/lab_eltwise_binary`](https://github.com/tenstorrent/tt-metal/tree/main/ttnn/examples/lab_eltwise_binary))
2. **02** — multicast intro ([`ttnn/examples/lab_multicast`](https://github.com/tenstorrent/tt-metal/tree/main/ttnn/examples/lab_multicast))
3. **03** — *(optional)* TTNN high-level add
4. **04–06** — single-core → multi-core → multicast **matmul**

## How the library-direct backend works

```
        your tt-metal program (host + reader/compute/writer kernels)
                     │  TT_METAL_SIMULATOR = /opt/ttsim/libttsim_wh.so
        ┌────────────▼─────────────┐
        │  libttsim_wh.so          │   ← the virtual Wormhole (Tensix grid,
        └──────────────────────────┘     RISC-V + compute engines, NoC, DRAM)
```

No operating system, no PCIe, no driver — tt-metal talks straight to the
simulator. Kernel results are **bit-exact to silicon**; only speed differs
(it's software simulation, so expect "slow but correct").

## Run the self-test

```bash
ttlab 00
```

This prints a pass/fail line for each prerequisite of the kernel track:

```
  [ ok ] virtual Wormhole library present: libttsim_wh.so (...)
  [ ok ] tt-sim helper present
  [ ok ] tt-metal built at /opt/tt-metal
```

On the **light** image the third line may be `[FAIL]` — run `tt-sim setup` once,
or switch to the FULL devcontainer.

It also checks the advanced-track tooling (the QEMU fork + the `ttsim` PCI
device) and reports it as informational — you don't need it for labs 01–06.

## Provision tt-metal (one time)

> **Using the `:full` prebuilt image?** tt-metal is already compiled at
> `/opt/tt-metal` — `tt-sim status` already reports "built", so you can
> **skip this step** and go straight to `ttlab 01`.

On the **light (`:latest`) image**, the kernel labs need a built tt-metal. Do
this once; it persists across Codespace stop/start:

```bash
tt-sim setup        # locate/clone + build tt-metal, wire up the soc descriptor
tt-sim status       # confirm it reports "built"
```

> **Resource reality check.** *Building* tt-metal is the only heavy step
> (tens of GB, a long compile). If your image ships a prebuilt tree
> (`tt-sim status` shows "built" immediately), setup is instant. *Running*
> kernels afterward is light. Wormhole requires the ttsim fix from
> [tt-metal PR #46871](https://github.com/tenstorrent/tt-metal/pull/46871);
> `tt-sim` clones a ref that includes it (override with `TT_METAL_REF`).

## What you just learned

- This course teaches tt-metal **kernel programming** on a virtual Wormhole.
- The **library-direct** flow (`TT_METAL_SIMULATOR`) is the light, fast
  backend used by labs 01–06 — no QEMU/driver/boot.
- The QEMU + `tt-kmd` **bring-up** story is a separate, optional advanced
  track (labs 10–16) for when you care about the driver/PCIe layer itself.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `libttsim_wh.so` missing | The release download failed at image-build time. Re-run the Actions build, or `wget` it from the [ttsim releases](https://github.com/tenstorrent/ttsim/releases) into `/opt/ttsim`. |
| `tt-sim: command not found` | Open a new terminal, or run `/usr/local/bin/tt-sim status`. |
| `tt-sim setup` build is huge / slow | Expected on a fresh tree. Use a larger machine type for the first build; the result persists in `~/work/tt-metal`. |

Next: [`ttlab 01`](../01-elementwise-binary/README.md) — elementwise add
(Metalium intro).
