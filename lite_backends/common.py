import base64
import json
import mimetypes
import os
import platform
import shutil
import socket
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import unquote

from PIL import Image, ImageDraw, UnidentifiedImageError


SUCCESS = 0
FAIL = 1
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".bmp"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
TYPE_MAP = ["", "变化检测", "目标检测", "地物分类", "场景分类", "影像超分重建", "自动配准", "目标跟踪"]


def env_bool(name: str, default: str = "false") -> bool:
    return str(os.getenv(name, default)).strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


VARIANT = os.getenv("GEOVIEW_LITE_VARIANT", "lite")
PORT = env_int("PORT", 5008)
SAMPLE_DIR = Path(os.getenv("GEOVIEW_SAMPLE_DIR", "/app/sample_assets"))
STATIC_ROOT = Path(os.getenv("GEOVIEW_EXTERNAL_STATIC_ROOT", "/data/geoview-lite/static"))
UPLOAD_ROOT = Path(os.getenv("UPLOADED_PHOTOS_DEST", str(STATIC_ROOT / "upload")))
RES_ROOT = UPLOAD_ROOT / "res"
TRANSFER_MODE = os.getenv("GEOVIEW_TRANSFER_MODE", "chunked").strip().lower()
OMIT_CONTENT_LENGTH = env_bool("GEOVIEW_OMIT_CONTENT_LENGTH", "true")
DEBUG_LOG = env_bool("GEOVIEW_DEBUG_LOG", "true")
CHUNK_SIZE = max(8192, env_int("GEOVIEW_CHUNK_SIZE", 65536))

_HISTORY: List[dict] = []
_NEXT_ID = 1


@dataclass
class FileSpec:
    path: Path
    relative_path: str
    status_code: int
    media_type: str
    headers: Dict[str, str]
    start: int = 0
    end: Optional[int] = None
    body: Optional[bytes] = None
    head_only: bool = False


def debug(scope: str, message: str, **extra) -> None:
    if not DEBUG_LOG:
        return
    payload = {
        "ts": datetime.now().isoformat(timespec="milliseconds"),
        "variant": VARIANT,
        **extra,
    }
    print(f"[GeoView轻量后端调试][{scope}] {message} {json.dumps(payload, ensure_ascii=False, default=str)}", flush=True)


def success_api(msg: str = "成功", data=None) -> dict:
    return {"success": True, "code": SUCCESS, "msg": msg, "data": {} if data is None else data}


def fail_api(msg: str = "失败", code_id: int = FAIL) -> dict:
    return {"success": False, "code": code_id, "msg": msg}


def table_api(data=None, count: int = 0, limit: int = 10, msg: str = "") -> dict:
    return {"success": True, "msg": msg, "code": SUCCESS, "data": [] if data is None else data, "count": count, "limit": limit}


def json_bytes(payload: dict) -> Tuple[bytes, Dict[str, str]]:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return body, {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "no-cache",
        "X-GeoView-Json-Bytes": str(len(body)),
    }


def cors_headers() -> Dict[str, str]:
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS,HEAD",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Expose-Headers": (
            "Content-Length,Content-Range,Accept-Ranges,X-GeoView-Request-Id,"
            "X-GeoView-Disk-Size,X-GeoView-Bytes-Sent,X-GeoView-Json-Bytes"
        ),
    }


def request_id() -> str:
    return uuid.uuid4().hex[:12]


def log_request(req_id: str, method: str, path: str, query: str = "", headers=None, client: str = "") -> None:
    headers = headers or {}
    debug(
        "后端请求",
        "收到前端/客户端请求",
        request_id=req_id,
        method=method,
        path=path,
        query=query,
        client=client,
        range=headers.get("range") or headers.get("Range") or "",
        request_content_length=headers.get("content-length") or headers.get("Content-Length") or "",
        transfer_encoding=headers.get("transfer-encoding") or headers.get("Transfer-Encoding") or "",
        forwarded_for=headers.get("x-forwarded-for") or headers.get("X-Forwarded-For") or "",
    )


def log_response(req_id: str, method: str, path: str, status_code: int, headers=None, bytes_sent: int = 0, started_at: float = 0.0) -> None:
    headers = headers or {}
    debug(
        "后端请求",
        "请求处理完成",
        request_id=req_id,
        method=method,
        path=path,
        status_code=status_code,
        response_content_length=headers.get("Content-Length", ""),
        content_range=headers.get("Content-Range", ""),
        transfer_mode=TRANSFER_MODE,
        bytes_sent=bytes_sent,
        elapsed_ms=int((time.time() - started_at) * 1000) if started_at else 0,
    )


