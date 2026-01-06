#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HuggingFace Inference Caller

此模块在 PaddleRS37 环境中运行，通过 subprocess 调用 HFPyTorch310 环境中的
HuggingFace 推理脚本，实现环境隔离。
"""

import json
import os
import os.path as osp
import subprocess
import sys
from typing import List, Optional

from applications.common.path_global import generate_url


# HuggingFace conda 环境名称
HF_CONDA_ENV = "HFPyTorch310"

# HuggingFace 推理脚本路径
_curr_dir = os.path.dirname(os.path.abspath(__file__))
HF_SR_SCRIPT = os.path.join(_curr_dir, "hf_super_resolution.py")


def call_hf_super_resolution(
    model_id: str,
    data_path: str,
    out_dir: str,
    names: List[str],
    device: str = "auto",
    timeout: int = 600
) -> List[str]:
    """
    调用 HuggingFace 超分辨率模型进行推理
    
    :param model_id: HuggingFace 模型 ID, 如 "caidas/swin2SR-classical-sr-x2-64"
    :param data_path: 输入图片文件夹路径
    :param out_dir: 结果保存路径
    :param names: 待处理文件名列表
    :param device: 设备选择 ('auto', 'cuda', 'cpu')
    :param timeout: 超时时间（秒）
    :return: 生成的图片 URL 列表
    """
    if not names:
        return []
    
    # 构建命令
    # 转换相对路径为绝对路径，避免 subprocess cwd 导致路径错误
    abs_data_path = os.path.abspath(data_path)
    abs_out_dir = os.path.abspath(out_dir)
    
    file_names_str = ",".join(names)
    cmd = [
        "conda", "run", "-n", HF_CONDA_ENV,
        "python", HF_SR_SCRIPT,
        "--model_id", model_id,
        "--input_dir", abs_data_path,
        "--output_dir", abs_out_dir,
        "--file_names", file_names_str,
        "--device", device
    ]
    
    print(f"[HF-Caller] Executing: {' '.join(cmd)}", flush=True)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=_curr_dir
        )
        
        if result.returncode != 0:
            print(f"[HF-Caller] Error output: {result.stderr}", file=sys.stderr)
            raise RuntimeError(f"HuggingFace inference failed: {result.stderr}")
        
        # 解析 JSON 输出
        output_data = json.loads(result.stdout.strip())
        
        if output_data.get("status") != "completed":
            raise RuntimeError(f"Inference incomplete: {output_data}")
        
        # 生成结果 URL 列表
        temps = []
        result_map = {res["name"]: res for res in output_data.get("results", [])}
        
        for name in names:
            res = result_map.get(name)
            if not res:
                raise RuntimeError(f"No result returned for file: {name}")
            
            if res.get("status") == "success":
                temps.append(generate_url + res["name"])
            else:
                error_msg = res.get("message", "Unknown error")
                print(f"[HF-Caller] Error processing {name}: {error_msg}", file=sys.stderr)
                raise RuntimeError(f"Processing failed for {name}: {error_msg}")
        
        return temps
        
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"HuggingFace inference timed out after {timeout}s")
    except json.JSONDecodeError as e:
        print(f"[HF-Caller] Failed to parse output: {result.stdout}", file=sys.stderr)
        raise RuntimeError(f"Failed to parse inference output: {e}")


def execute(
    model_id: str,
    data_path: str,
    out_dir: str,
    names: List[str],
    device: str = "auto"
) -> List[str]:
    """
    统一的执行接口，与 Paddle 推理模块保持一致
    
    :param model_id: HuggingFace 模型 ID
    :param data_path: 数据文件夹路径，里面只包含图片
    :param out_dir: 结果保存路径
    :param names: 待处理文件名列表
    :return: 生成的图片 URL 列表
    """
    return call_hf_super_resolution(
        model_id=model_id,
        data_path=data_path,
        out_dir=out_dir,
        names=names,
        device=device
    )


# 支持的 HuggingFace 模型列表
SUPPORTED_MODELS = {
    "swin2sr-x2": {
        "model_id": "caidas/swin2SR-classical-sr-x2-64",
        "scale": 2,
        "description": "Swin2SR 2x super-resolution"
    },
    "swin2sr-x4": {
        "model_id": "caidas/swin2SR-classical-sr-x4-64",
        "scale": 4,
        "description": "Swin2SR 4x super-resolution"
    }
}

# HuggingFace Object Detection Script Path
HF_OD_SCRIPT = os.path.join(_curr_dir, "hf_object_detection.py")


def call_hf_object_detection(
    model_id: str,
    data_path: str,
    out_dir: str,
    names: List[str],
    device: str = "auto",
    timeout: int = 600
) -> List[str]:
    """
    Call HuggingFace Object Detection model for inference
    """
    if not names:
        return []
    
    abs_data_path = os.path.abspath(data_path)
    abs_out_dir = os.path.abspath(out_dir)
    
    file_names_str = ",".join(names)
    cmd = [
        "conda", "run", "-n", HF_CONDA_ENV,
        "python", HF_OD_SCRIPT,
        "--model_id", model_id,
        "--input_dir", abs_data_path,
        "--output_dir", abs_out_dir,
        "--file_names", file_names_str,
        "--device", device
    ]
    
    print(f"[HF-Caller] Executing OD: {' '.join(cmd)}", flush=True)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=_curr_dir
        )
        
        if result.returncode != 0:
            print(f"[HF-Caller] OD Error output: {result.stderr}", file=sys.stderr)
            raise RuntimeError(f"HuggingFace inference failed: {result.stderr}")
        
        output_data = json.loads(result.stdout.strip())
        
        if output_data.get("status") != "completed":
            raise RuntimeError(f"OD Inference incomplete: {output_data}")
        
        temps = []
        result_map = {res["name"]: res for res in output_data.get("results", [])}
        
        for name in names:
            res = result_map.get(name)
            if not res:
                raise RuntimeError(f"No result returned for file: {name}")
            
            if res.get("status") == "success":
                temps.append(generate_url + res["name"])
            else:
                error_msg = res.get("message", "Unknown error")
                print(f"[HF-Caller] Error processing {name}: {error_msg}", file=sys.stderr)
                raise RuntimeError(f"Processing failed for {name}: {error_msg}")
        
        return temps
        
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"HuggingFace OD inference timed out after {timeout}s")
    except json.JSONDecodeError as e:
        print(f"[HF-Caller] Failed to parse output: {result.stdout}", file=sys.stderr)
        raise RuntimeError(f"Failed to parse inference output: {e}")
    """返回支持的模型列表"""
    return SUPPORTED_MODELS
