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
import traceback
import cv2
import torch
import kornia as K
import kornia.feature as KF
import numpy as np
from kornia.geometry import ransac

def register_pair(img1_path, img2_path, output_path, device='cuda'):
    # Load images
    img1_t = K.io.load_image(img1_path, K.io.ImageLoadType.RGB32)[None, ...]
    img2_t = K.io.load_image(img2_path, K.io.ImageLoadType.RGB32)[None, ...]
    
    img1_t = img1_t.to(device)
    img2_t = img2_t.to(device)
    
    # Convert to grayscale for feature extraction
    img1_gray = K.color.rgb_to_grayscale(img1_t)
    img2_gray = K.color.rgb_to_grayscale(img2_t)
    
    # Initialize LoFTR
    matcher = KF.LoFTR(pretrained='outdoor').to(device)
    
    input_dict = {
        "image0": img1_gray,
        "image1": img2_gray
    }
    
    with torch.inference_mode():
        correspondences = matcher(input_dict)
        
    mkpts0 = correspondences['keypoints0'].cpu().numpy()
    mkpts1 = correspondences['keypoints1'].cpu().numpy()
    
    if len(mkpts0) < 4:
        raise RuntimeError("Not enough matches found.")
        
    # Find Homography using OpenCV for robustness
    # Kornia has find_homography but usage with RANSAC can be tricky to tune perfectly in one go, 
    # cv2 is often more stable for generic use.
    H, mask = cv2.findHomography(mkpts0, mkpts1, cv2.RANSAC, 5.0)
    
    if H is None:
        raise RuntimeError("Homography estimation failed.")
        
    # Warp image1 to image2's frame
    # We use cv2 for warping to keep it simple and consistent with IO
    img1_cv = cv2.imread(img1_path)
    h, w, _ = cv2.imread(img2_path).shape
    
    img1_warped = cv2.warpPerspective(img1_cv, H, (w, h))
    
    cv2.imwrite(output_path, img1_warped)
    return True

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
                register_pair(input_path1, input_path2, output_path, device)
                results.append({"name": out_name, "status": "success", "output_path": output_path})
            except Exception as e:
                results.append({"name": out_name, "status": "error", "message": str(e)})
        
        print(json.dumps({"status": "completed", "results": results}))
        
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()
