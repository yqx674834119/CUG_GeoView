import base64
import io
import json
import mimetypes
import os
import re
import shutil
import subprocess
import time
from contextlib import suppress
from typing import List

import cv2
from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from PIL import Image, UnidentifiedImageError

from applications.common.asset_transport import build_asset_transport
from applications.common.debug_logging import log_debug
from applications.common.path_global import generate_url, md5_name
from applications.common.storage import (
    ensure_storage_dirs,
    log_asset,
    mirror_file,
    primary_upload_root,
    resolve_asset_path,
)
from applications.common.utils import type_utils
from applications.common.utils import upload as upload_curd
from applications.common.utils.http import fail_api
from applications.common.utils.tiff_processor import MAX_TIFF_SIZE_MB, is_tiff_file

file_api = APIRouter(prefix="/api/file", tags=["file"])
legacy_file_api = APIRouter(tags=["file"])

RANGE_HEADER_PATTERN = re.compile(r"bytes=(\d*)-(\d*)$")
MIN_PREVIEW_SIZE = 64
MAX_PREVIEW_SIZE = 1600
DEFAULT_PREVIEW_SIZE = 420
DEFAULT_PREVIEW_QUALITY = 75


def _json_stream_response(payload, status_code=200, extra_headers=None):
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    headers = {
        "Cache-Control": "no-cache",
        "X-GeoView-Json-Bytes": str(len(body)),
        **(extra_headers or {}),
    }
    return StreamingResponse(
        iter([body]),
        status_code=status_code,
        media_type="application/json; charset=utf-8",
        headers=headers,
    )


def _request_id(request):
    return getattr(getattr(request, "state", None), "request_id", "")


def _asset_chunk_size():
    return max(65536, int(os.getenv("GEOVIEW_PHOTO_ASSET_CHUNK_SIZE", "1048576")))


def _asset_serve_mode():
    return os.getenv("GEOVIEW_PHOTO_ASSET_SERVE_MODE", "buffered").lower()


def _omit_asset_content_length():
    return os.getenv("GEOVIEW_OMIT_ASSET_CONTENT_LENGTH", "true").lower() in {"1", "true", "yes", "on"}


def _resolve_asset_path(filename):
    resolved = resolve_asset_path(filename)
    if not resolved or not resolved.get("relative_path"):
        raise HTTPException(status_code=404, detail="asset path invalid")
    if not resolved.get("absolute_path"):
        log_asset(f"asset not found: {resolved.get('relative_path')} misses={resolved.get('misses')}", "warning")
        raise HTTPException(status_code=404, detail="asset not found")
    return (
        resolved["root"],
        resolved["relative_path"],
        resolved["absolute_path"],
        resolved["store"],
        resolved.get("misses", []),
    )


