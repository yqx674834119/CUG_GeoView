from copy import deepcopy
from datetime import datetime
from typing import Dict, List, Optional

from flask import Blueprint, jsonify, request

from applications.common.utils.service_registry import (
    find_service,
    load_services,
    mutable_services,
    next_service_id,
)

service_api = Blueprint("service_api", __name__, url_prefix="/api/v1/api/service")


def _ok(data=None, msg: str = "OK", status_code: int = 200):
    return jsonify({"code": status_code, "success": True, "msg": msg, "data": data}), status_code


def _error(msg: str, status_code: int = 400):
    return jsonify({"code": status_code, "success": False, "msg": msg}), status_code


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat()


def _parse_int(value, field_name: str):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} 必须是整数")


def _parse_ids_from_value(value) -> List[int]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        items = [item.strip() for item in value.split(",") if item.strip()]
    elif isinstance(value, list):
        items = value
    else:
        raise ValueError("ids/serviceIds 格式不正确")
    parsed = []
    for item in items:
        try:
            parsed.append(int(item))
        except (TypeError, ValueError):
            raise ValueError("ids/serviceIds 必须是整数或逗号分隔整数")
    return parsed


def _normalize_service_payload(payload: Dict, existing: Optional[Dict] = None) -> Dict:
    now = _now_iso()
    service = deepcopy(existing or {})
    service.update(payload)
    if existing is None:
        service.setdefault("serviceCreateTime", now)
    service["serviceUpdateTime"] = payload.get("serviceUpdateTime") or now
    for key in ("serviceStatus", "taskType", "priority", "serviceId"):
        if key in service and service[key] not in (None, ""):
            service[key] = int(service[key])
    if "serviceCreator" not in service or not service.get("serviceCreator"):
        service["serviceCreator"] = service.get("serviceCreatePer") or service.get("serviceCreatorId") or ""
    if "offlineServiceStatus" not in service and service.get("serviceStatus") == 1:
        service["offlineServiceStatus"] = "running"
    return service


def _extract_nested_payload(payload: Dict, preferred_key: str) -> Dict:
    nested = payload.get(preferred_key)
    return nested if isinstance(nested, dict) else payload


def _extract_restart_ids(payload: Dict) -> List[int]:
    ids = _parse_ids_from_value(payload.get("ids"))
    if ids:
        return ids
    nested = payload.get("serviceRestartDTO")
    if isinstance(nested, dict):
        return _parse_ids_from_value(nested.get("ids"))
    return []


def _extract_stop_ids(payload: Dict) -> List[int]:
    ids = _parse_ids_from_value(payload.get("serviceIds"))
    if ids:
        return ids
    nested = payload.get("serviceStopDTO")
    if isinstance(nested, dict):
        return _parse_ids_from_value(nested.get("serviceIds"))
    return []


def _extract_dispatch_id(payload: Dict):
    dispatch_id = payload.get("dispatchId")
    if dispatch_id not in (None, ""):
        return int(dispatch_id)
    nested = payload.get("serviceStopDTO")
    if isinstance(nested, dict) and nested.get("dispatchId") not in (None, ""):
        return int(nested.get("dispatchId"))
    return None


def _matches_text(value: str, pattern: str) -> bool:
    return pattern in (None, "") or str(pattern).lower() in str(value or "").lower()


def _matches_int(value, target) -> bool:
    if target is None:
        return True
    try:
        return int(value) == int(target)
    except (TypeError, ValueError):
        return False


def _service_creator_value(service: Dict) -> str:
    return service.get("serviceCreator") or service.get("serviceCreatePer") or service.get("serviceCreatorId") or ""


def _sort_services(services: List[Dict], sequence: Optional[int]) -> List[Dict]:
    if sequence is None:
        return sorted(services, key=lambda item: int(item.get("serviceId", 0)), reverse=True)
    return sorted(services, key=lambda item: int(item.get("serviceId", 0)), reverse=sequence < 0)


def _int_or_none(value):
    try:
        if value in (None, ""):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _json_payload():
    return request.get_json(silent=True) or {}


def _query_int(name, default=None):
    value = request.args.get(name)
    if value in (None, ""):
        return default
    return int(value)


