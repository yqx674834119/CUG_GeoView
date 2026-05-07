import base64
import io
import mimetypes
import os
import re
import shutil
import subprocess
import time
from contextlib import suppress

import cv2
from flask import (Blueprint, Response, abort, current_app, jsonify, request,
                   send_from_directory, stream_with_context)
from PIL import Image, UnidentifiedImageError

from applications.common.asset_transport import build_asset_transport
from applications.common.path_global import generate_url, md5_name
from applications.common.storage import (ensure_storage_dirs, log_asset,
                                         mirror_file, resolve_asset_path)
from applications.common.utils import upload as upload_curd, type_utils
from applications.common.utils.http import fail_api
from applications.common.utils.tiff_processor import is_tiff_file, MAX_TIFF_SIZE_MB

file_api = Blueprint('file_api', __name__, url_prefix='/api/file')
RANGE_HEADER_PATTERN = re.compile(r"bytes=(\d*)-(\d*)$")
MIN_PREVIEW_SIZE = 64
MAX_PREVIEW_SIZE = 1600
DEFAULT_PREVIEW_SIZE = 640
DEFAULT_PREVIEW_QUALITY = 82


def _resolve_asset_path(filename):
    resolved = resolve_asset_path(filename)
    if not resolved or not resolved.get("relative_path"):
        abort(404)
    if not resolved.get("absolute_path"):
        current_app.logger.warning(
            "asset not found: %s misses=%s",
            resolved.get("relative_path"),
            resolved.get("misses"),
        )
        abort(404)
    return (
        resolved["root"],
        resolved["relative_path"],
        resolved["absolute_path"],
        resolved["store"],
        resolved.get("misses", []),
    )


def _build_inline_headers(absolute_path):
    file_name = os.path.basename(absolute_path)
    return {
        "Content-Disposition": f'inline; filename="{file_name}"',
        "Cache-Control": "no-cache",
    }


def _relative_asset_path_from_public_path(value):
    normalized = str(value or "").replace("\\", "/").strip()
    prefixes = (
        "/api/file/assets-buffered/photos/",
        "/api/file/assets/photos/",
        "/_uploads/photos/",
    )
    for prefix in prefixes:
        if normalized.startswith(prefix):
            return normalized[len(prefix):].lstrip("/")
    return normalized.lstrip("/")


def _prefers_direct_streaming(absolute_path):
    mimetype = mimetypes.guess_type(absolute_path)[0] or ""
    return mimetype.startswith("video/")


def _serve_asset_buffered(absolute_path):
    mimetype = mimetypes.guess_type(absolute_path)[0] or "application/octet-stream"
    with open(absolute_path, "rb") as file:
        payload = file.read()
    response = Response(payload, mimetype=mimetype)
    response.headers.update(_build_inline_headers(absolute_path))
    response.content_length = len(payload)
    return response


def _int_query_arg(name, default, min_value, max_value):
    raw_value = request.args.get(name)
    if raw_value in (None, ""):
        return default
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return default
    return max(min_value, min(value, max_value))


def _build_image_preview_payload(absolute_path, source_store=""):
    started_at = time.time()
    max_size = _int_query_arg(
        "max_size",
        DEFAULT_PREVIEW_SIZE,
        MIN_PREVIEW_SIZE,
        MAX_PREVIEW_SIZE,
    )
    quality = _int_query_arg("quality", DEFAULT_PREVIEW_QUALITY, 40, 95)
    original_size = os.path.getsize(absolute_path)

    try:
        with Image.open(absolute_path) as image:
            image.load()
            original_width, original_height = image.size
            preview = image.copy()
    except UnidentifiedImageError:
        raise ValueError("仅支持图片文件预览")

    preview.thumbnail((max_size, max_size), Image.LANCZOS)
    has_alpha = preview.mode in ("RGBA", "LA") or (
        preview.mode == "P" and "transparency" in preview.info
    )

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
        "source_store": source_store,
        "original_size": original_size,
        "original_width": original_width,
        "original_height": original_height,
        "preview_size": len(preview_bytes),
        "preview_width": preview.width,
        "preview_height": preview.height,
        "max_size": max_size,
        "duration_ms": int((time.time() - started_at) * 1000),
    }


