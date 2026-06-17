# Lab 15 — Blackhole bring-up + a look at multichip

**Time:** ~30 minutes · **Device:** Blackhole (`libttsim_bh.so`, `bar4-size=32G`)

Everything you did for Wormhole applies to Blackhole — you just load a
different `.so` and use a 32 GB BAR4. This lab boots a virtual Blackhole,
loads the KMD against it, and then surveys what's coming with
**multichip** simulation.

## Run it

```bash
ttlab 15            # boots a BH guest (bar4-size=32G)
```

Inside the guest:

```sh
lspci -nn | grep -i tenstorrent          # a Blackhole now, not Wormhole
sudo apt install -y build-essential linux-headers-generic git   # if not done
[ -d ~/tt-kmd ] || git clone https://github.com/tenstorrent/tt-kmd
cd ~/tt-kmd && make -j"$(nproc)" && sudo insmod tenstorrent.ko
ls -l /dev/tenstorrent/                   # the KMD loads on Blackhole today
dmesg | grep -i tenstorrent
```

## Blackhole status (as of this lab)

- **KMD loads** against the virtual Blackhole and `/dev/tenstorrent/0`
  appears — labs 02–04 work the same as Wormhole.
- **tt-metal bring-up is underway**; full tt-metal applications on
  Blackhole are expected soon. For now, Wormhole (lab 05) is the
  recommended path for a complete tt-metal run.

## See the 32 GB aperture

```sh
D=/sys/bus/pci/devices/0000:01:00.0
sudo lspci -v -s 01:00.0 | grep -i 'Region 4\|Memory'
```

Compare with lab 04: Wormhole's BAR4 was 32 MB; Blackhole's is **32 GB**.
That huge window is why Blackhole uses `bar4-size=32G` on the QEMU
command line — getting this wrong is the most common BH bring-up
mistake.

## Multichip — what's coming

ttsim already ships multichip simulator builds, and multichip support is
arriving in ttsim-qemu too. The available configurations (see the
[ttsim releases](https://github.com/tenstorrent/ttsim/releases)) are:

| Config | Board | Library |
|---|---|---|
| `wh_x2`  | N300            | `libttsim_wh_x2.so` |
| `wh_x8`  | T3000 / LoudBox | `libttsim_wh_x8.so` |
| `wh_x32` | WH Galaxy       | `libttsim_wh_x32.so` |
| `bh_x2`  | P300            | `libttsim_bh_x2.so` |
| `bh_x32` | BH Galaxy       | `libttsim_bh_x32.so` |

On the library-direct path these already run real `ttnn`, fabric, and
CCL tests, with Ethernet / multi-device / fabric tests passing. To drive
them from tt-metal today you point at a cluster descriptor, e.g.:

```sh
export TT_METAL_MOCK_CLUSTER_DESC_PATH=\
$TT_METAL_HOME/tt_metal/third_party/umd/tests/cluster_descriptor_examples/wormhole_N300.yaml
# (or blackhole_P300_both_mmio.yaml for P300)
```

A test validated across N300, P300, T3000, WH Galaxy, and BH Galaxy —
dispatching work to *every* chip in both slow- and fast-dispatch mode —
is:

```
tests/ttnn/unit_tests/base_functionality/test_multi_device.py::test_multi_device_single_op_binary
```

> The `bh_x32` (BH Galaxy) build is x86_64-only for now, due to an
> aarch64 linker limitation with its very large BSS segment.

## On the horizon

Beyond the current Wormhole/Blackhole multichip work, future
**QSR / Keraunos** support is planned. The architecture here — a virtual
chip as a loadable `.so` behind a stock PCIe device — is what makes
adding a new generation a matter of shipping a new library, not a new
emulator.

## What you just learned

- Blackhole is "Wormhole with a different `.so` and a 32 GB BAR4"; the
  KMD path is identical and works today.
- tt-metal on Blackhole is in active bring-up; Wormhole is the complete
  path for now.
- Multichip (N300/P300/T3000/Galaxy) is real on the library-direct path
  and coming to ttsim-qemu, driven by cluster descriptors.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `bar4-size=32M` error on BH | Blackhole needs `32G`; `ttlab 15` sets this for you. |
| Multichip `.so` not present | The lab image ships single-chip WH/BH; download multichip libs from the [ttsim releases](https://github.com/tenstorrent/ttsim/releases) into `/opt/ttsim`. |

Next: [`ttlab 16`](../16-the-qemu-patch/README.md) — read the one patch that makes all of this possible.