def _inline_headers(absolute_path):
    return {
        "Content-Disposition": f'inline; filename="{os.path.basename(absolute_path)}"',
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


def _prefers_ranged(absolute_path):
    mimetype = mimetypes.guess_type(absolute_path)[0] or ""
    return mimetype.startswith("video/")


def _serve_asset_buffered(absolute_path, request: Request, relative_path="", store=""):
    mimetype = mimetypes.guess_type(absolute_path)[0] or "application/octet-stream"
    started_at = time.time()
    with open(absolute_path, "rb") as file:
        payload = file.read()
    disk_size = os.path.getsize(absolute_path)
    log_debug(
        "资产传输",
        "buffered 模式已完整读入文件并准备返回",
        request_id=_request_id(request),
        relative_path=relative_path,
        store=store,
        absolute_path=absolute_path,
        mimetype=mimetype,
        disk_size=disk_size,
        response_content_length=len(payload),
        length_matches_disk=(len(payload) == disk_size),
        elapsed_ms=int((time.time() - started_at) * 1000),
    )
    headers = {
        **_inline_headers(absolute_path),
        "X-GeoView-Disk-Size": str(disk_size),
        "X-GeoView-Bytes-Buffered": str(len(payload)),
    }
    if not _omit_asset_content_length():
        headers["Content-Length"] = str(len(payload))
    return StreamingResponse(
        iter([payload]),
        media_type=mimetype,
        headers=headers,
    )


def _serve_asset_chunked(absolute_path, request: Request, relative_path="", store=""):
    mimetype = mimetypes.guess_type(absolute_path)[0] or "application/octet-stream"
    chunk_size = _asset_chunk_size()
    disk_size = os.path.getsize(absolute_path)

    def generate():
        sent = 0
        chunks = 0
        started_at = time.time()
        with open(absolute_path, "rb") as file:
            while True:
                chunk = file.read(chunk_size)
                if not chunk:
                    break
                sent += len(chunk)
                chunks += 1
                yield chunk
        log_debug(
            "资产传输",
            "chunked 模式发送结束",
            request_id=_request_id(request),
            relative_path=relative_path,
            store=store,
            absolute_path=absolute_path,
            mimetype=mimetype,
            disk_size=disk_size,
            chunk_size=chunk_size,
            chunks=chunks,
            bytes_sent=sent,
            length_matches_disk=(sent == disk_size),
            elapsed_ms=int((time.time() - started_at) * 1000),
        )

    headers = {**_inline_headers(absolute_path), "X-GeoView-Disk-Size": str(disk_size)}
    if not _omit_asset_content_length():
        headers["Content-Length"] = str(disk_size)
    return StreamingResponse(generate(), media_type=mimetype, headers=headers)


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
        raise HTTPException(status_code=416, detail="range start invalid")
    end = min(end, file_size - 1)
    if end < start:
        raise HTTPException(status_code=416, detail="range end invalid")
    return start, end


def _serve_asset_ranged(absolute_path, request: Request, relative_path="", store=""):
    mimetype = mimetypes.guess_type(absolute_path)[0] or "application/octet-stream"
    file_size = os.path.getsize(absolute_path)
    byte_range = _parse_range_request(request.headers.get("range"), file_size)
    if byte_range is None:
        start, end, status_code = 0, file_size - 1, 200
    else:
        start, end = byte_range
        status_code = 206
    content_length = max(0, end - start + 1)
    chunk_size = _asset_chunk_size()

    def generate():
        remaining = content_length
        sent = 0
        chunks = 0
        started_at = time.time()
        with open(absolute_path, "rb") as file:
            file.seek(start)
            while remaining > 0:
                chunk = file.read(min(chunk_size, remaining))
                if not chunk:
                    log_debug(
                        "资产传输",
                        "ranged 模式读取提前结束，可能触发客户端 Content-Length 不一致",
                        request_id=_request_id(request),
                        relative_path=relative_path,
                        store=store,
                        absolute_path=absolute_path,
                        expected_remaining=remaining,
                        bytes_sent=sent,
                        file_size=file_size,
                    )
                    break
                remaining -= len(chunk)
                sent += len(chunk)
                chunks += 1
                yield chunk
        log_debug(
            "资产传输",
            "ranged 模式发送结束",
            request_id=_request_id(request),
            relative_path=relative_path,
            store=store,
            absolute_path=absolute_path,
            mimetype=mimetype,
            status_code=status_code,
            request_range=request.headers.get("range", ""),
            response_range=f"bytes {start}-{end}/{file_size}" if status_code == 206 else "",
            content_length=content_length,
            chunk_size=chunk_size,
            chunks=chunks,
            bytes_sent=sent,
            length_matches_header=(sent == content_length),
            elapsed_ms=int((time.time() - started_at) * 1000),
        )

    headers = {**_inline_headers(absolute_path), "Accept-Ranges": "bytes"}
    if status_code == 206 or not _omit_asset_content_length():
        headers["Content-Length"] = str(content_length)
    if status_code == 206:
        headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
    return StreamingResponse(generate(), status_code=status_code, media_type=mimetype, headers=headers)


def _serve_photo_asset(filename, request: Request, forced_mode=None):
    root, relative_path, absolute_path, store, misses = _resolve_asset_path(filename)
    mode = str(forced_mode or _asset_serve_mode()).lower()
    file_size = os.path.getsize(absolute_path)
    mimetype = mimetypes.guess_type(absolute_path)[0] or "application/octet-stream"
    selected_mode = "ranged" if _prefers_ranged(absolute_path) else mode
    log_debug(
        "资产传输",
        "开始处理图片/视频资源请求",
        request_id=_request_id(request),
        raw_filename=filename,
        relative_path=relative_path,
        store=store,
        root=root,
        absolute_path=absolute_path,
        misses=misses,
        file_size=file_size,
        mimetype=mimetype,
        requested_mode=mode,
        selected_mode=selected_mode,
        range=request.headers.get("range", ""),
        client=request.client.host if request.client else "",
    )
    if _prefers_ranged(absolute_path):
        return _serve_asset_ranged(absolute_path, request, relative_path=relative_path, store=store)
    if mode == "buffered":
        return _serve_asset_buffered(absolute_path, request, relative_path=relative_path, store=store)
    if mode == "chunked":
        return _serve_asset_chunked(absolute_path, request, relative_path=relative_path, store=store)
    return _serve_asset_ranged(absolute_path, request, relative_path=relative_path, store=store)


def _build_image_preview_payload(absolute_path, source_store, max_size, quality):
    started_at = time.time()
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
        preview.save(output, format=preview_format, quality=quality, optimize=True, progressive=True)
    preview_bytes = output.getvalue()
    encoded = base64.b64encode(preview_bytes).decode("ascii")
    log_debug(
        "资源预览",
        "图片预览 base64 已生成，仅用于小尺寸预览，不返回原图大 base64",
        absolute_path=absolute_path,
        source_store=source_store,
        original_size=os.path.getsize(absolute_path),
        original_width=original_width,
        original_height=original_height,
        preview_size=len(preview_bytes),
        preview_width=preview.width,
        preview_height=preview.height,
        max_size=max_size,
        quality=quality,
        duration_ms=int((time.time() - started_at) * 1000),
    )
    return {
        "filename": os.path.basename(absolute_path),
        "mimetype": mimetype,
        "format": preview_format.lower(),
        "data_url": f"data:{mimetype};base64,{encoded}",
        "source_store": source_store,
        "original_size": os.path.getsize(absolute_path),
        "original_width": original_width,
        "original_height": original_height,
        "preview_size": len(preview_bytes),
        "preview_width": preview.width,
        "preview_height": preview.height,
        "max_size": max_size,
        "duration_ms": int((time.time() - started_at) * 1000),
    }


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
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=1800)
    if result.returncode != 0 or not os.path.isfile(output_path):
        with suppress(Exception):
            os.remove(output_path)
        log_asset(f"ffmpeg transcode failed for {source_path}: {result.stderr}", "warning")
        return None
    return output_path


