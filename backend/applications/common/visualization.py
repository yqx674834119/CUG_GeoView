import copy
import json
import os
from typing import Any, Dict, List, Optional

import cv2
import numpy as np

from applications.common.asset_transport import (build_asset_transport,
                                                 build_record_media_transports)
from applications.common.path_global import generate_dir
from applications.common.utils import type_utils

VISUAL_PAYLOAD_KEY = "__visual_payload"
VISUAL_SCHEMA = "geoview.visualization.v1"


def ensure_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return copy.deepcopy(value)
    if value in (None, ""):
        return {}
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return {}
    return {}


def sanitize_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): sanitize_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize_json(item) for item in value]
    if isinstance(value, np.ndarray):
        return sanitize_json(value.tolist())
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def build_visual_payload(analysis_type: str,
                         renderer: str,
                         source: Optional[Dict[str, Any]] = None,
                         result: Optional[Dict[str, Any]] = None,
                         metrics: Optional[Dict[str, Any]] = None,
                         capabilities: Optional[Dict[str, Any]] = None,
                         legacy_assets: Optional[Dict[str, Any]] = None,
                         meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return sanitize_json({
        "schema": VISUAL_SCHEMA,
        "spec_version": 1,
        "transport": "json_only",
        "analysis_type": analysis_type,
        "renderer": renderer,
        "source": source or {},
        "result": result or {},
        "metrics": metrics or {},
        "capabilities": {
            "legacy_render_available": True,
            "frontend_renderable": True,
            "requires_local_source": True,
            "transport_modes": ["original", "base64", "json"],
            **(capabilities or {}),
        },
        "legacy_assets": legacy_assets or {},
        "meta": meta or {},
    })


def attach_visual_payload(data: Any,
                          payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    normalized = ensure_dict(data)
    if payload:
        normalized[VISUAL_PAYLOAD_KEY] = sanitize_json(payload)
    return normalized


def extract_visual_payload(data: Any) -> Optional[Dict[str, Any]]:
    normalized = ensure_dict(data)
    payload = normalized.get(VISUAL_PAYLOAD_KEY)
    return payload if isinstance(payload, dict) else None


def image_size_from_file(path: str) -> Dict[str, int]:
    if not path or not os.path.exists(path):
        return {}
    image = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if image is None:
        return {}
    height, width = image.shape[:2]
    return {"width": int(width), "height": int(height)}


def resolve_generated_path(public_path: str) -> str:
    normalized = str(public_path or "").replace("\\", "/")
    if normalized.startswith(generate_dir):
        return normalized
    if normalized.startswith("/api/file/assets/photos/res/"):
        return os.path.join(generate_dir, normalized.split("/res/", 1)[1])
    if normalized.startswith("/_uploads/photos/res/"):
        return os.path.join(generate_dir, normalized.split("/res/", 1)[1])
    return normalized


def _normalize_points(points: np.ndarray, width: int, height: int) -> List[List[float]]:
    normalized = []
    safe_width = max(int(width), 1)
    safe_height = max(int(height), 1)
    for point in points:
        x = round(float(point[0]) / safe_width, 6)
        y = round(float(point[1]) / safe_height, 6)
        normalized.append([x, y])
    return normalized


def extract_binary_regions(mask: np.ndarray,
                           min_area: float = 8.0,
                           max_regions: int = 128,
                           epsilon_ratio: float = 0.003) -> List[Dict[str, Any]]:
    if mask is None:
        return []

    if mask.ndim == 3:
        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
    mask = np.where(mask > 0, 255, 0).astype(np.uint8)
    height, width = mask.shape[:2]
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    regions = []
    for contour in contours[:max_regions]:
        area = float(cv2.contourArea(contour))
        if area < min_area:
            continue
        perimeter = cv2.arcLength(contour, True)
        epsilon = max(1.0, perimeter * epsilon_ratio)
        approx = cv2.approxPolyDP(contour, epsilon, True).reshape(-1, 2)
        x, y, w, h = cv2.boundingRect(contour)
        regions.append({
            "area": round(area, 2),
            "bbox": [int(x), int(y), int(w), int(h)],
            "points": _normalize_points(approx, width, height),
        })
    return regions


def extract_class_regions(mask: np.ndarray,
                          class_names: List[str],
                          palette: List[List[int]],
                          min_area: float = 24.0,
                          max_regions_per_class: int = 24) -> Dict[str, Any]:
    if mask is None:
        return {"classes": [], "totals": {}}

    height, width = mask.shape[:2]
    total_pixels = int(height * width)
    classes = []
    totals = {}
    for class_index, class_name in enumerate(class_names):
        class_mask = np.where(mask == class_index, 255, 0).astype(np.uint8)
        pixel_count = int(np.count_nonzero(class_mask))
        if pixel_count <= 0:
            continue
        totals[class_name] = pixel_count
        regions = extract_binary_regions(
            class_mask,
            min_area=min_area,
            max_regions=max_regions_per_class,
        )
        classes.append({
            "index": int(class_index),
            "name": class_name,
            "color": palette[class_index] if class_index < len(palette) else [255, 255, 255],
            "pixel_count": pixel_count,
            "ratio": round(pixel_count / max(total_pixels, 1), 6),
            "regions": regions,
        })
    return {
        "classes": classes,
        "totals": totals,
        "image_size": {
            "width": int(width),
            "height": int(height),
        },
        "pixel_count": total_pixels,
    }


def build_legacy_visual_payload(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    analysis_type = item.get("type")
    data = ensure_dict(item.get("data"))
    if analysis_type == "场景分类" and data:
        score_items = [
            {"label": key, "score": float(value)}
            for key, value in data.items()
            if key != VISUAL_PAYLOAD_KEY and isinstance(value, (int, float))
        ]
        if not score_items:
            return None
        score_items.sort(key=lambda entry: entry["score"], reverse=True)
        return build_visual_payload(
            analysis_type=analysis_type,
            renderer="scene_classification",
            source={"primary": {"asset_path": item.get("before_img")}},
            result={"scores": score_items},
            metrics={"top_label": score_items[0]["label"], "top_score": score_items[0]["score"]},
            legacy_assets={"primary_result": item.get("after_img")},
        )

    if analysis_type == "变化检测" and data:
        return build_visual_payload(
            analysis_type=analysis_type,
            renderer="change_detection",
            source={
                "primary": {"asset_path": item.get("before_img")},
                "secondary": {"asset_path": item.get("before_img1")},
            },
            result={
                "mask_path": data.get("mask"),
                "mask_hole_path": data.get("mask_hole"),
            },
            metrics={
                "change_count": data.get("count"),
                "fractional_variation": data.get("fractional_variation"),
            },
            legacy_assets={"primary_result": item.get("after_img")},
        )

    if analysis_type == "自动配准" and data:
        return build_visual_payload(
            analysis_type=analysis_type,
            renderer="registration",
            source={
                "primary": {"asset_path": item.get("before_img")},
                "secondary": {"asset_path": item.get("before_img1")},
            },
            result={
                "transform_type": data.get("transform_type"),
                "transform_matrix": data.get("transform_matrix"),
            },
            metrics={
                "match_count": data.get("match_count"),
                "inlier_count": data.get("inlier_count"),
                "inlier_ratio": data.get("inlier_ratio"),
                "rmse": data.get("rmse"),
            },
            legacy_assets={
                "primary_result": item.get("after_img"),
                "overlay_path": data.get("overlay_path"),
                "checkerboard_path": data.get("checkerboard_path"),
            },
        )

    if analysis_type == "目标跟踪" and data:
        return build_visual_payload(
            analysis_type=analysis_type,
            renderer="tracking",
            source={
                "primary": {"asset_path": data.get("source_input_path") or item.get("before_img")},
                "input_mode": data.get("input_mode", "image_sequence"),
            },
            result={},
            metrics=data.get("summary", {}),
            legacy_assets={
                "preview_path": item.get("after_img"),
                "video_path": data.get("output_video_path"),
                "trajectory_path": data.get("trajectory_path"),
            },
        )

    return None


def _has_base64_transport(value: Any) -> bool:
    if isinstance(value, dict):
        if value.get("preview_data_url"):
            return True
        return any(_has_base64_transport(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_base64_transport(item) for item in value)
    return False


def normalize_analysis_record(item: Dict[str, Any]) -> Dict[str, Any]:
    normalized = copy.deepcopy(item)
    if "type" in normalized and isinstance(normalized["type"], int):
        normalized["type"] = type_utils.type_to_str(normalized["type"])

    data = ensure_dict(normalized.get("data"))
    if normalized.get("type") == "变化检测":
        if not data.get("mask") and normalized.get("after_img"):
            stem, ext = normalized["after_img"].rsplit(".", 1) if "." in normalized["after_img"] else (normalized["after_img"], "png")
            data["mask"] = f"{stem}_mask.{ext}"
        if data.get("hole") and not data.get("mask_hole"):
            stem, ext = data["hole"].rsplit(".", 1) if "." in data["hole"] else (data["hole"], "png")
            data["mask_hole"] = f"{stem}_mask.{ext}"
    normalized["data"] = data

    payload = extract_visual_payload(data) or build_legacy_visual_payload(normalized)
    if isinstance(payload, dict):
        source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
        for key, value in list(source.items()):
            if isinstance(value, dict) and value.get("asset_path"):
                source[key]["transport"] = build_asset_transport(value.get("asset_path"), preview_max_size=640)
        legacy_assets = payload.get("legacy_assets") if isinstance(payload.get("legacy_assets"), dict) else {}
        for key, value in list(legacy_assets.items()):
            if isinstance(value, str):
                legacy_assets[key] = {
                    "asset_path": value,
                    "transport": build_asset_transport(value, preview_max_size=640),
                }
    normalized["visual_payload"] = payload
    normalized["json_visualization_available"] = bool(payload)
    normalized["media_transports"] = build_record_media_transports(normalized, preview_max_size=420)
    normalized["visualization_modes"] = ["original"]
    if _has_base64_transport(normalized["media_transports"]):
        normalized["visualization_modes"].append("base64")
    if payload:
        normalized["visualization_modes"].append("json")
    return normalized
