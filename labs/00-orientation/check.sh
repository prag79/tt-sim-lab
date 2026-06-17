#!/usr/bin/env bash
# Lab 00 - orientation / environment self-test.
# Verifies the three things every later lab depends on:
#   1. the ttsim QEMU fork is built and on PATH,
#   2. the `ttsim` PCI device is compiled into it,
#   3. the libttsim.so virtual chips are present.
# No guest is booted here - this is a 5-minute "is everything wired up?" check.

set -uo pipefail

QEMU_PREFIX="${QEMU_PREFIX:-/opt/qemu}"
TTSIM_DIR="${TTSIM_DIR:-/opt/ttsim}"
export PATH="$QEMU_PREFIX/bin:$PATH"

pass() { printf '  \033[32m[ ok ]\033[0m %s\n' "$1"; }
fail() { printf '  \033[31m[FAIL]\033[0m %s\n' "$1"; FAILED=1; }
FAILED=0

echo
echo "== ttsim-qemu environment check =="
echo

# 1. QEMU binaries.
for q in qemu-system-x86_64 qemu-system-aarch64; do
  if command -v "$q" >/dev/null 2>&1; then
    pass "$q present: $("$q" --version | head -1)"
  else
    fail "$q not found on PATH"
  fi
done

# 2. The ttsim PCI device is built into this QEMU.
echo
if qemu-system-x86_64 -device help 2>&1 | grep -qi 'ttsim'; then
  pass "the 'ttsim' PCI device is compiled into qemu-system-x86_64"
  echo "       -> $(qemu-system-x86_64 -device help 2>&1 | grep -i ttsim | head -1)"
else
  fail "qemu-system-x86_64 does not expose a 'ttsim' device"
fi

# 3. The libttsim.so virtual chips.
echo
ARCH="$(uname -m)"
sfx=""; [[ "$ARCH" == aarch64 || "$ARCH" == arm64 ]] && sfx="_aarch64"
for chip in wh bh; do
  lib="$TTSIM_DIR/libttsim_${chip}${sfx}.so"
  if [[ -f "$lib" ]]; then
    pass "$(basename "$lib")  ($(du -h "$lib" | cut -f1))"
  else
    fail "missing $lib"
  fi
done

# 4. Show the device's own parameters (this is what the labs configure).
echo
echo "== ttsim device parameters (qemu-system-x86_64 -device ttsim,help) =="
qemu-system-x86_64 -device ttsim,help 2>&1 | sed 's/^/  /' || true

echo
if [[ "$FAILED" == 0 ]]; then
  printf '\033[1;32mAll checks passed.\033[0m Next: run `ttlab 01` to boot a guest.\n'
else
  printf '\033[1;31mSome checks failed.\033[0m See labs/00-orientation/README.md troubleshooting.\n'
  exit 1
fi
echo
