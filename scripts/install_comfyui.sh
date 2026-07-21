#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -d ComfyUI ]; then
  git clone https://github.com/comfyanonymous/ComfyUI.git ComfyUI
fi

cd ComfyUI

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install -U pip

# Install PyTorch separately when the default resolver picks a CPU-only build.
# For CUDA 12.x, one common option is:
#   pip install --index-url https://download.pytorch.org/whl/cu124 torch torchvision torchaudio
pip install -r requirements.txt

mkdir -p models/checkpoints models/diffusion_models models/unet models/vae models/clip models/text_encoders models/upscale_models models/controlnet models/ipadapter models/loras

echo "ComfyUI installed in: $(pwd)"
echo "Put models under ComfyUI/models, then run: ../scripts/start_comfyui.sh"
