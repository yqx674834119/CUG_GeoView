import io
import mimetypes
import os
from typing import Iterable

from flask import Blueprint, jsonify, request, send_file

from applications.common.storage import ensure_storage_dirs, resolve_asset_path
from applications.common.utils import type_utils
from applications.common.utils import upload as upload_curd
from applications.common.utils.http import fail_api
from applications.common.utils.tiff_processor import MAX_TIFF_SIZE_MB, is_tiff_file

file_api = Blueprint("file_api", __name__, url_prefix="/api/file")
legacy_file_api = Blueprint("legacy_file_api", __name__)


def _json(payload, status_code=200):
    return jsonify(payload), status_code


def _uploaded_files() -> Iterable:
    return request.files.getlist("files")


def _validate_tiff_size(file_storage):
    filename = file_storage.filename or ""
    if not is_tiff_file(filename):
        return None
    stream = file_storage.stream
    stream.seek(0, os.SEEK_END)
    size_mb = stream.tell() / (1024 * 1024)
    stream.seek(0)
    if size_mb > MAX_TIFF_SIZE_MB:
        return f"TIFF 文件 '{filename}' 大小 ({size_mb:.1f}MB) 超过限制 ({MAX_TIFF_SIZE_MB}MB)"
    return None


@file_api.route("/upload", methods=["POST"])
def upload_api():
    ensure_storage_dirs()
    files = list(_uploaded_files())
    if not files:
        return _json(fail_api("请选择文件"), 400)

    type_name = request.form.get("type", "")
    is_slice = str(request.form.get("isSlice", "false")).lower() == "true"
    to_type = type_utils.str_to_type(type_name)

    for item in files:
        error = _validate_tiff_size(item)
        if error:
            return _json(fail_api(error), 400)

    data = []
    for item in files:
        mime = item.mimetype or mimetypes.guess_type(item.filename or "")[0] or "application/octet-stream"
        try:
            for file_url, photo_id, display_name in upload_curd.upload_one(item, mime, to_type, is_slice):
                data.append({
                    "src": file_url,
                    "filename": display_name,
                    "photo_id": photo_id,
                })
        except ValueError as exc:
            return _json(fail_api(str(exc)), 400)
        except Exception as exc:
            return _json(fail_api(f"文件上传失败: {str(exc)}"), 500)

    return jsonify({"msg": "上传成功", "code": 0, "success": True, "data": data})


def _send_asset(filename):
    resolved = resolve_asset_path(filename)
    if not resolved or not resolved.get("relative_path"):
        return _json(fail_api("资源路径无效"), 400)
    absolute_path = resolved.get("absolute_path")
    if not absolute_path or not os.path.isfile(absolute_path):
        return _json(fail_api("资源不存在"), 404)

    mimetype = mimetypes.guess_type(absolute_path)[0] or "application/octet-stream"
    with open(absolute_path, "rb") as source:
        payload = io.BytesIO(source.read())
    payload.seek(0)
    return send_file(
        payload,
        mimetype=mimetype,
        as_attachment=False,
        download_name=os.path.basename(absolute_path),
        max_age=0,
    )


@file_api.route("/assets/photos/<path:filename>", methods=["GET"])
def get_photo_asset(filename):
    return _send_asset(filename)


@legacy_file_api.route("/_uploads/photos/<path:filename>", methods=["GET"])
def get_legacy_photo_asset(filename):
    return _send_asset(filename)
