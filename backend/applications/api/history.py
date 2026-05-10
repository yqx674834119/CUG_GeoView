import json
import os

from fastapi import APIRouter, Body, Query, Request
from fastapi.responses import StreamingResponse
from typing import Optional
from sqlalchemy import desc

from applications.common.debug_logging import compact_json_bytes, log_debug
from applications.common.curd import model_to_dicts
from applications.common.utils import type_utils
from applications.common.utils.http import fail_api, success_api, table_api
from applications.common.visualization import VISUAL_PAYLOAD_KEY, normalize_analysis_record
from applications.extensions import db
from applications.models.analysis import Analysis
from applications.schemas import AnalysisSchema

history_api = APIRouter(prefix="/api/history", tags=["history"])

HISTORY_DATA_STRING_LIMIT = int(os.getenv("GEOVIEW_HISTORY_DATA_STRING_LIMIT", "4096"))
HISTORY_DATA_LIST_LIMIT = int(os.getenv("GEOVIEW_HISTORY_DATA_LIST_LIMIT", "80"))


def _json_stream_response(payload, status_code=200):
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return StreamingResponse(
        iter([body]),
        status_code=status_code,
        media_type="application/json; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "X-GeoView-Json-Bytes": str(len(body)),
        },
    )


def _looks_like_asset_path(value):
    if not isinstance(value, str):
        return False
    normalized = value.strip()
    return normalized.startswith((
        "/api/file/",
        "/_uploads/",
        "/static/upload/",
        "http://",
        "https://",
    ))


def _compact_history_value(value, depth=0):
    if depth > 4:
        return {"__truncated__": True, "reason": "max_depth"}
    if isinstance(value, str):
        if value.startswith("data:"):
            return {"__omitted__": True, "reason": "inline_data_url", "length": len(value)}
        if len(value) > HISTORY_DATA_STRING_LIMIT and not _looks_like_asset_path(value):
            return {
                "__truncated__": True,
                "length": len(value),
                "preview": value[:HISTORY_DATA_STRING_LIMIT],
            }
        return value
    if isinstance(value, list):
        if len(value) > HISTORY_DATA_LIST_LIMIT:
            return {
                "__truncated__": True,
                "length": len(value),
                "items": [_compact_history_value(item, depth + 1) for item in value[:HISTORY_DATA_LIST_LIMIT]],
            }
        return [_compact_history_value(item, depth + 1) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _compact_history_value(item, depth + 1)
            for key, item in value.items()
            if key != VISUAL_PAYLOAD_KEY
        }
    return value


def _compact_history_item(item):
    compacted = dict(item)
    if isinstance(compacted.get("data"), dict):
        compacted["data"] = _compact_history_value(compacted["data"])
    return compacted


def _paginate(query, page: int, limit: int):
    page = max(page, 1)
    limit = max(min(limit, 100), 1)
    total = query.count()
    items = query.offset((page - 1) * limit).limit(limit).all()
    return total, items


@history_api.get("/list")
def history_list(
    request: Request,
    type: Optional[str] = Query(default=None),
    page: int = Query(default=1),
    limit: int = Query(default=10),
):
    request_id = getattr(getattr(request, "state", None), "request_id", "")
    log_debug(
        "历史记录",
        "收到历史记录列表请求",
        request_id=request_id,
        type=type,
        page=page,
        limit=limit,
    )
    query = Analysis.query
    if type not in (None, "", '""'):
        query = query.filter_by(type=type_utils.str_to_type(type))
    query = query.order_by(desc(Analysis.create_time))
    count, items = _paginate(query, page, limit)
    dicts = model_to_dicts(schema=AnalysisSchema, data=items)
    dicts = [_compact_history_item(normalize_analysis_record(item)) for item in dicts]
    response_payload = table_api(data=dicts, count=count, limit=limit)
    media_summary = []
    inline_data_url_count = 0
    for item in dicts[:10]:
        summary = {
            "id": item.get("id"),
            "type": item.get("type"),
            "before_img": item.get("before_img") or "",
            "before_img1": item.get("before_img1") or "",
            "after_img": item.get("after_img") or "",
            "visualization_modes": item.get("visualization_modes") or [],
        }
        for field in ("before_img", "before_img1", "after_img"):
            if str(summary.get(field, "")).startswith("data:"):
                inline_data_url_count += 1
        data = item.get("data")
        if isinstance(data, dict):
            for value in data.values():
                if isinstance(value, str) and value.startswith("data:"):
                    inline_data_url_count += 1
            summary["data_keys"] = list(data.keys())[:12]
        media_summary.append(summary)
    log_debug(
        "历史记录",
        "历史记录列表返回完成",
        request_id=request_id,
        total=count,
        returned=len(dicts),
        limit=limit,
        estimated_json_bytes=compact_json_bytes(response_payload),
        inline_data_url_count=inline_data_url_count,
        media_summary=media_summary,
    )
    return _json_stream_response(response_payload)


@history_api.delete("/batchRemove")
def history_delete(payload: dict = Body(default={})):
    ids = payload.get("ids")
    if not ids:
        return fail_api(msg="参数异常")
    for item_id in ids:
        Analysis.query.filter_by(id=item_id).delete()
    db.session.commit()
    return success_api(msg="批量删除成功")
