# Lab 05 — Run a tt-metal application on virtual Wormhole

**Time:** ~1–3 hours (mostly building tt-metal) · **Device:** Wormhole
· **Difficulty:** advanced

This is the capstone for the Wormhole path: run a real
[TT-Metalium](https://github.com/tenstorrent/tt-metal) program against
the virtual chip. Because the device is presented through `tt-kmd` and
`/dev/tenstorrent/0` (labs 02–03), tt-metal runs **exactly as it does on
real silicon** — you do *not* set `TT_METAL_SIMULATOR`. That env var is
for the library-direct flow; here the simulation lives *below* the
driver, so the whole stack is none the wiser.

> ### Read this first — resource reality check
> Building tt-metal is large: tens of GB of disk, lots of RAM, and a
> long compile, then every kernel runs under TCG software emulation.
> **A free 4-core / 8 GB Codespace is not a comfortable fit for the full
> tt-metal build.** Treat this lab as a recipe to run on a bigger host
> (a roomy Codespace machine type, a workstation, or a CI runner). Labs
> 00–04 and 07 are the ones designed to run start-to-finish in a free
> Codespace; this one documents the real workflow so you can reproduce
> it where you have the resources.

## The one required fix (Wormhole)

tt-metal needs one small bug fix to run cleanly under ttsim-qemu on
Wormhole:

- **[tt-metal PR #46871](https://github.com/tenstorrent/tt-metal/pull/46871)**

Once that PR is merged, tt-metal applications run out of the box. Until
then, build from a tt-metal branch that includes it (or cherry-pick it).

## Steps (inside the guest)

Boot and load the driver:

```bash
ttlab 05            # WH guest
```

```sh
lsmod | grep tenstorrent || sudo insmod ~/tt-kmd/tenstorrent.ko
ls /dev/tenstorrent/0       # must exist
```

Build tt-metal per its own docs (abbreviated):

```sh
sudo apt install -y cmake ninja-build python3-dev python3-venv \
                    libhwloc-dev libnuma-dev git
git clone https://github.com/tenstorrent/tt-metal --recurse-submodules
cd tt-metal
# Use a branch/commit that includes PR #46871 until it lands on main.
export TT_METAL_HOME=$PWD
./build_metal.sh
```

Run a programming example — **slow dispatch is the recommended mode**
under the simulator:

```sh
export TT_METAL_HOME=$PWD
TT_METAL_SLOW_DISPATCH_MODE=1 \
  ./build/programming_examples/metal_example_add_2_integers_in_riscv
```

If the SFPU complains about `SFPLOADMACRO`, disable it (a documented
known issue):

```sh
export TT_METAL_DISABLE_SFPLOADMACRO=1
```

A successful run dispatches the kernel to the virtual Wormhole's RISC-V
cores, executes it, and reads the result back over BAR4 — the same path
silicon uses.

## Why this is the real thing, not a mock

- No `TT_METAL_SIMULATOR` env var: tt-metal talks to `/dev/tenstorrent/0`
  via the stock UMD/KMD, identical to a physical card.
- The numerical results are **bit-exact** to silicon (see ttsim's
  numerical-accuracy contract) for all supported operations.
- The only differences from hardware are speed and ttsim's deliberate
  strictness (it flags `UndefinedBehavior` that silicon might execute
  silently).

## Library-direct flow (contrast, no QEMU)

For comparison, ttsim can also be driven *without* QEMU by pointing
tt-metal straight at the `.so` (no KMD, no `/dev/tenstorrent`):

```sh
export TT_METAL_SIMULATOR=/opt/ttsim/libttsim_wh.so
cp $TT_METAL_HOME/tt_metal/soc_descriptors/wormhole_b0_80_arch.yaml \
   $(dirname $TT_METAL_SIMULATOR)/soc_descriptor.yaml
```

The QEMU flow in this lab is the more faithful one: it exercises the
real PCIe + KMD path, which is what you want when validating drivers,
firmware, or anything that touches `/dev/tenstorrent`.

## What you just learned

- Under ttsim-qemu, tt-metal runs as if on real silicon — the
  simulation is invisible below the driver.
- Wormhole needs PR #46871; slow dispatch and (sometimes)
  `TT_METAL_DISABLE_SFPLOADMACRO=1` are the recommended settings.
- The library-direct (`TT_METAL_SIMULATOR`) flow and the QEMU/KMD flow
  are two distinct ways to use the same `libttsim.so`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Out of disk / OOM during build | Use a larger host; the full tt-metal build doesn't fit a free Codespace. |
| Crash that mentions dispatch | Ensure `TT_METAL_SLOW_DISPATCH_MODE=1`. |
| SFPU `SFPLOADMACRO` error | `export TT_METAL_DISABLE_SFPLOADMACRO=1`. |
| Failure resembling the known WH bug | Confirm your tt-metal includes [PR #46871](https://github.com/tenstorrent/tt-metal/pull/46871). |

Next: [`ttlab 06`](../06-blackhole-multichip/README.md) — Blackhole and a look at multichip.
