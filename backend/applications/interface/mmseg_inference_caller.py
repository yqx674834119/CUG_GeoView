#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MMSegmentation Inference Caller

此模块在 PaddleRS37 环境中运行，通过 subprocess 调用 MMSeg310 环境中的
MMSegmentation 推理脚本，实现环境隔离。
"""

import json
import os
import os.path as osp
import subprocess
import sys
from typing import List

from applications.common.path_global import generate_url

# MMSegmentation conda 环境名称
MMSEG_CONDA_ENV = "MMSeg310"

# MMSegmentation 推理脚本路径
_curr_dir = os.path.dirname(os.path.abspath(__file__))
MMSEG_SCRIPT = os.path.join(_curr_dir, "mmseg_segmentation.py")

# 模型配置 - CUGRS 模型
CUGRS_CONFIG = {
    "model_id": "cc-ln/CUGRS",
    "config_path": os.path.join(_curr_dir, "..", "..", "model", "mmseg_config", "dinov3_swinV1.py"),
    "checkpoint_path": os.path.join(_curr_dir, "..", "..", "model", "mmseg_config", "model.pth"),
}


def get_model_paths(model_id: str) -> tuple:
    """
    根据模型 ID 获取配置文件和权重文件路径
    
    Args:
        model_id: 模型 ID，如 "cc-ln/CUGRS"
    
    Returns:
        (config_path, checkpoint_path)
    """
    if model_id == "cc-ln/CUGRS":
        config = os.path.abspath(CUGRS_CONFIG["config_path"])
        checkpoint = os.path.abspath(CUGRS_CONFIG["checkpoint_path"])
        return config, checkpoint
    else:
        raise ValueError(f"Unknown MMSeg model: {model_id}")


def call_mmseg_inference(
    model_id: str,
    data_path: str,
    out_dir: str,
    names: List[str],
    device: str = "cuda:0",
    timeout: int = 1200
) -> List[str]:
    """
    调用 MMSegmentation 模型进行语义分割推理
    
    :param model_id: 模型 ID, 如 "cc-ln/CUGRS"
    :param data_path: 输入图片文件夹路径
    :param out_dir: 结果保存路径
    :param names: 待处理文件名列表
    :param device: 设备选择
    :param timeout: 超时时间（秒）
    :return: 生成的图片 URL 列表
    """
    if not names:
        return []
    
    # 获取模型路径
    config_path, checkpoint_path = get_model_paths(model_id)
    
    # 检查模型文件是否存在
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    if not os.path.exists(checkpoint_path):
        raise FileNotFoundError(f"Checkpoint file not found: {checkpoint_path}")
    
    # 构建命令
    # 转换相对路径为绝对路径
    abs_data_path = os.path.abspath(data_path)
    abs_out_dir = os.path.abspath(out_dir)
    file_names_str = ",".join(names)

    # 动态检查 Python 解释器路径
    candidate_paths = [
        "/opt/conda/envs/MMSeg310/bin/python",              # Default Docker path
        "/home/livablecity/miniconda3/envs/MMSeg310/bin/python", # Dev environment path
    ]
    
    python_executable = None
    for path in candidate_paths:
        if os.path.exists(path):
            python_executable = path
            break
            
    # 如果找不到特定路径，回退到 conda run (虽然可能在某些 Docker 中有问题，但作为最后的 fallback)
    if python_executable:
        cmd = [
            python_executable, MMSEG_SCRIPT,
            "--config", config_path,
            "--checkpoint", checkpoint_path,
            "--input_dir", abs_data_path,
            "--output_dir", abs_out_dir,
            "--file_names", file_names_str,
            "--device", device
        ]
    else:
        print(f"[MMSeg-Caller] Warning: MMSeg310 python executable not found in candidates, falling back to 'conda run'", file=sys.stderr)
        cmd = [
            "conda", "run", "-n", MMSEG_CONDA_ENV,
            "python", MMSEG_SCRIPT,
            "--config", config_path,
            "--checkpoint", checkpoint_path,
            "--input_dir", abs_data_path,
            "--output_dir", abs_out_dir,
            "--file_names", file_names_str,
            "--device", device
        ]
    
    print(f"[MMSeg-Caller] Executing: {' '.join(cmd)}", flush=True)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=_curr_dir
        )
        
        if result.returncode != 0:
            print(f"[MMSeg-Caller] Error output: {result.stderr}", file=sys.stderr)
            raise RuntimeError(f"MMSegmentation inference failed: {result.stderr}")
        
        # Parse JSON output (robustly find the JSON line)
        output_data = None
        stdout_lines = result.stdout.strip().split('\n')
        for line in reversed(stdout_lines):
            try:
                if line.strip().startswith('{') and '"status": "completed"' in line:
                    output_data = json.loads(line)
                    break
            except json.JSONDecodeError:
                continue
        
        if output_data is None:
             raise RuntimeError(f"Could not find valid JSON output in stdout: {result.stdout}")
        
        if output_data.get("status") != "completed":
            raise RuntimeError(f"Inference incomplete: {output_data}")
        
        # 生成结果 URL 列表
        temps = []
        # Create map keyed by output filename (which is what res["name"] is)
        result_map = {res["name"]: res for res in output_data.get("results", [])}
        
        for name in names:
            # Construct expected output filename: pred_{basename_without_ext}.png
            # Note: mmseg_segmentation.py uses os.path.splitext(filename)[0]
            base_name = os.path.splitext(name)[0]
            expected_out_name = f"pred_{base_name}.png"
            
            res = result_map.get(expected_out_name)
            if not res:
                # Fallback: check if the name itself is in the map (unlikely based on script logic)
                res = result_map.get(name)
            
            if not res:
                # Debug print to help identify mismatch
                print(f"[MMSeg-Caller] available results: {list(result_map.keys())}", file=sys.stderr)
                # Try to fuzzy match or just fail
                raise RuntimeError(f"No result returned for file: {name} (expected {expected_out_name})")
            
            if res.get("status") == "success":
                temps.append(generate_url + res["name"])
            else:
                error_msg = res.get("message", "Unknown error")
                print(f"[MMSeg-Caller] Error processing {name}: {error_msg}", file=sys.stderr)
                raise RuntimeError(f"Processing failed for {name}: {error_msg}")
        
        return temps
        
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"MMSegmentation inference timed out after {timeout}s")
    except json.JSONDecodeError as e:
        print(f"[MMSeg-Caller] Failed to parse output: {result.stdout}", file=sys.stderr)
        raise RuntimeError(f"Failed to parse inference output: {e}")


def execute(
    model_id: str,
    data_path: str,
    out_dir: str,
    names: List[str],
    device: str = "cuda:0"
) -> List[str]:
    """
    统一的执行接口，与 Paddle 推理模块保持一致
    
    :param model_id: MMSegmentation 模型 ID
    :param data_path: 数据文件夹路径
    :param out_dir: 结果保存路径
    :param names: 待处理文件名列表
    :return: 生成的图片 URL 列表
    """
    return call_mmseg_inference(
        model_id=model_id,
        data_path=data_path,
        out_dir=out_dir,
        names=names,
        device=device
    )


# 支持的 MMSegmentation 模型列表
SUPPORTED_MODELS = {
    "cugrs": {
        "model_id": "cc-ln/CUGRS",
        "description": "CUGRS DinoV3+SwinTransformer 6类地物分类"
    }
}


def get_supported_models():
    """返回支持的模型列表"""
    return SUPPORTED_MODELS
