#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Official BoT-SORT runtime wrapper.

Runs inside the dedicated BoTSORTOfficial37 conda environment and uses the
original NirAharon/BoT-SORT codebase for detection + association on an image
sequence uploaded through GeoView.
"""

import argparse
import collections
import json
import math
import os
import sys
import types
from collections import Counter, defaultdict
from collections import abc
from contextlib import contextmanager
from datetime import datetime
from statistics import mean
from typing import Dict, List, Sequence, Tuple

import cv2
import numpy as np


def patch_python_compat():
    for name in ("Sequence", "Mapping", "MutableMapping"):
        if not hasattr(collections, name) and hasattr(abc, name):
            setattr(collections, name, getattr(abc, name))
    numpy_aliases = {
        "bool": bool,
        "int": int,
        "float": float,
        "complex": complex,
        "object": object,
    }
    for name, value in numpy_aliases.items():
        if name not in np.__dict__:
            setattr(np, name, value)
    if "torch._six" not in sys.modules:
        torch_six = types.ModuleType("torch._six")
        torch_six.string_classes = (str,)
        torch_six.int_classes = (int,)
        torch_six.container_abcs = abc
        sys.modules["torch._six"] = torch_six


def log(msg: str, level: str = "INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] [HF-BoT-SORT-Official] {msg}",
          file=sys.stderr,
          flush=True)


def parse_args():
    parser = argparse.ArgumentParser(description="Official BoT-SORT sequence wrapper")
    parser.add_argument("--input_dir", required=True)
    parser.add_argument("--file_names", required=True)
    parser.add_argument("--output_video", required=True)
    parser.add_argument("--output_preview", required=True)
    parser.add_argument("--output_trajectory", required=True)
    parser.add_argument("--output_mot", required=True)
    parser.add_argument("--repo_dir", required=True)
    parser.add_argument("--exp_file", required=True)
    parser.add_argument("--detector_ckpt", required=True)
    parser.add_argument("--with_reid", default="1")
    parser.add_argument("--fast_reid_config", required=True)
    parser.add_argument("--fast_reid_weights", required=True)
    parser.add_argument("--cmc_method", default="orb")
    parser.add_argument("--track_high_thresh", type=float, default=0.6)
    parser.add_argument("--track_low_thresh", type=float, default=0.1)
    parser.add_argument("--new_track_thresh", type=float, default=0.7)
    parser.add_argument("--track_buffer", type=int, default=30)
    parser.add_argument("--match_thresh", type=float, default=0.8)
    parser.add_argument("--min_box_area", type=float, default=10.0)
    parser.add_argument("--aspect_ratio_thresh", type=float, default=1.6)
    parser.add_argument("--proximity_thresh", type=float, default=0.5)
    parser.add_argument("--appearance_thresh", type=float, default=0.25)
    parser.add_argument("--fps", type=int, default=6)
    parser.add_argument("--device", default="cuda")
    return parser.parse_args()


def parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def resolve_repo_path(repo_dir: str, value: str, default_subdir: str = "") -> str:
    if not value:
        raise RuntimeError("Missing required repo-relative path")
    if os.path.isabs(value) and os.path.exists(value):
        return value
    candidate = os.path.join(repo_dir, value)
    if os.path.exists(candidate):
        return candidate
    if default_subdir:
        candidate = os.path.join(repo_dir, default_subdir, value)
        if os.path.exists(candidate):
            return candidate
    raise RuntimeError(f"Could not resolve required file: {value}")


def load_bgr_image(path: str) -> np.ndarray:
    image = cv2.imread(path, cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"Unable to read image: {path}")
    return image


def create_video_writer(path: str, width: int, height: int, fps: int):
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, float(max(1, fps)), (width, height))
    if not writer.isOpened():
        raise RuntimeError(f"Unable to create video writer: {path}")
    return writer


def build_preview_strip(frames: Sequence[np.ndarray]) -> np.ndarray:
    if not frames:
        return np.zeros((360, 960, 3), dtype=np.uint8)
    target_height = min(frame.shape[0] for frame in frames)
    resized = []
    for frame in frames:
        if frame.shape[0] == target_height:
            resized.append(frame)
            continue
        scale = target_height / frame.shape[0]
        resized.append(
            cv2.resize(frame,
                       (max(1, int(round(frame.shape[1] * scale))), target_height)))
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


def write_mot_results(path: str, frame_results: Sequence[Dict[str, object]]):
    lines = []
    for frame in frame_results:
        frame_id = int(frame["frame_index"]) + 1
        for obj in frame["objects"]:
            x, y, w, h = obj["bbox"]
            score = obj.get("score", 1.0)
            lines.append(
                f"{frame_id},{int(obj['track_id'])},{x:.2f},{y:.2f},{w:.2f},{h:.2f},{float(score):.4f},-1,-1,-1\n"
            )
    with open(path, "w", encoding="utf-8") as file:
        file.writelines(lines)


@contextmanager
def pushd(path: str):
    old_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_cwd)


def main():
    patch_python_compat()
    args = parse_args()

    repo_dir = os.path.abspath(args.repo_dir)
    if not os.path.isdir(repo_dir):
        raise RuntimeError(f"Official BoT-SORT repo not found: {repo_dir}")

    os.makedirs(os.path.dirname(args.output_video) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(args.output_preview) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(args.output_trajectory) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(args.output_mot) or ".", exist_ok=True)

    file_names = [name.strip() for name in args.file_names.split(",") if name.strip()]
    if len(file_names) < 2:
        print(json.dumps({
            "status": "error",
            "message": "Official BoT-SORT 至少需要 2 帧图像序列",
        }, ensure_ascii=False))
        sys.exit(1)

    os.environ.setdefault("FASTREID_DATASETS",
                          os.path.join(repo_dir, "fast_reid", "datasets"))
    if repo_dir not in sys.path:
        sys.path.insert(0, repo_dir)

    with pushd(repo_dir):
        import torch
        from yolox.data.data_augment import preproc
        from yolox.exp import get_exp
        from yolox.utils import fuse_model, get_model_info, postprocess
        from yolox.utils.visualize import plot_tracking
        from tracker.bot_sort import BoTSORT
        from tracker.tracking_utils.timer import Timer

        detector_ckpt = resolve_repo_path(repo_dir, args.detector_ckpt, "pretrained")
        exp_file = resolve_repo_path(repo_dir, args.exp_file)
        fast_reid_config = resolve_repo_path(repo_dir, args.fast_reid_config)
        fast_reid_weights = resolve_repo_path(repo_dir, args.fast_reid_weights, "pretrained")

        exp = get_exp(exp_file, None)

        class Predictor:
            def __init__(self, model, exp_obj, device_obj, fp16=False):
                self.model = model
                self.num_classes = exp_obj.num_classes
                self.confthre = exp_obj.test_conf
                self.nmsthre = exp_obj.nmsthre
                self.test_size = exp_obj.test_size
                self.device = device_obj
                self.fp16 = fp16
                self.rgb_means = (0.485, 0.456, 0.406)
                self.std = (0.229, 0.224, 0.225)

            def inference(self, img_path: str, timer_obj):
                img = cv2.imread(img_path)
                if img is None:
                    raise RuntimeError(f"Unable to read image: {img_path}")
                img_info = {
                    "file_name": os.path.basename(img_path),
                    "height": img.shape[0],
                    "width": img.shape[1],
                    "raw_img": img,
                }
                img_tensor, ratio = preproc(img, self.test_size, self.rgb_means, self.std)
                img_info["ratio"] = ratio
                img_tensor = torch.from_numpy(img_tensor).unsqueeze(0).float().to(self.device)
                if self.fp16:
                    img_tensor = img_tensor.half()
                with torch.no_grad():
                    timer_obj.tic()
                    outputs = self.model(img_tensor)
                    outputs = postprocess(outputs, self.num_classes, self.confthre,
                                          self.nmsthre)
                return outputs, img_info

        device = "cuda" if args.device == "auto" else args.device
        if device == "gpu":
            device = "cuda"
        if str(device).lower() == "cpu":
            raise RuntimeError("GPU-only inference requires CUDA device, got cpu")
        if device.startswith("cuda") and not torch.cuda.is_available():
            raise RuntimeError("CUDA requested but not available; refusing CPU inference")
        torch_device = torch.device(device)

        model = exp.get_model().to(torch_device)
        model.eval()
        log(f"Model Summary: {get_model_info(model, exp.test_size)}")

        ckpt = torch.load(detector_ckpt, map_location="cpu")
        model.load_state_dict(ckpt["model"])
        model = fuse_model(model)
        fp16 = torch_device.type == "cuda"
        if fp16:
            model = model.half()

        predictor = Predictor(model, exp, torch_device, fp16=fp16)

        tracker_args = argparse.Namespace(
            track_high_thresh=args.track_high_thresh,
            track_low_thresh=args.track_low_thresh,
            new_track_thresh=args.new_track_thresh,
            track_buffer=args.track_buffer,
            match_thresh=args.match_thresh,
            aspect_ratio_thresh=args.aspect_ratio_thresh,
            min_box_area=args.min_box_area,
            cmc_method=args.cmc_method,
            with_reid=parse_bool(args.with_reid),
            fast_reid_config=fast_reid_config,
            fast_reid_weights=fast_reid_weights,
            proximity_thresh=args.proximity_thresh,
            appearance_thresh=args.appearance_thresh,
            mot20=False,
            fps=args.fps,
            device=device,
            name="geoview_sequence",
            ablation=False,
        )
        tracker = BoTSORT(tracker_args, frame_rate=args.fps)
        timer = Timer()

        first_frame = load_bgr_image(os.path.join(args.input_dir, file_names[0]))
        height, width = first_frame.shape[:2]
        writer = create_video_writer(args.output_video, width, height, args.fps)
        preview_frames = []
        frame_results = []

        try:
            for index, file_name in enumerate(file_names):
                image_path = os.path.join(args.input_dir, file_name)
                outputs, img_info = predictor.inference(image_path, timer)
                frame = img_info["raw_img"]
                if frame.shape[:2] != (height, width):
                    frame = cv2.resize(frame, (width, height))
                    img_info["raw_img"] = frame
                    img_info["height"] = height
                    img_info["width"] = width

                scale = min(exp.test_size[0] / float(img_info["height"]),
                            exp.test_size[1] / float(img_info["width"]))
                objects = []
                online_tlwhs = []
                online_ids = []
                online_scores = []
                if outputs[0] is not None:
                    detections = outputs[0].cpu().numpy()[:, :7]
                    detections[:, :4] /= scale
                    online_targets = tracker.update(detections, img_info["raw_img"])
                    for target in online_targets:
                        tlwh = target.tlwh
                        tid = target.track_id
                        vertical = tlwh[2] / tlwh[3] > args.aspect_ratio_thresh
                        if tlwh[2] * tlwh[3] <= args.min_box_area or vertical:
                            continue
                        score = float(target.score)
                        bbox = [
                            int(round(tlwh[0])),
                            int(round(tlwh[1])),
                            int(round(tlwh[2])),
                            int(round(tlwh[3])),
                        ]
                        online_tlwhs.append(tlwh)
                        online_ids.append(tid)
                        online_scores.append(score)
                        objects.append({
                            "track_id": int(tid),
                            "label": "person",
                            "score": round(score, 4),
                            "bbox": bbox,
                        })
                timer.toc()
                annotated = plot_tracking(frame,
                                          online_tlwhs,
                                          online_ids,
                                          frame_id=index + 1,
                                          fps=1. / max(1e-5, timer.average_time))
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
        raise RuntimeError(f"Failed to write preview image: {args.output_preview}")

    write_mot_results(args.output_mot, frame_results)
    summary = compute_summary(frame_results)
    payload = {
        "status": "completed",
        "runtime_variant": "official",
        "method_used": "botsort_official_reid",
        "summary": summary,
        "frames": frame_results,
        "output_video": args.output_video,
        "output_preview": args.output_preview,
        "output_trajectory": args.output_trajectory,
        "output_mot": args.output_mot,
        "with_reid": parse_bool(args.with_reid),
        "exp_file": args.exp_file,
        "detector_ckpt": args.detector_ckpt,
    }
    with open(args.output_trajectory, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
