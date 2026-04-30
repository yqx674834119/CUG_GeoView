#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MMSegmentation Inference Script

此脚本在 MMSeg310 环境中运行，使用 MMSegmentation 进行语义分割推理。
支持 GeoTIFF 图像输入，保留地理坐标信息。

6类地物分类:
  0: grassland (草地) - 灰色
  1: forest (林地) - 红色
  2: building (建筑) - 绿色
  3: road (道路) - 浅绿色
  4: bareground (裸地) - 深灰色
  5: water (水体) - 青色
"""

import argparse
import json
import os
import sys
from typing import List, Optional


def patch_openmmlab_version_guards():
    try:
        import mmcv
        if getattr(mmcv, "__version__", "") in {"2.1.0", "2.2.0"}:
            mmcv.__version__ = "2.0.1"
    except Exception:
        pass


patch_openmmlab_version_guards()

# 添加 backend 路径到 sys.path，确保可以导入 backend 下的模块
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../"))
# 导入自定义模型以注册到 metrics/registry
try:
    import backend.model.custom_models
    print("[MMSeg] Custom models registered", file=sys.stderr)
except ImportError as e:
    print(f"[MMSeg] Warning: Failed to import custom models: {e}", file=sys.stderr)

import cv2
import numpy as np

# 类别颜色配置 (RGB格式)
PALETTE = [
    [0, 255, 0],      # 0: grassland - Lime
    [0, 128, 0],      # 1: forest - Green
    [255, 0, 0],      # 2: building - Red
    [255, 255, 0],    # 3: road - Yellow
    [255, 0, 255],    # 4: bareground - Magenta
    [0, 191, 255],    # 5: water - DeepSkyBlue
]

CLASS_NAMES = ['grassland', 'forest', 'building', 'road', 'bareground', 'water']


def load_rs_image_with_gdal(img_path: str, to_float32: bool = True) -> Optional[np.ndarray]:
    """
    使用 GDAL 加载遥感图像，支持多波段 GeoTIFF
    
    Args:
        img_path: 遥感图像路径
        to_float32: 是否转换为 float32
    
    Returns:
        图像数组 (H, W, C)，加载失败返回 None
    """
    try:
        from osgeo import gdal
    except ImportError:
        # 如果没有 GDAL，使用 cv2 加载
        img = cv2.imread(img_path)
        if img is not None and to_float32:
            img = img.astype(np.float32)
        return img
    
    ds = gdal.Open(img_path)
    if ds is None:
        print(f"Warning: Failed to open image with GDAL: {img_path}", file=sys.stderr)
        return None
    
    # 读取并调整维度 (C, H, W) -> (H, W, C)
    img_array = np.einsum('ijk->jki', ds.ReadAsArray())
    
    if to_float32:
        img_array = img_array.astype(np.float32)
    
    ds = None  # 关闭数据集
    return img_array


def save_with_georeference(output_path: str, data: np.ndarray, reference_path: str):
    """
    保存带地理参考信息的 GeoTIFF
    
    Args:
        output_path: 输出路径
        data: 数据数组 (H, W) 或 (H, W, C)
        reference_path: 参考影像路径 (用于获取投影信息)
    """
    try:
        from osgeo import gdal, osr
        
        ref_ds = gdal.Open(reference_path)
        if ref_ds is None:
            # 无法获取参考信息，使用普通保存
            cv2.imwrite(output_path, data)
            return
        
        # 获取投影信息
        geo_transform = ref_ds.GetGeoTransform()
        projection = ref_ds.GetProjection()
        
        # 创建输出文件
        driver = gdal.GetDriverByName('GTiff')
        if len(data.shape) == 2:
            out_ds = driver.Create(output_path, data.shape[1], data.shape[0], 1, gdal.GDT_Byte)
            out_ds.GetRasterBand(1).WriteArray(data)
        else:
            out_ds = driver.Create(output_path, data.shape[1], data.shape[0], data.shape[2], gdal.GDT_Byte)
            for i in range(data.shape[2]):
                out_ds.GetRasterBand(i + 1).WriteArray(data[:, :, i])
        
        out_ds.SetGeoTransform(geo_transform)
        out_ds.SetProjection(projection)
        out_ds.FlushCache()
        out_ds = None
        ref_ds = None
        
    except ImportError:
        # 没有 GDAL，使用普通保存
        cv2.imwrite(output_path, data)


def colorize_mask(pred_mask: np.ndarray) -> np.ndarray:
    """
    将预测掩码转换为彩色可视化图像
    
    Args:
        pred_mask: 预测掩码 (H, W)，值为类别索引
    
    Returns:
        彩色图像 (H, W, 3) BGR格式
    """
    color_mask = np.zeros((pred_mask.shape[0], pred_mask.shape[1], 3), dtype=np.uint8)
    for idx, color in enumerate(PALETTE):
        color_mask[pred_mask == idx] = color[::-1]  # RGB to BGR
    return color_mask


def run_inference(
    config_file: str,
    checkpoint_file: str,
    input_dir: str,
    output_dir: str,
    file_names: List[str],
    device: str = "cuda:0",
    opacity: float = 0.3
) -> dict:
    """
    运行 MMSegmentation 推理
    
    Args:
        config_file: 模型配置文件路径
        checkpoint_file: 模型权重文件路径
        input_dir: 输入图片目录
        output_dir: 输出目录
        file_names: 待处理文件名列表
        device: 计算设备
        opacity: 叠加透明度
    
    Returns:
        推理结果字典
    """
    from mmseg.apis import init_model, inference_model
    
    # 初始化模型
    print(f"[MMSeg] Loading model from {checkpoint_file}", file=sys.stderr)
    model = init_model(config_file, checkpoint_file, device=device)
    print(f"[MMSeg] Model loaded successfully", file=sys.stderr)
    
    os.makedirs(output_dir, exist_ok=True)
    
    results = []
    
    for filename in file_names:
        try:
            img_path = os.path.join(input_dir, filename)
            
            # 加载图像
            img_array = load_rs_image_with_gdal(img_path, to_float32=True)
            if img_array is None:
                results.append({
                    "name": filename,
                    "status": "error",
                    "error": "Failed to load image"
                })
                continue
            
            # 运行推理
            result = inference_model(model, img_array)
            pred_mask = result.pred_sem_seg.data[0].cpu().numpy().astype(np.uint8)
            
            # 生成彩色掩码
            color_mask = colorize_mask(pred_mask)
            
            # 叠加原图和掩码
            if len(img_array.shape) == 3 and img_array.shape[2] >= 3:
                # 取前三个波段作为 RGB
                img_rgb = img_array[:, :, :3]
                if img_rgb.max() > 1:
                    img_rgb = img_rgb / img_rgb.max() * 255
                img_bgr = img_rgb[:, :, ::-1].astype(np.uint8)
                overlay = cv2.addWeighted(img_bgr, opacity, color_mask, 1 - opacity, 0)
            else:
                overlay = color_mask
            
            # 保存结果
            base_name = os.path.splitext(filename)[0]
            out_name = f"pred_{base_name}.png"
            out_path = os.path.join(output_dir, out_name)
            cv2.imwrite(out_path, overlay)
            
            # 同时保存原始掩码（用于后续分析）
            mask_name = f"mask_{base_name}.png"
            mask_path = os.path.join(output_dir, mask_name)
            cv2.imwrite(mask_path, pred_mask)
            
            results.append({
                "name": out_name,
                "mask_name": mask_name,
                "status": "success",
                "class_names": CLASS_NAMES,
                "palette": PALETTE,
                "class_histogram": dict(Counter(pred_mask.reshape(-1).tolist())),
            })
            
            print(f"[MMSeg] Processed: {filename} -> {out_name}", file=sys.stderr)
            
        except Exception as e:
            results.append({
                "name": filename,
                "status": "error", 
                "error": str(e)
            })
            print(f"[MMSeg] Error processing {filename}: {e}", file=sys.stderr)
    
    return {
        "status": "completed",
        "total": len(file_names),
        "success": sum(1 for r in results if r.get("status") == "success"),
        "results": results
    }


def main():
    parser = argparse.ArgumentParser(description="MMSegmentation Inference")
    parser.add_argument("--config", required=True, help="Model config file path")
    parser.add_argument("--checkpoint", required=True, help="Model checkpoint file path")
    parser.add_argument("--input_dir", required=True, help="Input directory")
    parser.add_argument("--output_dir", required=True, help="Output directory")
    parser.add_argument("--file_names", required=True, help="Comma-separated file names")
    parser.add_argument("--device", default="cuda:0", help="Device (cuda:0 or cpu)")
    parser.add_argument("--opacity", type=float, default=0.3, help="Overlay opacity")
    
    args = parser.parse_args()
    
    file_names = [f.strip() for f in args.file_names.split(",") if f.strip()]
    
    result = run_inference(
        config_file=args.config,
        checkpoint_file=args.checkpoint,
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        file_names=file_names,
        device=args.device,
        opacity=args.opacity
    )
    
    # 输出 JSON 结果到 stdout
    print(json.dumps(result))


if __name__ == "__main__":
    main()
