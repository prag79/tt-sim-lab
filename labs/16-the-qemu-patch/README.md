# Lab 16 — Read the one patch that makes all this possible

**Time:** ~30 minutes · **Device:** none (this is a code-reading lab)

Everything in labs 00–06 rests on a **single commit** on top of upstream
QEMU `stable-11.0`. This lab opens it up. The whole fork is one new
device model — `hw/misc/ttsim.c` (~282 lines) — plus a handful of
one-line wiring changes (Kconfig, meson, the two `default.mak` device
lists, a PCI vendor ID, and two README files). That's it.

## Run it

```bash
ttlab 16
```

`explore.sh` downloads `hw/misc/ttsim.c` and `README.ttsim.md` from the
fork into your working copy and points out the four parts that matter.
Then open the file yourself:

```bash
nano ~/work/16-the-qemu-patch/ttsim.c
```

## The four jobs of `hw/misc/ttsim.c`

A QEMU PCI device that "is" a Tenstorrent chip needs to do exactly four
things. As you read, find each one:

1. **Load the simulator at realize time.** When QEMU instantiates the
   device, it `dlopen`s `libttsim.so` via gmodule (`g_module_open` /
   `g_module_symbol`). The PCI identity (vendor / device / class /
   revision) is then read *out of the library's config space*, so the
   guest-visible PCI header tracks whatever chip the loaded `.so` was
   built for. This is why lab 02's `lspci` showed the right vendor ID
   with no hard-coding in QEMU.

2. **Forward BAR MMIO and config space.** The device registers MMIO
   regions (`memory_region_init_io`) for the BARs; every guest read/write
   into a BAR — and into config space — is handed to libttsim. The
   simulator *is* the device's registers and memory windows.

3. **Route simulator-initiated DMA back into the guest.** When the
   virtual chip wants to read or write *guest* RAM (e.g. pulling a
   command queue, pushing results), the library's DMA callbacks are
   wired to `pci_dma_read()` / `pci_dma_write()`, so the DMA lands in the
   guest's address space exactly as a real card's bus-master DMA would.

4. **Advance simulated time.** A QEMU virtual-clock timer
   (`QEMU_CLOCK_VIRTUAL`) ticks libttsim's clock forward in fixed
   quanta, so the chip makes progress in step with the rest of the VM.

## The one big constraint: a single instance

Read the commit message and you'll see why there's only ever *one*
ttsim device per QEMU process:

> libttsim keeps its state in process-wide globals and its DMA callback
> API takes no opaque pointer, so only one instance is supported per
> QEMU process; the device recovers itself inside the DMA callbacks
> through a file-scope singleton.

So a single QEMU = a single chip. (Multichip, per lab 06, is a *single*
multi-chip `libttsim_*_xN.so`, not N separate `-device ttsim` flags.)

## Why this patch "can't go upstream"

From `README.ttsim.md`: the device loads an external library *by name at
runtime*. Upstream QEMU won't carry a device whose behavior is defined by
an out-of-tree `.so`, so the patch lives only in this fork, rebased onto
upstream point releases. The licensing note explains the GPL-v2 /
Apache-2.0 boundary: QEMU and libttsim are separate works, built and
linked by *you*, never shipped as one binary.

## Mini-experiment 1 — change a BAR size and watch the guest react

You don't have to rebuild QEMU to see the device respond to its
parameters. Boot Wormhole with a deliberately wrong BAR4 and observe the
guest:

```bash
tt-guest stop
# Hand-roll a boot with a different aperture (e.g. 16M instead of 32M):
qemu-system-x86_64 -machine q35 -accel kvm:tcg -cpu max -smp 2 -m 2048 \
  -drive file=$HOME/work/.ttsim-guest/guest.qcow2,if=virtio,format=qcow2 \
  -drive file=$HOME/work/.ttsim-guest/seed.iso,if=virtio,format=raw \
  -netdev user,id=n0,hostfwd=tcp::2222-:22 -device virtio-net-pci,netdev=n0 \
  -nographic \
  -device ttsim,lib=/opt/ttsim/libttsim_wh.so,bar4-size=16M
```

Inside the guest, `lspci -v -s 01:00.0` now reports a 16 MB Region 4. The
BAR size is a pure command-line knob handled by the patch — no recompile.

## Mini-experiment 2 — rebuild QEMU yourself (optional, advanced)

If you want the full edit/build loop on the device model:

```bash
git clone -b stable-11.0-ttsim https://github.com/tenstorrent/ttsim-qemu
cd ttsim-qemu
./configure --target-list=x86_64-softmmu --enable-slirp
# edit hw/misc/ttsim.c (e.g. add a debug printf in the realize path)
make -j"$(nproc)"
./build/qemu-system-x86_64 -device ttsim,help
```

This is exactly how the lab image's QEMU was built (see
`.devcontainer/Dockerfile`).

## What you just learned

- The entire ttsim-qemu fork is one PCI device model plus trivial wiring.
- A QEMU device "becomes" a Tenstorrent chip by (1) dlopen-ing the
  library, (2) forwarding BAR/config accesses, (3) routing DMA to guest
  memory, and (4) driving a clock.
- The PCI identity and BAR behavior come from `libttsim.so`, which is why
  stock drivers and tt-metal work unmodified.

## Where to go next

- ttsim: <https://github.com/tenstorrent/ttsim>
- ttsim-qemu: <https://github.com/tenstorrent/ttsim-qemu>
- tt-kmd: <https://github.com/tenstorrent/tt-kmd>
- tt-metal: <https://github.com/tenstorrent/tt-metal>
- libttsim API/ABI: `docs/libttsim_api.md` in the ttsim repo.
