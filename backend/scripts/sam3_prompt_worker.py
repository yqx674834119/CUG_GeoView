#!/usr/bin/env python
"""Run SAM3 prompt inference inside the isolated SAM3 conda environment."""

from __future__ import annotations

import argparse
import contextlib
import inspect
import json
import os
import sys
import time
import uuid
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def _to_numpy(value):
    if hasattr(value, "detach"):
        value = value.detach()
        if str(getattr(value, "dtype", "")) == "torch.bfloat16":
            value = value.float()
        return value.cpu().numpy()
    if hasattr(value, "cpu"):
        return value.cpu().numpy()
    return np.asarray(value)


def _mask_bbox(mask):
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    if not rows.any() or not cols.any():
        return [0, 0, 0, 0]
    y0, y1 = np.where(rows)[0][[0, -1]]
    x0, x1 = np.where(cols)[0][[0, -1]]
    return [int(x0), int(y0), int(x1 - x0 + 1), int(y1 - y0 + 1)]


def _save_mask(path, mask):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    mask_u8 = np.where(mask, 255, 0).astype(np.uint8)
    if not cv2.imwrite(str(path), mask_u8):
        raise RuntimeError(f"SAM3 mask write failed: {path}")
    return mask_u8


def _color_for_index(index):
    palette = [
        (255, 64, 64),
        (64, 210, 120),
        (64, 150, 255),
        (255, 190, 64),
        (190, 96, 255),
        (64, 220, 220),
    ]
    return palette[index % len(palette)]


def _overlay_masks(frame_bgr, masks):
    overlay = frame_bgr.copy()
    for index, mask in enumerate(masks):
        if not np.any(mask):
            continue
        color = np.array(_color_for_index(index), dtype=np.uint8)
        color_layer = np.zeros_like(overlay)
        color_layer[:, :] = color
        overlay = np.where(mask[..., None], cv2.addWeighted(overlay, 0.62, color_layer, 0.38, 0), overlay)
        contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(overlay, contours, -1, (255, 255, 255), 2)
    return overlay


def _torch_inference_context(device):
    import torch

    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    if str(device).startswith("cuda") and torch.cuda.is_available():
        return torch.autocast("cuda", dtype=torch.bfloat16)
    return contextlib.nullcontext()


def _load_image_model(checkpoint_path, confidence_threshold, device):
    from sam3 import build_sam3_image_model
    from sam3.model.sam3_image_processor import Sam3Processor

    bpe_path = "/opt/sam3/sam3/assets/bpe_simple_vocab_16e6.txt.gz"
    model = build_sam3_image_model(
        bpe_path=bpe_path if os.path.exists(bpe_path) else None,
        checkpoint_path=checkpoint_path,
        load_from_HF=False,
        device=device,
        compile=False,
    )
    return Sam3Processor(model, confidence_threshold=confidence_threshold)


def _run_image(payload):
    import torch

    prompt = payload["prompt_text"]
    device = payload.get("device", "cuda")

    results = []
    with _torch_inference_context(device):
        processor = _load_image_model(
            checkpoint_path=payload["checkpoint_path"],
            confidence_threshold=float(payload.get("confidence_threshold", 0.5)),
            device=device,
        )
        for job in payload.get("jobs", []):
            image_path = job["image_path"]
            image = Image.open(image_path).convert("RGB")
            state = processor.set_image(image)
            processor.reset_all_prompts(state)
            state = processor.set_text_prompt(prompt=prompt, state=state)

            masks = _to_numpy(state.get("masks", np.zeros((0, 1, image.height, image.width), dtype=bool)))
            scores = _to_numpy(state.get("scores", np.zeros((masks.shape[0],), dtype=np.float32))).reshape(-1)
            boxes = _to_numpy(state.get("boxes", np.zeros((masks.shape[0], 4), dtype=np.float32)))
            if masks.ndim == 4:
                masks = masks[:, 0]
            masks = masks.astype(bool)
            union_mask = np.any(masks, axis=0) if masks.size else np.zeros((image.height, image.width), dtype=bool)
            mask_u8 = _save_mask(job["mask_path"], union_mask)

            detections = []
            for index, mask in enumerate(masks):
                if not mask.any():
                    continue
                score = float(scores[index]) if index < len(scores) else 0.0
                box = [float(value) for value in boxes[index].tolist()] if index < len(boxes) else []
                detections.append(
                    {
                        "label": prompt,
                        "score": round(score, 5),
                        "bbox_xyxy": [round(value, 2) for value in box],
                        "bbox_xywh": _mask_bbox(mask),
                        "area": int(mask.sum()),
                    }
                )

            results.append(
                {
                    "image_path": image_path,
                    "mask_path": job["mask_path"],
                    "width": image.width,
                    "height": image.height,
                    "pixel_count": int(np.count_nonzero(mask_u8)),
                    "detections": detections,
                }
            )
            del state
            if device == "cuda":
                torch.cuda.empty_cache()
    return {"mode": "image", "prompt_text": prompt, "results": results}


