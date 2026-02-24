#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MMRotate Inference Script

此脚本在 MMSeg310 环境中运行，使用 MMRotate 进行旋转目标检测推理。
"""

import argparse
import json
import os
import sys
import subprocess
import traceback
import cv2
import numpy as np

def download_model(config_name):
    # Use mim to download model
    try:
        subprocess.check_call(["mim", "download", "mmrotate", "--config", config_name, "--dest", "checkpoints"])
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to download model: {e}", file=sys.stderr)
        return False

def run_inference(
    config_name: str,
    input_dir: str,
    output_dir: str,
    file_names: list,
    device: str = "cuda:0",
    score_thr: float = 0.3
) -> dict:
    from mmrotate.apis import init_model, inference_detector
    from mmrotate.registry import VISUALIZERS
    
    # Checkpoints handling
    if not os.path.exists("checkpoints"):
        os.makedirs("checkpoints")
        
    config_file = f"checkpoints/{config_name}.py"
    if not os.path.exists(config_file):
        print(f"Downloading model {config_name}...", file=sys.stderr)
        if not download_model(config_name):
             return {"status": "error", "message": "Model download failed"}
             
    # Find checkpoint file
    checkpoint_file = None
    for f in os.listdir("checkpoints"):
        if f.endswith(".pth") and (config_name in f or "oriented_rcnn" in f):
             checkpoint_file = os.path.join("checkpoints", f)
             break
    
    if not checkpoint_file:
        return {"status": "error", "message": "Checkpoint not found after download"}

    print(f"Initializing model with config: {config_file} and checkpoint: {checkpoint_file}", file=sys.stderr)
    model = init_model(config_file, checkpoint_file, device=device)
    
    visualizer = VISUALIZERS.build(model.cfg.visualizer)
    visualizer.dataset_meta = model.dataset_meta
    
    os.makedirs(output_dir, exist_ok=True)
    results = []
    
    for filename in file_names:
        try:
            img_path = os.path.join(input_dir, filename)
            if not os.path.exists(img_path):
                results.append({"name": filename, "status": "error", "message": "File not found"})
                continue
                
            result = inference_detector(model, img_path)
            
            img = cv2.imread(img_path)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            out_name = f"det_{filename}"
            out_path = os.path.join(output_dir, out_name)
            
            visualizer.add_datasample(
                'result',
                img,
                data_sample=result,
                draw_gt=False,
                show=False,
                out_file=out_path,
                pred_score_thr=score_thr
            )
            
            results.append({
                "name": out_name,
                "status": "success",
                "output_path": out_path
            })
            print(f"Processed {filename} -> {out_name}", file=sys.stderr)
            
        except Exception as e:
            print(f"Error processing {filename}: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            results.append({"name": filename, "status": "error", "message": str(e)})
            
    return {
        "status": "completed",
        "results": results
    }

def main():
    parser = argparse.ArgumentParser(description="MMRotate Inference")
    parser.add_argument("--config", default='oriented_rcnn_r50_fpn_1x_dota_le90', help="Model config name")
    parser.add_argument("--input_dir", required=True, help="Input directory")
    parser.add_argument("--output_dir", required=True, help="Output directory")
    parser.add_argument("--file_names", required=True, help="Comma-separated file names")
    parser.add_argument("--device", default="cuda:0", help="Device")
    parser.add_argument("--score_thr", type=float, default=0.3, help="Score threshold")
    
    args = parser.parse_args()
    
    file_names = [f.strip() for f in args.file_names.split(",") if f.strip()]
    
    try:
        result = run_inference(
            config_name=args.config,
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            file_names=file_names,
            device=args.device,
            score_thr=args.score_thr
        )
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()
