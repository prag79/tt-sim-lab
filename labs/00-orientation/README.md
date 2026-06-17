# Lab 00 — Orientation: what's in the box?

**Time:** ~5 minutes · **Device:** none (no guest boots yet)

This is the "is my toolchain wired up?" lab. Before booting a whole
operating system, you'll confirm that the three moving parts of
ttsim-qemu are present and talking to each other:

1. **The QEMU fork** — `qemu-system-x86_64` / `qemu-system-aarch64`,
   built from [`tenstorrent/ttsim-qemu`](https://github.com/tenstorrent/ttsim-qemu),
   which is *upstream QEMU `stable-11.0` plus one patch*.
2. **The `ttsim` PCI device** — the device model that the patch adds
   (`hw/misc/ttsim.c`). It's a normal QEMU `-device`, like
   `virtio-net-pci` or `e1000`, except it forwards PCIe traffic to a
   shared library instead of to emulated hardware.
3. **`libttsim.so`** — the actual chip simulator, downloaded from
   [`tenstorrent/ttsim`](https://github.com/tenstorrent/ttsim) releases.
   `libttsim_wh.so` *is* a virtual Wormhole; `libttsim_bh.so` *is* a
   virtual Blackhole. QEMU `dlopen`s one of these at start-up and the
   guest sees it as a real PCIe endpoint.

## The big picture

```
        guest Linux + tt-kmd + tt-metal
                     │  PCIe (BAR MMIO, config space, DMA)
        ┌────────────▼─────────────┐
        │  qemu-system-x86_64      │   ← ttsim-qemu fork
        │   └─ -device ttsim ──────┼──► libttsim_wh.so   (virtual Wormhole)
        └──────────────────────────┘   libttsim_bh.so   (virtual Blackhole)
```

The guest cannot tell the difference between this and a real card: the
KMD binds to the same PCI vendor/device IDs, `/dev/tenstorrent/0`
appears, and tt-metal dispatches work over the same BARs — all backed
by `libttsim.so` rather than silicon.

## Run it

```bash
ttlab 00
```

This runs `check.sh`, which prints a pass/fail line for each component
and then dumps the device's tunable parameters. You should see
something like:

```
  [ ok ] qemu-system-x86_64 present: QEMU emulator version 11.0.1
  [ ok ] the 'ttsim' PCI device is compiled into qemu-system-x86_64
  [ ok ] libttsim_wh.so  (...)
  [ ok ] libttsim_bh.so  (...)
```

## Poke around yourself

```bash
# List every device this QEMU knows about, and find ours:
qemu-system-x86_64 -device help | grep -i ttsim

# Show the parameters the labs set (lib=..., bar4-size=...):
qemu-system-x86_64 -device ttsim,help

# Confirm the libraries are real ELF shared objects:
file /opt/ttsim/libttsim_wh.so
```

The two parameters that matter:

| Parameter | What it does |
|---|---|
| `lib=` | Path to the `libttsim_*.so` to load — this *chooses the chip*. |
| `bar4-size=` | Size of PCI BAR4 (the big device-memory window). **Wormhole: `32M`, Blackhole: `32G`.** |

## What you just learned

- ttsim-qemu is *ordinary QEMU* with one extra device. Everything you
  already know about QEMU (machine types, `-nographic`, user
  networking, snapshots) still applies.
- A "chip" here is a file. Swapping `libttsim_wh.so` for
  `libttsim_bh.so` is the entire difference between booting against a
  Wormhole and a Blackhole.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `qemu-system-x86_64: command not found` | `export PATH=/opt/qemu/bin:$PATH`, or open a new terminal so `/etc/profile.d/ttsim-lab.sh` is sourced. |
| No `ttsim` in `-device help` | The image was built from upstream QEMU, not the fork. Rebuild from `tenstorrent/ttsim-qemu` branch `stable-11.0-ttsim`. |
| `libttsim_*.so` missing | The release download failed at image-build time. Re-run the Actions build, or `wget` it from the [ttsim releases](https://github.com/tenstorrent/ttsim/releases). |

Next: [`ttlab 01`](../01-boot-guest/README.md) — boot a real Linux guest.
