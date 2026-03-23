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


_MATCHER_CACHE = {}


def register_pair(img1_path, img2_path, output_path, device='cuda'):
    img1_t = K.io.load_image(img1_path, K.io.ImageLoadType.RGB32)[None, ...].to(device)
    img2_t = K.io.load_image(img2_path, K.io.ImageLoadType.RGB32)[None, ...].to(device)

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


def _get_matcher(device):
    matcher = _MATCHER_CACHE.get(device)
    if matcher is not None:
        return matcher

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
