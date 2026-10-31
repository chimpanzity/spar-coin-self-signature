#!/usr/bin/env bash
# GPU host setup for SPAR_DICE_LOGPROB_CROSSMODEL_v2.0 (vast.ai image pytorch/pytorch:2.7.1-cuda12.8-cudnn9-runtime).
# The same pins that reproduced Experiments 21/26 bit for bit in Experiment 27. Run from the deployed repo root (/root/spar).
set -euo pipefail
pip install -q torch==2.11.0 --index-url https://download.pytorch.org/whl/cu128
pip install -q transformers==5.22.0 accelerate==1.15.0 huggingface_hub==2.4.0 mistral_common==1.13.0 hf_xet
pip uninstall -y torchvision torchaudio || true      # the image's torchvision breaks transformers model imports
PYTHONPATH=src python - <<'EOF'
import time
from huggingface_hub import snapshot_download
from spar_dynamic.dice_crossed_guidance import config as C
t = time.time()
q, m = C.MODEL["qwen"], C.MODEL["mistral"]
snapshot_download(q["model_id"], revision=q["revision"], max_workers=16)
snapshot_download(m["model_id"], revision=m["revision"], allow_patterns=C.MISTRAL_DOWNLOAD, max_workers=16)
print(f"downloaded both models in {time.time() - t:.0f} s")
EOF
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv
python -c "import torch, transformers, mistral_common; print(torch.__version__, torch.version.cuda, transformers.__version__, mistral_common.__version__)"
