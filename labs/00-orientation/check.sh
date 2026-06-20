#!/usr/bin/env bash
# Lab 00 - orientation / environment self-test.
#
# Primary track (kernel programming, library-direct ttsim) prerequisites:
#   1. the virtual Wormhole library libttsim_wh.so is present,
#   2. the tt-sim helper is on PATH,
#   3. tt-metal is built (FULL image: already at /opt/tt-metal; light: tt-sim setup).
#
# Advanced track (QEMU + tt-kmd bring-up, labs 10-16) is checked too, but
# only reported informationally - you don't need it for labs 01-06.

set -uo pipefail

QEMU_PREFIX="${QEMU_PREFIX:-/opt/qemu}"
TTSIM_DIR="${TTSIM_DIR:-/opt/ttsim}"
WORK_TT_METAL="${WORK_ROOT:-$HOME/work}/tt-metal"
PREBAKED_TT_METAL="/opt/tt-metal"
export PATH="$QEMU_PREFIX/bin:$PATH"

pass() { printf '  \033[32m[ ok ]\033[0m %s\n' "$1"; }
fail() { printf '  \033[31m[FAIL]\033[0m %s\n' "$1"; FAILED=1; }
info() { printf '  \033[36m[info]\033[0m %s\n' "$1"; }
FAILED=0
METAL_BUILT=0
METAL_HOME=""

ARCH="$(uname -m)"
sfx=""; [[ "$ARCH" == aarch64 || "$ARCH" == arm64 ]] && sfx="_aarch64"
WH_LIB="$TTSIM_DIR/libttsim_wh${sfx}.so"

# Same resolution order as tt-sim: env -> /opt/tt-metal -> ~/work/tt-metal
resolve_metal_home() {
  if [[ -n "${TT_METAL_HOME:-}" && -d "$TT_METAL_HOME" ]]; then
    echo "$TT_METAL_HOME"; return 0
  fi
  if [[ -d "$PREBAKED_TT_METAL" ]]; then
    echo "$PREBAKED_TT_METAL"; return 0
  fi
  if [[ -d "$WORK_TT_METAL" ]]; then
    echo "$WORK_TT_METAL"; return 0
  fi
  return 1
}

metal_is_built() {
  local home="$1"
  [[ -d "$home/build" ]] && compgen -G "$home/build/programming_examples/*" >/dev/null 2>&1
}

echo
echo "== Primary track: kernel programming (library-direct ttsim) =="
echo

# 1. The virtual Wormhole library (the chip the kernel labs run on).
if [[ -f "$WH_LIB" ]]; then
  pass "virtual Wormhole library present: $(basename "$WH_LIB")  ($(du -h "$WH_LIB" | cut -f1))"
else
  fail "missing $WH_LIB (the virtual Wormhole)"
fi

# 2. The tt-sim helper that drives the library-direct flow.
if command -v tt-sim >/dev/null 2>&1; then
  pass "tt-sim helper present"
else
  fail "tt-sim not found on PATH"
fi

# 3. tt-metal — the thing kernel labs actually need.
if METAL_HOME="$(resolve_metal_home)" && metal_is_built "$METAL_HOME"; then
  METAL_BUILT=1
  pass "tt-metal built at $METAL_HOME"
else
  if [[ -n "$METAL_HOME" ]]; then
    fail "tt-metal found at $METAL_HOME but not built yet"
  else
    fail "no tt-metal tree found"
  fi
  info "Light image only: run  tt-sim setup"
  info "Or recreate the Codespace with the FULL devcontainer (tt-metal prebuilt)."
fi

# --- Advanced track (optional) --------------------------------------------
echo
echo "== Advanced track: QEMU + tt-kmd bring-up (labs 10-16, optional) =="
echo

for q in qemu-system-x86_64 qemu-system-aarch64; do
  if command -v "$q" >/dev/null 2>&1; then
    info "$q present: $("$q" --version | head -1)"
  else
    info "$q not found (only needed for the advanced track)"
  fi
done

if command -v qemu-system-x86_64 >/dev/null 2>&1 && \
   qemu-system-x86_64 -device help 2>&1 | grep -qi 'ttsim'; then
  info "the 'ttsim' PCI device is compiled into qemu-system-x86_64"
fi

bh_lib="$TTSIM_DIR/libttsim_bh${sfx}.so"
[[ -f "$bh_lib" ]] && info "$(basename "$bh_lib") present (Blackhole, lab 15)"

echo
if [[ "$FAILED" == 0 ]]; then
  if [[ "$METAL_BUILT" == 1 ]]; then
    printf '\033[1;32mPrimary-track checks passed.\033[0m tt-metal is ready — next: `ttlab 01` (elementwise intro).\n'
  else
    printf '\033[1;32mEnvironment OK (simulator present).\033[0m Next: `tt-sim setup`, then `ttlab 01`.\n'
  fi
else
  printf '\033[1;31mSome checks failed.\033[0m See labs/00-orientation/README.md troubleshooting.\n'
  exit 1
fi
echo
