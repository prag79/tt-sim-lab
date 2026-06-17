# Lab 12 — Build & load tt-kmd, surface `/dev/tenstorrent/0`

**Time:** ~25 minutes · **Device:** Wormhole

This is the payoff lab. You'll take the *unmodified* Tenstorrent
kernel-mode driver ([`tt-kmd`](https://github.com/tenstorrent/tt-kmd)),
build it inside the guest, load it against the virtual Wormhole from
lab 02, and watch `/dev/tenstorrent/0` appear — exactly as it would on a
machine with a real card plugged in.

## Run it

```bash
ttlab 12
```

Wait for the guest's autologin shell. The steps below run **inside the
guest** (either on the serial console or via `ttlab ssh` from a second
terminal). They mirror the official instructions verbatim, because
nothing about the driver build is simulation-specific:

```sh
sudo apt update
sudo apt install -y build-essential linux-headers-generic git

git clone https://github.com/tenstorrent/tt-kmd
cd tt-kmd
make -j"$(nproc)"

sudo insmod tenstorrent.ko
```

> The guest reaches the internet through QEMU user-mode networking, so
> `apt` and `git clone` Just Work. The `linux-headers-generic` package
> must match the running kernel — `uname -r` and
> `dpkg -l | grep linux-headers` should agree.

## Confirm the device node

```sh
ls -l /dev/tenstorrent/
#   crw------- 1 root root 240, 0 ... 0

dmesg | grep -i tenstorrent
#   tenstorrent 0000:01:00.0: enabling device ...
#   tenstorrent 0000:01:00.0: Tenstorrent ... device registered
```

`/dev/tenstorrent/0` is the same character device tt-metal opens on real
hardware. From userspace's point of view, you now have a Tenstorrent
accelerator in this machine.

## What just happened, end to end

```
tt-metal / tt-smi        (userspace, lab 04+)
      │  ioctl / mmap on /dev/tenstorrent/0
   tt-kmd (tenstorrent.ko)        ← you just built & loaded this
      │  PCIe config + BAR MMIO + DMA
  ttsim QEMU device (hw/misc/ttsim.c)
      │  function calls
  libttsim_wh.so                  ← the virtual Wormhole
```

The KMD probed the PCIe device by its Tenstorrent vendor ID (the one you
saw in lab 02), claimed it, set up its BAR mappings and DMA, and created
the device node — never knowing the hardware underneath is a shared
library.

## Mini-experiment: unload and reload

```sh
sudo rmmod tenstorrent
ls /dev/tenstorrent/ 2>&1        # gone
dmesg | tail -3                   # "device removed"
sudo insmod ~/tt-kmd/tenstorrent.ko
ls -l /dev/tenstorrent/           # back
```

This is the full hot-plug path of the driver against a simulated device
— useful when you're developing the KMD itself and want a tight
edit/build/`rmmod`/`insmod` loop with no hardware on your desk.

## Persisting the build across reboots

The guest's disk overlay survives `ttlab stop` / reboot, so your cloned
`~/tt-kmd` and the compiled `tenstorrent.ko` stay put. To auto-load on
boot you could `sudo cp tenstorrent.ko /lib/modules/$(uname -r)/...` and
`depmod`, but for the labs a manual `insmod` after each boot is simplest.

## What you just learned

- The stock `tt-kmd` builds and loads against the virtual device with
  zero changes — the headline feature of ttsim-qemu.
- `/dev/tenstorrent/0` is created by the KMD claiming the PCIe endpoint.
- You can develop and test the kernel driver with no silicon at all.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `make` fails: no `/lib/modules/$(uname -r)/build` | `sudo apt install -y linux-headers-$(uname -r)` (or `linux-headers-generic` then reboot so versions match). |
| `insmod: Operation not permitted` / secure boot | Not an issue in this guest; ensure you used `sudo`. |
| `insmod` ok but no `/dev/tenstorrent/0` | `dmesg | grep -i tenstorrent` — if the driver didn't bind, re-check `lspci` shows the device (you booted with `--device wh`). |
| `apt` / `git` time out | Networking down; confirm `ip addr` shows a `10.0.2.x` address and `ping -c1 github.com` works. |

Next: [`ttlab 13`](../13-inspect-device/README.md) — inspect the device the driver just claimed.