def normalize_relative_path(value: str) -> str:
    normalized = str(value or "").replace("\\", "/").split("?", 1)[0].strip()
    prefixes = (
        "/api/file/assets-preview/photos/",
        "/api/file/assets-buffered/photos/",
        "/api/file/assets/photos/",
        "/_uploads/photos/",
        "/static/upload/",
    )
    for prefix in prefixes:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
            break
    normalized = normalized.lstrip("/")
    parts = [part for part in normalized.split("/") if part not in ("", ".")]
    if any(part == ".." for part in parts):
        return ""
    return "/".join(parts)


def asset_url(relative_path: str) -> str:
    return f"/api/file/assets/photos/{normalize_relative_path(relative_path)}"


def buffered_asset_url(relative_path: str) -> str:
    return f"/api/file/assets-buffered/photos/{normalize_relative_path(relative_path)}"


def legacy_asset_url(relative_path: str) -> str:
    return f"/_uploads/photos/{normalize_relative_path(relative_path)}"


def absolute_asset_path(relative_path: str) -> Optional[Path]:
    normalized = normalize_relative_path(relative_path)
    if not normalized:
        return None
    candidate = (UPLOAD_ROOT / normalized).resolve()
    root = UPLOAD_ROOT.resolve()
    if not (str(candidate) == str(root) or str(candidate).startswith(str(root) + os.sep)):
        return None
    return candidate if candidate.is_file() else None


def sample_rel(name: str) -> str:
    return name


def output_rel(name: str) -> str:
    return f"res/{name}"


def copy_if_present(src: Path, dest: Path) -> bool:
    if not src.is_file():
        debug("启动探测", "样例文件不存在，跳过复制", src=str(src), dest=str(dest))
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists() or dest.stat().st_size != src.stat().st_size:
        shutil.copy2(src, dest)
    return True


def ensure_runtime_assets() -> None:
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    RES_ROOT.mkdir(parents=True, exist_ok=True)
    mapping = {
        "cd_val1_2_3mb.png": sample_rel("cd_val1_2_3mb.png"),
        "cd_val2_2_0mb.png": sample_rel("cd_val2_2_0mb.png"),
        "scene_7_7mb.png": sample_rel("scene_7_7mb.png"),
        "aircraft_100kb.jpg": sample_rel("aircraft_100kb.jpg"),
        "aircraft_200kb.jpg": sample_rel("aircraft_200kb.jpg"),
        "seg_787kb.tif": sample_rel("seg_787kb.tif"),
        "mask_8kb.png": output_rel("mask_8kb.png"),
        "pred_440kb.png": output_rel("pred_440kb.png"),
        "tracking_12mb.mp4": sample_rel("tracking_12mb.mp4"),
    }
    for source_name, rel_path in mapping.items():
        copy_if_present(SAMPLE_DIR / source_name, UPLOAD_ROOT / rel_path)

    derived = {
        output_rel("cd_result_2mb.png"): sample_rel("cd_val2_2_0mb.png"),
        output_rel("object_result_200kb.jpg"): sample_rel("aircraft_200kb.jpg"),
        output_rel("scene_result_7mb.png"): sample_rel("scene_7_7mb.png"),
        output_rel("restored_2mb.png"): sample_rel("cd_val1_2_3mb.png"),
        output_rel("registration_output.png"): output_rel("pred_440kb.png"),
        output_rel("tracking_preview.png"): sample_rel("aircraft_100kb.jpg"),
        output_rel("tracking_output.mp4"): sample_rel("tracking_12mb.mp4"),
    }
    for dest_rel, src_rel in derived.items():
        src = UPLOAD_ROOT / src_rel
        dest = UPLOAD_ROOT / dest_rel
        if src.is_file():
            copy_if_present(src, dest)

    trajectory = UPLOAD_ROOT / output_rel("tracking_trajectory.json")
    trajectory.write_text(json.dumps({
        "frames": [{"frame": index, "tracks": [{"id": 1, "bbox": [40 + index, 30, 90, 70], "score": 0.91}]} for index in range(8)],
        "summary": {"track_count": 1, "frame_count": 8},
    }, ensure_ascii=False), encoding="utf-8")


