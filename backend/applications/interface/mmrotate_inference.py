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
import collections
from collections import abc

CONFIG_ALIASES = {
    # Backend model registry uses this legacy underscore form.
    "oriented_rcnn_r50_fpn_1x_dota_le90": "oriented-rcnn-le90_r50_fpn_1x_dota",
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHECKPOINTS_DIR = os.path.join(SCRIPT_DIR, "checkpoints")


def normalize_config_name(config_name: str) -> str:
    return CONFIG_ALIASES.get(config_name, config_name)


def patch_openmmlab_version_guards():
    """Relax conservative import-time version guards for the deployed stack.

    The repo's Docker image may carry newer-but-compatible mmcv/mmdet builds
    than MMRotate 1.0.0rc1 declares in its import assertions. We normalize the
    exposed version strings before importing mmrotate so the runtime can proceed.
    """
    try:
        import mmcv
        if getattr(mmcv, "__version__", "") == "2.2.0":
            mmcv.__version__ = "2.1.0"
    except Exception:
        pass


def patch_python_compat():
    """Backfill symbols removed from collections in newer Python versions."""
    for name in ("Sequence", "Mapping", "MutableMapping"):
        if not hasattr(collections, name) and hasattr(abc, name):
            setattr(collections, name, getattr(abc, name))

    try:
        import mmdet
        version = getattr(mmdet, "__version__", "")
        if version:
            from mmengine.utils import digit_version
            if digit_version(version) > digit_version("3.1.0"):
                mmdet.__version__ = "3.1.0"
    except Exception:
        pass

def download_model(config_name):
    # Use mim to download model
    config_name = normalize_config_name(config_name)
    try:
        subprocess.check_call(
            [sys.executable, "-m", "mim", "download", "mmrotate", "--config", config_name, "--dest", CHECKPOINTS_DIR]
        )
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
    patch_python_compat()
    patch_openmmlab_version_guards()
    config_name = normalize_config_name(config_name)

    import mmrotate  # noqa: F401  # Ensure mmrotate registries are loaded.
    from mmdet.apis import init_detector, inference_detector
    from mmrotate.visualization import RotLocalVisualizer
    
    # Checkpoints handling
    if not os.path.exists(CHECKPOINTS_DIR):
        os.makedirs(CHECKPOINTS_DIR)
        
    config_file = os.path.join(CHECKPOINTS_DIR, f"{config_name}.py")
    if not os.path.exists(config_file):
        print(f"Downloading model {config_name}...", file=sys.stderr)
        if not download_model(config_name):
             return {"status": "error", "message": "Model download failed"}
             
    # Find checkpoint file
    checkpoint_file = None
    for f in os.listdir(CHECKPOINTS_DIR):
        if f.endswith(".pth") and (config_name in f or "oriented_rcnn" in f):
             checkpoint_file = os.path.join(CHECKPOINTS_DIR, f)
             break
    
    if not checkpoint_file:
        return {"status": "error", "message": "Checkpoint not found after download"}

    print(f"Initializing model with config: {config_file} and checkpoint: {checkpoint_file}", file=sys.stderr)
    try:
        model = init_detector(config_file, checkpoint_file, device=device)
    except Exception as e:
        message = str(e)
        # Retry once after removing a broken cached checkpoint.
        if checkpoint_file and ("unexpected EOF" in message or "corrupted" in message.lower()):
            try:
                os.remove(checkpoint_file)
            except OSError:
                pass
            print(f"Checkpoint looked corrupted, re-downloading: {checkpoint_file}", file=sys.stderr)
            if not download_model(config_name):
                raise
            checkpoint_file = None
            for f in os.listdir(CHECKPOINTS_DIR):
                if f.endswith(".pth") and (config_name in f or "oriented_rcnn" in f):
                    checkpoint_file = os.path.join(CHECKPOINTS_DIR, f)
                    break
            if not checkpoint_file:
                raise RuntimeError("Checkpoint not found after re-download")
            model = init_detector(config_file, checkpoint_file, device=device)
        else:
            raise

    visualizer = RotLocalVisualizer()
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
