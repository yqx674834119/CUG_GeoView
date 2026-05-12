import json
import os
import re
import shutil
import subprocess
import tempfile
from contextlib import suppress
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np

from applications.common.model_assets import (load_model_manifest,
                                              resolve_model_dir,
                                              resolve_repo_path)
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


@dataclass
class TrackingInputBundle:
    frames: List[FrameItem]
    input_mode: str
    first_frame_input: str
    source_input_path: str
    source_input_name: str
    temp_dir: str = ""


class TrackingError(RuntimeError):
    pass


def _public_source_sequence_paths(input_bundle: TrackingInputBundle,
                                  frames: Sequence[FrameItem]) -> List[str]:
    if input_bundle.input_mode == "video":
        return []
    return [up_url + frame.relative_path for frame in frames]


VIDEO_EXTENSIONS = {
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
    ".m4v",
    ".webm",
    ".mpg",
    ".mpeg",
}

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".tif",
    ".tiff",
    ".webp",
}

BROWSER_VIDEO_SUFFIX = ".mp4"


def requires_initial_rect(model_path: Optional[str]) -> bool:
    return _resolve_tracking_runtime(model_path) not in {
        "botsort",
        "botsort_engineering",
        "botsort_official",
    }


def execute(model_path: str, data_path: str, out_dir: str, names: List[dict],
            rect: Optional[Sequence[int]]) -> dict:
    os.makedirs(out_dir, exist_ok=True)

    input_bundle = _prepare_tracking_input(names, data_path, out_dir)
    frames = input_bundle.frames
    if len(frames) < 2:
        raise TrackingError("至少需要上传 2 帧图像，或 1 个包含至少 2 帧的有效视频")

    try:
        tracker_mode = _resolve_tracking_runtime(model_path)
        if tracker_mode in {"botsort", "botsort_engineering"}:
            return _execute_botsort_engineering(model_path, out_dir, frames, input_bundle)
        if tracker_mode == "botsort_official":
            return _execute_botsort_official(model_path, out_dir, frames, input_bundle)

        if rect is None or len(rect) != 4:
            raise TrackingError("当前跟踪模型需要提供初始跟踪框")

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

        _rewrite_video_for_web(video_path)

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
            "first_frame_input": input_bundle.first_frame_input,
            "source_input_path": input_bundle.source_input_path,
            "source_input_name": input_bundle.source_input_name,
            "source_sequence_paths": _public_source_sequence_paths(input_bundle, frames),
            "input_mode": input_bundle.input_mode,
            "preview_path": generate_url + preview_name,
            "output_video_path": generate_url + video_name,
            "trajectory_path": generate_url + trajectory_name,
            "summary": summary,
            "tracked_frame_count": success_frames,
            "total_frame_count": len(frames),
        }
    finally:
        _cleanup_tracking_input(input_bundle)