def _build_preview_strip(frames):
    if not frames:
        return np.zeros((360, 640, 3), dtype=np.uint8)
    target_h = min(360, max(160, min(frame.shape[0] for frame in frames)))
    resized = []
    for frame in frames:
        scale = target_h / max(frame.shape[0], 1)
        width = max(1, int(round(frame.shape[1] * scale)))
        resized.append(cv2.resize(frame, (width, target_h), interpolation=cv2.INTER_AREA))
    return cv2.hconcat(resized)


def _patch_multiplex_start_session(predictor):
    parameters = inspect.signature(predictor.model.init_state).parameters
    if "offload_state_to_cpu" in parameters:
        return

    def start_session(resource_path, session_id=None, offload_video_to_cpu=False, offload_state_to_cpu=False):
        init_kwargs = {
            "resource_path": resource_path,
            "offload_video_to_cpu": offload_video_to_cpu,
        }
        if hasattr(predictor, "async_loading_frames"):
            init_kwargs["async_loading_frames"] = predictor.async_loading_frames
        if hasattr(predictor, "video_loader_type"):
            init_kwargs["video_loader_type"] = predictor.video_loader_type
        init_kwargs = {key: value for key, value in init_kwargs.items() if key in parameters}
        inference_state = predictor.model.init_state(**init_kwargs)
        session_id = session_id or str(uuid.uuid4())
        predictor._all_inference_states[session_id] = {
            "state": inference_state,
            "session_id": session_id,
            "start_time": time.time(),
            "last_use_time": time.time(),
        }
        return {"session_id": session_id}

    predictor.start_session = start_session


