import json
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np

from applications.common.model_assets import load_model_manifest
from applications.common.path_global import generate_url, md5_name, up_url
from applications.common.utils.upload import img_url_handle

try:
    import rasterio
except Exception:
    rasterio = None


@dataclass
class FrameItem:
    filename: str
    relative_path: str
    absolute_path: str


class TrackingError(RuntimeError):
    pass


def execute(model_path: str, data_path: str, out_dir: str, names: List[dict],
            rect: Sequence[int]) -> dict:
    os.makedirs(out_dir, exist_ok=True)

    frames = _normalize_frames(names, data_path)
    if len(frames) < 2:
        raise TrackingError("至少需要上传 2 帧图像序列")

    tracker_mode = _normalize_model_path(model_path)
    first_frame_bgr = _load_bgr_image(frames[0].absolute_path)
    tracking_scale = _tracking_scale(first_frame_bgr.shape[1], first_frame_bgr.shape[0])

    first_tracking_frame = _resize_for_tracking(first_frame_bgr, tracking_scale)
    init_bbox = _scale_bbox(rect, tracking_scale)
    init_bbox = _clip_bbox(init_bbox, first_tracking_frame.shape[1],
                           first_tracking_frame.shape[0])
    if init_bbox[2] < 6 or init_bbox[3] < 6:
        raise TrackingError("初始框过小，无法稳定跟踪")

    tracker, method_used = _create_tracker(tracker_mode)
    if tracker is not None:
        tracker.init(first_tracking_frame, tuple(init_bbox))

    template = _extract_template(_build_feature_gray(first_tracking_frame), init_bbox)
    if template is None:
        raise TrackingError("无法从首帧提取目标模板")

    video_name = md5_name(f"tracking_{frames[0].filename}_sequence.mp4")
    preview_name = md5_name(f"tracking_{frames[0].filename}_preview.png")
    trajectory_name = md5_name(f"tracking_{frames[0].filename}_trajectory.json")

    video_path = os.path.join(out_dir, video_name)
    preview_path = os.path.join(out_dir, preview_name)
    trajectory_path = os.path.join(out_dir, trajectory_name)

    writer = _create_video_writer(video_path, first_tracking_frame.shape[1],
                                  first_tracking_frame.shape[0])

    trajectory = []
    preview_frames = []
    success_frames = 0
    confidence_values = []
    last_valid_bbox = init_bbox

    try:
        for index, frame_item in enumerate(frames):
            frame_bgr = _load_bgr_image(frame_item.absolute_path)
            tracking_frame = _resize_for_tracking(frame_bgr, tracking_scale)
            feature_gray = _build_feature_gray(tracking_frame)

            if index == 0:
                current_bbox = init_bbox
                confidence = 1.0
                ok = True
            else:
                ok, current_bbox, confidence, tracker, method_used = _track_next_frame(
                    tracker=tracker,
                    tracker_mode=tracker_mode,
                    method_used=method_used,
                    tracking_frame=tracking_frame,
                    feature_gray=feature_gray,
                    template=template,
                    last_valid_bbox=last_valid_bbox,
                )

                if ok and confidence >= 0.45:
                    new_template = _extract_template(feature_gray, current_bbox)
                    if new_template is not None:
                        template = _blend_template(template, new_template)

            current_bbox = _clip_bbox(current_bbox, tracking_frame.shape[1],
                                      tracking_frame.shape[0])
            last_valid_bbox = current_bbox

            bbox_original = _restore_bbox(current_bbox, tracking_scale)
            tracked = bool(ok and confidence >= 0.2)
            if tracked:
                success_frames += 1
            confidence_values.append(float(confidence))

            trajectory.append({
                "frame_index": index,
                "filename": frame_item.filename,
                "bbox": [int(value) for value in bbox_original],
                "confidence": round(float(confidence), 4),
                "tracked": tracked,
            })

            annotated = _draw_tracking_overlay(
                tracking_frame=tracking_frame,
                bbox=current_bbox,
                frame_index=index,
                confidence=confidence,
                tracked=tracked,
            )
            writer.write(annotated)

            if index in {0, len(frames) // 2, len(frames) - 1}:
                preview_frames.append(annotated.copy())
    finally:
        writer.release()

    preview_image = _build_preview_strip(preview_frames)
    if not cv2.imwrite(preview_path, preview_image):
        raise TrackingError("预览图写入失败")

    summary = _build_summary(
        model_path=model_path,
        method_used=method_used,
        trajectory=trajectory,
        confidence_values=confidence_values,
        sequence_length=len(frames),
    )
    with open(trajectory_path, "w", encoding="utf-8") as file:
        json.dump({
            "model_path": model_path,
            "method_used": method_used,
            "summary": summary,
            "frames": trajectory,
        }, file, ensure_ascii=False, indent=2)

    return {
        "status": "success",
        "method_used": method_used,
        "model_path": model_path,
        "first_frame_input": up_url + frames[0].relative_path,
        "preview_path": generate_url + preview_name,
        "output_video_path": generate_url + video_name,
        "trajectory_path": generate_url + trajectory_name,
        "summary": summary,
        "tracked_frame_count": success_frames,
        "total_frame_count": len(frames),
    }


def _normalize_frames(names: List[dict], data_path: str) -> List[FrameItem]:
    frames = []
    for item in names:
        if isinstance(item, dict):
            relative_path = item.get("src") or item.get("path") or item.get("name")
            filename = item.get("filename") or os.path.basename(relative_path or "")
        else:
            relative_path = item
            filename = os.path.basename(item)

        if not relative_path:
            continue

        relative_name = img_url_handle(relative_path)
        absolute_path = os.path.join(data_path, relative_name)
        if not os.path.exists(absolute_path):
            raise TrackingError(f"图像不存在: {relative_name}")

        frames.append(
            FrameItem(
                filename=filename or relative_name,
                relative_path=relative_name,
                absolute_path=absolute_path,
            ))

    if not frames:
        raise TrackingError("未找到可用的图像序列")

    frames.sort(key=lambda item: _natural_key(item.filename))
    return frames


def _normalize_model_path(model_path: Optional[str]) -> str:
    if model_path in ("builtin:tracking:auto", None, ""):
        return "auto"
    if model_path == "builtin:tracking:csrt":
        return "csrt"
    if model_path == "builtin:tracking:kcf":
        return "kcf"
    manifest = load_model_manifest(model_path)
    if manifest and manifest.get("backend") == "tracking":
        return manifest.get("runtime", "auto")
    raise TrackingError(f"不支持的跟踪模型: {model_path}")


def _create_tracker(mode: str):
    creators = []
    if mode == "auto":
        creators = [
            ("opencv_csrt", _tracker_creator("TrackerCSRT_create")),
            ("opencv_kcf", _tracker_creator("TrackerKCF_create")),
            ("opencv_mil", _tracker_creator("TrackerMIL_create")),
        ]
    elif mode == "csrt":
        creators = [
            ("opencv_csrt", _tracker_creator("TrackerCSRT_create")),
            ("opencv_kcf", _tracker_creator("TrackerKCF_create")),
            ("opencv_mil", _tracker_creator("TrackerMIL_create")),
        ]
    elif mode == "kcf":
        creators = [
            ("opencv_kcf", _tracker_creator("TrackerKCF_create")),
            ("opencv_mil", _tracker_creator("TrackerMIL_create")),
        ]

    for method_name, creator in creators:
        if creator is None:
            continue
        return creator(), method_name
    if mode == "auto":
        return None, "template_only"
    raise TrackingError("当前 OpenCV 环境缺少可用跟踪器，请检查 opencv-contrib 支持")


def _reinitialize_tracker(mode: str, tracking_frame: np.ndarray,
                          bbox: Sequence[float],
                          fallback_method: str):
    tracker, method_used = _create_tracker(mode)
    if tracker is None:
        return None, method_used or fallback_method
    try:
        tracker.init(tracking_frame, tuple(bbox))
    except Exception:
        tracker, method_used = _create_tracker("auto")
        if tracker is not None:
            tracker.init(tracking_frame, tuple(bbox))
    return tracker, method_used or fallback_method


def _track_next_frame(tracker,
                      tracker_mode: str,
                      method_used: str,
                      tracking_frame: np.ndarray,
                      feature_gray: np.ndarray,
                      template: np.ndarray,
                      last_valid_bbox: Sequence[int]):
    if tracker is None:
        return _track_with_template_only(
            tracker_mode=tracker_mode,
            method_used=method_used,
            tracking_frame=tracking_frame,
            feature_gray=feature_gray,
            template=template,
            last_valid_bbox=last_valid_bbox,
        )

    ok, tracker_bbox = tracker.update(tracking_frame)
    tracker_bbox = _clip_bbox(
        tracker_bbox if ok else last_valid_bbox,
        tracking_frame.shape[1],
        tracking_frame.shape[0],
    )

    refined_bbox, confidence = _template_refine(
        feature_gray=feature_gray,
        template=template,
        anchor_bbox=tracker_bbox,
        search_scale=2.4 if ok else None,
    )

    if refined_bbox is None and ok:
        refined_bbox, confidence = _template_refine(
            feature_gray=feature_gray,
            template=template,
            anchor_bbox=last_valid_bbox,
            search_scale=None,
        )

    if refined_bbox is not None and confidence >= 0.35:
        current_bbox = refined_bbox
        tracker, method_used = _reinitialize_tracker(
            tracker_mode,
            tracking_frame,
            current_bbox,
            fallback_method=method_used,
        )
        return True, current_bbox, float(confidence), tracker, method_used

    current_bbox = tracker_bbox
    confidence = 0.0 if not ok else max(0.0, confidence)
    return bool(ok), current_bbox, float(confidence), tracker, method_used


def _track_with_template_only(tracker_mode: str,
                              method_used: str,
                              tracking_frame: np.ndarray,
                              feature_gray: np.ndarray,
                              template: np.ndarray,
                              last_valid_bbox: Sequence[int]):
    refined_bbox, confidence = _template_refine(
        feature_gray=feature_gray,
        template=template,
        anchor_bbox=last_valid_bbox,
        search_scale=2.8,
    )
    if refined_bbox is None:
        refined_bbox, confidence = _template_refine(
            feature_gray=feature_gray,
            template=template,
            anchor_bbox=last_valid_bbox,
            search_scale=None,
        )

    if refined_bbox is None:
        return False, list(last_valid_bbox), 0.0, None, method_used

    current_bbox = _clip_bbox(refined_bbox, tracking_frame.shape[1],
                              tracking_frame.shape[0])
    tracked = confidence >= 0.2
    return tracked, current_bbox, float(confidence), None, method_used


def _tracker_creator(name: str):
    direct = getattr(cv2, name, None)
    if direct is not None:
        return direct

    legacy = getattr(cv2, "legacy", None)
    if legacy is not None:
        legacy_creator = getattr(legacy, name, None)
        if legacy_creator is not None:
            return legacy_creator
    return None


def _tracking_scale(width: int, height: int) -> float:
    max_dim = max(width, height)
    if max_dim <= 1280:
        return 1.0
    return 1280.0 / float(max_dim)


def _resize_for_tracking(frame_bgr: np.ndarray, scale: float) -> np.ndarray:
    if scale >= 0.999:
        return frame_bgr
    width = max(64, int(round(frame_bgr.shape[1] * scale)))
    height = max(64, int(round(frame_bgr.shape[0] * scale)))
    return cv2.resize(frame_bgr, (width, height), interpolation=cv2.INTER_AREA)


def _scale_bbox(rect: Sequence[int], scale: float) -> List[int]:
    x, y, w, h = rect
    return [
        max(0, int(round(x * scale))),
        max(0, int(round(y * scale))),
        max(1, int(round(w * scale))),
        max(1, int(round(h * scale))),
    ]


def _restore_bbox(rect: Sequence[float], scale: float) -> List[int]:
    if scale <= 0:
        return [int(value) for value in rect]

    inv = 1.0 / scale
    x, y, w, h = rect
    return [
        int(round(x * inv)),
        int(round(y * inv)),
        int(round(w * inv)),
        int(round(h * inv)),
    ]


def _clip_bbox(rect: Sequence[float], width: int, height: int) -> List[int]:
    x, y, w, h = [float(value) for value in rect]
    x = max(0.0, min(x, width - 1))
    y = max(0.0, min(y, height - 1))
    w = max(1.0, min(w, width - x))
    h = max(1.0, min(h, height - y))
    return [int(round(x)), int(round(y)), int(round(w)), int(round(h))]


def _template_refine(feature_gray: np.ndarray, template: np.ndarray,
                     anchor_bbox: Sequence[int],
                     search_scale: Optional[float]) -> Tuple[Optional[List[int]], float]:
    if template is None or template.size == 0:
        return None, 0.0

    frame_height, frame_width = feature_gray.shape[:2]
    x, y, w, h = [int(value) for value in anchor_bbox]
    if search_scale is None:
        left, top = 0, 0
        right, bottom = frame_width, frame_height
    else:
        margin_x = max(w, int(round(w * search_scale)))
        margin_y = max(h, int(round(h * search_scale)))
        left = max(0, x - margin_x)
        top = max(0, y - margin_y)
        right = min(frame_width, x + w + margin_x)
        bottom = min(frame_height, y + h + margin_y)

    search_region = feature_gray[top:bottom, left:right]
    if (search_region.shape[0] < template.shape[0]
            or search_region.shape[1] < template.shape[1]):
        return None, 0.0

    match_map = cv2.matchTemplate(search_region, template, cv2.TM_CCOEFF_NORMED)
    _, max_score, _, max_loc = cv2.minMaxLoc(match_map)
    refined_bbox = [
        int(left + max_loc[0]),
        int(top + max_loc[1]),
        int(template.shape[1]),
        int(template.shape[0]),
    ]
    refined_bbox = _clip_bbox(refined_bbox, frame_width, frame_height)
    return refined_bbox, float(max_score)


def _extract_template(feature_gray: np.ndarray,
                      rect: Sequence[int]) -> Optional[np.ndarray]:
    x, y, w, h = [int(value) for value in rect]
    crop = feature_gray[y:y + h, x:x + w]
    if crop.size == 0 or crop.shape[0] < 6 or crop.shape[1] < 6:
        return None
    return crop.copy()


def _blend_template(template: np.ndarray, new_template: np.ndarray) -> np.ndarray:
    if template.shape != new_template.shape:
        new_template = cv2.resize(new_template,
                                  (template.shape[1], template.shape[0]),
                                  interpolation=cv2.INTER_LINEAR)
    return cv2.addWeighted(template, 0.7, new_template, 0.3, 0)


def _build_feature_gray(frame_bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(gray)
    blur = cv2.GaussianBlur(clahe, (0, 0), 1.2)
    return cv2.addWeighted(clahe, 1.2, blur, -0.2, 0)


def _draw_tracking_overlay(tracking_frame: np.ndarray, bbox: Sequence[int],
                           frame_index: int, confidence: float,
                           tracked: bool) -> np.ndarray:
    annotated = tracking_frame.copy()
    x, y, w, h = [int(value) for value in bbox]
    color = (0, 220, 0) if tracked else (0, 0, 255)
    label = f"Frame {frame_index:03d} | conf {confidence:.2f}"

    cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
    cv2.rectangle(annotated, (12, 12), (300, 52), (20, 20, 20), -1)
    cv2.putText(annotated, label, (20, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                (255, 255, 255), 2, cv2.LINE_AA)
    return annotated


def _build_preview_strip(frames: List[np.ndarray]) -> np.ndarray:
    if not frames:
        return np.zeros((256, 256, 3), dtype=np.uint8)

    resized = []
    for frame in frames[:3]:
        height, width = frame.shape[:2]
        target_width = 360
        scale = target_width / float(width)
        target_height = max(120, int(round(height * scale)))
        resized.append(
            cv2.resize(frame, (target_width, target_height),
                       interpolation=cv2.INTER_AREA))

    max_height = max(frame.shape[0] for frame in resized)
    padded = []
    for frame in resized:
        if frame.shape[0] == max_height:
            padded.append(frame)
            continue
        pad = np.zeros((max_height - frame.shape[0], frame.shape[1], 3),
                       dtype=np.uint8)
        padded.append(np.vstack([frame, pad]))
    return np.hstack(padded)


def _build_summary(model_path: str, method_used: str, trajectory: List[dict],
                   confidence_values: List[float],
                   sequence_length: int) -> Dict[str, object]:
    tracked_frames = len([item for item in trajectory if item["tracked"]])
    mean_confidence = (sum(confidence_values) / len(confidence_values)
                       if confidence_values else 0.0)
    start_bbox = trajectory[0]["bbox"]
    end_bbox = trajectory[-1]["bbox"]
    displacement = _bbox_center_distance(start_bbox, end_bbox)

    return {
        "model_path": model_path,
        "method_used": method_used,
        "total_frames": sequence_length,
        "tracked_frames": tracked_frames,
        "lost_frames": max(0, sequence_length - tracked_frames),
        "tracking_ratio": round(tracked_frames / sequence_length, 4),
        "mean_confidence": round(float(mean_confidence), 4),
        "start_bbox": start_bbox,
        "end_bbox": end_bbox,
        "center_displacement": round(float(displacement), 2),
    }


def _bbox_center_distance(box_a: Sequence[int], box_b: Sequence[int]) -> float:
    ax = box_a[0] + box_a[2] / 2.0
    ay = box_a[1] + box_a[3] / 2.0
    bx = box_b[0] + box_b[2] / 2.0
    by = box_b[1] + box_b[3] / 2.0
    return float(np.hypot(ax - bx, ay - by))


def _create_video_writer(path: str, width: int, height: int):
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, 10.0, (width, height))
    if not writer.isOpened():
        raise TrackingError("结果视频写入失败，请检查 OpenCV 编码器支持")
    return writer


def _load_bgr_image(path: str) -> np.ndarray:
    ext = os.path.splitext(path)[1].lower()
    if ext in {".tif", ".tiff"}:
        if rasterio is None:
            raise TrackingError("当前环境未安装 rasterio，无法读取 TIFF 序列")
        with rasterio.open(path) as dataset:
            array = dataset.read()
        if array.size == 0:
            raise TrackingError(f"无法读取图像: {path}")
        return _multiband_to_bgr(array)

    image = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if image is None:
        raise TrackingError(f"无法读取图像: {path}")

    if image.ndim == 2:
        image = np.stack([image] * 3, axis=-1)
    elif image.shape[2] == 4:
        image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)

    if image.dtype != np.uint8:
        image = _normalize_to_uint8(image)
    return image


def _multiband_to_bgr(array: np.ndarray) -> np.ndarray:
    bands = array.shape[0]
    if bands >= 3:
        rgb = np.stack([array[0], array[1], array[2]], axis=-1)
    elif bands == 2:
        mean_band = ((array[0].astype(np.float32) + array[1].astype(np.float32))
                     / 2.0)
        rgb = np.stack([array[0], array[1], mean_band], axis=-1)
    else:
        rgb = np.stack([array[0], array[0], array[0]], axis=-1)
    rgb = _normalize_to_uint8(rgb)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def _normalize_to_uint8(image: np.ndarray) -> np.ndarray:
    image = np.nan_to_num(image.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    if image.ndim == 2:
        return _robust_channel_normalize(image)
    channels = []
    for index in range(image.shape[2]):
        channels.append(_robust_channel_normalize(image[:, :, index]))
    return np.stack(channels, axis=-1)


def _robust_channel_normalize(channel: np.ndarray) -> np.ndarray:
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


def _natural_key(value: str):
    return [int(part) if part.isdigit() else part.lower()
            for part in re.split(r"(\d+)", value)]
