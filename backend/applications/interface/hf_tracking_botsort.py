#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BoT-SORT multi-object tracking script.

Runs inside the HFPyTorch310 conda environment and uses Ultralytics'
BoT-SORT tracker to process an uploaded image sequence.
"""

import argparse
import json
import math
import os
import sys
from collections import Counter, defaultdict
from contextlib import redirect_stdout
from datetime import datetime
from statistics import mean
from typing import Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np


def log(msg: str, level: str = "INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] [HF-BoT-SORT] {msg}",
          file=sys.stderr,
          flush=True)


def parse_args():
    parser = argparse.ArgumentParser(description="BoT-SORT multi-object tracking")
    parser.add_argument("--input_dir", required=True, help="Input image directory")
    parser.add_argument("--file_names",
                        required=True,
                        help="Comma separated image file names in order")
    parser.add_argument("--output_video", required=True, help="Output video path")
    parser.add_argument("--output_preview",
                        required=True,
                        help="Output preview image path")
    parser.add_argument("--output_trajectory",
                        required=True,
                        help="Output trajectory json path")
    parser.add_argument("--output_mot",
                        default="",
                        help="Optional MOTChallenge txt output path")
    parser.add_argument("--model_id",
                        default="StephanST/WALDO30",
                        help="Ultralytics detector model id")
    parser.add_argument("--model_file",
                        default="",
                        help="Optional detector weight filename inside the model repo")
    parser.add_argument("--tracker_config",
                        default="botsort.yaml",
                        help="Path to BoT-SORT tracker yaml")
    parser.add_argument("--threshold",
                        type=float,
                        default=0.25,
                        help="Detection confidence threshold")
    parser.add_argument("--iou",
                        type=float,
                        default=0.45,
                        help="Tracking IoU threshold")
    parser.add_argument("--imgsz",
                        type=int,
                        default=1280,
                        help="Inference image size")
    parser.add_argument("--device",
                        default="auto",
                        help="auto, cpu, cuda:0 or GPU index")
    parser.add_argument("--allowed_labels",
                        default="",
                        help="Optional comma separated label whitelist")
    return parser.parse_args()


def resolve_device(device: str):
    import torch

    if device == "auto":
        return 0 if torch.cuda.is_available() else "cpu"
    return device


def resolve_ultralytics_weights(model_id: str, model_file: str = "") -> str:
    from huggingface_hub import hf_hub_download

    possible_files = []
    if model_file:
        possible_files.append(model_file)
    possible_files.extend([
        "WALDO30_yolov8n_640x640.pt",
        "WALDO30_yolov8m_640x640.pt",
        "best.pt",
        "model.pt",
        "weights.pt",
    ])
    for filename in possible_files:
        try:
            weight_file = hf_hub_download(repo_id=model_id, filename=filename)
            log(f"Resolved detector weights: {weight_file}")
            return weight_file
        except Exception:
            continue
    raise RuntimeError(f"Could not find a .pt detector weight in {model_id}")


def load_bgr_image(path: str) -> np.ndarray:
    image = cv2.imread(path, cv2.IMREAD_COLOR)
    if image is not None:
        return image

    from PIL import Image

    with Image.open(path) as pil_image:
        rgb = pil_image.convert("RGB")
    return cv2.cvtColor(np.array(rgb), cv2.COLOR_RGB2BGR)


def create_video_writer(path: str, width: int, height: int):
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, 6.0, (width, height))
    if not writer.isOpened():
        raise RuntimeError(f"Unable to create video writer: {path}")
    return writer


def draw_tracks(frame: np.ndarray,
                objects: Sequence[Dict[str, object]],
                frame_index: int) -> np.ndarray:
    canvas = frame.copy()
    cv2.putText(
        canvas,
        f"Frame {frame_index + 1}",
        (20, 36),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )

    for obj in objects:
        x, y, w, h = [int(v) for v in obj["bbox"]]
        x2, y2 = x + w, y + h
        track_id = obj.get("track_id")
        score = obj.get("score", 0.0)
        label = obj.get("label", "object")
        color = ((37 * int(track_id or 1)) % 255, (91 * int(track_id or 1)) % 255,
                 (151 * int(track_id or 1)) % 255)
        cv2.rectangle(canvas, (x, y), (x2, y2), color, 2)
        text = f"ID {track_id} {label} {score:.2f}"
        cv2.putText(
            canvas,
            text,
            (x, max(20, y - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
            cv2.LINE_AA,
        )

    return canvas


def build_preview_strip(frames: Sequence[np.ndarray]) -> np.ndarray:
    if not frames:
        return np.zeros((360, 960, 3), dtype=np.uint8)

    target_height = min(frame.shape[0] for frame in frames)
    resized = []
    for frame in frames:
        if frame.shape[0] != target_height:
            scale = target_height / frame.shape[0]
            resized.append(
                cv2.resize(frame,
                           (max(1, int(round(frame.shape[1] * scale))),
                            target_height)))
        else:
            resized.append(frame)
    return cv2.hconcat(resized)


def bbox_center(bbox: Sequence[float]) -> Tuple[float, float]:
    x, y, w, h = bbox
    return x + w / 2.0, y + h / 2.0


def compute_summary(frame_results: Sequence[Dict[str, object]]) -> Dict[str, object]:
    total_frames = len(frame_results)
    tracked_frames = sum(1 for frame in frame_results if frame["objects"])
    all_scores = [
        obj["score"] for frame in frame_results for obj in frame["objects"]
        if obj.get("score") is not None
    ]
    total_objects = sum(len(frame["objects"]) for frame in frame_results)
    max_concurrent_tracks = max((len(frame["objects"]) for frame in frame_results),
                                default=0)
    unique_track_ids = sorted(
        {
            int(obj["track_id"]) for frame in frame_results for obj in frame["objects"]
            if obj.get("track_id") is not None
        })
    label_hist = Counter(
        obj["label"] for frame in frame_results for obj in frame["objects"])

    track_paths: Dict[int, List[Tuple[float, float]]] = defaultdict(list)
    for frame in frame_results:
        for obj in frame["objects"]:
            track_id = obj.get("track_id")
            if track_id is None:
                continue
            track_paths[int(track_id)].append(bbox_center(obj["bbox"]))

    displacements = []
    for points in track_paths.values():
        if len(points) < 2:
            continue
        start_x, start_y = points[0]
        end_x, end_y = points[-1]
        displacements.append(math.hypot(end_x - start_x, end_y - start_y))

    return {
        "total_frames": total_frames,
        "tracked_frames": tracked_frames,
        "lost_frames": max(0, total_frames - tracked_frames),
        "tracking_ratio": round(tracked_frames / total_frames, 4) if total_frames else 0.0,
        "mean_confidence": round(float(mean(all_scores)), 4) if all_scores else 0.0,
        "center_displacement": round(float(mean(displacements)), 2)
        if displacements else 0.0,
        "total_detections": int(total_objects),
        "unique_track_count": len(unique_track_ids),
        "unique_track_ids": unique_track_ids,
        "max_concurrent_tracks": int(max_concurrent_tracks),
        "label_histogram": dict(sorted(label_hist.items())),
    }


def extract_objects(result) -> List[Dict[str, object]]:
    boxes = getattr(result, "boxes", None)
    if boxes is None or len(boxes) == 0:
        return []

    ids = boxes.id.int().cpu().tolist() if boxes.id is not None else [None] * len(boxes)
    confs = boxes.conf.float().cpu().tolist() if boxes.conf is not None else [0.0] * len(
        boxes)
    classes = boxes.cls.int().cpu().tolist() if boxes.cls is not None else [0] * len(boxes)
    xyxy_boxes = boxes.xyxy.cpu().tolist()
    names = result.names or {}

    objects = []
    for track_id, cls_id, score, xyxy in zip(ids, classes, confs, xyxy_boxes):
        x1, y1, x2, y2 = [float(v) for v in xyxy]
        objects.append({
            "track_id": int(track_id) if track_id is not None else None,
            "label": names.get(int(cls_id), str(cls_id)),
            "score": round(float(score), 4),
            "bbox": [
                int(round(x1)),
                int(round(y1)),
                int(round(max(0.0, x2 - x1))),
                int(round(max(0.0, y2 - y1))),
            ],
        })
    return objects


def write_mot_results(path: str, frame_results: Sequence[Dict[str, object]]):
    if not path:
        return
    lines = []
    for frame in frame_results:
        frame_id = int(frame["frame_index"]) + 1
        for obj in frame["objects"]:
            track_id = obj.get("track_id")
            if track_id is None:
                continue
            x, y, w, h = obj["bbox"]
            score = obj.get("score", 1.0)
            lines.append(
                f"{frame_id},{int(track_id)},{x:.2f},{y:.2f},{w:.2f},{h:.2f},{float(score):.4f},-1,-1,-1\n"
            )
    with open(path, "w", encoding="utf-8") as file:
        file.writelines(lines)


def main():
    args = parse_args()
    os.makedirs(os.path.dirname(args.output_video) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(args.output_preview) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(args.output_trajectory) or ".", exist_ok=True)
    if args.output_mot:
        os.makedirs(os.path.dirname(args.output_mot) or ".", exist_ok=True)

    file_names = [name.strip() for name in args.file_names.split(",") if name.strip()]
    if len(file_names) < 2:
        print(json.dumps({
            "status": "error",
            "message": "BoT-SORT 至少需要 2 帧图像序列",
        }))
        sys.exit(1)

    device = resolve_device(args.device)
    weight_path = resolve_ultralytics_weights(args.model_id, args.model_file)
    allowed_labels = {
        label.strip().lower()
        for label in args.allowed_labels.split(",")
        if label.strip()
    }

    from ultralytics import YOLO

    model = YOLO(weight_path)
    tracker_config = os.path.abspath(args.tracker_config)

    first_frame = load_bgr_image(os.path.join(args.input_dir, file_names[0]))
    height, width = first_frame.shape[:2]
    writer = create_video_writer(args.output_video, width, height)

    preview_frames = []
    frame_results = []

    try:
        for index, file_name in enumerate(file_names):
            image_path = os.path.join(args.input_dir, file_name)
            frame = load_bgr_image(image_path)
            if frame.shape[:2] != (height, width):
                frame = cv2.resize(frame, (width, height))

            with open(os.devnull, "w", encoding="utf-8") as devnull, redirect_stdout(
                    devnull):
                results = model.track(
                    frame,
                    persist=True,
                    tracker=tracker_config,
                    conf=args.threshold,
                    iou=args.iou,
                    imgsz=args.imgsz,
                    device=device,
                    verbose=False,
                )

            result = results[0]
            objects = extract_objects(result)
            if allowed_labels:
                objects = [
                    obj for obj in objects
                    if str(obj.get("label", "")).strip().lower() in allowed_labels
                ]
            annotated = draw_tracks(frame, objects, index)
            writer.write(annotated)

            if index in {0, len(file_names) // 2, len(file_names) - 1}:
                preview_frames.append(annotated.copy())

            frame_results.append({
                "frame_index": index,
                "filename": file_name,
                "objects": objects,
            })
    finally:
        writer.release()

    preview = build_preview_strip(preview_frames)
    if not cv2.imwrite(args.output_preview, preview):
        print(json.dumps({
            "status": "error",
            "message": f"Failed to write preview image: {args.output_preview}",
        }))
        sys.exit(1)

    summary = compute_summary(frame_results)
    write_mot_results(args.output_mot, frame_results)
    payload = {
        "status": "completed",
        "runtime_variant": "engineering",
        "method_used": "ultralytics_botsort",
        "detector_model_id": args.model_id,
        "detector_weight_file": os.path.basename(weight_path),
        "summary": summary,
        "frames": frame_results,
        "output_video": args.output_video,
        "output_preview": args.output_preview,
        "output_trajectory": args.output_trajectory,
        "output_mot": args.output_mot,
    }
    with open(args.output_trajectory, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