def _execute_botsort_engineering(model_path: str, out_dir: str,
                                 frames: Sequence[FrameItem],
                                 input_bundle: TrackingInputBundle) -> dict:
    from applications.interface.hf_inference_caller import call_hf_botsort_tracking

    manifest = load_model_manifest(model_path) or {}
    model_dir = resolve_model_dir(model_path)

    video_name = md5_name(f"tracking_{frames[0].filename}_botsort_sequence.mp4")
    preview_name = md5_name(f"tracking_{frames[0].filename}_botsort_preview.png")
    trajectory_name = md5_name(f"tracking_{frames[0].filename}_botsort_trajectory.json")

    video_path = os.path.join(out_dir, video_name)
    preview_path = os.path.join(out_dir, preview_name)
    trajectory_path = os.path.join(out_dir, trajectory_name)

    detector_model_id = manifest.get("detector_model_id", "StephanST/WALDO30")
    detector_weight_file = manifest.get("detector_weight_file",
                                        "WALDO30_yolov8l-p2_1024x1024.pt")
    tracker_config_name = manifest.get("tracker_config", "botsort.yaml")
    tracker_config_path = str(model_dir / tracker_config_name)

    output_data = call_hf_botsort_tracking(
        input_dir=os.path.dirname(frames[0].absolute_path),
        file_names=[frame.relative_path for frame in frames],
        output_video_path=video_path,
        output_preview_path=preview_path,
        output_trajectory_path=trajectory_path,
        model_id=detector_model_id,
        model_file=detector_weight_file,
        tracker_config=tracker_config_path,
    )
    _rewrite_video_for_web(video_path)

    summary = output_data.get("summary") or {}
    tracked_frames = int(summary.get("tracked_frames", 0))
    return {
        "status": "success",
        "runtime_variant": "engineering",
        "method_used": output_data.get("method_used", "ultralytics_botsort"),
        "model_path": model_path,
        "first_frame_input": input_bundle.first_frame_input,
        "source_input_path": input_bundle.source_input_path,
        "source_input_name": input_bundle.source_input_name,
        "source_sequence_paths": _public_source_sequence_paths(input_bundle, frames),
        "input_mode": input_bundle.input_mode,
        "preview_path": generate_url + preview_name,
        "output_video_path": generate_url + video_name,
        "trajectory_path": generate_url + trajectory_name,
        "summary": summary,
        "tracked_frame_count": tracked_frames,
        "total_frame_count": len(frames),
    }


def _resolve_input_items(names: List[dict], data_path: str) -> List[FrameItem]:
    items = []
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
            raise TrackingError(f"输入文件不存在: {relative_name}")

        items.append(
            FrameItem(
                filename=filename or relative_name,
                relative_path=relative_name,
                absolute_path=absolute_path,
            ))

    if not items:
        raise TrackingError("未找到可用的跟踪输入")

    return items


def _normalize_frames(names: List[dict], data_path: str) -> List[FrameItem]:
    frames = _resolve_input_items(names, data_path)
    for item in frames:
        ext = os.path.splitext(item.filename)[1].lower()
        if ext not in IMAGE_EXTENSIONS:
            raise TrackingError("当前输入包含非图像文件，请上传图像序列或单个视频文件")

    frames.sort(key=lambda item: _natural_key(item.filename))
    return frames


def _execute_botsort_official(model_path: str, out_dir: str,
                              frames: Sequence[FrameItem],
                              input_bundle: TrackingInputBundle) -> dict:
    from applications.interface.hf_inference_caller import call_botsort_official_tracking

    manifest = load_model_manifest(model_path) or {}

    video_name = md5_name(f"tracking_{frames[0].filename}_botsort_official_sequence.mp4")
    preview_name = md5_name(f"tracking_{frames[0].filename}_botsort_official_preview.png")
    trajectory_name = md5_name(
        f"tracking_{frames[0].filename}_botsort_official_trajectory.json")
    mot_name = md5_name(f"tracking_{frames[0].filename}_botsort_official_tracks.txt")

    video_path = os.path.join(out_dir, video_name)
    preview_path = os.path.join(out_dir, preview_name)
    trajectory_path = os.path.join(out_dir, trajectory_name)
    mot_path = os.path.join(out_dir, mot_name)

    output_data = call_botsort_official_tracking(
        input_dir=os.path.dirname(frames[0].absolute_path),
        file_names=[frame.relative_path for frame in frames],
        output_video_path=video_path,
        output_preview_path=preview_path,
        output_trajectory_path=trajectory_path,
        output_mot_path=mot_path,
        repo_dir=str(resolve_repo_path(manifest.get("official_repo_dir",
                                                    "backend/runtime/BoT-SORT"))),
        exp_file=str(manifest.get("exp_file",
                                  "yolox/exps/example/mot/yolox_x_mix_det.py")),
        detector_ckpt=str(manifest.get("detector_ckpt_file",
                                       "bytetrack_x_mot17.pth.tar")),
        with_reid=bool(manifest.get("with_reid", True)),
        fast_reid_config=str(manifest.get("fast_reid_config",
                                          "fast_reid/configs/MOT17/sbs_S50.yml")),
        fast_reid_weights=str(manifest.get("fast_reid_weights_file",
                                           "mot17_sbs_S50.pth")),
        cmc_method=str(manifest.get("cmc_method", "orb")),
        track_high_thresh=float(manifest.get("track_high_thresh", 0.6)),
        track_low_thresh=float(manifest.get("track_low_thresh", 0.1)),
        new_track_thresh=float(manifest.get("new_track_thresh", 0.7)),
        track_buffer=int(manifest.get("track_buffer", 30)),
        match_thresh=float(manifest.get("match_thresh", 0.8)),
        min_box_area=float(manifest.get("min_box_area", 10)),
        aspect_ratio_thresh=float(manifest.get("aspect_ratio_thresh", 1.6)),
        proximity_thresh=float(manifest.get("proximity_thresh", 0.5)),
        appearance_thresh=float(manifest.get("appearance_thresh", 0.25)),
    )
    _rewrite_video_for_web(video_path)

    summary = output_data.get("summary") or {}
    tracked_frames = int(summary.get("tracked_frames", 0))
    return {
        "status": "success",
        "runtime_variant": "official",
        "method_used": output_data.get("method_used", "botsort_official_reid"),
        "model_path": model_path,
        "first_frame_input": input_bundle.first_frame_input,
        "source_input_path": input_bundle.source_input_path,
        "source_input_name": input_bundle.source_input_name,
        "source_sequence_paths": _public_source_sequence_paths(input_bundle, frames),
        "input_mode": input_bundle.input_mode,
        "preview_path": generate_url + preview_name,
        "output_video_path": generate_url + video_name,
        "trajectory_path": generate_url + trajectory_name,
        "mot_result_path": generate_url + mot_name,
        "summary": summary,
        "tracked_frame_count": tracked_frames,
        "total_frame_count": len(frames),
    }


