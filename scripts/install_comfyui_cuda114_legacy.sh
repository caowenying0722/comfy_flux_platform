#!/usr/bin/env bash
set -euo pipefail

# Legacy runtime for hosts with NVIDIA driver 470.x / CUDA 11.4.
# This can make PyTorch CUDA visible, but current ComfyUI + Flux will not run
# because current ComfyUI depends on newer torch APIs.

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
  git clone https://github.com/comfyanonymous/ComfyUI.git "$tmp_dir/ComfyUI"
  cp -a "$tmp_dir/ComfyUI/." ComfyUI/
  rm -rf "$tmp_dir"
fi

cd ComfyUI
git fetch --depth 1 origin tag v0.3.20
git checkout -f v0.3.20
cd ..

miniconda/bin/python -m pip install -U pip setuptools wheel
miniconda/bin/python -m pip install "numpy>=1.25,<2"
miniconda/bin/python -m pip install \
  torch==1.12.1+cu113 \
  torchvision==0.13.1+cu113 \
  torchaudio==0.12.1 \
  --extra-index-url https://download.pytorch.org/whl/cu113

if command -v patchelf >/dev/null 2>&1; then
  patchelf --clear-execstack miniconda/lib/python3.10/site-packages/torch/lib/libtorch_cpu.so || true
fi

./scripts/patch_comfyui_torch112.sh

./scripts/diagnose_gpu_runtime.sh
