#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tracking Inference Script

此脚本在 HFPyTorch310 环境中运行。
用于处理全域静态目标跟踪与预警 (模拟/简化版)。
注意: 真实的 SOTA 跟踪 (如 OSTrack) 需要复杂的环境配置。
此处演示使用 OpenCV 跟踪器或简单的帧间差分/光流作为演示，
或者如果环境中有 dimp/prdimp 等库则调用之。

考虑到 SatSOT 是卫星视频跟踪，我们将实现一个基于 CSRT (Discriminative Correlation Filter with Channel and Spatial Reliability) 的跟踪器，
它在 OpenCV 中可用且性能尚可。
"""

import argparse
import json
import os
import sys
import cv2
import numpy as np

def run_tracking(video_path, init_rect, output_path):
    """
    运行跟踪
    :param video_path: 视频路径 (或者图像序列文件夹)
    :param init_rect: 初始框 [x, y, w, h]
    :param output_path: 输出视频路径
    """
    # Check if input is video or folder
    if os.path.isdir(video_path):
        frames = sorted([os.path.join(video_path, f) for f in os.listdir(video_path) if f.endswith(('.jpg', '.png', '.tif'))])
        if not frames:
            raise ValueError("No images found in input directory")
        first_frame = cv2.imread(frames[0])
    else:
        cap = cv2.VideoCapture(video_path)
        ret, first_frame = cap.read()
        if not ret:
            raise ValueError("Failed to read video")
        frames = None # Mark as video source

    # Initialize tracker
    # Try different trackers
    try:
        tracker = cv2.TrackerCSRT_create()
    except AttributeError:
        # For older opencv-headless or different versions
        try:
            tracker = cv2.TrackerCSRT_create()
        except:
            print("CSRT tracker not available, falling back to MIL", file=sys.stderr)
            tracker = cv2.TrackerMIL_create()

    bbox = tuple(init_rect)
    tracker.init(first_frame, bbox)

    # Video writer
    h, w, _ = first_frame.shape
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, 20.0, (w, h))
    
    # Process
    if frames:
        iterator = frames
        is_video = False
    else:
        iterator = range(10000) # Max frames safety
        is_video = True

    results = []
    
    for i, item in enumerate(iterator):
        if is_video:
            ret, frame = cap.read()
            if not ret:
                break
        else:
            frame = cv2.imread(item)
            if frame is None:
                break
        
        # Update tracker
        ok, bbox = tracker.update(frame)
        
        if ok:
            p1 = (int(bbox[0]), int(bbox[1]))
            p2 = (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))
            cv2.rectangle(frame, p1, p2, (255,0,0), 2, 1)
            results.append({"frame": i, "bbox": [int(x) for x in bbox], "score": 1.0})
        else:
            cv2.putText(frame, "Tracking failure detected", (100,80), cv2.FONT_HERSHEY_SIMPLEX, 0.75,(0,0,255),2)
            results.append({"frame": i, "bbox": None, "score": 0.0})

        out.write(frame)

    if is_video:
        cap.release()
    out.release()
    
    return results

def main():
    parser = argparse.ArgumentParser(description="Tracking Inference")
    parser.add_argument("--input", required=True, help="Input video or folder")
    parser.add_argument("--output", required=True, help="Output video path")
    parser.add_argument("--rect", required=True, help="Initial rect x,y,w,h e.g. 100,100,50,50")
    
    args = parser.parse_args()
    
    try:
        rect = [int(x) for x in args.rect.split(',')]
        results = run_tracking(args.input, rect, args.output)
        print(json.dumps({"status": "completed", "results": results}))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()
