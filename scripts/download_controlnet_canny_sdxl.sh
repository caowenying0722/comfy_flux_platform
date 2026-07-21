#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

COMFYUI_DIR="${COMFYUI_DIR:-$PWD/ComfyUI}"
MIRROR_BASE="${MIRROR_BASE:-https://hf-mirror.com}"
MODEL_URL="${MIRROR_BASE}/diffusers/controlnet-canny-sdxl-1.0-small/resolve/main/diffusion_pytorch_model.safetensors?download=true"
TARGET="$COMFYUI_DIR/models/controlnet/controlnet-canny-sdxl-1.0-small.safetensors"

mkdir -p "$COMFYUI_DIR/models/controlnet"

if [ -f "$TARGET" ]; then
  echo "exists: $TARGET"
  ls -lh "$TARGET"
  exit 0
fi

df -h "$COMFYUI_DIR"
curl -L --fail --retry 10 --continue-at - "$MODEL_URL" -o "$TARGET"
ls -lh "$TARGET"
