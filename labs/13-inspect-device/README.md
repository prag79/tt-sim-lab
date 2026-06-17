# Lab 13 — Inspect the virtual device (sysfs, BARs, config space)

**Time:** ~20 minutes · **Device:** Wormhole (KMD loaded)

With `tt-kmd` bound to the virtual Wormhole, the device is fully
represented in the guest's `/sys` tree just like a real card. This lab
is a guided tour of where the kernel keeps the device's identity, BAR
mappings, and driver binding — the same places you'd look when
debugging a real card that "doesn't come up."

## Run it

```bash
ttlab 13            # boots WH guest
```

Inside the guest, make sure the driver is loaded (from lab 03):

```sh
lsmod | grep tenstorrent || sudo insmod ~/tt-kmd/tenstorrent.ko
ls /dev/tenstorrent/
```

## Tour 1 — sysfs identity

```sh
D=/sys/bus/pci/devices/0000:01:00.0

cat $D/vendor          # 0x1e52  (Tenstorrent)
cat $D/device          # chip/generation id, straight from libttsim.so
cat $D/class           # 0x120000  processing accelerator
readlink $D/driver     # .../drivers/tenstorrent  <- the KMD claimed it
cat $D/uevent
```

## Tour 2 — the BARs

```sh
lspci -v -s 01:00.0 | sed -n '/Region/p;/Memory/p'
ls -l $D/resource*     # one file per BAR the kernel mapped
```

`resource0` / `resource2` / `resource4` correspond to the device's BARs.
**BAR4** is the big device-memory aperture — 32 MB on Wormhole (set by
`bar4-size=32M`). This is the window tt-metal uses to stream programs and
tensors to the chip.

## Tour 3 — raw config space

```sh
sudo lspci -xxx -s 01:00.0 | head
# or read it byte-exact from sysfs:
sudo hexdump -C $D/config | head
```

The first 64 bytes are the standard PCI header: vendor/device ID,
command/status, BARs, capabilities pointer. Every byte here is served by
`libttsim.so` through the `ttsim` QEMU device — the simulator *is* the
config space.

## Tour 4 — talk to the device from userspace (optional)

You can map BAR4 yourself without tt-metal, to prove the window is live:

```sh
sudo dd if=$D/resource4 bs=4 count=4 2>/dev/null | hexdump -C
```

(Reads are served by the simulator; what you get back depends on the
chip model's reset state. The point is the access path works end to
end.)

## Why each of these matters on real hardware

| What you read | When you'd reach for it |
|---|---|
| `vendor`/`device` | "Is my card even enumerated? Is it the generation I think?" |
| `driver` symlink | "Did the KMD actually bind, or is the device unclaimed?" |
| BAR sizes (`resource*`) | "Is the big aperture the size the firmware expects?" |
| `dmesg` on `insmod` | "Where in probe did bring-up fail?" |

Because the simulator reproduces all of these, a bring-up procedure you
debug here transfers directly to silicon.

## Mini-experiment: compare WH vs. BH BAR4

Note the BAR4 size now (Wormhole, 32 MB). In [lab 15](../15-blackhole-multichip/README.md)
you'll boot Blackhole (`bar4-size=32G`) and see the same `resource4`
entry report a *32 GB* window — the single biggest visible difference
between the two chips at the PCIe level.

## What you just learned

- A simulated Tenstorrent device populates `/sys/bus/pci/...` exactly
  like a physical one: identity, BARs, driver binding.
- BAR4 is the device-memory aperture; its size is chip-specific and
  set on the QEMU command line.
- The config space the guest sees is literally `libttsim.so`'s.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `0000:01:00.0` doesn't exist | The bus address can differ; find it with `lspci | grep -i tenstorrent` and substitute. |
| `driver` symlink missing | KMD not loaded — `sudo insmod ~/tt-kmd/tenstorrent.ko` (lab 03). |
| `resource4` read errors | Some apertures aren't byte-readable via `dd`; that's fine — use `lspci -vv` to inspect instead. |

Next: [`ttlab 14`](../14-tt-metal-qemu/README.md) — run an actual tt-metal program.
