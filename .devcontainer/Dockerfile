# syntax=docker/dockerfile:1.7
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    LAB_HOME=/labs \
    TTSIM_DIR=/opt/ttsim \
    QEMU_PREFIX=/opt/qemu

# Build deps for QEMU + the ttsim PCI device, plus guest-image tooling.
# IMPORTANT: never put `# comments` mid-line inside a `\`-continued RUN.
# A `#` consumes the trailing `\` and silently breaks line continuation;
# the next "line" then runs as a separate shell command.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential git ninja-build meson pkg-config \
        python3 python3-venv python3-pip python3-tomli python3-setuptools \
        libglib2.0-dev libpixman-1-dev libslirp-dev \
        zlib1g-dev libfdt-dev flex bison \
        cloud-image-utils genisoimage qemu-utils \
        wget curl ca-certificates sudo nano less file unzip xz-utils \
        openssh-client netcat lsof procps \
 && rm -rf /var/lib/apt/lists/*

# --- Build the Tenstorrent ttsim QEMU fork (single patch on upstream stable-11.0).
# x86_64 + aarch64 system targets are the two the ttsim device is wired up for.
# --enable-slirp gives the guest user-mode networking (so it can apt-install
# kernel headers and `git clone` tt-kmd, exactly as the upstream README expects).
ARG QEMU_BRANCH=stable-11.0-ttsim
RUN git clone --depth 1 -b "${QEMU_BRANCH}" \
        https://github.com/tenstorrent/ttsim-qemu /tmp/ttsim-qemu && \
    cd /tmp/ttsim-qemu && \
    ./configure --prefix="${QEMU_PREFIX}" \
        --target-list=x86_64-softmmu,aarch64-softmmu \
        --enable-slirp --disable-docs --disable-werror && \
    make -j"$(nproc)" && make install && \
    rm -rf /tmp/ttsim-qemu
ENV PATH="${QEMU_PREFIX}/bin:${PATH}"

# --- Fetch the prebuilt libttsim shared objects (virtual PCIe devices).
# Wormhole + Blackhole, both host arches; the QEMU device dlopen's one of
# these at realize time. Pin a known-good release.
ARG TTSIM_VERSION=v1.8.5
RUN mkdir -p "${TTSIM_DIR}" && cd "${TTSIM_DIR}" && \
    base="https://github.com/tenstorrent/ttsim/releases/download/${TTSIM_VERSION}" && \
    for f in libttsim_wh.so libttsim_bh.so \
             libttsim_wh_aarch64.so libttsim_bh_aarch64.so; do \
      wget -q "${base}/${f}" -O "${f}"; \
    done

# Non-root user with sudo (matches devcontainer.json's remoteUser).
RUN groupadd -f kvm && \
    useradd -m -s /bin/bash -G sudo,kvm student && \
    echo "student ALL=(ALL) NOPASSWD:ALL" >/etc/sudoers.d/student && \
    mkdir -p /home/student/work && chown -R student:student /home/student

# Lab content + helpers (kept at the repo root so they're easy to edit and
# review without touching the Dockerfile).
COPY --chown=student:student labs/ /labs/
COPY ttlab          /usr/local/bin/ttlab
COPY tt-guest       /usr/local/bin/tt-guest
COPY tt-sim         /usr/local/bin/tt-sim
COPY entrypoint.sh  /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/ttlab /usr/local/bin/tt-guest \
             /usr/local/bin/tt-sim /usr/local/bin/entrypoint.sh

# --- (optional) prebuild tt-metal for the primary kernel track -------------
# The primary labs (01-03) run tt-metal against the virtual chip via the
# library-direct flow. tt-metal itself is large to BUILD (tens of GB, long
# compile) though light to RUN. Baking it in gives students a zero-setup
# start, but it bloats the image well past a free Codespace's storage quota
# and likely exceeds a GitHub-hosted runner's disk. So it is OFF by default:
#
#   * PREBUILD_TT_METAL=0 (default): the image ships WITHOUT tt-metal. On
#     first use, `tt-sim setup` clones+builds it into ~/work/tt-metal (which
#     persists across Codespace stop/start). Best for free Codespaces.
#   * PREBUILD_TT_METAL=1: clone+build tt-metal into /opt/tt-metal at image
#     build time. Only enable on a builder with ample disk (a large self-
#     hosted runner); the result is a "tt-metal already set up" image.
#
# Either way `tt-sim` finds the tree automatically (see its resolve order).
ARG PREBUILD_TT_METAL=0
ARG TT_METAL_REF=5a4436244ae1b421504da84c01f81fdfdf6049de
RUN if [ "$PREBUILD_TT_METAL" = "1" ]; then \
        set -eux; \
        git clone https://github.com/tenstorrent/tt-metal /opt/tt-metal; \
        cd /opt/tt-metal; \
        git checkout "${TT_METAL_REF}"; \
        git submodule update --init --recursive; \
        [ -x ./install_dependencies.sh ] && ./install_dependencies.sh || true; \
        TT_METAL_HOME=/opt/tt-metal ./build_metal.sh --build-programming-examples; \
        cp tt_metal/soc_descriptors/wormhole_b0_80_arch.yaml \
           "${TTSIM_DIR}/soc_descriptor.yaml"; \
        chown -R student:student /opt/tt-metal; \
    else \
        echo "Skipping tt-metal prebuild; students run 'tt-sim setup' on first use."; \
    fi

USER student
WORKDIR /home/student/work

# 2222: SSH into the guest VM (QEMU user-net hostfwd).
EXPOSE 2222
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["sleep", "infinity"]
