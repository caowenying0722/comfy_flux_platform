#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "== GPU =="
nvidia-smi || true

echo
echo "== System Python =="
python3 --version || true
which python3 || true

echo
echo "== Project Python =="
if [ -x miniconda/bin/python ]; then
  miniconda/bin/python --version
  miniconda/bin/python - <<'PY'
try:
    import torch
    print("torch", torch.__version__)
    print("torch_cuda", torch.version.cuda)
    print("cuda_available", torch.cuda.is_available())
    print("device_count", torch.cuda.device_count())
    if torch.cuda.is_available():
        print("device0", torch.cuda.get_device_name(0))
except Exception as exc:
    print("torch_error", repr(exc))
PY
else
  echo "miniconda not installed"
fi

echo
echo "== Disk =="
df -h .
