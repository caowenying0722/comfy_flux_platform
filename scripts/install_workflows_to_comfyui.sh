#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMFYUI_DIR="${COMFYUI_DIR:-$PROJECT_DIR/ComfyUI}"
TARGET_DIR="$COMFYUI_DIR/user/default/workflows"

mkdir -p "$TARGET_DIR"

cp "$PROJECT_DIR/workflows/sdxl_base_img2img.json" "$TARGET_DIR/sdxl_base_img2img_api.json"
cp "$PROJECT_DIR/workflows/sd15_img2img.json" "$TARGET_DIR/sd15_img2img_api.json"
cp "$PROJECT_DIR/workflows/sdxl_base_img2img_ui.json" "$TARGET_DIR/sdxl_base_img2img_ui.json"

echo "Installed workflows:"
ls -lh \
  "$TARGET_DIR"/sdxl_base_img2img_api.json \
  "$TARGET_DIR"/sd15_img2img_api.json \
  "$TARGET_DIR"/sdxl_base_img2img_ui.json
