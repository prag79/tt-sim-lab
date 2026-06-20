# Student Handout — tt-sim Lab on GitHub Codespaces

Welcome. Over the next few hours you will learn **kernel programming on
Tenstorrent AI hardware** with TT-Metalium: write and run matrix-
multiplication kernels (single-core → multi-core → multicast) on a
**virtual Wormhole**, with results bit-exact to silicon — entirely inside a
browser tab, with **nothing installed on your laptop**.

The course has two tracks:

- **Primary — kernel programming (labs 00–06).** Start with
  [ttnn/examples](https://github.com/tenstorrent/tt-metal/tree/main/ttnn/examples)
  (elementwise add, multicast intro), then matrix multiplication. tt-metal talks
  straight to the virtual chip (`libttsim_wh.so`) via the library-direct flow.
- **Advanced — bring-up (labs 10–16, optional).** Boot Linux inside QEMU,
  attach a virtual Wormhole/Blackhole over (virtual) PCIe, load the real
  Tenstorrent kernel driver, watch `/dev/tenstorrent/0` appear, and read the
  single QEMU patch that makes it possible. Take this if you care about the
  driver/PCIe layer itself.

This document walks you through the setup once. After that, everything
you need is in the per-lab `README.md` files.

## 1. What you need before starting

### 1.1 A personal GitHub account

If you don't have one, create a **free personal account** at
<https://github.com/join>. School-issued accounts work too, but a
personal account is preferred so your Codespace and edits follow you
after the course ends.

GitHub's free tier includes:

| Resource | Free quota / month |
|---|---|
| Codespaces compute | 120 core-hours (≈ 30 hours on the 4-core machine this lab requests) |
| Codespaces storage | 15 GB-month |

The lab fits comfortably if you **stop** your Codespace on breaks and
**delete** it when you're done for the day (§6).

### 1.2 A modern web browser

Chrome, Firefox, Safari, or Edge from the last two years. You'll spend
the lab in the **VS Code** tab GitHub auto-opens — its terminal and
editor are all you need. (Unlike the sister renode-lab, there's no GUI
desktop here; ttsim-qemu is entirely terminal/serial-based.)

### 1.3 Working knowledge of basic Linux

You should be comfortable, from a terminal, with:

- Navigating: `pwd`, `cd`, `ls -la`
- Reading files: `cat`, `less`, `dmesg`, `tail -f`
- Editing files: `nano`, `vim`, or VS Code's editor
- Pipes/redirection: `|`, `>`, `grep`
- Processes & modules: `ps`, `lsmod`, `sudo`
- Recognising errors and reading exit codes

You do **not** need to know Docker, QEMU internals, or Codespaces
internals going in — the labs teach the QEMU parts.

### 1.4 Familiarity with basic PCIe / device concepts (advanced track only)

The **primary kernel track (labs 00–06) does not need any of this** — it
never touches PCIe or a driver. The following is background for the
**optional advanced track (labs 10–16)**. You'll get much more out of those
labs if you already understand, at a hand-wave level:

- A **PCIe device** sits on a bus and is identified by a
  **vendor ID + device ID** (Tenstorrent's vendor ID is `0x1e52`).
- A device exposes **BARs** (Base Address Registers) — memory windows
  the CPU reads/writes to talk to the hardware. Tenstorrent's **BAR4**
  is the large device-memory aperture (Wormhole 32 MB, Blackhole 32 GB).
- **Config space** is a small standard region holding the IDs, BAR
  sizes, and capability list; the OS reads it to enumerate the device.
- **DMA** lets a device read/write *system* RAM directly.
- A **kernel module / driver** (here, `tt-kmd` → `tenstorrent.ko`)
  **binds** to a device by its IDs and creates a `/dev/...` node that
  userspace opens.
- A **full-system emulator** (QEMU) emulates a whole computer — CPU,
  RAM, buses, devices — so a guest OS boots unmodified.

Advanced-track labs 11–13 make every bullet above concrete on a (virtual)
Tenstorrent card.

## 2. First launch (only do this once)

### 2.1 Open the lab repository

Visit <https://github.com/prag79/tt-sim-lab>. Sign in if prompted.

### 2.2 Click the "Open in GitHub Codespaces" badge

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/prag79/tt-sim-lab?quickstart=1)

GitHub will:

1. Show a **"Create codespace"** screen. **Recommended:** use **⋯ → New with
   options…**, pick **"tt-sim Lab (FULL — tt-metal prebuilt)"**, then choose a
   **4-core** machine (fits personal accounts). The FULL image has tt-metal
   already built — students skip `tt-sim setup`. The badge alone opens the
   **light** image (no prebuilt tt-metal); only use that if you intend to build
   tt-metal yourself.
2. Boot a small Linux VM (~30 s).
3. Pull the prebuilt image from GHCR (`:full` or `:latest`, ~1 min first launch).
4. Open VS Code in your browser, attached to the container.

### 2.3 Verify the environment

In the VS Code terminal (open one with **Ctrl-`** if needed):

```bash
ttlab list
```

You should see the labs listed, in two tracks. Then run the self-test:

```bash
ttlab 00
```

You should see green `[ ok ]` lines confirming the virtual Wormhole library
and the `tt-sim` helper (plus informational lines about the advanced-track
QEMU tooling). If a primary-track line is red, see §5.

### 2.4 Provision tt-metal, then run your first kernel

> **On the `:full` image?** tt-metal is already prebuilt at `/opt/tt-metal`
> (`tt-sim status` reports "built") — **skip this step** and go straight to
> `ttlab 01`.

On the **light (`:latest`) image**, the kernel labs need a built tt-metal. Do
this **once** (it persists across Codespace stop/start):

```bash
tt-sim setup        # locate/clone + build tt-metal, wire up the virtual chip
tt-sim status       # should report "built"
```

> The tt-metal **build** is the one heavy step (tens of GB, a long compile).
> On a fresh free Codespace, run it on a larger machine type the first time;
> the result lives in `~/work/tt-metal` and survives stop/start.

Then run the Metalium intro example on the virtual Wormhole:

```bash
ttlab 01            # opens the lab README
tt-sim run example_lab_eltwise_binary
```

Expect **`Test Passed`**. Then continue 02 → 04 → 05 → 06 (03 is optional).

For matmul verification (Lab 04+):

```bash
tt-sim run metal_example_matmul_single_core
```

## 3. The exercises

Each lab has its own detailed `README.md`. Do the **primary track in order**
— the labs build on each other. The advanced track is optional.

For a **unified matmul source-code walkthrough** (labs 04–06: host, kernels,
CBs, and how to read `409600` / PCC / Test Passed), see
[`labs/MATMUL_GUIDE.md`](labs/MATMUL_GUIDE.md).

### Primary track — kernel programming (library-direct ttsim)

| Lab | Time | What you'll do | Detailed README |
|---|---|---|---|
| **00** | ~5–10 min | Verify the env (`tt-sim status` should show tt-metal **built** on FULL). | [`labs/00-orientation/README.md`](labs/00-orientation/README.md) |
| **01** | ~45–60 min | Elementwise add: Metalium intro (reader/compute/writer, CBs) — [ttnn/examples/lab_eltwise_binary](https://github.com/tenstorrent/tt-metal/tree/main/ttnn/examples/lab_eltwise_binary). | [`labs/01-elementwise-binary/README.md`](labs/01-elementwise-binary/README.md) |
| **02** | ~45–60 min | Multicast intro: NoC broadcast + semaphores — [ttnn/examples/lab_multicast](https://github.com/tenstorrent/tt-metal/tree/main/ttnn/examples/lab_multicast). | [`labs/02-multicast-intro/README.md`](labs/02-multicast-intro/README.md) |
| **03** | ~15–20 min | *(Optional)* TTNN high-level add — [ttnn/examples/add](https://github.com/tenstorrent/tt-metal/tree/main/ttnn/examples/add). | [`labs/03-ttnn-add/README.md`](labs/03-ttnn-add/README.md) |
| **04** | ~45–60 min | Single-core matmul: tiles, circular buffers, `matmul_tiles`. | [`labs/04-matmul-single-core/README.md`](labs/04-matmul-single-core/README.md) |
| **05** | ~45–60 min | Multi-core matmul: SPMD, per-core runtime args. | [`labs/05-matmul-multi-core/README.md`](labs/05-matmul-multi-core/README.md) |
| **06** | ~60–90 min | Multicast matmul: reuse data over the NoC. | [`labs/06-matmul-multicast/README.md`](labs/06-matmul-multicast/README.md) |

Primary-track rhythm on the **FULL** image: `tt-sim run <example>` — no setup,
no guest, no SSH. On the **light** image only: `tt-sim setup` once first.

### Advanced track — QEMU + tt-kmd bring-up (optional)

| Lab | Time | What you'll do | Detailed README |
|---|---|---|---|
| **10** | ~15 min | Boot a full Linux guest under QEMU; meet the serial console and SSH. | [`labs/10-boot-guest/README.md`](labs/10-boot-guest/README.md) |
| **11** | ~15 min | Attach a virtual Wormhole with one flag; find it in `lspci`; read its BARs. | [`labs/11-attach-ttsim/README.md`](labs/11-attach-ttsim/README.md) |
| **12** | ~25 min | Build & `insmod` the stock `tt-kmd`; watch `/dev/tenstorrent/0` appear. | [`labs/12-load-kmd/README.md`](labs/12-load-kmd/README.md) |
| **13** | ~20 min | Inspect the device via `/sys`, BARs, and config space. | [`labs/13-inspect-device/README.md`](labs/13-inspect-device/README.md) |
| **14** | 1–3 h | Run a real tt-metal program through the full QEMU + driver path (bigger host). | [`labs/14-tt-metal-qemu/README.md`](labs/14-tt-metal-qemu/README.md) |
| **15** | ~30 min | Blackhole bring-up (32 GB BAR4) + the multichip roadmap. | [`labs/15-blackhole-multichip/README.md`](labs/15-blackhole-multichip/README.md) |
| **16** | ~30 min | Read `hw/misc/ttsim.c` — how a `.so` becomes a PCIe chip. | [`labs/16-the-qemu-patch/README.md`](labs/16-the-qemu-patch/README.md) |

**Advanced-track two-terminal rhythm:** run `ttlab 1N` in one terminal (it
boots the guest and shows the serial console), then open a **second** VS Code
terminal and run `ttlab ssh` to work inside the guest interactively.
`ttlab stop` powers it off.

## 4. Where your edits live

`ttlab NN` copies each lab into a writable scratch tree on first use:

| Path | What it is | Survives stop? | Survives rebuild? | Survives delete? |
|---|---|:---:|:---:|:---:|
| `/labs/<lab-name>/` | Read-only image content | yes | no | no |
| `~/work/<lab-name>/` | Editable copy made by `ttlab NN` | **yes** | no | no |
| `~/work/.ttsim-guest/` | Guest base image, disk overlay, seed, SSH key | **yes** | no | no |
| `/workspaces/tt-sim-lab/` | The cloned git repo | yes | yes | only if `git push`-ed |

**Important (primary track):** the tt-metal tree `tt-sim setup` builds lives
in `~/work/tt-metal`, which **survives Codespace stop/start** — you only
build it once. It is lost if the Codespace is deleted.

**Important (advanced track):** anything you build *inside the guest* (your
`tt-kmd` clone, `tenstorrent.ko`, a tt-metal tree) lives on the guest's disk
overlay under `~/work/.ttsim-guest/guest.qcow2`, which also survives
stop/start. It is lost only if you `tt-guest reset`/`clean` or the Codespace
is deleted.

### 4.1 Persisting lab edits past Codespace deletion

`prag79/tt-sim-lab` is read-only for you. To save edits you make to the
lab files, fork and push to your fork. Run these **inside the Codespace**
in `/workspaces/tt-sim-lab/`:

```bash
cd /workspaces/tt-sim-lab

# 1. One-time: fork and rewire remotes (origin = your fork, upstream = prag79):
gh repo fork --remote --remote-name=origin
git remote -v

# 2. Work on a branch:
git checkout -b my-experiments

# 3. Copy any lab edits back into the tracked tree:
cp -ru ~/work/04-matmul-single-core/.  labs/04-matmul-single-core/
# ...repeat for any lab you changed.

# 4. Commit and push to YOUR fork:
git add -A
git commit -m "my tt-sim lab notes"
git push -u origin my-experiments
```

> The **guest disk image is not tracked in git** (it's gigabytes and
> in `.gitignore`). To carry guest-side work to another machine, copy
> the artifact out of the guest (`scp`, or `git push` from inside the
> guest) rather than trying to commit the `.qcow2`.

## 5. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ttlab 00` red `[FAIL]` for `libttsim_wh.so` | Release download failed at build | `wget` it from the [ttsim releases](https://github.com/tenstorrent/ttsim/releases) into `/opt/ttsim`. |
| `tt-sim run` says tt-metal not built | Using the **light** image without setup | Run `tt-sim setup`, or recreate with the **FULL** config |
| `tt-sim setup` build is huge / OOM | tt-metal build is heavy | Use a larger machine type for the first build; result persists in `~/work/tt-metal`. |
| matmul example name not found | Names vary by tt-metal version | `ls $TT_METAL_HOME/build/programming_examples/ \| grep matmul`. |
| (advanced) `ttlab 00` no `ttsim` device | Image built from upstream QEMU | Rebuild from the `stable-11.0-ttsim` fork branch. |
| (advanced) First `ttlab 10` boot hangs at download | Network hiccup | `tt-guest clean` then `ttlab 10`. |
| (advanced) Guest boot is very slow | No KVM in Codespaces → TCG | Expected. A KVM host (`ls /dev/kvm`) is much faster. |
| (advanced) `ttlab ssh` "Connection refused" | Guest still booting | Wait for the serial login prompt, then retry. |
| (advanced) No Tenstorrent line in `lspci` | Booted without a device | Use `ttlab 11`+ (device `wh`), not `ttlab 10`. |
| (advanced) `tt-kmd` `make` fails (no `build` dir) | Missing kernel headers | In the guest: `sudo apt install -y linux-headers-generic` (match `uname -r`). |
| Codespace can't pull the image | GHCR package private | Owner makes the `tt-sim-lab` package public under GitHub → Packages. |

## 6. Cost discipline (so you don't burn quota)

1. **Stop the Codespace when you walk away.** Bottom-left of VS Code →
   **Stop codespace**. Compute billing pauses immediately. Your guest
   disk overlay (and lab edits) survive a stop.
2. **Delete the Codespace when you're done for the day** — after pushing
   any lab edits you care about (§4.1):

   ```bash
   gh codespace list
   gh codespace delete --codespace <name> --force
   ```

   Note: deleting also discards the guest disk overlay, so finish or
   copy out guest-side work first.

Recreate any time from the badge; only the first launch is slow.

## 7. Where to go after the labs

- ttsim (the simulator): <https://github.com/tenstorrent/ttsim>
- ttsim-qemu (the QEMU fork): <https://github.com/tenstorrent/ttsim-qemu>
- tt-kmd (the kernel driver): <https://github.com/tenstorrent/tt-kmd>
- tt-metal (the application stack): <https://github.com/tenstorrent/tt-metal>
- Setup reference (upstream): <https://github.com/tenstorrent/ttsim#running-ttsim-as-a-qemu-pci-device>

ttsim does not accept pull requests (development is internal), but bug
reports and feature requests via GitHub issues are welcome.

---

**Quick reference card** (print this if you want a single-page cheat
sheet):

```
Open lab:           click the badge in the README
List labs:          ttlab list                          (banner runs this on attach)
Self-test:          ttlab 00                             env check, no boot

-- Primary track: kernel programming (library-direct ttsim) --
Codespace config:   FULL (recommended) — tt-metal prebuilt, no setup
Light image only:   tt-sim setup                         (one-time heavy build)
Status:             tt-sim status
Run intro examples: tt-sim run example_lab_eltwise_binary
                    tt-sim run example_lab_multicast
Run matmul:         tt-sim run metal_example_matmul_single_core
Timing in output:   tt-sim patch-timing   # once, if Timing line missing (older FULL image)
Other matmuls:      tt-sim run metal_example_matmul_multi_core
                    tt-sim run metal_example_matmul_multicore_reuse_mcast
List examples:      ls $TT_METAL_HOME/build/ttnn/examples/
                    ls $TT_METAL_HOME/build/programming_examples/ | grep matmul
Hand-run env:       eval "$(tt-sim env)"   |   tt-sim shell

-- Advanced track: QEMU + tt-kmd bring-up (optional) --
Boot guest:         ttlab 10 (none) / 11..14 (WH) / 15 (BH)
SSH into guest:     ttlab ssh                            (2nd terminal; user/pass tt/tt)
Power off guest:    ttlab stop      (or in guest: sudo poweroff; or Ctrl-a x)
See the device:     (in guest) lspci -nn | grep -i tenstorrent
Load the driver:    (in guest) git clone .../tt-kmd && cd tt-kmd && make && sudo insmod tenstorrent.ko
Read the patch:     ttlab 16  ->  nano ~/work/16-the-qemu-patch/ttsim.c
WH vs BH:           libttsim_wh.so bar4-size=32M   |   libttsim_bh.so bar4-size=32G

Save lab edits:     gh repo fork --remote --remote-name=origin       (one-time)
                    git checkout -b my-experiments
                    cp -ru ~/work/<lab>/. labs/<lab>/
                    git add -A && git commit -m "..." && git push -u origin my-experiments
Stop Codespace:     bottom-left of VS Code -> Stop codespace
Delete Codespace:   gh codespace delete -c <name> --force            (AFTER pushing)
```