def _build_video_preview_assets(absolute_path, display_name):
    if not os.path.isfile(absolute_path):
        raise HTTPException(status_code=404, detail="video not found")
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
    output_dir = os.path.join(primary_upload_root(), "res")
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


@file_api.post("/upload")
def upload_api(
    files: List[UploadFile] = File(default=[]),
    type: str = Form(...),
    isSlice: str = Form("false"),
):
    started_at = time.time()
    ensure_storage_dirs()
    if not files:
        return fail_api("请选择文件")
    to_type = type_utils.str_to_type(type)
    log_debug(
        "文件上传",
        "收到上传请求",
        files=[
            {
                "filename": photo.filename,
                "content_type": photo.content_type,
                "spooled_size": getattr(photo.file, "_file", None) and getattr(getattr(photo.file, "_file", None), "tell", lambda: "")(),
            }
            for photo in files
        ],
        type=type,
        resolved_type=to_type,
        is_slice=isSlice,
    )
    for photo in files:
        if is_tiff_file(photo.filename):
            photo.file.seek(0, 2)
            size_mb = photo.file.tell() / (1024 * 1024)
            photo.file.seek(0)
            if size_mb > MAX_TIFF_SIZE_MB:
                return fail_api(f"TIFF 文件 '{photo.filename}' 大小 ({size_mb:.1f}MB) 超过限制 ({MAX_TIFF_SIZE_MB}MB)")
    data = []
    is_slice = str(isSlice).lower() == "true"
    for photo in files:
        mime = photo.content_type or mimetypes.guess_type(photo.filename or "")[0] or "application/octet-stream"
        try:
            for file_url, photo_id, display_name in upload_curd.upload_one(photo, mime, to_type, is_slice):
                transport = build_asset_transport(file_url, preview_max_size=420)
                log_debug(
                    "文件上传",
                    "单个文件保存完成",
                    original_filename=photo.filename,
                    display_name=display_name,
                    mime=mime,
                    photo_id=photo_id,
                    file_url=file_url,
                    transport_kind=transport.get("kind") if transport else "",
                    transport_modes=transport.get("modes") if transport else [],
                )
                data.append({
                    "src": file_url,
                    "filename": display_name,
                    "photo_id": photo_id,
                    "transport": transport,
                })
        except ValueError as exc:
            log_debug("文件上传", "上传校验失败", filename=photo.filename, error=str(exc))
            return fail_api(str(exc))
        except Exception as exc:
            log_debug("文件上传", "上传保存异常", filename=photo.filename, error=str(exc))
            return fail_api(f"文件上传失败: {str(exc)}")
    log_debug(
        "文件上传",
        "上传请求处理完成",
        uploaded_count=len(data),
        elapsed_ms=int((time.time() - started_at) * 1000),
    )
    return {"msg": "上传成功", "code": 0, "success": True, "data": data}


