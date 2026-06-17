#!/usr/bin/env bash
# /usr/local/bin/entrypoint.sh - environment setup for the ttsim-qemu lab.
#
# Unlike a GUI simulator, ttsim-qemu is entirely terminal/serial-based, so
# there is no virtual desktop to bring up here. This script just makes the
# QEMU and ttsim paths discoverable and is otherwise a no-op.
#
# Idempotent: safe to run multiple times. Used as both the Docker ENTRYPOINT
# (for local `docker run` testing) and as the Codespaces `postStartCommand`
# (Codespaces does not always invoke the Dockerfile ENTRYPOINT).

set -e

PROFILE_SNIPPET='/etc/profile.d/ttsim-lab.sh'

# Make qemu-system-* visible on PATH for interactive shells. Written once.
if [[ ! -f "$PROFILE_SNIPPET" ]]; then
  sudo tee "$PROFILE_SNIPPET" >/dev/null <<'EOF'
export QEMU_PREFIX="${QEMU_PREFIX:-/opt/qemu}"
export TTSIM_DIR="${TTSIM_DIR:-/opt/ttsim}"
export PATH="$QEMU_PREFIX/bin:$PATH"
EOF
fi

# When invoked as the Docker ENTRYPOINT, exec the container CMD.
# When invoked as a Codespaces postStartCommand with `true`, exits cleanly.
exec "$@"