def build_preview_data_url(relative_path: str, max_size: int = 420, quality: int = 75) -> str:
    path = absolute_asset_path(relative_path)
    if not path or path.suffix.lower() not in IMAGE_EXTS:
        return ""
    try:
        with Image.open(path) as image:
            image.load()
            preview = image.copy()
            preview.thumbnail((max(64, min(max_size, 1600)), max(64, min(max_size, 1600))), Image.LANCZOS)
            has_alpha = preview.mode in ("RGBA", "LA") or (preview.mode == "P" and "transparency" in preview.info)
            out = bytearray()
            import io
            bio = io.BytesIO()
            if has_alpha:
                preview.convert("RGBA").save(bio, format="PNG", optimize=True)
                mime = "image/png"
            else:
                preview.convert("RGB").save(bio, format="JPEG", quality=quality, optimize=True)
                mime = "image/jpeg"
            out.extend(bio.getvalue())
            return f"data:{mime};base64,{base64.b64encode(bytes(out)).decode('ascii')}"
    except Exception as exc:
        debug("资源预览", "生成内联预览失败", relative_path=relative_path, error=str(exc))
        return ""


def build_preview_payload(relative_path: str, max_size: int = 420, quality: int = 75) -> dict:
    path = absolute_asset_path(relative_path)
    if not path:
        raise FileNotFoundError(relative_path)
    started_at = time.time()
    with Image.open(path) as image:
        image.load()
        original_width, original_height = image.size
        preview = image.copy()
    preview.thumbnail((max(64, min(max_size, 1600)), max(64, min(max_size, 1600))), Image.LANCZOS)
    import io
    output = io.BytesIO()
    if preview.mode in ("RGBA", "LA") or (preview.mode == "P" and "transparency" in preview.info):
        preview.convert("RGBA").save(output, format="PNG", optimize=True)
        mime = "image/png"
        fmt = "png"
    else:
        preview.convert("RGB").save(output, format="JPEG", quality=max(40, min(quality, 95)), optimize=True)
        mime = "image/jpeg"
        fmt = "jpeg"
    payload = output.getvalue()
    debug(
        "资源预览",
        "图片预览 base64 已生成",
        relative_path=relative_path,
        absolute_path=str(path),
        original_size=path.stat().st_size,
        preview_size=len(payload),
        max_size=max_size,
        elapsed_ms=int((time.time() - started_at) * 1000),
    )
    return {
        "filename": path.name,
        "mimetype": mime,
        "format": fmt,
        "data_url": f"data:{mime};base64,{base64.b64encode(payload).decode('ascii')}",
        "source_store": "lite",
        "original_size": path.stat().st_size,
        "original_width": original_width,
        "original_height": original_height,
        "preview_size": len(payload),
        "preview_width": preview.width,
        "preview_height": preview.height,
        "max_size": max_size,
        "duration_ms": int((time.time() - started_at) * 1000),
    }


def safe_draw_text(value: str, max_len: int = 96) -> str:
    text = str(value or "").strip()
    if len(text) > max_len:
        text = "..." + text[-max_len:]
    return text.encode("latin-1", "replace").decode("latin-1")


def source_image_for_annotation(source_path: str, fallback_rel: str) -> Path:
    source = absolute_asset_path(source_path)
    if source and source.suffix.lower() in IMAGE_EXTS:
        return source
    fallback = absolute_asset_path(fallback_rel)
    if fallback and fallback.suffix.lower() in IMAGE_EXTS:
        return fallback
    raise FileNotFoundError(fallback_rel)