@file_api.post("/upload-video-preview")
def upload_video_preview_api(file: UploadFile = File(...), type: str = Form("目标跟踪")):
    started_at = time.time()
    mime = file.content_type or ""
    suffix = os.path.splitext(file.filename or "")[1].lower()
    log_debug(
        "视频预览",
        "收到视频预览上传请求",
        filename=file.filename,
        content_type=file.content_type,
        suffix=suffix,
        type=type,
    )
    if not (mime.startswith("video/") or suffix in {".mp4", ".avi", ".mov", ".mkv", ".m4v", ".webm", ".mpg", ".mpeg"}):
        return fail_api("仅支持常见视频文件预览")
    try:
        upload_results = upload_curd.upload_one(file, mime or "video/mp4", type_utils.str_to_type(type), False)
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
        log_debug("视频预览", "视频预览生成失败", filename=file.filename, absolute_path=absolute_path, error=str(exc))
        return fail_api(str(exc))
    log_debug(
        "视频预览",
        "视频预览生成完成",
        filename=file.filename,
        source_path=absolute_path,
        source_size=os.path.getsize(absolute_path) if os.path.isfile(absolute_path) else -1,
        first_frame_path=preview_assets.get("first_frame_path"),
        preview_video_path=preview_assets.get("preview_video_path"),
        elapsed_ms=int((time.time() - started_at) * 1000),
    )
    return {
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
        },
    }


@file_api.get("/assets/photos/{filename:path}")
def get_photo_asset(filename: str, request: Request):
    return _serve_photo_asset(filename, request)


@file_api.get("/assets-buffered/photos/{filename:path}")
def get_photo_asset_buffered(filename: str, request: Request):
    return _serve_photo_asset(filename, request, forced_mode="buffered")


@legacy_file_api.get("/_uploads/photos/{filename:path}", include_in_schema=False)
def get_legacy_photo_asset(filename: str, request: Request):
    return _serve_photo_asset(filename, request)


@file_api.get("/assets-preview/photos/{filename:path}")
def get_photo_asset_preview(
    filename: str,
    max_size: int = Query(DEFAULT_PREVIEW_SIZE, ge=MIN_PREVIEW_SIZE, le=MAX_PREVIEW_SIZE),
    quality: int = Query(DEFAULT_PREVIEW_QUALITY, ge=40, le=95),
):
    started_at = time.time()
    resolved = resolve_asset_path(filename)
    if not resolved or not resolved.get("relative_path"):
        log_debug("资源预览", "图片预览路径无效", filename=filename, max_size=max_size)
        return _json_stream_response({"msg": "图片路径无效", "code": 400, "success": False, "data": {}}, status_code=400)
    normalized = resolved["relative_path"]
    absolute_path = resolved.get("absolute_path")
    source_store = resolved.get("store", "")
    misses = resolved.get("misses", [])
    if not absolute_path:
        log_debug(
            "资源预览",
            "图片预览文件不存在",
            filename=filename,
            normalized=normalized,
            fallback_misses=misses,
        )
        return _json_stream_response({
            "msg": "图片文件不存在",
            "code": 404,
            "success": False,
            "data": {"src": f"/api/file/assets/photos/{normalized}", "fallback_misses": misses},
        }, status_code=404)
    try:
        payload = _build_image_preview_payload(absolute_path, source_store, max_size, quality)
    except ValueError as exc:
        log_debug(
            "资源预览",
            "图片预览生成失败",
            filename=filename,
            normalized=normalized,
            absolute_path=absolute_path,
            error=str(exc),
        )
        return _json_stream_response({
            "msg": str(exc),
            "code": 415,
            "success": False,
            "data": {"src": f"/api/file/assets/photos/{normalized}", "fallback_misses": misses},
        }, status_code=415)
    payload["src"] = f"/api/file/assets/photos/{normalized}"
    payload["fallback_misses"] = misses
    log_debug(
        "资源预览",
        "图片预览接口返回成功",
        filename=filename,
        normalized=normalized,
        source_store=source_store,
        original_size=payload.get("original_size"),
        preview_size=payload.get("preview_size"),
        data_url_length=len(payload.get("data_url") or ""),
        elapsed_ms=int((time.time() - started_at) * 1000),
    )
    return _json_stream_response({"msg": "图片预览生成成功", "code": 0, "success": True, "data": payload})


@file_api.get("/assets-transport/photos/{filename:path}")
def get_photo_asset_transport(filename: str):
    relative_path = _relative_asset_path_from_public_path(filename)
    transport = build_asset_transport(f"/api/file/assets/photos/{relative_path}", preview_max_size=640)
    if not transport:
        log_debug("资源传输信息", "资源路径无法生成传输信息", filename=filename, relative_path=relative_path)
        return JSONResponse({"msg": "资源路径无效", "code": 400, "success": False, "data": {}}, status_code=400)
    log_debug(
        "资源传输信息",
        "资源传输信息返回成功",
        filename=filename,
        relative_path=relative_path,
        transport_kind=transport.get("kind"),
        transport_modes=transport.get("modes"),
        original_size=transport.get("original_size"),
        has_preview_data_url=bool(transport.get("preview_data_url")),
    )
    return {"msg": "资源传输信息获取成功", "code": 0, "success": True, "data": transport}
