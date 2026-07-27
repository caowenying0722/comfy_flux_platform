#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMFYUI_DIR="${COMFYUI_DIR:-$PROJECT_DIR/ComfyUI}"

mkdir -p "$COMFYUI_DIR/custom_nodes"

if [ -d "$PROJECT_DIR/custom_nodes/comfy_flux_video_nodes" ]; then
  rm -rf "$COMFYUI_DIR/custom_nodes/comfy_flux_video_nodes"
  cp -r "$PROJECT_DIR/custom_nodes/comfy_flux_video_nodes" "$COMFYUI_DIR/custom_nodes/comfy_flux_video_nodes"
fi

echo "Installed custom nodes:"
ls -lh "$COMFYUI_DIR/custom_nodes/comfy_flux_video_nodes"