def _serve_asset_chunked(absolute_path):
    mimetype = mimetypes.guess_type(absolute_path)[0] or "application/octet-stream"
    chunk_size = max(65536, int(current_app.config.get("PHOTO_ASSET_CHUNK_SIZE", 1048576)))

    def generate():
        with open(absolute_path, "rb") as file:
            while True:
                chunk = file.read(chunk_size)
                if not chunk:
                    break
                yield chunk

    response = Response(stream_with_context(generate()), mimetype=mimetype)
    response.headers.update(_build_inline_headers(absolute_path))
    with suppress(Exception):
        response.content_length = None
    return response


def _parse_range_request(range_header, file_size):
    if not range_header:
        return None

    match = RANGE_HEADER_PATTERN.match(range_header.strip())
    if not match:
        return None

    start_raw, end_raw = match.groups()
    if start_raw == "" and end_raw == "":
        return None

    if start_raw == "":
        length = min(file_size, int(end_raw))
        start = max(0, file_size - length)
        end = file_size - 1
    else:
        start = int(start_raw)
        end = int(end_raw) if end_raw else file_size - 1

    if start < 0 or start >= file_size:
        abort(416)

    end = min(end, file_size - 1)
    if end < start:
        abort(416)

    return start, end


def _serve_asset_ranged(absolute_path):
    mimetype = mimetypes.guess_type(absolute_path)[0] or "application/octet-stream"
    file_size = os.path.getsize(absolute_path)
    range_header = request.headers.get("Range")
    byte_range = _parse_range_request(range_header, file_size)
    chunk_size = max(65536, int(current_app.config.get("PHOTO_ASSET_CHUNK_SIZE", 1048576)))

    if byte_range is None:
        start = 0
        end = file_size - 1
        status_code = 200
    else:
        start, end = byte_range
        status_code = 206

    content_length = max(0, end - start + 1)

    def generate():
        remaining = content_length
        with open(absolute_path, "rb") as file:
            file.seek(start)
            while remaining > 0:
                chunk = file.read(min(chunk_size, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    response = Response(
        stream_with_context(generate()),
        status=status_code,
        mimetype=mimetype,
        direct_passthrough=True,
    )
    response.headers.update(_build_inline_headers(absolute_path))
    response.headers["Accept-Ranges"] = "bytes"
    response.content_length = content_length
    if status_code == 206:
        response.headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
    return response


def _transcode_video_for_web(source_path, output_path):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not os.path.isfile(source_path):
        return None

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
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
        output_path,
    ]
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=1800,
    )
    if result.returncode != 0 or not os.path.isfile(output_path):
        with suppress(Exception):
            os.remove(output_path)
        current_app.logger.warning(
            "ffmpeg transcode failed for %s: %s",
            source_path,
            result.stderr,
        )
        return None
    return output_path


