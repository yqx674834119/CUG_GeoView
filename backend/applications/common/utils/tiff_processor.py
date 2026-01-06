#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sentinel-2 / GeoTIFF 文件处理模块

功能：
1. TIFF 文件验证 (格式、大小)
2. 多波段 RGB 提取 (Sentinel-2: B4, B3, B2)
3. 数值归一化 (uint16 -> uint8)
4. 导出为 PNG 格式
5. 大尺寸图像切片

配置：
- 最大文件大小: 500MB
- RGB 波段: Sentinel-2 标准 (B4→R, B3→G, B2→B) 或自动检测
- 地理元数据: 丢弃
- 大图切片: 超过 1024x1024 进行切片
"""

import os
import os.path as osp
import uuid
import math
from typing import Tuple, Optional, List, Dict

import numpy as np
from PIL import Image

# 配置常量
MAX_TIFF_SIZE_MB = 500  # 最大文件大小 (MB)
MAX_TIFF_SIZE_BYTES = MAX_TIFF_SIZE_MB * 1024 * 1024
LARGE_IMAGE_THRESHOLD = (1024, 1024) # 大图阈值 (width, height)
SLICE_SIZE = 1024 # 切片大小

# Sentinel-2 10m 分辨率波段
# 在 TIFF 中的顺序通常是 B2, B3, B4, B8 (需要根据实际数据调整)
SENTINEL2_RGB_BAND_INDICES = {
    'red': 3,    # B4 - Red (波段索引从0开始，通常第4个波段)
    'green': 2,  # B3 - Green
    'blue': 1,   # B2 - Blue
}

# 归一化百分位 (用于对比度拉伸)
NORMALIZE_PERCENTILE = (2, 98)


def is_tiff_file(filename: str) -> bool:
    """判断是否为 TIFF 文件"""
    ext = osp.splitext(filename.lower())[1]
    return ext in ('.tif', '.tiff')


def validate_tiff_file(file_path: str) -> dict:
    """
    验证 TIFF 文件
    
    :param file_path: TIFF 文件路径
    :return: dict 包含验证结果和文件信息
    """
    result = {
        'valid': False,
        'error': None,
        'info': {}
    }
    
    # 检查文件存在
    if not osp.exists(file_path):
        result['error'] = f"文件不存在: {file_path}"
        return result
    
    # 检查文件大小
    file_size = osp.getsize(file_path)
    file_size_mb = file_size / (1024 * 1024)
    result['info']['size_mb'] = round(file_size_mb, 2)
    
    if file_size > MAX_TIFF_SIZE_BYTES:
        result['error'] = f"文件大小 ({file_size_mb:.1f}MB) 超过限制 ({MAX_TIFF_SIZE_MB}MB)"
        return result
    
    # 尝试读取 TIFF 并获取元数据
    try:
        import rasterio
        with rasterio.open(file_path) as src:
            result['info']['width'] = src.width
            result['info']['height'] = src.height
            result['info']['bands'] = src.count
            result['info']['dtype'] = str(src.dtypes[0])
            result['info']['crs'] = str(src.crs) if src.crs else None
    except ImportError:
        # 如果没有 rasterio，使用 PIL 尝试读取
        try:
            from PIL import Image
            with Image.open(file_path) as img:
                result['info']['width'] = img.width
                result['info']['height'] = img.height
                result['info']['bands'] = len(img.getbands())
                result['info']['dtype'] = img.mode
        except Exception as e:
            result['error'] = f"无法读取 TIFF 文件: {str(e)}"
            return result
    except Exception as e:
        result['error'] = f"无法读取 TIFF 文件: {str(e)}"
        return result
    
    result['valid'] = True
    return result


def is_large_image(width: int, height: int) -> bool:
    """
    判断是否为大尺寸图像
    """
    return width > LARGE_IMAGE_THRESHOLD[0] or height > LARGE_IMAGE_THRESHOLD[1]


def normalize_array(array: np.ndarray, percentile: Tuple[int, int] = NORMALIZE_PERCENTILE) -> np.ndarray:
    """
    将数组归一化到 0-255 uint8 范围
    
    使用百分位裁剪以增强对比度
    
    :param array: 输入数组
    :param percentile: 归一化百分位范围
    :return: uint8 数组
    """
    # 处理每个通道
    if array.ndim == 3:
        result = np.zeros_like(array, dtype=np.uint8)
        for i in range(array.shape[2]):
            result[:, :, i] = normalize_array(array[:, :, i], percentile)
        return result
    
    # 单通道处理
    p_low, p_high = np.percentile(array, percentile)
    
    # 避免除零
    if p_high - p_low < 1e-6:
        if p_high > 0:
            return (array / p_high * 255).astype(np.uint8)
        else:
            return np.zeros_like(array, dtype=np.uint8)
    
    # 裁剪并归一化
    clipped = np.clip(array, p_low, p_high)
    normalized = (clipped - p_low) / (p_high - p_low) * 255
    
    return normalized.astype(np.uint8)


def extract_rgb_from_multiband(data: np.ndarray, band_count: int) -> np.ndarray:
    """
    从多波段数据中提取 RGB
    
    策略:
    - 3 波段: 直接作为 RGB
    - 4+ 波段 (Sentinel-2): 使用 B4(R), B3(G), B2(B)
    - 1 波段: 复制为 3 通道灰度图
    
    :param data: 多波段数组 [bands, height, width] 或 [height, width, bands]
    :param band_count: 波段数量
    :return: RGB 数组 [height, width, 3]
    """
    # 确保数据格式为 [height, width, bands]
    if data.ndim == 3 and data.shape[0] < data.shape[2]:
        # [bands, height, width] -> [height, width, bands]
        data = np.transpose(data, (1, 2, 0))
    
    if band_count == 1:
        # 单波段 -> 灰度 RGB
        if data.ndim == 2:
            gray = data
        else:
            gray = data[:, :, 0]
        return np.stack([gray, gray, gray], axis=-1)
    
    elif band_count == 3:
        # 已经是 RGB
        return data
    
    elif band_count >= 4:
        # Sentinel-2 多波段 - 提取 B4(R), B3(G), B2(B)
        # 注意: 波段索引需要根据实际数据调整
        # 常见的 Sentinel-2 L2A 10m 产品波段顺序: B2, B3, B4, B8
        # 索引: B2=0, B3=1, B4=2, B8=3
        try:
            # 尝试标准 Sentinel-2 波段顺序
            red = data[:, :, 2]    # B4
            green = data[:, :, 1]  # B3
            blue = data[:, :, 0]   # B2
            return np.stack([red, green, blue], axis=-1)
        except IndexError:
            # 如果波段不足，使用前3个
            return data[:, :, :3]
    
    else:
        # 2 波段 - 使用第一个波段作为灰度
        gray = data[:, :, 0]
        return np.stack([gray, gray, gray], axis=-1)


def read_tiff_as_rgb(tiff_path: str) -> np.ndarray:
    """
    读取 TIFF 文件并转换为 RGB 数组
    
    :param tiff_path: TIFF 文件路径
    :return: RGB 数组 [height, width, 3] uint8
    """
    try:
        import rasterio
        with rasterio.open(tiff_path) as src:
            # 读取所有波段
            data = src.read()  # [bands, height, width]
            band_count = src.count
            
            # 转换为 [height, width, bands]
            data = np.transpose(data, (1, 2, 0))
    except ImportError:
        # 使用 PIL 作为后备
        from PIL import Image
        img = Image.open(tiff_path)
        data = np.array(img)
        
        if data.ndim == 2:
            band_count = 1
        else:
            band_count = data.shape[2] if data.ndim == 3 else 1
    
    print(f"[TIFF] 读取文件: {tiff_path}")
    print(f"[TIFF] 波段数: {band_count}, 形状: {data.shape}, 数据类型: {data.dtype}")
    
    # 提取 RGB
    rgb_data = extract_rgb_from_multiband(data, band_count)
    print(f"[TIFF] RGB 提取完成, 形状: {rgb_data.shape}")
    
    # 归一化到 uint8
    if rgb_data.dtype != np.uint8:
        rgb_data = normalize_array(rgb_data)
        print(f"[TIFF] 归一化完成, 范围: [{rgb_data.min()}, {rgb_data.max()}]")
    
    return rgb_data


def tiff_to_png(tiff_path: str, output_path: str = None) -> str:
    """
    将 TIFF 文件转换为 PNG
    
    :param tiff_path: TIFF 文件路径
    :param output_path: 输出 PNG 路径 (可选，默认同目录同名)
    :return: PNG 文件路径
    """
    if output_path is None:
        base_name = osp.splitext(tiff_path)[0]
        output_path = base_name + '.png'
    
    # 读取并转换
    rgb_data = read_tiff_as_rgb(tiff_path)
    
    # 保存为 PNG
    img = Image.fromarray(rgb_data)
    img.save(output_path, 'PNG')
    
    print(f"[TIFF] 已保存 PNG: {output_path}")
    return output_path


def slice_image(image_data: np.ndarray, output_dir: str, base_filename: str, 
               slice_size: int = SLICE_SIZE) -> List[Dict[str, str]]:
    """
    将大图切分为多个小图
    
    :param image_data: 图像数据 (H, W, C)
    :param output_dir: 输出目录
    :param base_filename: 基础文件名
    :param slice_size: 切片大小
    :return: 切片文件信息列表
    """
    height, width = image_data.shape[:2]
    rows = math.ceil(height / slice_size)
    cols = math.ceil(width / slice_size)
    
    slices = []
    
    print(f"[Slice] 开始切片: {base_filename}, 尺寸: {width}x{height} -> {rows}x{cols} 块")
    
    for r in range(rows):
        for c in range(cols):
            # 计算切片范围
            r_start = r * slice_size
            r_end = min((r + 1) * slice_size, height)
            c_start = c * slice_size
            c_end = min((c + 1) * slice_size, width)
            
            # 提取切片
            slice_img = image_data[r_start:r_end, c_start:c_end]
            
            # 检查是否需要填充 (如果不是完整块且需要正方形输入)
            # 这里我们保持原样，如果非正方形，后端算法通常也能处理，或者resize
            # 为了更好的配对，我们保留原始大小
            
            # 生成文件名: name_row_col.png
            # 注意: 使用 png 以确保兼容性
            slice_filename = f"{base_filename}_{r}_{c}.png"
            slice_path = osp.join(output_dir, slice_filename)
            
            # 保存
            img = Image.fromarray(slice_img)
            img.save(slice_path, 'PNG')
            
            slices.append({
                'path': slice_path,
                'filename': slice_filename
            })
            
    return slices


def process_uploaded_tiff(tiff_path: str, output_dir: str, original_filename: str = None) -> List[Dict[str, str]]:
    """
    处理上传的 TIFF 文件 (支持切片)
    
    1. 验证文件
    2. 读取并提取 RGB
    3. 检查尺寸，如果过大则切片
    4. 导出为 PNG (单个或多个)
    5. 返回生成的文件列表
    
    :param tiff_path: 上传的 TIFF 文件路径
    :param output_dir: 输出目录
    :param original_filename: 原始文件名 (用于生成切片名)
    :return: 文件信息列表 [{'path': ..., 'filename': ...}]
    """
    # 验证
    validation = validate_tiff_file(tiff_path)
    if not validation['valid']:
        raise ValueError(validation['error'])
    
    print(f"[TIFF] 验证通过: {validation['info']}")
    
    width = validation['info'].get('width', 0)
    height = validation['info'].get('height', 0)
    
    # 读取并转换 RGB
    rgb_data = read_tiff_as_rgb(tiff_path)
    
    results = []
    
    # 确定基础文件名
    if original_filename:
        # 去除扩展名
        base_name = osp.splitext(original_filename)[0]
    else:
        base_name = str(uuid.uuid4())
        
    # 判断是否需要切片
    if is_large_image(width, height):
        print(f"[TIFF] 检测到大图 ({width}x{height})，执行切片处理...")
        results = slice_image(rgb_data, output_dir, base_name)
    else:
        # 不切片，直接保存为单张 PNG
        png_filename = base_name + '.png'
        # 如果不是 UUID 生成的，可能发生冲突，但通常 output_dir 是唯一的或文件名有 UUID 前缀
        # 为了安全，如果 original_filename 没提供，用 UUID
        if not original_filename:
            png_filename = str(uuid.uuid4()) + '.png'
            
        output_path = osp.join(output_dir, png_filename)
        
        img = Image.fromarray(rgb_data)
        img.save(output_path, 'PNG')
        
        results.append({
            'path': output_path,
            'filename': png_filename
        })
    
    return results


def get_tiff_info(tiff_path: str) -> dict:
    """获取 TIFF 文件信息"""
    validation = validate_tiff_file(tiff_path)
    return validation['info'] if validation['valid'] else {}