def create_annotated_image(source_path: str, prefix: str, title: str, model_path: str, mode: str = "object") -> str:
    ensure_runtime_assets()
    fallback = sample_rel("aircraft_200kb.jpg") if mode == "object" else output_rel("tracking_preview.png")
    image_path = source_image_for_annotation(source_path, fallback)
    started = time.time()
    with Image.open(image_path) as image:
        image.load()
        canvas = image.convert("RGB")

    draw = ImageDraw.Draw(canvas)
    width, height = canvas.size
    band_h = max(72, min(140, height // 5))
    draw.rectangle([(0, 0), (width, band_h)], fill=(0, 0, 0))
    lines = [
        safe_draw_text(f"GeoView Lite {title}"),
        safe_draw_text(f"model: {model_path or '未选择模型'}"),
        safe_draw_text(f"source: {normalize_relative_path(source_path) or image_path.name}"),
    ]
    y = 10
    for line in lines:
        draw.text((18, y), line, fill=(255, 230, 120))
        y += 20

    if mode == "tracking":
        box = (
            max(8, width // 5),
            max(band_h + 8, height // 4),
            min(width - 8, width // 5 + max(80, width // 4)),
            min(height - 8, height // 4 + max(70, height // 4)),
        )
        draw.rectangle(box, outline=(48, 255, 120), width=max(3, width // 220))
        draw.text((box[0], max(0, box[1] - 18)), "track_id=1 score=0.91", fill=(48, 255, 120))
    else:
        boxes = [
            (width * 0.18, height * 0.28, width * 0.42, height * 0.55, "aircraft 0.93"),
            (width * 0.52, height * 0.36, width * 0.76, height * 0.62, "vehicle 0.88"),
        ]
        for x1, y1, x2, y2, label in boxes:
            box = (int(x1), int(y1), int(x2), int(y2))
            draw.rectangle(box, outline=(255, 70, 70), width=max(3, width // 240))
            draw.text((box[0], max(0, box[1] - 18)), label, fill=(255, 70, 70))

    output_rel_path = output_rel(f"{prefix}_{uuid.uuid4().hex[:12]}.jpg")
    output_path = UPLOAD_ROOT / output_rel_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, format="JPEG", quality=92, optimize=True)
    debug(
        "轻量处理",
        "已生成带模型文字的处理后图像",
        mode=mode,
        source=str(image_path),
        output=output_rel_path,
        model_path=model_path,
        size=output_path.stat().st_size,
        elapsed_ms=int((time.time() - started) * 1000),
    )
    return asset_url(output_rel_path)


def create_tracking_video(source_path: str) -> str:
    source = absolute_asset_path(source_path)
    if not source or source.suffix.lower() not in VIDEO_EXTS:
        source = absolute_asset_path(output_rel("tracking_output.mp4")) or absolute_asset_path(sample_rel("tracking_12mb.mp4"))
    if not source:
        raise FileNotFoundError("tracking_output.mp4")
    output_rel_path = output_rel(f"tracking_output_{uuid.uuid4().hex[:12]}{source.suffix or '.mp4'}")
    output_path = UPLOAD_ROOT / output_rel_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, output_path)
    debug("轻量处理", "已生成目标跟踪输出视频", source=str(source), output=output_rel_path, size=output_path.stat().st_size)
    return asset_url(output_rel_path)


def build_transport(relative_path: str, include_preview: bool = True) -> dict:
    rel = normalize_relative_path(relative_path)
    path = absolute_asset_path(rel)
    mime = mimetypes.guess_type(rel)[0] or "application/octet-stream"
    ext = Path(rel).suffix.lower()
    kind = "video" if ext in VIDEO_EXTS else "image" if ext in IMAGE_EXTS else "file"
    data_url = build_preview_data_url(rel, 420) if include_preview and kind == "image" else ""
    return {
        "kind": kind,
        "mimetype": mime,
        "relative_path": rel,
        "asset_path": asset_url(rel),
        "original_url": asset_url(rel),
        "buffered_url": buffered_asset_url(rel),
        "legacy_url": legacy_asset_url(rel),
        "preview_url": f"/api/file/assets-preview/photos/{rel}?max_size=420" if kind == "image" else "",
        "preview_data_url": data_url,
        "supports_base64": bool(data_url),
        "modes": ["original"] + (["preview"] if data_url else []),
        "original_size": path.stat().st_size if path else 0,
    }


def media_transports(before_img="", after_img="", before_img1="", data=None) -> dict:
    transports = {}
    for field, value in (("before_img", before_img), ("after_img", after_img), ("before_img1", before_img1)):
        if value:
            transports[field] = build_transport(value)
    data_transports = {}
    for key, value in (data or {}).items():
        if isinstance(value, str) and normalize_relative_path(value) and absolute_asset_path(value):
            data_transports[key] = build_transport(value)
    if data_transports:
        transports["data"] = data_transports
    return transports


def visual_payload(renderer: str, before_img: str, after_img: str) -> dict:
    return {
        "schema": "geoview-lite-transport-diagnostics",
        "renderer": renderer,
        "transport_modes": ["original", "preview", "json"],
        "source": {"primary": {"asset_path": before_img, "transport": build_transport(before_img)}},
        "result": {"primary": {"asset_path": after_img, "transport": build_transport(after_img)}},
    }


def make_record(record_type: str, before_img: str, after_img: str, before_img1: str = "", data=None, renderer: str = "") -> dict:
    global _NEXT_ID
    data = data or {}
    record = {
        "id": _NEXT_ID,
        "type": record_type,
        "before_img": before_img,
        "before_img1": before_img1,
        "after_img": after_img,
        "data": data,
        "is_hole": False,
        "checked": "",
        "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "visualization_modes": ["original", "preview", "json"],
        "media_transports": media_transports(before_img, after_img, before_img1, data),
    }
    record["visual_payload"] = visual_payload(renderer or renderer_for_type(record_type), before_img, after_img)
    _NEXT_ID += 1
    return record


def renderer_for_type(record_type: str) -> str:
    return {
        "变化检测": "change_detection",
        "目标检测": "object_detection",
        "地物分类": "semantic_segmentation",
        "场景分类": "scene_classification",
        "影像超分重建": "image_restoration",
        "自动配准": "registration",
        "目标跟踪": "tracking",
    }.get(record_type, "object_detection")


def change_data() -> dict:
    return {
        "mask": asset_url(output_rel("mask_8kb.png")),
        "mask_hole": asset_url(output_rel("mask_8kb.png")),
        "hole": asset_url(output_rel("pred_440kb.png")),
        "overlay_path": asset_url(output_rel("pred_440kb.png")),
        "checkerboard_path": asset_url(output_rel("pred_440kb.png")),
        "size_distribution": [{"name": "小斑块", "value": 12}, {"name": "中斑块", "value": 6}, {"name": "大斑块", "value": 2}],
        "size_distribution_hole": [{"name": "孔洞填充后", "value": 15}],
        "top_changes": [{"label": "建筑变化", "area": 1024}, {"label": "道路变化", "area": 512}],
        "top_changes_hole": [{"label": "填充后变化", "area": 1536}],
    }


def tracking_data() -> dict:
    return {
        "preview_path": asset_url(output_rel("tracking_preview.png")),
        "output_video_path": asset_url(output_rel("tracking_output.mp4")),
        "trajectory_path": asset_url(output_rel("tracking_trajectory.json")),
        "label_histogram": {"目标1": 8},
        "track_count": 1,
        "frame_count": 8,
    }


def init_history() -> None:
    if _HISTORY:
        return
    ensure_runtime_assets()
    samples = [
        make_record("变化检测", asset_url(sample_rel("cd_val1_2_3mb.png")), asset_url(output_rel("cd_result_2mb.png")), asset_url(sample_rel("cd_val2_2_0mb.png")), change_data()),
        make_record("目标检测", asset_url(sample_rel("aircraft_200kb.jpg")), asset_url(output_rel("object_result_200kb.jpg")), data={"detections": [{"label": "aircraft", "score": 0.93}]}),
        make_record("地物分类", asset_url(sample_rel("seg_787kb.tif")), asset_url(output_rel("pred_440kb.png")), data={"mask": asset_url(output_rel("mask_8kb.png"))}),
        make_record("场景分类", asset_url(sample_rel("scene_7_7mb.png")), asset_url(sample_rel("scene_7_7mb.png")), data={"label": "机场", "score": 0.88}),
        make_record("影像超分重建", asset_url(sample_rel("aircraft_100kb.jpg")), asset_url(output_rel("restored_2mb.png")), data={"scale": "2x"}),
        make_record("自动配准", asset_url(sample_rel("cd_val1_2_3mb.png")), asset_url(output_rel("registration_output.png")), asset_url(sample_rel("cd_val2_2_0mb.png")), data={"overlay_path": asset_url(output_rel("pred_440kb.png"))}),
        make_record("目标跟踪", asset_url(output_rel("tracking_preview.png")), asset_url(output_rel("tracking_preview.png")), data=tracking_data()),
    ]
    _HISTORY.extend(samples)
    debug("历史记录", "内存历史样例已初始化", count=len(_HISTORY))


def history_list(record_type: Optional[str], page: int, limit: int) -> dict:
    init_history()
    record_type = unquote(str(record_type or "")).strip()
    items = [item for item in _HISTORY if not record_type or item.get("type") == record_type]
    items = list(reversed(items))
    page = max(1, int(page or 1))
    limit = max(1, min(int(limit or 10), 100))
    start = (page - 1) * limit
    return table_api(data=items[start:start + limit], count=len(items), limit=limit)


def delete_history(ids: Iterable[int]) -> dict:
    global _HISTORY
    id_set = {int(item) for item in ids}
    before = len(_HISTORY)
    _HISTORY = [item for item in _HISTORY if int(item.get("id", 0)) not in id_set]
    return success_api(msg="批量删除成功", data={"deleted": before - len(_HISTORY)})


def model_list(model_type: str) -> dict:
    models = {
        "change_detection": ("change_detector", "轻量变化检测诊断模型", "/lite/model/change_detection/mock"),
        "classification": ("classifier", "轻量场景分类诊断模型", "/lite/model/classification/mock"),
        "image_restoration": ("restorer", "轻量图像复原诊断模型", "/lite/model/image_restoration/mock"),
        "object_detection": ("detector", "轻量目标检测诊断模型", "/lite/model/object_detection/mock"),
        "semantic_segmentation": ("segmenter", "轻量地物分类诊断模型", "/lite/model/semantic_segmentation/mock"),
        "registration": ("register", "轻量自动配准诊断模型", "/lite/model/registration/mock"),
        "tracking": ("tracker", "轻量目标跟踪诊断模型", "/lite/model/tracking/botsort_official/mock"),
    }
    if model_type not in models:
        return fail_api("模型类型不正确")
    model_type_name, model_name, model_path = models[model_type]
    return success_api(data=[{
        "model_path": model_path,
        "model_type": model_type_name,
        "model_name": model_name,
        "backend": "lite",
        "description": f"{VARIANT} 诊断模型：不执行真实推理，只验证前后端数据传输。",
    }])


def save_uploaded_bytes(filename: str, content: bytes, upload_type: str = "") -> dict:
    init_history()
    safe_name = Path(filename or "upload.bin").name.replace(" ", "_")
    final_name = f"{uuid.uuid4().hex}_{safe_name}"
    path = UPLOAD_ROOT / final_name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    rel = sample_rel(final_name)
    debug("文件上传", "上传文件已保存", filename=filename, upload_type=upload_type, relative_path=rel, size=len(content))
    return {
        "src": asset_url(rel),
        "filename": final_name,
        "photo_id": uuid.uuid4().hex,
        "transport": build_transport(rel, include_preview=Path(final_name).suffix.lower() in IMAGE_EXTS),
    }


def handle_upload(files: List[Tuple[str, bytes]], upload_type: str = "") -> dict:
    if not files:
        return fail_api("请选择文件")
    data = [save_uploaded_bytes(filename, content, upload_type) for filename, content in files]
    return {"msg": "上传成功", "code": SUCCESS, "success": True, "data": data}


def handle_video_preview(filename: str, content: bytes, upload_type: str = "") -> dict:
    upload = save_uploaded_bytes(filename, content, upload_type)
    preview_name = f"{Path(upload['filename']).stem}_preview{Path(upload['filename']).suffix or '.mp4'}"
    preview_rel = output_rel(preview_name)
    shutil.copy2(absolute_asset_path(upload["src"]), UPLOAD_ROOT / preview_rel)
    data = {
        **upload,
        "preview_video_path": asset_url(preview_rel),
        "first_frame_path": asset_url(output_rel("tracking_preview.png")),
    }
    return {"msg": "视频预览生成成功", "code": SUCCESS, "success": True, "data": data}


def first_input_from_payload(payload: dict, fallback: str) -> str:
    items = payload.get("list") or []
    if not items:
        return fallback
    first = items[0]
    if isinstance(first, dict):
        return first.get("src") or first.get("first") or fallback
    return first or fallback


def first_pair_from_payload(payload: dict) -> Tuple[str, str]:
    items = payload.get("list") or []
    if items and isinstance(items[0], dict):
        return items[0].get("first") or items[0].get("src") or asset_url(sample_rel("cd_val1_2_3mb.png")), items[0].get("second") or asset_url(sample_rel("cd_val2_2_0mb.png"))
    return asset_url(sample_rel("cd_val1_2_3mb.png")), asset_url(sample_rel("cd_val2_2_0mb.png"))


def handle_analysis(route_name: str, payload: dict) -> dict:
    init_history()
    started = time.time()
    debug("模型推理", "收到轻量伪推理请求", route=route_name, payload_keys=list((payload or {}).keys()), estimated_request_bytes=len(json.dumps(payload or {}, ensure_ascii=False)))
    if route_name == "change_detection":
        first, second = first_pair_from_payload(payload)
        record = make_record("变化检测", first, asset_url(output_rel("cd_result_2mb.png")), second, change_data())
    elif route_name == "object_detection":
        before = first_input_from_payload(payload, asset_url(sample_rel("aircraft_200kb.jpg")))
        model_path = str((payload or {}).get("model_path") or "")
        result_image = create_annotated_image(before, "object_detection_result", "Object Detection", model_path, mode="object")
        record = make_record(
            "目标检测",
            before,
            result_image,
            data={
                "model_path": model_path,
                "detections": [
                    {"label": "aircraft", "score": 0.93, "bbox": [0.18, 0.28, 0.42, 0.55]},
                    {"label": "vehicle", "score": 0.88, "bbox": [0.52, 0.36, 0.76, 0.62]},
                ],
            },
        )
    elif route_name == "semantic_segmentation":
        before = first_input_from_payload(payload, asset_url(sample_rel("seg_787kb.tif")))
        record = make_record("地物分类", before, asset_url(output_rel("pred_440kb.png")), data={"mask": asset_url(output_rel("mask_8kb.png"))})
    elif route_name == "classification":
        before = first_input_from_payload(payload, asset_url(sample_rel("scene_7_7mb.png")))
        record = make_record("场景分类", before, before, data={"label": "机场", "score": 0.88})
    elif route_name == "image_restoration":
        before = first_input_from_payload(payload, asset_url(sample_rel("aircraft_100kb.jpg")))
        record = make_record("影像超分重建", before, asset_url(output_rel("restored_2mb.png")), data={"scale": "2x"})
    elif route_name == "registration":
        first, second = first_pair_from_payload(payload)
        record = make_record("自动配准", first, asset_url(output_rel("registration_output.png")), second, data={"overlay_path": asset_url(output_rel("pred_440kb.png"))})
    else:
        return fail_api(f"未知伪推理接口: {route_name}")
    _HISTORY.append(record)
    debug("模型推理", "轻量伪推理完成", route=route_name, record_id=record["id"], elapsed_ms=int((time.time() - started) * 1000))
    return success_api(data={"records": [record]})


def handle_tracking(payload: dict) -> dict:
    init_history()
    before = first_input_from_payload(payload, asset_url(sample_rel("tracking_12mb.mp4")))
    model_path = str((payload or {}).get("model_path") or "")
    preview_path = create_annotated_image(before, "tracking_preview_result", "Tracking Preview", model_path, mode="tracking")
    output_video_path = create_tracking_video(before)
    data_payload = {
        **tracking_data(),
        "model_path": model_path,
        "preview_path": preview_path,
        "output_video_path": output_video_path,
    }
    record = make_record("目标跟踪", preview_path, preview_path, data=data_payload)
    _HISTORY.append(record)
    data = {
        "first_frame_input": preview_path,
        "source_input_path": before,
        "preview_path": preview_path,
        "output_video_path": output_video_path,
        "trajectory_path": asset_url(output_rel("tracking_trajectory.json")),
        "summary": {
            "track_count": 1,
            "frame_count": 8,
            "label_histogram": {"目标1": 8},
            "model_path": model_path,
        },
        "record": record,
    }
    debug("模型推理", "轻量目标跟踪伪推理完成，已返回预览图和视频", model_path=model_path, preview_path=preview_path, output_video_path=output_video_path)
    return success_api(msg="轻量目标跟踪伪推理完成", data=data)


def handle_histogram_match(payload: dict) -> dict:
    first, second = first_pair_from_payload(payload)
    return success_api(data=[{"first": first, "first1": asset_url(output_rel("pred_440kb.png")), "second": second, "second1": asset_url(output_rel("cd_result_2mb.png"))}])


def handle_image_pre(payload: dict) -> dict:
    items = payload.get("list") or []
    if payload.get("type") == 1:
        first, second = first_pair_from_payload(payload)
        return success_api(data=[{"first": first, "first1": asset_url(output_rel("pred_440kb.png")), "second": second, "second1": asset_url(output_rel("cd_result_2mb.png"))}])
    if not items:
        return success_api(data=[asset_url(output_rel("pred_440kb.png"))])
    return success_api(data=[asset_url(output_rel("pred_440kb.png")) for _ in items])


def system_ping() -> dict:
    init_history()
    return success_api(data={
        "status": "ok",
        "variant": VARIANT,
        "framework_purpose": "GeoView 轻量传输诊断后端",
        "transfer_mode": TRANSFER_MODE,
        "omit_content_length": OMIT_CONTENT_LENGTH,
        "chunk_size": CHUNK_SIZE,
        "uploaded_photos_dest": str(UPLOAD_ROOT),
        "sample_dir": str(SAMPLE_DIR),
        "history_count": len(_HISTORY),
        "preferred_asset_prefix": "/api/file/assets/photos/",
        "buffered_asset_prefix": "/api/file/assets-buffered/photos/",
        "legacy_asset_prefix": "/_uploads/photos/",
    })


def startup_probe() -> None:
    ensure_runtime_assets()
    init_history()
    upload_write_ok = False
    try:
        test = UPLOAD_ROOT / ".write-test"
        test.write_text("ok", encoding="utf-8")
        test.unlink(missing_ok=True)
        upload_write_ok = True
    except Exception:
        upload_write_ok = False
    sample_sizes = []
    for path in sorted(UPLOAD_ROOT.rglob("*")):
        if path.is_file():
            sample_sizes.append({"relative": str(path.relative_to(UPLOAD_ROOT)), "size": path.stat().st_size})
    debug(
        "启动探测",
        "轻量后端启动环境探测完成",
        python=platform.python_version(),
        platform=platform.platform(),
        hostname=socket.gethostname(),
        pid=os.getpid(),
        port=PORT,
        cwd=os.getcwd(),
        static_root=str(STATIC_ROOT),
        upload_root=str(UPLOAD_ROOT),
        upload_write_ok=upload_write_ok,
        transfer_mode=TRANSFER_MODE,
        omit_content_length=OMIT_CONTENT_LENGTH,
        chunk_size=CHUNK_SIZE,
        sample_count=len(sample_sizes),
        samples=sample_sizes[:20],
    )


def parse_range(range_header: str, file_size: int) -> Optional[Tuple[int, int]]:
    if not range_header or not range_header.startswith("bytes="):
        return None
    raw = range_header[len("bytes="):]
    if "-" not in raw:
        return None
    start_raw, end_raw = raw.split("-", 1)
    if start_raw == "" and end_raw == "":
        return None
    if start_raw == "":
        length = min(file_size, int(end_raw))
        return max(0, file_size - length), file_size - 1
    start = int(start_raw)
    end = int(end_raw) if end_raw else file_size - 1
    if start < 0 or start >= file_size:
        raise ValueError("range start invalid")
    return start, min(end, file_size - 1)


def build_file_spec(relative_path: str, method: str = "GET", range_header: str = "", forced_mode: str = "") -> FileSpec:
    rel = normalize_relative_path(relative_path)
    path = absolute_asset_path(rel)
    if not path:
        raise FileNotFoundError(rel)
    file_size = path.stat().st_size
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    mode = (forced_mode or TRANSFER_MODE or "chunked").lower()
    byte_range = parse_range(range_header or "", file_size) if range_header else None
    is_video = path.suffix.lower() in VIDEO_EXTS
    status = 200
    start = 0
    end = file_size - 1
    headers = {
        "Content-Type": media_type,
        "Cache-Control": "no-cache",
        "Content-Disposition": f'inline; filename="{path.name}"',
        "X-GeoView-Disk-Size": str(file_size),
        "X-GeoView-Transfer-Mode": mode,
    }
    body = None
    if byte_range:
        start, end = byte_range
        status = 206
        content_length = end - start + 1
        headers["Accept-Ranges"] = "bytes"
        headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
        headers["Content-Length"] = str(content_length)
        headers["X-GeoView-Bytes-Sent"] = str(content_length)
    elif is_video and mode == "ranged":
        headers["Accept-Ranges"] = "bytes"
        if not OMIT_CONTENT_LENGTH:
            headers["Content-Length"] = str(file_size)
    elif mode == "buffered":
        body = path.read_bytes()
        headers["X-GeoView-Bytes-Buffered"] = str(len(body))
        headers["X-GeoView-Bytes-Sent"] = str(len(body))
        if not OMIT_CONTENT_LENGTH:
            headers["Content-Length"] = str(len(body))
    else:
        headers["X-GeoView-Bytes-Sent"] = str(file_size)
        if not OMIT_CONTENT_LENGTH:
            headers["Content-Length"] = str(file_size)
    debug(
        "资产传输",
        "构建文件响应规格",
        relative_path=rel,
        absolute_path=str(path),
        file_size=file_size,
        media_type=media_type,
        method=method,
        range=range_header,
        status_code=status,
        selected_mode=mode,
        omit_content_length=OMIT_CONTENT_LENGTH,
        start=start,
        end=end,
    )
    return FileSpec(path=path, relative_path=rel, status_code=status, media_type=media_type, headers=headers, start=start, end=end, body=body, head_only=method.upper() == "HEAD")


def iter_file_chunks(spec: FileSpec) -> Iterable[bytes]:
    if spec.head_only:
        return
    if spec.body is not None:
        yield spec.body
        return
    remaining = (spec.end if spec.end is not None else spec.path.stat().st_size - 1) - spec.start + 1
    sent = 0
    chunks = 0
    started = time.time()
    with spec.path.open("rb") as file:
        file.seek(spec.start)
        while remaining > 0:
            chunk = file.read(min(CHUNK_SIZE, remaining))
            if not chunk:
                debug("资产传输", "文件读取提前结束", relative_path=spec.relative_path, expected_remaining=remaining, sent=sent)
                break
            remaining -= len(chunk)
            sent += len(chunk)
            chunks += 1
            yield chunk
    debug(
        "资产传输",
        "文件分块发送结束",
        relative_path=spec.relative_path,
        chunks=chunks,
        bytes_sent=sent,
        disk_size=spec.path.stat().st_size,
        elapsed_ms=int((time.time() - started) * 1000),
    )
