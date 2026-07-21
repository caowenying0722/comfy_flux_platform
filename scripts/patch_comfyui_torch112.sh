#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

FILE="${COMFYUI_DIR:-$PWD/ComfyUI}/comfy/clip_model.py"

if [ ! -f "$FILE" ]; then
  echo "ComfyUI clip_model.py not found: $FILE"
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
PY
