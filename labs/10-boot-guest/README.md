# Lab 10 — Boot a Linux guest under full-system QEMU

> **Advanced track (optional).** This and labs 11–16 teach the QEMU + `tt-kmd`
> bring-up story — how the virtual chip appears to a real OS as a PCIe device.
> If you only want kernel programming, the primary track is labs 01–03.

**Time:** ~15 minutes · **Device:** none

Before we attach a virtual Tenstorrent chip, you need a machine to plug
it into. This lab boots a complete Ubuntu 22.04 guest under the ttsim
QEMU fork — kernel, systemd, userspace, networking — with **no**
Tenstorrent device yet. The point is to get comfortable with the
full-system simulation loop you'll use in every later lab.

## What "full-system" means

Unlike a user-mode emulator (which runs a single binary), QEMU
full-system emulates an entire computer: CPU, RAM, a PCIe bus, disks,
a NIC, a serial port. The guest kernel boots exactly as it would on
real hardware. That's the whole reason ttsim-qemu can present a
Tenstorrent card as a *PCIe device* — there's a real (virtual) PCIe
bus for it to sit on.

## Run it

```bash
ttlab 10
```

The first run downloads the Ubuntu cloud image (~700 MB, cached
afterward), builds a cloud-init seed, and boots. On a Codespaces VM
there's no KVM, so QEMU uses **TCG** (pure software translation) —
expect the boot to take a few minutes. You'll see the kernel log
stream by on the **serial console**, ending at an autologin shell:

```
[    0.000000] Linux version 5.15.0-...
...
Ubuntu 22.04 LTS ttsim ttyS0
tt@ttsim:~$
```

You are now *inside the guest*.

## Look around inside the guest

```sh
uname -a                      # the guest kernel
nproc                         # virtual CPUs (set by tt-guest, default 2)
free -h                       # guest RAM
lspci                         # PCI devices — note: NO Tenstorrent device yet
ip addr                       # user-mode networking gives you 10.0.2.x
ping -c1 github.com           # outbound internet works (we'll need it in lab 03)
```

Keep that `lspci` output in mind — in [lab 11](../11-attach-ttsim/README.md)
a new line will appear for the Tenstorrent device.

## Two ways to talk to the guest

1. **Serial console** — the terminal you ran `ttlab 10` in. This is the
   kernel's `ttyS0`; everything the kernel prints lands here.
2. **SSH** — from a *second* Codespaces terminal:

```bash
ttlab ssh                     # == tt-guest ssh ; user 'tt', password 'tt'
```

SSH is nicer for real work (scrollback, copy/paste, multiple sessions).
The serial console is where you watch boot logs and `dmesg`.

## Exit cleanly

- Inside the guest: `sudo poweroff`, or
- From the serial console: press **Ctrl-a** then **x** to kill QEMU, or
- From another terminal: `ttlab stop`.

## Mini-experiment: snapshot the cost of TCG

Time a trivial workload to feel how software emulation compares to
native:

```sh
time (for i in $(seq 1 1000000); do :; done)
```

It's slower than your laptop — that's the price of cycle-by-cycle
emulation, and exactly why slow-dispatch mode is recommended for
tt-metal later.

## What you just learned

- The guest is a full computer with a PCIe bus — the socket the virtual
  Tenstorrent device will plug into.
- Serial console vs. SSH: logs vs. interactive work.
- The lifecycle: `ttlab NN` boots, `ttlab ssh` attaches, `ttlab stop`
  powers off.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Download stalls on first run | `tt-guest clean` then `ttlab 10` to retry the image fetch. |
| Boot is *very* slow | Expected under TCG. A KVM-capable host (`ls /dev/kvm`) is far faster; Codespaces typically has none. |
| `ttlab ssh` refuses connection | The guest may still be booting; wait for the login prompt on the serial console, then retry. |

Next: [`ttlab 11`](../11-attach-ttsim/README.md) — give this machine a Tenstorrent card.
