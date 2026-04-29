#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HuggingFace Registration Inference Script (Kornia)

此脚本需要在 HFPyTorch310 conda 环境中运行。
用于处理多模态遥感数据目标自动配准。
"""

import argparse
import json
import os
import sys

import cv2
import kornia as K
import kornia.feature as KF
import numpy as np
import torch

try:
    import rasterio
except Exception:
    rasterio = None

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOFTR_CHECKPOINT = os.path.abspath(
    os.path.join(SCRIPT_DIR, "..", "..", "model", "registration",
                 "loftr_outdoor", "loftr_outdoor.ckpt"))

_MATCHER_CACHE = {}


def register_pair(img1_path, img2_path, output_path, device='cuda'):
    img1_t = _load_image_tensor(img1_path, device)
    img2_t = _load_image_tensor(img2_path, device)

    img1_gray = K.color.rgb_to_grayscale(img1_t)
    img2_gray = K.color.rgb_to_grayscale(img2_t)

    matcher = _get_matcher(device)
    input_dict = {"image0": img1_gray, "image1": img2_gray}

    with torch.inference_mode():
        correspondences = matcher(input_dict)

    mkpts0 = correspondences['keypoints0'].detach().cpu().numpy()
    mkpts1 = correspondences['keypoints1'].detach().cpu().numpy()

    if len(mkpts0) < 4:
        raise RuntimeError("Not enough matches found.")

    homography, mask = cv2.findHomography(mkpts0, mkpts1, cv2.RANSAC, 5.0)
    if homography is None or mask is None:
        raise RuntimeError("Homography estimation failed.")

    mask = mask.reshape(-1).astype(bool)
    inlier_count = int(mask.sum())
    if inlier_count < 4:
        raise RuntimeError("Not enough inliers after RANSAC.")

    img1_cv = cv2.imread(img1_path)
    img2_cv = cv2.imread(img2_path)
    h, w = img2_cv.shape[:2]
    img1_warped = cv2.warpPerspective(img1_cv, homography, (w, h))
    cv2.imwrite(output_path, img1_warped)

    rmse = _compute_rmse(mkpts0[mask], mkpts1[mask], homography)
    return {
        "transform_matrix": np.round(homography.astype(float), 6).tolist(),
        "transform_type": "homography",
        "method_used": "kornia_loftr_external",
        "match_count": int(len(mask)),
        "inlier_count": inlier_count,
        "inlier_ratio": round(float(inlier_count / len(mask)), 4),
        "rmse": round(float(rmse), 4),
    }


def _load_image_tensor(path, device):
    rgb = _load_rgb_image(path)
    tensor = torch.from_numpy(rgb).permute(2, 0, 1).float() / 255.0
    return tensor.unsqueeze(0).to(device)


def _load_rgb_image(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in {'.tif', '.tiff'}:
        if rasterio is None:
            raise RuntimeError('rasterio is required to read TIFF images')
        with rasterio.open(path) as dataset:
            array = dataset.read()
        if array.size == 0:
            raise RuntimeError(f'Failed to read image: {path}')
        return _multiband_to_rgb(array)

    image = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if image is None:
        raise RuntimeError(f'Failed to read image: {path}')
    if image.ndim == 2:
        image = np.stack([image] * 3, axis=-1)
    elif image.shape[2] == 4:
        image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    if image.dtype != np.uint8:
        image = _normalize_to_uint8(image)
    return image


def _multiband_to_rgb(array):
    bands = array.shape[0]
    if bands >= 3:
        rgb = np.stack([array[0], array[1], array[2]], axis=-1)
    elif bands == 2:
        mean_band = ((array[0].astype(np.float32) + array[1].astype(np.float32)) /
                     2.0)
        rgb = np.stack([array[0], array[1], mean_band], axis=-1)
    else:
        rgb = np.stack([array[0], array[0], array[0]], axis=-1)
    return _normalize_to_uint8(rgb)


def _normalize_to_uint8(image):
    image = np.nan_to_num(image.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    if image.ndim == 2:
        return _robust_channel_normalize(image)

    channels = []
    for index in range(image.shape[2]):
        channels.append(_robust_channel_normalize(image[:, :, index]))
    return np.stack(channels, axis=-1)


def _robust_channel_normalize(channel):
    valid = channel[np.isfinite(channel)]
    if valid.size == 0:
        return np.zeros(channel.shape, dtype=np.uint8)

    low, high = np.percentile(valid, [2, 98])
    if high <= low:
        low = float(valid.min())
        high = float(valid.max())
    if high <= low:
        return np.zeros(channel.shape, dtype=np.uint8)

    channel = np.clip(channel, low, high)
    channel = (channel - low) / (high - low)
    return np.clip(channel * 255.0, 0, 255).astype(np.uint8)


def _get_matcher(device):
    matcher = _MATCHER_CACHE.get(device)
    if matcher is not None:
        return matcher

    if os.path.exists(LOFTR_CHECKPOINT):
        matcher = KF.LoFTR(pretrained=None).to(device)
        state = torch.load(LOFTR_CHECKPOINT, map_location=device)
        state_dict = state.get("state_dict", state)
        matcher.load_state_dict(state_dict, strict=False)
    else:
        matcher = KF.LoFTR(pretrained='outdoor').to(device)
    matcher.eval()
    _MATCHER_CACHE[device] = matcher
    return matcher


def _compute_rmse(src_points, dst_points, matrix):
    projected = cv2.perspectiveTransform(src_points.reshape(-1, 1, 2),
                                         matrix).reshape(-1, 2)
    error = np.linalg.norm(projected - dst_points, axis=1)
    return float(np.sqrt(np.mean(np.square(error))))

def main():
    parser = argparse.ArgumentParser(description="Registration Inference")
    parser.add_argument("--input_dir", required=True, help="Input directory")
    parser.add_argument("--output_dir", required=True, help="Output directory")
    parser.add_argument("--file_pairs", required=True, help="JSON string of file pairs [{'first': 'a.jpg', 'second': 'b.jpg'}]")
    parser.add_argument("--device", default="cuda", help="Device")
    
    args = parser.parse_args()
    
    try:
        if args.device == 'auto':
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            device = args.device
            
        pairs = json.loads(args.file_pairs)
        os.makedirs(args.output_dir, exist_ok=True)
        
        results = []
        
        for pair in pairs:
            name1 = pair['first']
            name2 = pair['second']
            
            # Output will be named reg_{name1} (registered version of first image)
            out_name = f"reg_{name1}"
            
            input_path1 = os.path.join(args.input_dir, name1)
            input_path2 = os.path.join(args.input_dir, name2)
            output_path = os.path.join(args.output_dir, out_name)
            
            if not os.path.exists(input_path1) or not os.path.exists(input_path2):
                results.append({"name": out_name, "status": "error", "message": "File not found"})
                continue
                
            try:
                metadata = register_pair(input_path1, input_path2, output_path, device)
                results.append({
                    "name": out_name,
                    "status": "success",
                    "output_path": output_path,
                    **metadata,
                })
            except Exception as e:
                results.append({"name": out_name, "status": "error", "message": str(e)})
        
        print(json.dumps({"status": "completed", "results": results}))
        
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()