@service_api.route("/list", methods=["GET"])
def service_list():
    curPage = _query_int("curPage", 1)
    pageSize = _query_int("pageSize", 10)
    sequence = _query_int("sequence")
    serviceStatus = _query_int("serviceStatus")
    taskType = _query_int("taskType")
    serviceCreator = request.args.get("serviceCreator")
    serviceName = request.args.get("serviceName")
    services = load_services()
    filtered = []
    for service in services:
        if not _matches_text(_service_creator_value(service), serviceCreator):
            continue
        if not _matches_text(service.get("serviceName", ""), serviceName):
            continue
        if not _matches_int(service.get("serviceStatus"), serviceStatus):
            continue
        if not _matches_int(service.get("taskType"), taskType):
            continue
        filtered.append(service)
    ordered = _sort_services(filtered, sequence)
    total = len(ordered)
    start = max(curPage - 1, 0) * pageSize
    return _ok({"records": ordered[start:start + pageSize], "total": total, "curPage": curPage, "pageSize": pageSize})


@service_api.route("/restart", methods=["POST"])
def service_restart():
    payload = _json_payload()
    try:
        ids = _extract_restart_ids(payload)
    except ValueError as exc:
        return _error(str(exc), 400)
    if not ids:
        return _error("缺少待重启的服务 ids", 400)
    with mutable_services() as services:
        updated = 0
        for service_id in ids:
            service = find_service(services, service_id)
            if service is None:
                continue
            service["serviceStatus"] = 1
            service["offlineServiceStatus"] = "running"
            service["serviceUpdateTime"] = _now_iso()
            updated += 1
    return _ok(True, "服务重启成功") if updated else _error("未找到待重启的服务", 404)


@service_api.route("/stop", methods=["POST"])
def service_stop():
    payload = _json_payload()
    try:
        ids = _extract_stop_ids(payload)
        dispatch_id = _extract_dispatch_id(payload)
    except ValueError as exc:
        return _error(str(exc), 400)
    if not ids and dispatch_id is None:
        return _error("缺少待停止的服务标识", 400)
    with mutable_services() as services:
        updated = 0
        for service in services:
            service_id = _int_or_none(service.get("serviceId"))
            service_dispatch_id = _int_or_none(service.get("dispatchId"))
            if not ((ids and service_id in ids) or (dispatch_id is not None and service_dispatch_id == dispatch_id)):
                continue
            service["serviceStatus"] = 2
            service["offlineServiceStatus"] = "stopped"
            service["serviceUpdateTime"] = _now_iso()
            updated += 1
    return _ok(True, "服务停止成功") if updated else _error("未找到待停止的服务", 404)


@service_api.route("/update", methods=["POST"])
def service_update():
    payload = _json_payload()
    payload = _extract_nested_payload(payload, "serviceInfoDTO")
    if not payload:
        return _error("缺少 serviceInfoDTO", 400)
    service_id = payload.get("serviceId")
    if service_id in (None, ""):
        return _error("serviceId 不能为空", 400)
    try:
        service_id = int(service_id)
    except (TypeError, ValueError):
        return _error("serviceId 必须是整数", 400)
    with mutable_services() as services:
        existing = find_service(services, service_id)
        if existing is None:
            return _error("服务不存在", 404)
        normalized = _normalize_service_payload(payload, existing=existing)
        existing.clear()
        existing.update(normalized)
    return _ok(True, "服务更新成功")


@service_api.route("/delete", methods=["DELETE"])
def service_delete():
    ids = request.args.get("ids")
    try:
        parsed_ids = _parse_ids_from_value(ids)
    except ValueError as exc:
        return _error(str(exc), 400)
    if not parsed_ids:
        return _error("ids 不能为空", 400)
    with mutable_services() as services:
        before = len(services)
        services[:] = [item for item in services if int(item.get("serviceId", 0)) not in parsed_ids]
        deleted = before - len(services)
    return _ok(True, "服务删除成功") if deleted else _error("未找到待删除的服务", 404)


def _service_detail_impl(service_id):
    if service_id in (None, ""):
        return _error("serviceId 不能为空", 400)
    try:
        service_id = int(service_id)
    except (TypeError, ValueError):
        return _error("serviceId 必须是整数", 400)
    service = find_service(load_services(), service_id)
    return _ok(service) if service is not None else _error("服务不存在", 404)


@service_api.route("/detail", methods=["GET"])
def service_detail_get():
    return _service_detail_impl(request.args.get("serviceId"))


@service_api.route("/detail", methods=["POST"])
def service_detail_post():
    return _service_detail_impl(_json_payload().get("serviceId"))


def seed_service_record(service_info: Dict):
    with mutable_services() as services:
        normalized = _normalize_service_payload(service_info)
        if "serviceId" not in normalized or normalized["serviceId"] in (None, ""):
            normalized["serviceId"] = next_service_id(services)
        services.append(normalized)
