#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MMRotate Inference Script

此脚本在 MMSeg310 环境中运行，使用本地显式模型目录进行旋转目标检测推理。
"""

import argparse
import json
import os
import sys
import traceback
import cv2
import numpy as np
import collections
from collections import abc


def patch_openmmlab_version_guards():
    try:
        import mmcv
        if getattr(mmcv, "__version__", "") in {"2.1.0", "2.2.0"}:
            mmcv.__version__ = "2.0.1"
    except Exception:
        pass


def patch_python_compat():
    for name in ("Sequence", "Mapping", "MutableMapping"):
        if not hasattr(collections, name) and hasattr(abc, name):
            setattr(collections, name, getattr(abc, name))

    try:
        import mmdet
        version = getattr(mmdet, "__version__", "")
        if version:
            from mmengine.utils import digit_version
            if digit_version(version) > digit_version("3.1.0"):
                mmdet.__version__ = "3.1.0"
    except Exception:
        pass


def resolve_local_artifacts(model_dir: str):
    model_dir = os.path.abspath(model_dir)
    config_file = os.path.join(model_dir, "config.py")
    checkpoint_file = os.path.join(model_dir, "checkpoint.pth")

    if not os.path.exists(config_file):
        for filename in os.listdir(model_dir):
            if filename.endswith(".py"):
                config_file = os.path.join(model_dir, filename)
                break
    if not os.path.exists(checkpoint_file):
        for filename in os.listdir(model_dir):
            if filename.endswith(".pth"):
                checkpoint_file = os.path.join(model_dir, filename)
                break

    if not os.path.exists(config_file):
        raise FileNotFoundError(f"MMRotate config not found in {model_dir}")
    if not os.path.exists(checkpoint_file):
        raise FileNotFoundError(f"MMRotate checkpoint not found in {model_dir}")
    return config_file, checkpoint_file


def _label_name(dataset_meta, label_index: int) -> str:
    classes = None
    if isinstance(dataset_meta, dict):
        classes = dataset_meta.get("classes")
    if classes and 0 <= label_index < len(classes):
        return str(classes[label_index])
    return str(label_index)


def _serialize_rotated_box(raw_box: np.ndarray):
    values = np.asarray(raw_box, dtype=float).reshape(-1).tolist()
    if len(values) >= 8:
        points = [[round(float(values[i]), 2), round(float(values[i + 1]), 2)] for i in range(0, 8, 2)]
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        bbox = [round(min(xs), 2), round(min(ys), 2), round(max(xs), 2), round(max(ys), 2)]
        return {"polygon": points, "box": bbox}
    if len(values) >= 5:
        cx, cy, w, h, angle = values[:5]
        rect = ((float(cx), float(cy)), (float(w), float(h)), float(np.degrees(angle)))
        points = cv2.boxPoints(rect)
        points = [[round(float(point[0]), 2), round(float(point[1]), 2)] for point in points]
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        bbox = [round(min(xs), 2), round(min(ys), 2), round(max(xs), 2), round(max(ys), 2)]
        return {
            "polygon": points,
            "box": bbox,
            "rbox": [
                round(float(cx), 2),
                round(float(cy), 2),
                round(float(w), 2),
                round(float(h), 2),
                round(float(angle), 4),
            ],
        }
    return {"box": [round(float(value), 2) for value in values[:4]]}


def run_inference(
    model_dir: str,
    input_dir: str,
    output_dir: str,
    file_names: list,
    device: str = "cuda:0",
    score_thr: float = 0.3,
) -> dict:
    patch_openmmlab_version_guards()
    patch_python_compat()

    try:
        import mmdet  # noqa: F401
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "MMRotate runtime dependency missing: mmdet is not installed in the MMSeg310 "
            "environment. Please rebuild the Docker image so the current Dockerfile can "
            "install the OpenMMLab detection stack."
        ) from exc

    import mmrotate  # noqa: F401
    if str(device).startswith("cuda"):
        try:
            import torch
            if not torch.cuda.is_available():
                raise RuntimeError("CUDA requested but not available; refusing CPU inference")
        except Exception:
            raise RuntimeError("CUDA requested but unavailable; refusing CPU inference")

    from mmdet.apis import init_detector, inference_detector
    from mmrotate.visualization import RotLocalVisualizer

    config_file, checkpoint_file = resolve_local_artifacts(model_dir)
    print(
        f"Initializing model with config: {config_file} and checkpoint: {checkpoint_file}",
        file=sys.stderr,
    )
    model = init_detector(config_file, checkpoint_file, device=device)

    visualizer = RotLocalVisualizer()
    visualizer.dataset_meta = model.dataset_meta

    os.makedirs(output_dir, exist_ok=True)
    results = []

    for filename in file_names:
        try:
            img_path = os.path.join(input_dir, filename)
            if not os.path.exists(img_path):
                results.append({
                    "name": filename,
                    "status": "error",
                    "message": "File not found",
                })
                continue

            result = inference_detector(model, img_path)
            img = cv2.imread(img_path)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            pred_instances = getattr(result, "pred_instances", None)
            detections = []
            if pred_instances is not None:
                bboxes = pred_instances.bboxes.cpu().numpy() if hasattr(pred_instances, "bboxes") else []
                scores = pred_instances.scores.cpu().numpy() if hasattr(pred_instances, "scores") else []
                labels = pred_instances.labels.cpu().numpy() if hasattr(pred_instances, "labels") else []
                for bbox, score, label in zip(bboxes, scores, labels):
                    serialized = _serialize_rotated_box(bbox)
                    serialized["score"] = round(float(score), 4)
                    serialized["label"] = _label_name(model.dataset_meta, int(label))
                    detections.append(serialized)

            out_name = f"det_{filename}"
            out_path = os.path.join(output_dir, out_name)
            visualizer.add_datasample(
                "result",
                img,
                data_sample=result,
                draw_gt=False,
                show=False,
                out_file=out_path,
                pred_score_thr=score_thr,
            )
            results.append({
                "name": out_name,
                "status": "success",
                "output_path": out_path,
                "image_size": {
                    "width": int(img.shape[1]),
                    "height": int(img.shape[0]),
                },
                "detections": detections,
            })
            print(f"Processed {filename} -> {out_name}", file=sys.stderr)
        except Exception as exc:
            print(f"Error processing {filename}: {exc}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            results.append({
                "name": filename,
                "status": "error",
                "message": str(exc),
            })

    return {"status": "completed", "results": results}


def main():
    parser = argparse.ArgumentParser(description="MMRotate Inference")
    parser.add_argument("--model_dir", required=True, help="Local model directory")
    parser.add_argument("--input_dir", required=True, help="Input directory")
    parser.add_argument("--output_dir", required=True, help="Output directory")
    parser.add_argument("--file_names", required=True, help="Comma-separated file names")
    parser.add_argument("--device", default="cuda:0", help="Device")
    parser.add_argument("--score_thr", type=float, default=0.3, help="Score threshold")

    args = parser.parse_args()
    file_names = [f.strip() for f in args.file_names.split(",") if f.strip()]

    try:
        result = run_inference(
            model_dir=args.model_dir,
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            file_names=file_names,
            device=args.device,
            score_thr=args.score_thr,
        )
        print(json.dumps(result))
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
