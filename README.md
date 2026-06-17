# tt-sim Lab — kernel programming on a virtual Tenstorrent chip

Learn **TT-Metalium kernel programming** — write and run matrix-multiplication
kernels on a virtual Tenstorrent Wormhole — all in your browser, with **no
silicon and nothing installed on your laptop**. An optional advanced track
also covers the full bring-up story (boot Linux, load the real driver, see
`/dev/tenstorrent/0`).

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
Quasar packaged as a single `libttsim.so`, with results **bit-exact to
silicon**. This lab uses it to teach
[TT-Metalium](https://github.com/tenstorrent/tt-metal) kernel programming.

There are two ways to drive the virtual chip, and this repo has a track for
each:

```
  Primary (kernel programming, library-direct):
        your tt-metal program  ──TT_METAL_SIMULATOR──►  libttsim_wh.so
        (host + reader/compute/writer kernels)          (the virtual chip)

  Advanced (bring-up, optional):
        guest Linux + tt-kmd + tt-metal
                     │  PCIe (BAR MMIO, config space, DMA)
        ┌────────────▼─────────────┐
        │  qemu-system-x86_64      │   ← ttsim-qemu (upstream stable-11.0 + 1 patch)
        │   └─ -device ttsim ──────┼──► libttsim_wh.so / libttsim_bh.so
        └──────────────────────────┘   (the virtual chip)
```

The **primary track** points tt-metal straight at `libttsim_wh.so` — no
QEMU, no driver, no guest — so you can focus on writing and running kernels.
The **advanced track** uses [ttsim-qemu](https://github.com/tenstorrent/ttsim-qemu),
a one-patch fork of QEMU that exposes the library to a guest VM as a real
**PCIe device**, so you can boot Linux, load the
[KMD](https://github.com/tenstorrent/tt-kmd), see `/dev/tenstorrent/0`, and
run tt-metal through the full silicon-faithful path.

## What you get

- The **ttsim QEMU fork** prebuilt: `qemu-system-x86_64` and
  `qemu-system-aarch64`, both with the `ttsim` PCI device compiled in.
- Prebuilt **`libttsim_wh.so` and `libttsim_bh.so`** (Wormhole +
  Blackhole, x86_64 and aarch64) under `/opt/ttsim`.
- An **Ubuntu 22.04 guest** (advanced track) booted on demand with
  user-mode networking, so it can `apt install` kernel headers and
  `git clone` tt-kmd exactly per the upstream instructions.
- Lab exercises under `/labs/` (read-only). On first run, `ttlab NN`
  mirrors the lab into your editable `~/work/<lab-name>/` and runs it.

## Two tracks

| Track | Backend | Helper | What it's for | Labs |
|---|---|---|---|---|
| **Primary — kernel programming** | **library-direct** (`TT_METAL_SIMULATOR` → `libttsim_wh.so`) | `tt-sim` | Write/run tt-metal matmul kernels on a virtual Wormhole. No QEMU, no driver, no guest VM — light and fast. | **00–03** |
| Advanced — bring-up (optional) | QEMU + `tt-kmd` | `tt-guest` | See how the chip appears to a real OS as a PCIe device; load the real driver; run tt-metal through the full PCIe path. | 10–16 |

Most students only need the **primary track**. Start there; dip into the
advanced track if you care about the driver/PCIe layer itself.

## Quick start (in the Codespace terminal)

```bash
ttlab list              # see available exercises
ttlab 00                # orientation: verify env + provision tt-metal
tt-sim setup            # one-time: clone/build tt-metal, wire up the virtual chip
ttlab 01                # single-core matrix multiplication
ttlab 02                # multi-core matrix multiplication (SPMD across the grid)
ttlab 03                # multicast for data reuse in multi-core matmul

# Run a lab's program on the virtual Wormhole:
tt-sim run metal_example_matmul_single_core

# --- optional advanced (QEMU + driver) track ---
ttlab 10                # boot a Linux guest (no device yet)
ttlab 14                # run tt-metal through the full QEMU + driver path
ttlab ssh               # ssh into the running guest (second terminal)
ttlab stop              # power off the guest
```

Primary-track rhythm: `tt-sim setup` once, then `tt-sim run <example>` to
execute kernels — no guest, no SSH. Advanced-track rhythm: run `ttlab 1N`
in one terminal (it boots the guest on the serial console), then open a
**second** terminal and `ttlab ssh` in to work interactively.

## Exercises

### Primary track — kernel programming (library-direct ttsim)

| Lab | What it teaches | Source |
|---|---|---|
| `ttlab 00` | Orientation: verify the env; provision tt-metal with `tt-sim setup` | [`labs/00-orientation/`](labs/00-orientation/) |
| `ttlab 01` | Single-core matmul: tiles, reader/compute/writer kernels, circular buffers, the matmul FPU API | [`labs/01-matmul-single-core/`](labs/01-matmul-single-core/) |
| `ttlab 02` | Multi-core matmul: SPMD work-splitting across the Tensix grid, per-core runtime args | [`labs/02-matmul-multi-core/`](labs/02-matmul-multi-core/) |
| `ttlab 03` | Multicast: NoC data reuse to kill redundant DRAM reads in multi-core matmul | [`labs/03-matmul-multicast/`](labs/03-matmul-multicast/) |

These mirror the upstream
[TT-Metalium matmul labs](https://github.com/tenstorrent/tt-metal/tree/main/docs/source/tt-metalium/tt_metal/labs/matmul).
Building tt-metal is the one heavy step; running the kernels afterward is
light. Wormhole needs [tt-metal PR #46871](https://github.com/tenstorrent/tt-metal/pull/46871),
which `tt-sim` pulls in.

### Advanced track — QEMU + tt-kmd bring-up (optional)

| Lab | What it teaches | Source |
|---|---|---|
| `ttlab 10` | Full-system QEMU: boot a complete Linux guest with a PCIe bus | [`labs/10-boot-guest/`](labs/10-boot-guest/) |
| `ttlab 11` | Attach a virtual Wormhole with one `-device` flag; read its PCI identity & BARs | [`labs/11-attach-ttsim/`](labs/11-attach-ttsim/) |
| `ttlab 12` | Build & load the **stock** `tt-kmd`; surface `/dev/tenstorrent/0` | [`labs/12-load-kmd/`](labs/12-load-kmd/) |
| `ttlab 13` | Inspect the device via `/sys`, BARs, and config space | [`labs/13-inspect-device/`](labs/13-inspect-device/) |
| `ttlab 14` | Run tt-metal through the full QEMU + driver path (no `TT_METAL_SIMULATOR`) | [`labs/14-tt-metal-qemu/`](labs/14-tt-metal-qemu/) |
| `ttlab 15` | Blackhole bring-up (32 GB BAR4) + multichip preview (N300/P300/T3000/Galaxy) | [`labs/15-blackhole-multichip/`](labs/15-blackhole-multichip/) |
| `ttlab 16` | Read the single patch: how `hw/misc/ttsim.c` turns a `.so` into a PCIe chip | [`labs/16-the-qemu-patch/`](labs/16-the-qemu-patch/) |

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
- Primary-track labs run tt-metal against `/opt/ttsim/libttsim_wh.so`
  via the library-direct flow (the `tt-sim` helper); advanced-track labs
  boot a guest via QEMU using the prebuilt `qemu-system-*` and the same
  `libttsim_*.so`.

## Two images: light (`:latest`) vs. full (`:full`)

| | `:latest` (light) | `:full` (prebuilt) |
|---|---|---|
| Built by | `build.yml` (on every push) | `build-full.yml` (manual) |
| Contains | QEMU fork + `libttsim` | …**plus tt-metal prebuilt** at `/opt/tt-metal` |
| First-run setup | `tt-sim setup` builds tt-metal (slow, once) | none — already built |
| Image size | small | large (multi-GB) |
| Devcontainer | `.devcontainer/devcontainer.json` | `.devcontainer/full/devcontainer.json` |
| Good for | free Codespaces | "zero-setup" classes on bigger machines |

### Building the full image

The full build bakes tt-metal in, which is heavy — so it runs **manually**,
not on every push:

```bash
# From the Actions tab, run "Build & push FULL lab image", or:
gh workflow run build-full.yml -f runner=ubuntu-latest-16-cores -f tag=full
# tt_metal_ref defaults to the pinned PR #46871 merge commit; override to
# track main:  -f tt_metal_ref=main
```

`build-full.yml` reclaims ~30 GB of runner disk first, then builds with
`--build-arg PREBUILD_TT_METAL=1`. **`ubuntu-latest` is tight** for a full
tt-metal build; prefer a [larger GitHub-hosted runner](https://docs.github.com/en/actions/using-github-hosted-runners/about-larger-runners)
you've configured (e.g. `ubuntu-latest-16-cores`, which has far more disk),
or a self-hosted runner. Pass its label via the `runner` input.

Students then create their Codespace from the **FULL** devcontainer config
(the create-codespace screen lists both) and skip `tt-sim setup`.

## Bigger Codespace machines (more RAM / disk)

A Codespace's RAM **and disk** are set by the **machine type** chosen when it
is created — `hostRequirements` in `devcontainer.json` only sets the
*minimum*. Typical GitHub options:

| Machine | RAM | Storage |
|---|---|---|
| 2-core | 8 GB | 32 GB |
| 4-core | 16 GB | 32 GB |
| 8-core | 32 GB | 64 GB |
| 16-core | 64 GB | 128 GB |
| 32-core | 128 GB | 256 GB |

To get more space:

1. **Pick a larger machine type** on the "Create codespace" screen
   (use **⋯ → New with options…** from the repo's Code dropdown), or raise
   `hostRequirements` so Codespaces won't offer anything smaller. The light
   config asks for 4-core/8 GB/64 GB; the full config asks for
   8-core/16 GB/128 GB.
2. **Enable the bigger types if they're greyed out.** Larger machine types
   must be permitted by the account/org: GitHub → Settings → Codespaces →
   *Machine types* (org), and they require a billing/spending limit > $0.
3. **Mind the quota.** Bigger machines burn the 120 free core-hours faster
   (a 16-core machine is 4× a 4-core), and the larger disk counts against the
   15 GB free storage. Stop/delete Codespaces between sessions.

## Cost (personal GitHub account)

| Meter | Free quota / month | Notes |
|---|---|---|
| Compute | 120 core-hours | This devcontainer requests a 4-core machine → ~30 wall-clock hours |
| Storage | 15 GB-month | The image + a `tt-sim`-built tt-metal tree (`~/work/tt-metal`) is sizable; **delete** the Codespace between sessions to avoid storage overage |

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
| Guest download stalls | Network hiccup on first boot | `tt-guest clean && ttlab 10`. |
| `ttlab ssh` refused | Guest still booting | Wait for the serial login prompt, retry. |
| `tt-sim run` says tt-metal not built | tt-metal not provisioned yet | Run `tt-sim setup` (clones + builds; the first build is slow). |
| matmul example name not found | Binary names vary by tt-metal version | `ls $TT_METAL_HOME/build/programming_examples/ \| grep matmul`. |
| Codespace can't pull `ghcr.io/prag79/tt-sim-lab` | GHCR package is private | Owner: make the package public under GitHub → Packages. |
| Build fails in Actions | See the failing step | `gh run view <id> --log-failed`. |
