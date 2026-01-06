#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HuggingFace Super-Resolution Inference Script

此脚本需要在 HFPyTorch310 conda 环境中运行。
用于处理 HuggingFace Hub 上的超分辨率模型推理。

用法:
    conda run -n HFPyTorch310 python hf_super_resolution.py \
        --model_id caidas/swin2SR-classical-sr-x2-64 \
        --input_dir /path/to/inputs \
        --output_dir /path/to/outputs \
        --file_names image1.png,image2.png

支持的模型:
    - caidas/swin2SR-classical-sr-x2-64 (2x upscale)
    - caidas/swin2SR-classical-sr-x4-64 (4x upscale)
    - 其他兼容 Swin2SRForImageSuperResolution 的模型
"""

import argparse
import json
import os
import sys
import time
import traceback
from datetime import datetime


def log(msg: str, level: str = "INFO"):
    """统一日志格式"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] [HF-SR] {msg}", file=sys.stderr, flush=True)


def check_environment():
    """检查运行环境"""
    log("=== Environment Check ===")
    log(f"Python version: {sys.version}")
    log(f"Python executable: {sys.executable}")
    
    # Check HuggingFace mirror
    hf_endpoint = os.environ.get("HF_ENDPOINT", "https://huggingface.co")
    log(f"HF_ENDPOINT: {hf_endpoint}")
    
    try:
        import torch
        log(f"PyTorch version: {torch.__version__}")
        log(f"CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            log(f"CUDA version: {torch.version.cuda}")
            log(f"GPU count: {torch.cuda.device_count()}")
            for i in range(torch.cuda.device_count()):
                log(f"GPU {i}: {torch.cuda.get_device_name(i)}")
        else:
            log("WARNING: CUDA not available, will use CPU", level="WARN")
    except Exception as e:
        log(f"Error checking PyTorch: {e}", level="ERROR")
    
    try:
        import transformers
        log(f"Transformers version: {transformers.__version__}")
    except Exception as e:
        log(f"Error checking transformers: {e}", level="ERROR")
    
    try:
        import numpy as np
        log(f"NumPy version: {np.__version__}")
    except Exception as e:
        log(f"Error checking NumPy: {e}", level="ERROR")
    
    log("=== Environment Check Complete ===")


def load_model(model_id: str, device: str):
    """加载 HuggingFace 超分模型和处理器"""
    from transformers import Swin2SRForImageSuperResolution, Swin2SRImageProcessor
    import torch
    
    log(f"Loading model: {model_id}")
    log(f"Target device: {device}")
    
    start_time = time.time()
    
    log("Loading image processor...")
    processor = Swin2SRImageProcessor.from_pretrained(model_id)
    log(f"Image processor loaded in {time.time() - start_time:.2f}s")
    
    load_start = time.time()
    log("Loading model weights (this may take a while on first run)...")
    model = Swin2SRForImageSuperResolution.from_pretrained(model_id)
    log(f"Model weights loaded in {time.time() - load_start:.2f}s")
    
    move_start = time.time()
    log(f"Moving model to {device}...")
    model = model.to(device).eval()
    log(f"Model moved to {device} in {time.time() - move_start:.2f}s")
    
    log(f"Total model load time: {time.time() - start_time:.2f}s")
    return processor, model


def process_image(image_path: str, processor, model, device: str):
    """处理单张图片进行超分辨率"""
    import torch
    import numpy as np
    from PIL import Image
    
    log(f"Processing image: {image_path}")
    
    # 加载图片
    load_start = time.time()
    image = Image.open(image_path).convert("RGB")
    log(f"Image loaded: {image.size} in {time.time() - load_start:.2f}s")
    
    # 预处理
    preprocess_start = time.time()
    inputs = processor(image, return_tensors="pt").to(device)
    log(f"Preprocessing done in {time.time() - preprocess_start:.2f}s")
    
    # 推理
    inference_start = time.time()
    log("Running inference...")
    with torch.no_grad():
        outputs = model(**inputs)
    log(f"Inference done in {time.time() - inference_start:.2f}s")
    
    # 后处理
    postprocess_start = time.time()
    output = outputs.reconstruction.squeeze().cpu()
    output = output.clamp(0, 1)
    output = output.permute(1, 2, 0).numpy()  # CHW -> HWC
    output = (output * 255).astype(np.uint8)
    log(f"Postprocessing done in {time.time() - postprocess_start:.2f}s, output shape: {output.shape}")
    
    return output


def main():
    parser = argparse.ArgumentParser(description="HuggingFace Super-Resolution Inference")
    parser.add_argument("--model_id", type=str, required=True,
                        help="HuggingFace model ID, e.g., caidas/swin2SR-classical-sr-x2-64")
    parser.add_argument("--input_dir", type=str, required=True,
                        help="Directory containing input images")
    parser.add_argument("--output_dir", type=str, required=True,
                        help="Directory to save output images")
    parser.add_argument("--file_names", type=str, required=True,
                        help="Comma-separated list of file names to process")
    parser.add_argument("--device", type=str, default="cuda",
                        help="Device to use: 'cuda' or 'cpu' (default: cuda)")
    args = parser.parse_args()
    
    log("=== HuggingFace Super-Resolution Script Started ===")
    log(f"Arguments: model_id={args.model_id}, input_dir={args.input_dir}, output_dir={args.output_dir}")
    log(f"File names: {args.file_names}")
    log(f"Device: {args.device}")
    
    # 检查环境
    check_environment()
    
    # 确定设备
    import torch
    if args.device == "cuda":
        if not torch.cuda.is_available():
            log("CUDA requested but not available, falling back to CPU", level="WARN")
            device = "cpu"
        else:
            device = "cuda"
    else:
        device = args.device
    
    log(f"Using device: {device}")
    
    # 解析文件名列表
    file_names = [f.strip() for f in args.file_names.split(",") if f.strip()]
    log(f"Files to process: {len(file_names)}")
    
    # 确保输出目录存在
    os.makedirs(args.output_dir, exist_ok=True)
    log(f"Output directory: {args.output_dir}")
    
    try:
        # 加载模型
        processor, model = load_model(args.model_id, device)
    except Exception as e:
        log(f"Failed to load model: {e}", level="ERROR")
        log(traceback.format_exc(), level="ERROR")
        print(json.dumps({"status": "error", "message": f"Model load failed: {str(e)}"}))
        sys.exit(1)
    
    # 处理每张图片
    results = []
    total_start = time.time()
    
    for i, name in enumerate(file_names):
        log(f"Processing file {i+1}/{len(file_names)}: {name}")
        input_path = os.path.join(args.input_dir, name)
        output_path = os.path.join(args.output_dir, name)
        
        if not os.path.exists(input_path):
            log(f"Input file not found: {input_path}", level="ERROR")
            results.append({"name": name, "status": "error", "message": "File not found"})
            continue
        
        try:
            from PIL import Image
            output_array = process_image(input_path, processor, model, device)
            Image.fromarray(output_array).save(output_path)
            results.append({"name": name, "status": "success", "output_path": output_path})
            log(f"Saved: {output_path}")
        except Exception as e:
            log(f"Error processing {name}: {e}", level="ERROR")
            log(traceback.format_exc(), level="ERROR")
            results.append({"name": name, "status": "error", "message": str(e)})
    
    total_time = time.time() - total_start
    log(f"=== Processing Complete ===")
    log(f"Total time: {total_time:.2f}s for {len(file_names)} images")
    if file_names:
        log(f"Average: {total_time/len(file_names):.2f}s per image")
    
    # 输出 JSON 结果到 stdout (便于 subprocess 解析)
    print(json.dumps({"status": "completed", "results": results}))


if __name__ == "__main__":
    main()
