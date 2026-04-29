import json

from flask import Blueprint, request
from sqlalchemy import desc

from applications.common.curd import model_to_dicts
from applications.common.utils import type_utils
from applications.common.utils.http import fail_api, success_api, table_api
from applications.common.utils.type_utils import items_handle
from applications.extensions import db
from applications.models.analysis import Analysis
from applications.schemas import AnalysisSchema

history_api = Blueprint('history_api', __name__, url_prefix='/api/history')
"""
    查询我的历史记录
"""


@history_api.get('/list')
def history_list():
    # orm查询
    # 使用分页获取data需要.items
    _type = request.args.get('type', type=str)
    if _type is None or _type == '""' or _type == "":
        log = Analysis.query.order_by(desc(
            Analysis.create_time)).layui_paginate()
        count = log.total
        items = log.items
        analysis_handle(items)
        dicts = model_to_dicts(schema=AnalysisSchema, data=items)
        items_handle(dicts)
        return table_api(data=dicts, count=count)
    else:
        to_type = type_utils.str_to_type(_type)
        log = Analysis.query.filter_by(
            type=to_type).order_by(desc(Analysis.create_time)).layui_paginate()
        count = log.total
        items = log.items
        analysis_handle(items)
        dicts = model_to_dicts(schema=AnalysisSchema, data=items)
        items_handle(dicts)
        return table_api(data=dicts, count=count)


def analysis_handle(items):
    for t in items:
        if t.data == "" or t.data is None:
            continue
        t.data = json.loads(t.data)
        if type_utils.type_to_str(t.type) == "变化检测":
            _normalize_change_detection_assets(t)
    pass


def _derive_mask_path(path):
    if not path:
        return ""
    stem, ext = path.rsplit(".", 1) if "." in path else (path, "png")
    return f"{stem}_mask.{ext}"


def _normalize_change_detection_assets(item):
    data = item.data or {}
    if not isinstance(data, dict):
        return

    if not data.get("mask") and item.after_img:
        data["mask"] = _derive_mask_path(item.after_img)

    hole_path = data.get("hole")
    if not data.get("mask_hole") and hole_path:
        data["mask_hole"] = _derive_mask_path(hole_path)


"""
批量删除
"""


@history_api.delete('/batchRemove')
def history_delete():
    req_json = request.json
    if 'ids' in req_json:
        ids = req_json['ids']
        for id in ids:
            res = Analysis.query.filter_by(id=id).delete()
            db.session.commit()
        return success_api(msg="批量删除成功")
    return fail_api(msg="参数异常")
    pass
