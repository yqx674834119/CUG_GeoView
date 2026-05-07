import base64
import io
import mimetypes
import os
from typing import Any, Dict

from PIL import Image, UnidentifiedImageError

from applications.common.storage import resolve_asset_path, safe_asset_relative_path

MIN_PREVIEW_SIZE = 64
MAX_PREVIEW_SIZE = 1600
DEFAULT_PREVIEW_SIZE = 640
DEFAULT_PREVIEW_QUALITY = 82


def normalize_transport_path(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    normalized = value.replace("\\", "/").strip()
    if normalized.startswith(("http://", "https://", "data:", "blob:")):
        return normalized

    relative = safe_asset_relative_path(normalized)
    if relative:
        return f"/api/file/assets/photos/{relative}"
    return normalized


def _transport_relative_path(value: Any) -> str:
    normalized = normalize_transport_path(value)
    prefixes = (
        "/api/file/assets/photos/",
        "/api/file/assets-buffered/photos/",
        "/api/file/assets-preview/photos/",
        "/_uploads/photos/",
        "/static/upload/",
    )
    for prefix in prefixes:
        if normalized.startswith(prefix):
            return normalized[len(prefix):].lstrip("/")
    return ""


def _image_preview_payload(absolute_path: str, max_size: int = DEFAULT_PREVIEW_SIZE, quality: int = DEFAULT_PREVIEW_QUALITY) -> Dict[str, Any]:
    with Image.open(absolute_path) as image:
        image.load()
        original_width, original_height = image.size
        preview = image.copy()

    preview.thumbnail((max_size, max_size), Image.LANCZOS)
    has_alpha = preview.mode in ("RGBA", "LA") or (preview.mode == "P" and "transparency" in preview.info)

    output = io.BytesIO()
    if has_alpha:
        preview = preview.convert("RGBA")
        preview_format = "PNG"
        mimetype = "image/png"
        preview.save(output, format=preview_format, optimize=True)
    else:
        preview = preview.convert("RGB")
        preview_format = "JPEG"
        mimetype = "image/jpeg"
        preview.save(
            output,
            format=preview_format,
            quality=quality,
            optimize=True,
            progressive=True,
        )

    preview_bytes = output.getvalue()
    encoded = base64.b64encode(preview_bytes).decode("ascii")
    file_name = os.path.basename(absolute_path)

    return {
        "filename": file_name,
        "mimetype": mimetype,
        "format": preview_format.lower(),
        "data_url": f"data:{mimetype};base64,{encoded}",
        "original_size": os.path.getsize(absolute_path),
        "original_width": original_width,
        "original_height": original_height,
        "preview_size": len(preview_bytes),
        "preview_width": preview.width,
        "preview_height": preview.height,
        "max_size": max_size,
    }


def build_asset_transport(value: Any,
                          preview_max_size: int = DEFAULT_PREVIEW_SIZE,
                          quality: int = DEFAULT_PREVIEW_QUALITY) -> Dict[str, Any]:
    normalized = normalize_transport_path(value)
    if not normalized:
        return {}

    if normalized.startswith(("http://", "https://", "data:", "blob:")):
        return {
            "asset_path": normalized,
            "original_url": normalized,
            "buffered_url": normalized,
            "preview_url": normalized,
            "preview_data_url": normalized if normalized.startswith("data:") else "",
            "relative_path": "",
            "kind": "external",
            "supports_base64": normalized.startswith("data:"),
            "modes": ["original", "json"] if normalized.startswith("data:") else ["original"],
        }

    relative_path = _transport_relative_path(normalized)
    if not relative_path:
        return {
            "asset_path": normalized,
            "original_url": normalized,
            "buffered_url": normalized,
            "preview_url": normalized,
            "preview_data_url": "",
            "relative_path": "",
            "kind": "unknown",
            "supports_base64": False,
            "modes": ["original"],
        }

    original_url = f"/api/file/assets/photos/{relative_path}"
    buffered_url = f"/api/file/assets-buffered/photos/{relative_path}"
    preview_url = f"/api/file/assets-preview/photos/{relative_path}"
    resolved = resolve_asset_path(relative_path)
    absolute_path = resolved.get("absolute_path") if resolved else ""
    mimetype = mimetypes.guess_type(absolute_path or relative_path)[0] or ""
    kind = "video" if mimetype.startswith("video/") else "image" if mimetype.startswith("image/") else "binary"

    transport = {
        "asset_path": normalized,
        "original_url": original_url,
        "buffered_url": buffered_url,
        "preview_url": preview_url,
        "preview_data_url": "",
        "relative_path": relative_path,
        "kind": kind,
        "mimetype": mimetype,
        "supports_base64": kind == "image",
        "modes": ["original", "base64"] if kind == "image" else ["original"],
    }

    if kind == "image" and absolute_path and os.path.isfile(absolute_path):
        try:
            preview_payload = _image_preview_payload(absolute_path, max_size=preview_max_size, quality=quality)
            transport.update({
                "preview_data_url": preview_payload.get("data_url", ""),
                "preview_meta": preview_payload,
            })
        except (UnidentifiedImageError, OSError, ValueError):
            transport["supports_base64"] = False

    if kind == "video":
        transport["preview_data_url"] = ""

    return transport


def attach_transports_to_value(value: Any,
                               preview_max_size: int = DEFAULT_PREVIEW_SIZE,
                               quality: int = DEFAULT_PREVIEW_QUALITY) -> Any:
    if isinstance(value, dict):
        return {key: attach_transports_to_value(item, preview_max_size, quality) for key, item in value.items()}
    if isinstance(value, list):
        return [attach_transports_to_value(item, preview_max_size, quality) for item in value]
    transport = build_asset_transport(value, preview_max_size=preview_max_size, quality=quality)
    return transport or value


def build_record_media_transports(record: Dict[str, Any],
                                  preview_max_size: int = DEFAULT_PREVIEW_SIZE,
                                  quality: int = DEFAULT_PREVIEW_QUALITY) -> Dict[str, Any]:
    transports: Dict[str, Any] = {}
    for field in ("before_img", "before_img1", "after_img"):
        if record.get(field):
            transports[field] = build_asset_transport(record.get(field), preview_max_size=preview_max_size, quality=quality)

    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    data_transports = {}
    for key, value in data.items():
        if isinstance(value, dict):
            nested = attach_transports_to_value(value, preview_max_size, quality)
            if nested != value:
                data_transports[key] = nested
            continue
        if isinstance(value, list):
            nested = attach_transports_to_value(value, preview_max_size, quality)
            if nested != value:
                data_transports[key] = nested
            continue
        transport = build_asset_transport(value, preview_max_size=preview_max_size, quality=quality)
        if transport:
            data_transports[key] = transport
    if data_transports:
        transports["data"] = data_transports
    return transports
