#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

COMFYUI_DIR="${COMFYUI_DIR:-$PWD/ComfyUI}"
CUSTOM_NODE_DIR="$COMFYUI_DIR/custom_nodes/comfyui_controlnet_aux"

if [ ! -d "$CUSTOM_NODE_DIR" ]; then
  git clone https://github.com/Fannovel16/comfyui_controlnet_aux.git "$CUSTOM_NODE_DIR"
else
  git -C "$CUSTOM_NODE_DIR" pull --ff-only || true
fi

"$PWD/miniconda/bin/python" -m pip install -r "$CUSTOM_NODE_DIR/requirements.txt"
"$PWD/miniconda/bin/python" -m pip install --force-reinstall "numpy==1.26.4"
"$PWD/miniconda/bin/python" -m pip install --force-reinstall --no-deps \
  "opencv-python==4.9.0.80" \
  "opencv-python-headless==4.9.0.80" \
  "opencv-contrib-python==4.9.0.80"