def _build_video_preview_assets(absolute_path, display_name):
    if not os.path.isfile(absolute_path):
        abort(404)

    capture = cv2.VideoCapture(absolute_path)
    if not capture.isOpened():
        raise ValueError("无法读取视频文件，无法生成预览")

    first_frame = None
    try:
        ok, frame = capture.read()
        if ok and frame is not None:
            first_frame = frame
    finally:
        capture.release()

    if first_frame is None:
        raise ValueError("视频内容无效，无法生成预览")

    output_dir = os.path.join(current_app.config["UPLOADED_PHOTOS_DEST"], "res")
    os.makedirs(output_dir, exist_ok=True)

    preview_base = os.path.splitext(os.path.basename(display_name or absolute_path))[0][:48]
    first_frame_name = md5_name(f"tracking_{preview_base}_input_preview.png")
    preview_video_name = md5_name(f"tracking_{preview_base}_source_preview.mp4")

    first_frame_path = os.path.join(output_dir, first_frame_name)
    preview_video_path = os.path.join(output_dir, preview_video_name)

    if not cv2.imwrite(first_frame_path, first_frame):
        raise ValueError("视频首帧预览图写入失败")
    mirror_file(first_frame_path)

    transcoded_path = _transcode_video_for_web(absolute_path, preview_video_path)
    if not transcoded_path:
        raise ValueError("视频标准化转码失败")
    mirror_file(transcoded_path)

    return {
        "first_frame_path": generate_url + first_frame_name,
        "preview_video_path": generate_url + os.path.basename(transcoded_path),
    }


def _serve_photo_asset(filename, forced_mode=None):
    _, normalized, absolute_path, _, _ = _resolve_asset_path(filename)
    mode = str(forced_mode or current_app.config.get("PHOTO_ASSET_SERVE_MODE", "sendfile")).lower()

    if _prefers_direct_streaming(absolute_path):
        return _serve_asset_ranged(absolute_path)

    if mode == "buffered":
        return _serve_asset_buffered(absolute_path)
    if mode == "chunked":
        return _serve_asset_chunked(absolute_path)
    return _serve_asset_ranged(absolute_path)


#   上传接口
@file_api.post('/upload')
def upload_api():
    ensure_storage_dirs()
    if 'files' in request.files:
        type_ = request.form['type']
        to_type = type_utils.str_to_type(type_)
        photos = request.files.getlist("files")
        
        # 预检查文件大小 (特别是 TIFF 文件)
        for photo in photos:
            if is_tiff_file(photo.filename):
                # 获取文件大小
                photo.seek(0, 2)  # 移动到文件末尾
                size_bytes = photo.tell()
                photo.seek(0)  # 重置到开头
                
                size_mb = size_bytes / (1024 * 1024)
                if size_mb > MAX_TIFF_SIZE_MB:
                    return fail_api(f"TIFF 文件 '{photo.filename}' 大小 ({size_mb:.1f}MB) 超过限制 ({MAX_TIFF_SIZE_MB}MB)")
        
        data = list()
        is_slice_str = request.form.get('isSlice', 'false')
        is_slice = is_slice_str.lower() == 'true'

        for photo in photos:
            mime = photo.content_type or mimetypes.guess_type(getattr(photo, "filename", "") or "")[0] or "application/octet-stream"
            try:
                # upload_one now returns a list of (file_url, photo_id, display_name)
                upload_results = upload_curd.upload_one(
                    photo=photo, mime=mime, type_=to_type, enable_slicing=is_slice)
                
                for file_url, photo_id, display_name in upload_results:
                    data.append({
                        "src": file_url,
                        "filename": display_name, # Use the display name for frontend pairing
                        "photo_id": photo_id,
                        "transport": build_asset_transport(file_url, preview_max_size=420),
                    })
            except ValueError as e:
                # TIFF 处理失败
                return fail_api(str(e))
            except Exception as e:
                return fail_api(f"文件上传失败: {str(e)}")
        
        res = {"msg": "上传成功", "code": 0, "success": True, "data": data}
        return jsonify(res)
    return fail_api("请选择文件")