def _prepare_tracking_input(names: List[dict], data_path: str,
                            out_dir: str) -> TrackingInputBundle:
    items = _resolve_input_items(names, data_path)
    extensions = {os.path.splitext(item.filename)[1].lower() for item in items}
    has_video = any(ext in VIDEO_EXTENSIONS for ext in extensions)
    has_image = any(ext in IMAGE_EXTENSIONS for ext in extensions)

    if has_video and has_image:
        raise TrackingError("请上传单个视频文件，或多帧图像序列，暂不支持混合输入")
    if has_video:
        if len(items) != 1:
            raise TrackingError("视频跟踪当前仅支持上传 1 个视频文件")
        return _extract_video_frames(items[0], out_dir)

    if not has_image:
        raise TrackingError("当前跟踪仅支持图像序列或常见视频文件")

    items.sort(key=lambda item: _natural_key(item.filename))
    return TrackingInputBundle(
        frames=items,
        input_mode="image_sequence",
        first_frame_input=up_url + items[0].relative_path,
        source_input_path="",
        source_input_name=f"{len(items)} frame sequence",
    )


def _extract_video_frames(video_item: FrameItem,
                          out_dir: str) -> TrackingInputBundle:
    capture = cv2.VideoCapture(video_item.absolute_path)
    if not capture.isOpened():
        raise TrackingError(f"无法读取视频: {video_item.filename}")

    temp_dir = tempfile.mkdtemp(prefix="tracking_video_", dir=out_dir)
    frames: List[FrameItem] = []
    first_frame_bgr = None
    frame_index = 0

    try:
        while True:
            ok, frame = capture.read()
            if not ok or frame is None:
                break

            if first_frame_bgr is None:
                first_frame_bgr = frame.copy()

            frame_name = f"{frame_index:06d}.jpg"
            frame_path = os.path.join(temp_dir, frame_name)
            if not cv2.imwrite(frame_path, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95]):
                raise TrackingError("视频解帧失败，无法写入临时帧图像")

            frames.append(
                FrameItem(
                    filename=frame_name,
                    relative_path=frame_name,
                    absolute_path=frame_path,
                ))
            frame_index += 1
    finally:
        capture.release()

    if len(frames) < 2 or first_frame_bgr is None:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise TrackingError("视频帧数不足，至少需要 2 帧有效内容")

    preview_base = os.path.splitext(os.path.basename(video_item.filename))[0]
    preview_name = md5_name(f"tracking_{preview_base[:48]}_input_preview.png")
    source_preview_name = md5_name(f"tracking_{preview_base[:48]}_source_preview{BROWSER_VIDEO_SUFFIX}")
    preview_path = os.path.join(out_dir, preview_name)
    source_preview_path = os.path.join(out_dir, source_preview_name)
    if not cv2.imwrite(preview_path, first_frame_bgr):
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise TrackingError("视频首帧预览图写入失败")

    normalized_source_path = _transcode_video_for_web(
        video_item.absolute_path,
        source_preview_path,
    )
    if normalized_source_path:
        source_input_path = generate_url + os.path.basename(normalized_source_path)
    else:
        source_input_path = up_url + video_item.relative_path

    return TrackingInputBundle(
        frames=frames,
        input_mode="video",
        first_frame_input=generate_url + preview_name,
        source_input_path=source_input_path,
        source_input_name=video_item.filename,
        temp_dir=temp_dir,
    )