def _run_video(payload):
    from sam3.model_builder import build_sam3_multiplex_video_predictor

    frame_dir = Path(payload["frame_dir"])
    frame_paths = sorted(
        [
            path
            for path in frame_dir.iterdir()
            if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        ]
    )
    if len(frame_paths) < 2:
        raise RuntimeError("SAM3 video prompt tracking requires at least 2 frames")

    prompt = payload["prompt_text"]
    predictor = build_sam3_multiplex_video_predictor(
        checkpoint_path=payload["checkpoint_path"],
        use_fa3=False,
        use_rope_real=True,
        compile=False,
        warm_up=False,
        async_loading_frames=False,
        default_output_prob_thresh=float(payload.get("confidence_threshold", 0.5)),
    )
    _patch_multiplex_start_session(predictor)
    response = predictor.handle_request(
        request={"type": "start_session", "resource_path": str(frame_dir)}
    )
    session_id = response["session_id"]
    response = predictor.handle_request(
        request={
            "type": "add_prompt",
            "session_id": session_id,
            "frame_index": 0,
            "text": prompt,
        }
    )
    outputs_per_frame = {0: response["outputs"]}
    for stream_response in predictor.handle_stream_request(
        request={"type": "propagate_in_video", "session_id": session_id}
    ):
        outputs_per_frame[int(stream_response["frame_index"])] = stream_response["outputs"]

    first_frame = cv2.imread(str(frame_paths[0]))
    if first_frame is None:
        raise RuntimeError(f"SAM3 could not read first frame: {frame_paths[0]}")
    height, width = first_frame.shape[:2]
    fps = float(payload.get("fps") or 8.0)
    output_video_path = payload["output_video_path"]
    Path(output_video_path).parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        output_video_path,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )
    if not writer.isOpened():
        raise RuntimeError(f"SAM3 could not open output video: {output_video_path}")

    preview_frames = []
    frames_payload = []
    confidence_values = []
    unique_ids = set()
    tracked_frames = 0
    total_detections = 0
    max_concurrent = 0

    try:
        for frame_index, frame_path in enumerate(frame_paths):
            frame_bgr = cv2.imread(str(frame_path))
            if frame_bgr is None:
                continue
            out = outputs_per_frame.get(frame_index) or {}
            masks = _to_numpy(out.get("out_binary_masks", np.zeros((0, height, width), dtype=bool)))
            obj_ids = _to_numpy(out.get("out_obj_ids", np.zeros((0,), dtype=np.int64))).reshape(-1)
            probs = _to_numpy(out.get("out_probs", np.zeros((len(obj_ids),), dtype=np.float32))).reshape(-1)
            if masks.ndim == 4:
                masks = masks[:, 0]
            masks = masks.astype(bool)

            detections = []
            for index, mask in enumerate(masks):
                if not mask.any():
                    continue
                obj_id = int(obj_ids[index]) if index < len(obj_ids) else index
                score = float(probs[index]) if index < len(probs) else 0.0
                bbox = _mask_bbox(mask)
                detections.append(
                    {
                        "track_id": obj_id,
                        "label": prompt,
                        "bbox": bbox,
                        "score": round(score, 5),
                        "area": int(mask.sum()),
                    }
                )
                unique_ids.add(obj_id)
                confidence_values.append(score)

            total_detections += len(detections)
            max_concurrent = max(max_concurrent, len(detections))
            tracked = bool(detections)
            if tracked:
                tracked_frames += 1
            annotated = _overlay_masks(frame_bgr, masks)
            cv2.putText(
                annotated,
                f"Text prompt: {prompt} | frame {frame_index} | objects {len(detections)}",
                (18, 34),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.78,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )
            writer.write(annotated)
            if frame_index in {0, len(frame_paths) // 2, len(frame_paths) - 1}:
                preview_frames.append(annotated.copy())
            frames_payload.append(
                {
                    "frame_index": frame_index,
                    "filename": frame_path.name,
                    "tracked": tracked,
                    "detections": detections,
                }
            )
    finally:
        writer.release()
        with contextlib.suppress(Exception):
            predictor.handle_request(request={"type": "close_session", "session_id": session_id})

    preview = _build_preview_strip(preview_frames)
    preview_path = payload["preview_path"]
    if not cv2.imwrite(preview_path, preview):
        raise RuntimeError(f"SAM3 preview write failed: {preview_path}")

    total_frames = len(frames_payload)
    lost_frames = max(0, total_frames - tracked_frames)
    mean_confidence = float(np.mean(confidence_values)) if confidence_values else 0.0
    summary = {
        "total_frames": total_frames,
        "tracked_frames": tracked_frames,
        "lost_frames": lost_frames,
        "tracking_ratio": round(tracked_frames / max(total_frames, 1), 4),
        "mean_confidence": round(mean_confidence, 5),
        "unique_track_count": len(unique_ids),
        "total_detections": total_detections,
        "max_concurrent_tracks": max_concurrent,
        "label_histogram": {prompt: total_detections},
    }
    trajectory = {
        "model_path": payload.get("model_path"),
        "method_used": "sam3.1_prompt_dense_tracking",
        "prompt_text": prompt,
        "summary": summary,
        "frames": frames_payload,
    }
    with open(payload["trajectory_path"], "w", encoding="utf-8") as file:
        json.dump(trajectory, file, ensure_ascii=False, indent=2)

    return {
        "mode": "video",
        "prompt_text": prompt,
        "summary": summary,
        "frame_count": total_frames,
    }


def _main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    with open(args.input, "r", encoding="utf-8") as file:
        payload = json.load(file)
    mode = payload.get("mode")
    if mode == "image":
        return _run_image(payload)
    if mode == "video":
        return _run_video(payload)
    raise ValueError(f"Unsupported SAM3 worker mode: {mode}")


if __name__ == "__main__":
    with contextlib.redirect_stdout(sys.stderr):
        result = _main()
    print(json.dumps(result, ensure_ascii=False))
