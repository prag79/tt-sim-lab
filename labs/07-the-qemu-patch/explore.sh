#!/usr/bin/env bash
# Lab 07 - fetch and tour the single QEMU patch that adds the ttsim device.
# Downloads the two fork-specific files into the working copy so you can read
# them locally, then highlights the key call sites.

set -uo pipefail

QEMU_PREFIX="${QEMU_PREFIX:-/opt/qemu}"
export PATH="$QEMU_PREFIX/bin:$PATH"

BR=stable-11.0-ttsim
RAW="https://raw.githubusercontent.com/tenstorrent/ttsim-qemu/${BR}"

echo "==> Fetching the fork-specific files into $(pwd) ..."
wget -q "$RAW/hw/misc/ttsim.c"     -O ttsim.c        || echo "  (offline? ttsim.c not fetched)"
wget -q "$RAW/README.ttsim.md"     -O README.ttsim.md || true

echo
echo "== The device, as QEMU sees it =="
qemu-system-x86_64 -device ttsim,help 2>&1 | sed 's/^/  /' || true

if [[ -f ttsim.c ]]; then
  lines=$(wc -l < ttsim.c)
  echo
  echo "== hw/misc/ttsim.c is $lines lines. The load-bearing pieces: =="

  echo
  echo "-- 1. dlopen libttsim at realize time (gmodule) --"
  grep -nE 'g_module_open|g_module_symbol|realize' ttsim.c | head -8 | sed 's/^/   /'

  echo
  echo "-- 2. BAR MMIO + config space forwarded to the library --"
  grep -nE 'memory_region_init_io|pci_default_(read|write)_config|config_(read|write)|bar' ttsim.c | head -10 | sed 's/^/   /'

  echo
  echo "-- 3. Simulator-initiated DMA routed back into guest memory --"
  grep -nE 'pci_dma_read|pci_dma_write|dma' ttsim.c | head -8 | sed 's/^/   /'

  echo
  echo "-- 4. Virtual-clock timer drives libttsim in fixed quanta --"
  grep -nE 'timer_|QEMU_CLOCK_VIRTUAL|clock' ttsim.c | head -8 | sed 's/^/   /'

  echo
  echo "Open the whole file with:  nano $(pwd)/ttsim.c"
else
  echo
  echo "(ttsim.c wasn't downloaded - read it online:)"
  echo "  $RAW/hw/misc/ttsim.c"
fi
echo
