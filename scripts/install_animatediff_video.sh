#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMFYUI_DIR="${COMFYUI_DIR:-$PROJECT_DIR/ComfyUI}"
CUSTOM_NODES_DIR="$COMFYUI_DIR/custom_nodes"
ANIMATEDIFF_DIR="$CUSTOM_NODES_DIR/ComfyUI-AnimateDiff-Evolved"
ANIMATEDIFF_COMMIT="${ANIMATEDIFF_COMMIT:-13ed169}"
MOTION_MODEL_URL="${MOTION_MODEL_URL:-https://hf-mirror.com/guoyww/animatediff/resolve/main/mm_sd_v15_v2.ckpt}"
MOTION_MODEL_PATH="$COMFYUI_DIR/models/animatediff_models/mm_sd_v15_v2.ckpt"

mkdir -p "$CUSTOM_NODES_DIR" "$COMFYUI_DIR/models/animatediff_models"

if [ ! -d "$ANIMATEDIFF_DIR/.git" ]; then
  git clone https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved.git "$ANIMATEDIFF_DIR"
fi

cd "$ANIMATEDIFF_DIR"
if git cat-file -e "$ANIMATEDIFF_COMMIT^{commit}" 2>/dev/null; then
  git checkout "$ANIMATEDIFF_COMMIT"
else
  git fetch --all --prune
  git checkout "$ANIMATEDIFF_COMMIT"
fi

python3 - <<PY
from pathlib import Path

init_file = Path("$ANIMATEDIFF_DIR/__init__.py")
init_text = init_file.read_text()
shim = '''import torch
from collections import OrderedDict

if not hasattr(torch.nn.Sequential, "insert"):
    def _codex_torch112_sequential_insert(self, index, module):
        if not isinstance(module, torch.nn.Module):
            raise TypeError(f"{module!r} is not a Module subclass")
        modules = list(self._modules.items())
        if index < 0:
            index += len(modules)
        index = max(0, min(index, len(modules)))
        modules.insert(index, (str(index), module))
        self._modules = OrderedDict((str(i), item[1]) for i, item in enumerate(modules))
        return self
    torch.nn.Sequential.insert = _codex_torch112_sequential_insert

'''
if "_codex_torch112_sequential_insert" not in init_text:
    init_file.write_text(shim + init_text)
    print("patched torch Sequential.insert compatibility:", init_file)
else:
    print("already patched torch Sequential.insert compatibility:", init_file)

file = Path("$ANIMATEDIFF_DIR/animatediff/model_injection.py")
text = file.read_text()
old = """            if comfy.utils.get_attr(self.model, key).dtype not in [torch.float8_e5m2, torch.float8_e4m3fn]:
                break"""
new = """            float8_dtypes = [dtype for dtype in [getattr(torch, "float8_e5m2", None), getattr(torch, "float8_e4m3fn", None)] if dtype is not None]
            if not float8_dtypes or comfy.utils.get_attr(self.model, key).dtype not in float8_dtypes:
                break"""
if old in text:
    file.write_text(text.replace(old, new))
    print("patched torch float8 compatibility:", file)
elif "float8_dtypes = [dtype for dtype in" in text:
    print("already patched torch float8 compatibility:", file)
else:
    raise SystemExit("AnimateDiff float8 patch pattern not found: " + str(file))
PY

if [ ! -s "$MOTION_MODEL_PATH" ]; then
  curl -L --fail --retry 5 --retry-delay 5 -C - -o "$MOTION_MODEL_PATH" "$MOTION_MODEL_URL"
fi

echo "AnimateDiff plugin:"
git rev-parse --short HEAD
echo "Motion model:"
ls -lh "$MOTION_MODEL_PATH"