@file_api.post('/upload-video-preview')
def upload_video_preview_api():
    if 'file' not in request.files:
        return fail_api("请选择视频文件")

    video = request.files['file']
    type_ = request.form.get('type', '目标跟踪')
    mime = video.content_type or ""
    suffix = os.path.splitext(getattr(video, "filename", "") or "")[1].lower()
    if not (mime.startswith("video/") or suffix in {".mp4", ".avi", ".mov", ".mkv", ".m4v", ".webm", ".mpg", ".mpeg"}):
        return fail_api("仅支持常见视频文件预览")

    try:
        upload_results = upload_curd.upload_one(
            photo=video,
            mime=mime or "video/mp4",
            type_=type_utils.str_to_type(type_),
            enable_slicing=False,
        )
    except Exception as exc:
        return fail_api(f"视频上传失败: {str(exc)}")

    if not upload_results:
        return fail_api("视频上传失败")

    file_url, photo_id, display_name = upload_results[0]
    relative_path = _relative_asset_path_from_public_path(file_url)
    _, _, absolute_path, _, _ = _resolve_asset_path(relative_path)

    try:
        preview_assets = _build_video_preview_assets(absolute_path, display_name)
    except ValueError as exc:
        return fail_api(str(exc))

    return jsonify({
        "msg": "视频预览生成成功",
        "code": 0,
        "success": True,
        "data": {
            "src": file_url,
            "filename": display_name,
            "photo_id": photo_id,
            "transport": build_asset_transport(file_url, preview_max_size=420),
            "first_frame_transport": build_asset_transport(preview_assets["first_frame_path"], preview_max_size=420),
            "preview_video_transport": build_asset_transport(preview_assets["preview_video_path"], preview_max_size=420),
            **preview_assets,
        }
    })


@file_api.get('/assets/photos/<path:filename>')
def get_photo_asset(filename):
    return _serve_photo_asset(filename)


@file_api.get('/assets-buffered/photos/<path:filename>')
def get_photo_asset_buffered(filename):
    return _serve_photo_asset(filename, forced_mode="buffered")


@file_api.get('/assets-preview/photos/<path:filename>')
def get_photo_asset_preview(filename):
    resolved = resolve_asset_path(filename)
    if not resolved or not resolved.get("relative_path"):
        return jsonify({
            "msg": "图片路径无效",
            "code": 400,
            "success": False,
            "data": {
                "source_store": "",
                "fallback_misses": [],
            },
        }), 400

    normalized = resolved["relative_path"]
    absolute_path = resolved.get("absolute_path")
    source_store = resolved.get("store", "")
    misses = resolved.get("misses", [])
    if not absolute_path:
        current_app.logger.warning(
            "preview asset not found: %s misses=%s",
            normalized,
            misses,
        )
        return jsonify({
            "msg": "图片文件不存在",
            "code": 404,
            "success": False,
            "data": {
                "src": f"/api/file/assets/photos/{normalized}",
                "source_store": "",
                "fallback_misses": misses,
            },
        }), 404

    try:
        payload = _build_image_preview_payload(absolute_path, source_store=source_store)
    except ValueError as exc:
        return jsonify({
            "msg": str(exc),
            "code": 415,
            "success": False,
            "data": {
                "src": f"/api/file/assets/photos/{normalized}",
                "source_store": source_store,
                "fallback_misses": misses,
            },
        }), 415

    payload["src"] = f"/api/file/assets/photos/{normalized}"
    payload["fallback_misses"] = misses
    log_asset(
        "preview relative={} source_store={} original_size={} preview_size={} duration_ms={}".format(
            normalized,
            payload["source_store"],
            payload["original_size"],
            payload["preview_size"],
            payload["duration_ms"],
        ),
        "info",
    )
    return jsonify({
        "msg": "图片预览生成成功",
        "code": 0,
        "success": True,
        "data": payload,
    })


@file_api.get('/assets-transport/photos/<path:filename>')
def get_photo_asset_transport(filename):
    relative_path = _relative_asset_path_from_public_path(filename)
    transport = build_asset_transport(f"/api/file/assets/photos/{relative_path}", preview_max_size=640)
    if not transport:
        return jsonify({
            "msg": "资源路径无效",
            "code": 400,
            "success": False,
            "data": {},
        }), 400
    return jsonify({
        "msg": "资源传输信息获取成功",
        "code": 0,
        "success": True,
        "data": transport,
    })
