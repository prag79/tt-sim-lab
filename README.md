# tt-sim Lab — kernel programming on a virtual Tenstorrent chip

Learn **TT-Metalium kernel programming** — write and run matrix-multiplication
kernels on a virtual Tenstorrent Wormhole — all in your browser, with **no
silicon and nothing installed on your laptop**. An optional advanced track
also covers the full bring-up story (boot Linux, load the real driver, see
`/dev/tenstorrent/0`).

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/prag79/tt-sim-lab?quickstart=1)

The badge opens the **light** image by default. For classes, use **Code → ⋯ →
New with options…** and select **"tt-sim Lab (FULL — tt-metal prebuilt)"** so
students skip `tt-sim setup`. The first launch pulls a prebuilt image from GHCR
(~1 min). Re-opening the same Codespace afterwards is instant.

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
| **Primary — kernel programming** | **library-direct** (`TT_METAL_SIMULATOR` → `libttsim_wh.so`) | `tt-sim` | TT-Metalium intro examples, then matmul kernels on a virtual Wormhole. No QEMU, no driver, no guest VM. | **00–06** |
| Advanced — bring-up (optional) | QEMU + `tt-kmd` | `tt-guest` | See how the chip appears to a real OS as a PCIe device; load the real driver; run tt-metal through the full PCIe path. | 10–16 |

Most students only need the **primary track**. Start there; dip into the
advanced track if you care about the driver/PCIe layer itself.

## Quick start (in the Codespace terminal)

**Recommended for students:** create the Codespace with the **"tt-sim Lab (FULL —
tt-metal prebuilt)"** devcontainer (Code → **⋯ → New with options…** → pick that
configuration). tt-metal is already built at `/opt/tt-metal` — **no
`tt-sim setup`**.

```bash
ttlab list              # see available exercises
ttlab 00                # orientation: verify env (tt-metal should already be built)
ttlab 01                # elementwise add — Metalium intro (ttnn/examples)
tt-sim run example_lab_eltwise_binary
ttlab 02                # multicast intro on the NoC
tt-sim run example_lab_multicast
ttlab 04                # single-core matrix multiplication
tt-sim run metal_example_matmul_single_core
ttlab 05                # multi-core matmul (SPMD)
tt-sim run metal_example_matmul_multi_core
ttlab 06                # multicast matmul (data reuse)
tt-sim run metal_example_matmul_multicore_reuse_mcast
```

(`ttlab 03` is an optional TTNN high-level API demo — skip if you like.)

Primary-track rhythm on the **FULL** image: `ttlab NN` for the lab README, then
`tt-sim run <example>` — no guest, no SSH, no build step.

<details>
<summary>Light image (`:latest`) — only if you did not use the FULL config</summary>

The default badge opens the **light** image, which does **not** include a
prebuilt tt-metal tree. You must build once:

```bash
ttlab 00
tt-sim setup            # one-time: clone/build tt-metal (slow; needs a bigger machine)
tt-sim run metal_example_matmul_single_core
```

</details>

```bash
# --- optional advanced (QEMU + driver) track ---
ttlab 10                # boot a Linux guest (no device yet)
ttlab 14                # run tt-metal through the full QEMU + driver path
ttlab ssh               # ssh into the running guest (second terminal)
ttlab stop              # power off the guest
```

Advanced-track rhythm: run `ttlab 1N` in one terminal (it boots the guest on
the serial console), then open a **second** terminal and `ttlab ssh` in to
work interactively.

## Exercises

### Primary track — kernel programming (library-direct ttsim)

