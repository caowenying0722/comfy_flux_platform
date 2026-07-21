#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

COMFYUI_DIR="${COMFYUI_DIR:-$PWD/ComfyUI}"
VARIANT="${1:-flux2-dev-fp8}"
MIN_FREE_GB="${MIN_FREE_GB:-50}"

if [ ! -d "$COMFYUI_DIR" ]; then
  echo "ComfyUI directory not found: $COMFYUI_DIR"
  echo "Run ./scripts/install_comfyui.sh first."
  exit 1
fi

mkdir -p \
  "$COMFYUI_DIR/models/text_encoders" \
  "$COMFYUI_DIR/models/diffusion_models" \
  "$COMFYUI_DIR/models/vae" \
  "$COMFYUI_DIR/models/loras" \
  "$COMFYUI_DIR/user/default/workflows"

available_gb="$(df -BG "$COMFYUI_DIR" | awk 'NR==2 {gsub("G","",$4); print $4}')"
if [ "${available_gb:-0}" -lt "$MIN_FREE_GB" ]; then
  echo "Not enough free disk space under $COMFYUI_DIR: ${available_gb}G available, ${MIN_FREE_GB}G required."
  echo "Set MIN_FREE_GB to a lower value only if you accept the risk of filling the disk."
  exit 2
fi

download() {
  local url="$1"
  local target="$2"
  if [ -f "$target" ]; then
    echo "exists: $target"
    return
  fi

  echo "download: $url"
  if [ -n "${HF_TOKEN:-}" ]; then
    curl -L --fail --retry 3 -H "Authorization: Bearer ${HF_TOKEN}" "$url" -o "$target"
  else
    curl -L --fail --retry 3 "$url" -o "$target"
  fi
}

case "$VARIANT" in
  flux2-dev-fp8)
    download "https://huggingface.co/Comfy-Org/flux2-dev/resolve/main/split_files/text_encoders/mistral_3_small_flux2_fp8.safetensors" \
      "$COMFYUI_DIR/models/text_encoders/mistral_3_small_flux2_fp8.safetensors"
    download "https://huggingface.co/Comfy-Org/flux2-dev/resolve/main/split_files/diffusion_models/flux2_dev_fp8mixed.safetensors" \
      "$COMFYUI_DIR/models/diffusion_models/flux2_dev_fp8mixed.safetensors"
    download "https://huggingface.co/Comfy-Org/flux2-dev/resolve/main/split_files/vae/flux2-vae.safetensors" \
      "$COMFYUI_DIR/models/vae/flux2-vae.safetensors"
    download "https://huggingface.co/Comfy-Org/flux2-dev/resolve/main/split_files/loras/Flux2TurboComfyv2.safetensors" \
      "$COMFYUI_DIR/models/loras/Flux2TurboComfyv2.safetensors"
    download "https://raw.githubusercontent.com/Comfy-Org/workflow_templates/refs/heads/main/templates/image_flux2_fp8.json" \
      "$COMFYUI_DIR/user/default/workflows/image_flux2_fp8.json"
    ;;
  *)
    echo "Unsupported variant: $VARIANT"
    echo "Supported: flux2-dev-fp8"
    exit 1
    ;;
esac

echo "Flux2 assets are ready for ComfyUI variant: $VARIANT"
echo "Open ComfyUI, load user/default/workflows/image_flux2_fp8.json, verify it runs, then export API format workflow into this project's workflows/ directory."
