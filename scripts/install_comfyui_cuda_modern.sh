#!/usr/bin/env bash
set -euo pipefail

# Recommended runtime after upgrading the host NVIDIA driver to 535+.
# This is the target path for current ComfyUI + Flux/Flux2.

cd "$(dirname "$0")/.."

if [ ! -x miniconda/bin/python ]; then
  curl -L --fail --retry 5 --connect-timeout 30 --max-time 600 \
    https://repo.anaconda.com/miniconda/Miniconda3-py310_25.5.1-0-Linux-x86_64.sh \
    -o /tmp/miniconda_py310.sh
  bash /tmp/miniconda_py310.sh -b -p "$PWD/miniconda"
fi

if [ ! -f ComfyUI/main.py ]; then
  mkdir -p ComfyUI
  tmp_dir="$(mktemp -d)"
  git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git "$tmp_dir/ComfyUI"
  cp -a "$tmp_dir/ComfyUI/." ComfyUI/
  rm -rf "$tmp_dir"
fi

miniconda/bin/python -m pip install -U pip setuptools wheel

# Current ComfyUI requires modern torch APIs. CUDA 12.1 wheels require a modern
# host driver; use NVIDIA 535+ for this path.
miniconda/bin/python -m pip install --index-url https://download.pytorch.org/whl/cu121 \
  torch torchvision torchaudio

miniconda/bin/python -m pip install -r ComfyUI/requirements.txt

./scripts/diagnose_gpu_runtime.sh
