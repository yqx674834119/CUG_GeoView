import argparse
import sys
import cv2
import torch
import kornia as K
import kornia.feature as KF
import numpy as np
from kornia.geometry import ransac
import matplotlib.pyplot as plt

def register_images(img1_path, img2_path, output_path):
    print(f"Loading images: {img1_path}, {img2_path}")
    
    # Load images
    img1 = K.io.load_image(img1_path, K.io.ImageLoadType.RGB32)[None, ...]
    img2 = K.io.load_image(img2_path, K.io.ImageLoadType.RGB32)[None, ...]
    
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but not available; refusing CPU inference")
    device = torch.device('cuda')
    img1 = img1.to(device)
    img2 = img2.to(device)
    
    # Convert to grayscale for feature extraction
    img1_gray = K.color.rgb_to_grayscale(img1)
    img2_gray = K.color.rgb_to_grayscale(img2)
    
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
        print("Not enough matches found.")
        sys.exit(1)
        
    # Find Homography
    Fm, inliers = cv2.findFundamentalMat(mkpts0, mkpts1, cv2.USAC_MAGSAC, 0.5, 0.999, 100000)
    inliers = inliers > 0
    
    # Estimate homography
    src_pts = mkpts0[inliers.flatten()]
    dst_pts = mkpts1[inliers.flatten()]
    
    if len(src_pts) < 4:
         print("Not enough inliers found.")
         sys.exit(1)

    H, _ = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
    
    # Warp image1 to image2
    h, w = img2.shape[2], img2.shape[3]
    img1_warped = cv2.warpPerspective(cv2.imread(img1_path), H, (w, h))
    
    # Save output
    cv2.imwrite(output_path, img1_warped)
    print(f"Registered image saved to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Image Registration Runner')
    parser.add_argument('--img1', required=True, help='Path to first image (source)')
    parser.add_argument('--img2', required=True, help='Path to second image (target)')
    parser.add_argument('--output', required=True, help='Path to save registered image')
    
    args = parser.parse_args()
    
    try:
        register_images(args.img1, args.img2, args.output)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