| Lab | What it teaches | Source |
|---|---|---|
| `ttlab 00` | Orientation: verify the env (`tt-sim status` should show tt-metal **built**) | [`labs/00-orientation/`](labs/00-orientation/) |
| `ttlab 01` | **Elementwise add** — reader/compute/writer, CBs ([ttnn/examples/lab_eltwise_binary](https://github.com/tenstorrent/tt-metal/tree/main/ttnn/examples/lab_eltwise_binary)) | [`labs/01-elementwise-binary/`](labs/01-elementwise-binary/) |
| `ttlab 02` | **Multicast intro** — NoC broadcast + semaphores ([ttnn/examples/lab_multicast](https://github.com/tenstorrent/tt-metal/tree/main/ttnn/examples/lab_multicast)) | [`labs/02-multicast-intro/`](labs/02-multicast-intro/) |
| `ttlab 03` | *(Optional)* TTNN high-level `add` — no custom kernels | [`labs/03-ttnn-add/`](labs/03-ttnn-add/) |
| `ttlab 04` | Single-core matmul: tiles, matmul FPU API | [`labs/04-matmul-single-core/`](labs/04-matmul-single-core/) |
| `ttlab 05` | Multi-core matmul: SPMD, per-core runtime args | [`labs/05-matmul-multi-core/`](labs/05-matmul-multi-core/) |
| `ttlab 06` | Multicast matmul: NoC data reuse | [`labs/06-matmul-multicast/`](labs/06-matmul-multicast/) |

Intro labs **01–02** match the upstream [Lab 1 tutorial](https://docs.tenstorrent.com/tt-metal/latest/tt-metalium/tt_metal/labs/matmul/lab1/lab1.html)
foundation (eltwise before matmul). Matmul labs **04–06** mirror the upstream
[matmul labs](https://github.com/tenstorrent/tt-metal/tree/main/docs/source/tt-metalium/tt_metal/labs/matmul).

See [`labs/MATMUL_GUIDE.md`](labs/MATMUL_GUIDE.md) for matmul source walkthrough
(labs 04–06), test output (`409600`, PCC, sample values), and [§9 API glossary](labs/MATMUL_GUIDE.md#9-api-glossary-source--docs).
On the **FULL** image, tt-metal is prebuilt — students run examples immediately.
On the **light** image, `tt-sim setup` is the one heavy step (build once).
Wormhole needs [tt-metal PR #46871](https://github.com/tenstorrent/tt-metal/pull/46871),
which the FULL image and `tt-sim` both include.

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
| Good for | DIY / development (build tt-metal yourself) | **classes — zero-setup** (recommended) |

### Building the full image

The full build bakes tt-metal in, which is heavy — so it runs **manually**,
not on every push:

```bash
# From the Actions tab, run "Build & push FULL lab image", or:
gh workflow run build-full.yml -f tag=full           # uses a self-hosted runner
# tt_metal_ref defaults to the pinned PR #46871 merge commit; override to
# track main:  -f tt_metal_ref=main
# Use a GitHub larger runner instead:  -f runner=ubuntu-latest-16-cores
```

`build-full.yml` builds with `--build-arg PREBUILD_TT_METAL=1`. It defaults
to a **self-hosted runner** (`runner: self-hosted`) — the machine needs
Docker and ~150 GB free disk; the tt-metal compile runs *inside* the build
container, so no host toolchain is required. Register one via the repo's
**Settings → Actions → Runners → New self-hosted runner**. (GitHub-hosted
larger runners are an alternative but require an Org on a Team/Enterprise
plan; pass e.g. `-f runner=ubuntu-latest-16-cores` if you have one.)

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
   `hostRequirements` so Codespaces won't offer anything smaller. Both configs
   currently ask for 4-core / 8 GB / 32 GB (fits personal accounts).
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
| Storage | 15 GB-month | The **FULL** image is large; **delete** the Codespace between sessions to avoid storage overage |

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
| `tt-sim run` says tt-metal not built | Using the **light** image without running setup | Run `tt-sim setup`, or recreate the Codespace with the **FULL** config |
| matmul example name not found | Binary names vary by tt-metal version | `ls $TT_METAL_HOME/build/programming_examples/ \| grep matmul`. |
| Codespace can't pull `ghcr.io/prag79/tt-sim-lab` | GHCR package is private | Owner: make the package public under GitHub → Packages. |
| Build fails in Actions | See the failing step | `gh run view <id> --log-failed`. |
