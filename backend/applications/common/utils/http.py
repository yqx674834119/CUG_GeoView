from typing import Any

from applications.common.utils.code import FAIL, SUCCESS


def success_api(msg: str = "成功", data: Any = None):
    return {"success": True, "code": SUCCESS, "msg": msg, "data": {} if data is None else data}


def fail_api(msg: str = "失败", code_id: int = FAIL):
    return {"success": False, "code": code_id, "msg": msg}


def table_api(msg: str = "", count: int = 0, data=None, limit: int = 10):
    return {
        "success": True,
        "msg": msg,
        "code": SUCCESS,
        "data": [] if data is None else data,
        "count": count,
        "limit": limit,
    }
