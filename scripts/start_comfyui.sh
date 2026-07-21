#!/usr/bin/env bash
set -euo pipefail
COMFYUI_DIR="${COMFYUI_DIR:-$PWD/ComfyUI}"
cd "$COMFYUI_DIR"
source .venv/bin/activate
python main.py --listen 0.0.0.0 --port "${COMFYUI_PORT:-8188}" --disable-auto-launch
