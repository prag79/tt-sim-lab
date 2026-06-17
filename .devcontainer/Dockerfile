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
RUN useradd -m -s /bin/bash -G sudo,kvm student && \
    echo "student ALL=(ALL) NOPASSWD:ALL" >/etc/sudoers.d/student && \
    mkdir -p /home/student/work && chown -R student:student /home/student

# Lab content + helpers (kept at the repo root so they're easy to edit and
# review without touching the Dockerfile).
COPY --chown=student:student labs/ /labs/
COPY ttlab          /usr/local/bin/ttlab
COPY tt-guest       /usr/local/bin/tt-guest
COPY entrypoint.sh  /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/ttlab /usr/local/bin/tt-guest /usr/local/bin/entrypoint.sh

USER student
WORKDIR /home/student/work

# 2222: SSH into the guest VM (QEMU user-net hostfwd).
EXPOSE 2222
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["sleep", "infinity"]
