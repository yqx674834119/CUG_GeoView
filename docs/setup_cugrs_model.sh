#!/bin/bash
# CUGRS Model Setup Script
# Downloads and configures the MMSegmentation CUGRS model for land cover classification

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_DIR="${SCRIPT_DIR}/../backend/model/mmseg_config"

echo "=== CUGRS Model Setup ==="
echo "Model Directory: ${MODEL_DIR}"

# Create model directory
mkdir -p "${MODEL_DIR}"

# Check if files already exist
if [ -f "${MODEL_DIR}/model.pth" ] && [ -f "${MODEL_DIR}/dinov3_swinV1.py" ]; then
    echo "Model files already exist. Skipping download."
    exit 0
fi

# Check for huggingface_hub
if ! python -c "import huggingface_hub" 2>/dev/null; then
    echo "Installing huggingface_hub..."
    pip install huggingface_hub
fi

echo "Downloading CUGRS model from HuggingFace (cc-ln/CUGRS)..."
echo "This may take a while (~5.93GB checkpoint file)..."

python << 'EOF'
import os
from huggingface_hub import hf_hub_download

model_dir = os.environ.get('MODEL_DIR', 'backend/model/mmseg_config')
os.makedirs(model_dir, exist_ok=True)

print("Downloading config file...")
config_path = hf_hub_download(
    repo_id='cc-ln/CUGRS',
    filename='dinov3_swinV1-Copy1.py',
    local_dir=model_dir,
    local_dir_use_symlinks=False
)

print("Downloading checkpoint file (~5.93GB)...")
checkpoint_path = hf_hub_download(
    repo_id='cc-ln/CUGRS',
    filename='epoch_89-Copy1.pth',
    local_dir=model_dir,
    local_dir_use_symlinks=False
)

# Rename files to standard names
import shutil
config_final = os.path.join(model_dir, 'dinov3_swinV1.py')
checkpoint_final = os.path.join(model_dir, 'model.pth')

if os.path.exists(os.path.join(model_dir, 'dinov3_swinV1-Copy1.py')):
    shutil.move(os.path.join(model_dir, 'dinov3_swinV1-Copy1.py'), config_final)
    print(f"Config saved to: {config_final}")

if os.path.exists(os.path.join(model_dir, 'epoch_89-Copy1.pth')):
    shutil.move(os.path.join(model_dir, 'epoch_89-Copy1.pth'), checkpoint_final)
    print(f"Checkpoint saved to: {checkpoint_final}")

print("Download complete!")
EOF

echo ""
echo "=== Setup Complete ==="
echo "Model files saved to: ${MODEL_DIR}"
echo "  - dinov3_swinV1.py (config)"
echo "  - model.pth (checkpoint)"
