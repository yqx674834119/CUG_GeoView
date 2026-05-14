import base64
import mimetypes
import os

from flask import Blueprint, jsonify, request

from applications.common.result_transport import get_result_chunk, normalize_chunk_size
from applications.common.storage import resolve_asset_path
from applications.common.utils.http import fail_api

transport_api = Blueprint("transport_api", __name__, url_prefix="/api/transport")


@transport_api.route("/result/<result_id>/chunk", methods=["GET"])
def result_chunk(result_id):
    limit = normalize_chunk_size(request.args.get("limit"))
    offset = request.args.get("offset", 0)
    payload = get_result_chunk(result_id, offset=offset, limit=limit)
    if payload is None:
        return jsonify(fail_api("推理结果已过期或不存在")), 404
    return jsonify({"success": True, "code": 0, "msg": "成功", "data": payload})


def _resolve_asset_or_response(path):
    resolved = resolve_asset_path(path)
    if not resolved or not resolved.get("relative_path"):
        return None, (jsonify(fail_api("资源路径无效")), 400)
    absolute_path = resolved.get("absolute_path")
    if not absolute_path or not os.path.isfile(absolute_path):
        return None, (jsonify(fail_api("资源不存在")), 404)
    return resolved, None


def _encoded_budget(limit):
    # limit is treated as the target maximum JSON response size. Keep enough
    # room for JSON metadata so the actual resource payload stays below it.
    size = normalize_chunk_size(limit)
    budget = max(64, size - 512)
    return budget - (budget % 4)


@transport_api.route("/asset/manifest", methods=["GET"])
def asset_manifest():
    path = request.args.get("path", "")
    resolved, error = _resolve_asset_or_response(path)
    if error:
        return error

    absolute_path = resolved["absolute_path"]
    size = os.path.getsize(absolute_path)
    mimetype = mimetypes.guess_type(absolute_path)[0] or "application/octet-stream"
    return jsonify({
        "success": True,
        "code": 0,
        "msg": "成功",
        "data": {
            "transport": "chunked_asset_v1",
            "path": resolved["relative_path"],
            "size": size,
            "mime": mimetype,
            "filename": os.path.basename(absolute_path),
        },
    })


@transport_api.route("/asset/chunk", methods=["GET"])
def asset_chunk():
    path = request.args.get("path", "")
    resolved, error = _resolve_asset_or_response(path)
    if error:
        return error

    try:
        offset = max(0, int(request.args.get("offset", 0)))
    except Exception:
        offset = 0

    absolute_path = resolved["absolute_path"]
    file_size = os.path.getsize(absolute_path)
    encoded_limit = _encoded_budget(request.args.get("limit"))
    read_size = max(1, (encoded_limit // 4) * 3)
    offset = min(offset, file_size)

    with open(absolute_path, "rb") as source:
        source.seek(offset)
        raw = source.read(read_size)

    encoded = base64.b64encode(raw).decode("ascii")
    next_offset = offset + len(raw)
    return jsonify({
        "success": True,
        "code": 0,
        "msg": "成功",
        "data": {
            "transport": "chunked_asset_v1",
            "offset": offset,
            "next_offset": next_offset,
            "size": file_size,
            "done": next_offset >= file_size,
            "chunk": encoded,
        },
    })
