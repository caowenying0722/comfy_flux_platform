#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

FILE="${COMFYUI_DIR:-$PWD/ComfyUI}/comfy/clip_model.py"
UTILS_FILE="${COMFYUI_DIR:-$PWD/ComfyUI}/comfy/utils.py"

if [ ! -f "$FILE" ]; then
  echo "ComfyUI clip_model.py not found: $FILE"
  exit 1
fi

if [ ! -f "$UTILS_FILE" ]; then
  echo "ComfyUI utils.py not found: $UTILS_FILE"
  exit 1
fi

python3 - <<PY
from pathlib import Path
file = Path("$FILE")
text = file.read_text()
old = "torch.round(input_tokens).to(dtype=torch.int, device=x.device)"
new = "input_tokens.to(dtype=torch.int, device=x.device)"
if old in text:
    file.write_text(text.replace(old, new))
    print("patched:", file)
elif new in text:
    print("already patched:", file)
else:
    raise SystemExit("patch pattern not found: " + str(file))

utils_file = Path("$UTILS_FILE")
utils_text = utils_file.read_text()
old = "pl_sd = torch.load(ckpt, map_location=device, weights_only=True)"
new = """try:
                pl_sd = torch.load(ckpt, map_location=device, weights_only=True)
            except TypeError as exc:
                if "weights_only" not in str(exc):
                    raise
                pl_sd = torch.load(ckpt, map_location=device)"""
if old in utils_text:
    utils_file.write_text(utils_text.replace(old, new))
    print("patched:", utils_file)
elif "weights_only\" not in str(exc)" in utils_text:
    print("already patched:", utils_file)
else:
    raise SystemExit("patch pattern not found: " + str(utils_file))
PY