def _cleanup_tracking_input(bundle: TrackingInputBundle):
    if bundle.temp_dir:
        shutil.rmtree(bundle.temp_dir, ignore_errors=True)


def _resolve_tracking_runtime(model_path: Optional[str]) -> str:
    if model_path in ("builtin:tracking:auto", None, ""):
        return "botsort"
    if model_path == "builtin:tracking:botsort":
        return "botsort"
    if model_path == "builtin:tracking:botsort_engineering":
        return "botsort_engineering"
    if model_path == "builtin:tracking:botsort_official":
        _ensure_official_botsort_enabled(None)
        return "botsort_official"
    if model_path == "builtin:tracking:csrt":
        raise TrackingError("CSRT CPU 跟踪已禁用；当前交付只允许 GPU BoT-SORT 跟踪")
    if model_path == "builtin:tracking:kcf":
        raise TrackingError("KCF CPU 跟踪已禁用；当前交付只允许 GPU BoT-SORT 跟踪")
    manifest = load_model_manifest(model_path)
    if manifest and manifest.get("backend") == "tracking":
        runtime = manifest.get("runtime", "auto")
        if runtime == "auto":
            return "botsort"
        if runtime in {"csrt", "kcf"}:
            raise TrackingError("CPU 跟踪模型已禁用；当前交付只允许 GPU BoT-SORT 跟踪")
        if runtime == "botsort_official":
            _ensure_official_botsort_enabled(manifest)
        return runtime
    raise TrackingError(f"不支持的跟踪模型: {model_path}")


def _ensure_official_botsort_enabled(manifest: Optional[dict]):
    repo_dir = (manifest or {}).get(
        "official_repo_dir",
        "backend/runtime/BoT-SORT",
    )
    if os.path.isdir(resolve_repo_path(repo_dir)):
        return
    raise TrackingError(
        "Official BoT-SORT 运行目录不存在；请确认 BoT-SORT 官方仓库已随交付环境提供。"
    )


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


def _transcode_video_for_web(source_path: str,
                             output_path: Optional[str] = None) -> Optional[str]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not os.path.isfile(source_path):
        return None

    target_path = output_path or f"{source_path}.h264.mp4"
    os.makedirs(os.path.dirname(target_path) or ".", exist_ok=True)

    cmd = [
        ffmpeg,
        "-y",
        "-i",
        source_path,
        "-map",
        "0:v:0",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-an",
        target_path,
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=1800,
    )
    if result.returncode != 0 or not os.path.isfile(target_path):
        with suppress(Exception):
            os.remove(target_path)
        print(
            f"[Tracking] ffmpeg transcode failed for {source_path}: {result.stderr}",
            flush=True,
        )
        return None
    return target_path


def _rewrite_video_for_web(source_path: str):
    temp_output_path = f"{source_path}.h264.mp4"
    normalized_path = _transcode_video_for_web(source_path, temp_output_path)
    if not normalized_path:
        return
    os.replace(normalized_path, source_path)


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
