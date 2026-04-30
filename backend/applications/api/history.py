from flask import Blueprint, request
from sqlalchemy import desc

from applications.common.curd import model_to_dicts
from applications.common.visualization import normalize_analysis_record
from applications.common.utils import type_utils
from applications.common.utils.http import fail_api, success_api, table_api
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
        dicts = model_to_dicts(schema=AnalysisSchema, data=items)
        dicts = [normalize_analysis_record(item) for item in dicts]
        return table_api(data=dicts, count=count)
    else:
        to_type = type_utils.str_to_type(_type)
        log = Analysis.query.filter_by(
            type=to_type).order_by(desc(Analysis.create_time)).layui_paginate()
        count = log.total
        items = log.items
        dicts = model_to_dicts(schema=AnalysisSchema, data=items)
        dicts = [normalize_analysis_record(item) for item in dicts]
        return table_api(data=dicts, count=count)


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
