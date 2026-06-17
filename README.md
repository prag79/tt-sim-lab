# ttsim-qemu Lab

Boot Linux, load the Tenstorrent driver, see `/dev/tenstorrent/0`, and
run AI-accelerator software against a **virtual** Tenstorrent chip — all
in your browser, no silicon and nothing installed on your laptop.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/prag79/tt-sim-lab?quickstart=1)

The first launch pulls a prebuilt image from GHCR (~1 min). Re-opening
the same Codespace afterwards is instant.

> **Students:** start with [`HANDOUT.md`](HANDOUT.md) — a one-document
> walkthrough of how to launch the Codespace from a personal GitHub
> account, the Linux/PCIe background you should already have, and a
> one-page cheat sheet.

## What is this?

[ttsim](https://github.com/tenstorrent/ttsim) is a fast full-system
simulator of Tenstorrent AI hardware: a virtual Wormhole, Blackhole, or
Quasar packaged as a single `libttsim.so`.
[ttsim-qemu](https://github.com/tenstorrent/ttsim-qemu) is a one-patch
fork of QEMU that exposes that library to a guest VM as a **PCIe
device**. The result is a 100% open-source, full-system environment that
behaves like a real Tenstorrent card:

```
        guest Linux + tt-kmd + tt-metal
                     │  PCIe (BAR MMIO, config space, DMA)
        ┌────────────▼─────────────┐
        │  qemu-system-x86_64      │   ← ttsim-qemu (upstream stable-11.0 + 1 patch)
        │   └─ -device ttsim ──────┼──► libttsim_wh.so / libttsim_bh.so
        └──────────────────────────┘   (the virtual chip)
```

You can boot Linux, load the [KMD](https://github.com/tenstorrent/tt-kmd),
see `/dev/tenstorrent/0`, and run full
[tt-metal](https://github.com/tenstorrent/tt-metal) applications — just
as if you had real silicon — backed by `libttsim.so`.

## What you get

- The **ttsim QEMU fork** prebuilt: `qemu-system-x86_64` and
  `qemu-system-aarch64`, both with the `ttsim` PCI device compiled in.
- Prebuilt **`libttsim_wh.so` and `libttsim_bh.so`** (Wormhole +
  Blackhole, x86_64 and aarch64) under `/opt/ttsim`.
- An **Ubuntu 22.04 guest** booted on demand with user-mode networking,
  so it can `apt install` kernel headers and `git clone` tt-kmd exactly
  per the upstream instructions.
- Eight exercises under `/labs/` (read-only). On first run, `ttlab NN`
  mirrors the lab into your editable `~/work/<lab-name>/` and runs it.

## Quick start (in the Codespace terminal)

```bash
ttlab list              # see available exercises
ttlab 00                # orientation: verify QEMU + ttsim device + libttsim.so
ttlab 01                # boot a Linux guest (no device yet)
ttlab 02                # attach a virtual Wormhole; find it with lspci
ttlab 03                # build & load tt-kmd; get /dev/tenstorrent/0
ttlab 04                # inspect the device (sysfs, BARs, config space)
ttlab 05                # run a tt-metal app on virtual Wormhole (advanced)
ttlab 06                # Blackhole + a look at multichip
ttlab 07                # read the one QEMU patch (hw/misc/ttsim.c)
ttlab ssh               # ssh into the running guest (second terminal)
ttlab stop              # power off the guest
```

The usual rhythm: run `ttlab NN` in one terminal (it boots the guest on
the serial console), then open a **second** terminal and `ttlab ssh` in
to do interactive work.

## Exercises

| Lab | What it teaches | Runs in a free Codespace? | Source |
|---|---|:---:|---|
| `ttlab 00` | The three components (QEMU fork, `ttsim` device, `libttsim.so`) and how they connect | yes | [`labs/00-orientation/`](labs/00-orientation/) |
| `ttlab 01` | Full-system QEMU: boot a complete Linux guest with a PCIe bus | yes | [`labs/01-boot-guest/`](labs/01-boot-guest/) |
| `ttlab 02` | Attach a virtual Wormhole with one `-device` flag; read its PCI identity & BARs | yes | [`labs/02-attach-ttsim/`](labs/02-attach-ttsim/) |
| `ttlab 03` | Build & load the **stock** `tt-kmd`; surface `/dev/tenstorrent/0` | yes | [`labs/03-load-kmd/`](labs/03-load-kmd/) |
| `ttlab 04` | Inspect the device via `/sys`, BARs, and config space — bring-up debugging skills | yes | [`labs/04-inspect-device/`](labs/04-inspect-device/) |
| `ttlab 05` | Run a real tt-metal program on virtual Wormhole (no `TT_METAL_SIMULATOR` — it's the KMD path) | needs a bigger host | [`labs/05-tt-metal-wormhole/`](labs/05-tt-metal-wormhole/) |
| `ttlab 06` | Blackhole bring-up (32 GB BAR4) + multichip preview (N300/P300/T3000/Galaxy) | KMD: yes | [`labs/06-blackhole-multichip/`](labs/06-blackhole-multichip/) |
| `ttlab 07` | Read the single patch: how `hw/misc/ttsim.c` turns a `.so` into a PCIe chip | yes | [`labs/07-the-qemu-patch/`](labs/07-the-qemu-patch/) |

Labs are ordered by difficulty. 00 is a 5-minute sanity check; 01–04
build the full boot → driver → device-inspection path that runs
comfortably in a free Codespace; 05 is the heavyweight tt-metal capstone
(best on a larger machine); 06 covers Blackhole and the multichip
roadmap; 07 reads the source that makes it all work.

### Where your editable copy of each lab lives

`ttlab NN` follows a copy-on-first-use pattern, like the sister
renode-lab:

| Path | What it is | Mutable? |
|---|---|---|
| `/labs/<lab-name>/` | Canonical content baked into the image | no — wiped on rebuild |
| `~/work/<lab-name>/` | Mirror created on first `ttlab NN` invocation | **yes — edit here** |
| `~/work/.ttsim-guest/` | The downloaded guest image, overlay disk, seed, SSH key | yes — survives stop/start |
| `/workspaces/tt-sim-lab/` | The cloned git repo | yes; **`git push` to your fork** to keep changes past Codespace deletion |

The guest's writable disk overlay lives in `~/work/.ttsim-guest/` and
**survives Codespace stop/start**, so anything you build inside the guest
(your `tt-kmd` clone, compiled `tenstorrent.ko`, tt-metal tree) is still
there after a restart.

## Wormhole vs. Blackhole at a glance

| | Wormhole | Blackhole |
|---|---|---|
| Library | `libttsim_wh.so` | `libttsim_bh.so` |
| `bar4-size` | `32M` | `32G` |
| KMD loads? | yes | yes |
| tt-metal apps? | yes (needs [tt-metal PR #46871](https://github.com/tenstorrent/tt-metal/pull/46871)) | bring-up underway |

## How this works

```
You (this repo)  →  GitHub Actions  →  GHCR  →  Codespaces VM  →  Your browser
```

- `git push` to `main` triggers `.github/workflows/build.yml`, which
  builds the Docker image (builds QEMU from the fork + downloads
  `libttsim`, ~10 min) and pushes it to `ghcr.io/prag79/tt-sim-lab:latest`.
- A student clicks the badge; Codespaces boots a VM, pulls the image,
  attaches VS Code in the browser.
- Labs boot a guest via QEMU using the prebuilt `qemu-system-*` and
  `/opt/ttsim/libttsim_*.so`.

## Cost (personal GitHub account)

| Meter | Free quota / month | Notes |
|---|---|---|
| Compute | 120 core-hours | This devcontainer requests a 4-core machine → ~30 wall-clock hours |
| Storage | 15 GB-month | The image + guest overlay fit; **delete** the Codespace between sessions to avoid storage overage |

Stop a Codespace to pause compute billing; delete it (after pushing your
work) to stop storage billing. See [`HANDOUT.md`](HANDOUT.md) §6.

## Acknowledgements

ttsim-qemu, ttsim, tt-kmd, and tt-metal are open-source projects by
[Tenstorrent](https://github.com/tenstorrent). This repo only packages
them into a Codespaces teaching lab; all simulator credit is theirs.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ttlab` not found | `/usr/local/bin` not on `$PATH` (rare) | Run `/usr/local/bin/ttlab list`. |
| `qemu-system-x86_64: command not found` | `/opt/qemu/bin` not on PATH | `export PATH=/opt/qemu/bin:$PATH` or open a fresh terminal. |
| No `ttsim` in `qemu-system-x86_64 -device help` | Image built from upstream QEMU, not the fork | Rebuild from `tenstorrent/ttsim-qemu` `stable-11.0-ttsim`. |
| Guest download stalls | Network hiccup on first boot | `tt-guest clean && ttlab 01`. |
| `ttlab ssh` refused | Guest still booting | Wait for the serial login prompt, retry. |
| Codespace can't pull `ghcr.io/prag79/tt-sim-lab` | GHCR package is private | Owner: make the package public under GitHub → Packages. |
| Build fails in Actions | See the failing step | `gh run view <id> --log-failed`. |
