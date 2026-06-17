# Lab 02 — Attach a virtual Wormhole and find it on the bus

**Time:** ~15 minutes · **Device:** Wormhole (`libttsim_wh.so`, `bar4-size=32M`)

Same guest as lab 01, but now QEMU is launched with one extra argument:

```
-device ttsim,lib=/opt/ttsim/libttsim_wh.so,bar4-size=32M
```

That single flag makes a Tenstorrent Wormhole appear on the guest's
PCIe bus. No kernel driver is involved yet — this lab is purely about
seeing the raw PCIe endpoint that `libttsim.so` presents.

## Run it

```bash
ttlab 02
```

Wait for the autologin shell, then from inside the guest:

```sh
lspci -nn | grep -i tenstorrent
```

You should see a new device that was **not** there in lab 01, e.g.:

```
01:00.0 Processing accelerators [1200]: Tenstorrent ... [1e52:401e]
```

`1e52` is Tenstorrent's PCI vendor ID. The device ID identifies the
chip/generation — and, crucially, it's read straight out of
`libttsim.so`'s config space at QEMU realize time, so the guest sees
exactly the identity of whichever library you loaded.

## Inspect the endpoint

```sh
# Full config space + capabilities + BAR layout:
sudo lspci -vv -s 01:00.0

# Just the BARs (Base Address Registers — the device's memory windows):
sudo lspci -v -s 01:00.0 | grep -i 'Region\|Memory'
```

Note **BAR4** — the big window. For Wormhole it's the 32 MB you set with
`bar4-size=32M`. This is the device-memory aperture the KMD and tt-metal
will map and pour data through. (On Blackhole in lab 06 it's *32 GB*.)

## Why this matters

On real silicon the PCIe identity, the BAR sizes, and the config-space
capabilities are baked into the card. Here they're produced by
`libttsim.so` and faithfully relayed by the `ttsim` QEMU device. Because
they match real hardware, the *unmodified* Tenstorrent kernel driver
will bind to this device in the next lab without knowing it's a
simulation.

## Mini-experiment: prove the device comes from the library

Exit (`ttlab stop`), then boot the *same guest with no device*:

```bash
tt-guest boot --device none
```

`lspci | grep -i tenstorrent` now returns nothing. Power off, and bring
it back with the device:

```bash
tt-guest boot --device wh
```

The Tenstorrent line reappears. The chip is entirely a function of the
`-device ttsim,...` flag — i.e. of `libttsim.so`.

## What you just learned

- A virtual Tenstorrent card is added to a VM with one `-device` flag.
- The PCI vendor/device IDs and BAR sizes come from `libttsim.so`,
  which is why stock drivers bind to it.
- BAR4 is the large device-memory window (WH 32 M, BH 32 G).

## Troubleshooting

| Symptom | Fix |
|---|---|
| No Tenstorrent line in `lspci` | Confirm you ran `ttlab 02` (device `wh`), not `ttlab 01`. Check QEMU didn't error on the device — see the serial output right after boot. |
| `qemu: -device ttsim: ... bar4-size` error | Wormhole must use `32M`; only Blackhole uses `32G`. The dispatcher sets this for you; if you hand-rolled the command, fix the size. |

Next: [`ttlab 03`](../03-load-kmd/README.md) — load the driver and get `/dev/tenstorrent/0`.
