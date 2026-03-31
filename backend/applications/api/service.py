from copy import deepcopy
from datetime import datetime
from typing import Dict, List, Optional

from flask import Blueprint, jsonify, request

from applications.common.utils.service_registry import (find_service,
                                                        load_services,
                                                        mutable_services,
                                                        next_service_id)

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

    if "serviceStatus" in service and service["serviceStatus"] not in (None, ""):
        service["serviceStatus"] = int(service["serviceStatus"])
    if "taskType" in service and service["taskType"] not in (None, ""):
        service["taskType"] = int(service["taskType"])
    if "priority" in service and service["priority"] not in (None, ""):
        service["priority"] = int(service["priority"])

    if "serviceId" in service and service["serviceId"] not in (None, ""):
        service["serviceId"] = int(service["serviceId"])

    if "serviceCreator" not in service or not service.get("serviceCreator"):
        service["serviceCreator"] = (service.get("serviceCreatePer")
                                      or service.get("serviceCreatorId")
                                      or "")

    if "offlineServiceStatus" not in service and service.get("serviceStatus") == 1:
        service["offlineServiceStatus"] = "running"

    return service


def _extract_nested_payload(preferred_key: str) -> Dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return {}
    nested = data.get(preferred_key)
    if isinstance(nested, dict):
        return nested
    return data


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
    if pattern is None or pattern == "":
        return True
    return pattern.lower() in str(value or "").lower()


def _matches_int(value, target) -> bool:
    if target is None:
        return True
    try:
        return int(value) == int(target)
    except (TypeError, ValueError):
        return False


def _service_creator_value(service: Dict) -> str:
    return (service.get("serviceCreator")
            or service.get("serviceCreatePer")
            or service.get("serviceCreatorId")
            or "")


def _sort_services(services: List[Dict], sequence: Optional[int]) -> List[Dict]:
    if sequence is None:
        return sorted(services, key=lambda item: int(item.get("serviceId", 0)), reverse=True)

    reverse = sequence < 0
    return sorted(services, key=lambda item: int(item.get("serviceId", 0)), reverse=reverse)


def _int_or_none(value):
    try:
        if value in (None, ""):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


@service_api.get("/list")
def service_list():
    try:
        cur_page = _parse_int(request.args.get("curPage"), "curPage") or 1
        page_size = _parse_int(request.args.get("pageSize"), "pageSize") or 10
        sequence = _parse_int(request.args.get("sequence"), "sequence")
        service_status = _parse_int(request.args.get("serviceStatus"), "serviceStatus")
        task_type = _parse_int(request.args.get("taskType"), "taskType")
    except ValueError as exc:
        return _error(str(exc), 400)

    services = load_services()
    filtered = []
    for service in services:
        if not _matches_text(_service_creator_value(service), request.args.get("serviceCreator")):
            continue
        if not _matches_text(service.get("serviceName", ""), request.args.get("serviceName")):
            continue
        if not _matches_int(service.get("serviceStatus"), service_status):
            continue
        if not _matches_int(service.get("taskType"), task_type):
            continue
        filtered.append(service)

    ordered = _sort_services(filtered, sequence)
    total = len(ordered)
    start = max(cur_page - 1, 0) * page_size
    end = start + page_size

    return _ok({
        "records": ordered[start:end],
        "total": total,
        "curPage": cur_page,
        "pageSize": page_size,
    })


@service_api.post("/restart")
def service_restart():
    payload = request.get_json(silent=True) or {}
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

    if updated == 0:
        return _error("未找到待重启的服务", 404)
    return _ok(True, "服务重启成功")


@service_api.post("/stop")
def service_stop():
    payload = request.get_json(silent=True) or {}
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
            should_stop = False
            if ids and service_id in ids:
                should_stop = True
            if dispatch_id is not None and service_dispatch_id == dispatch_id:
                should_stop = True
            if not should_stop:
                continue
            service["serviceStatus"] = 2
            service["offlineServiceStatus"] = "stopped"
            service["serviceUpdateTime"] = _now_iso()
            updated += 1

    if updated == 0:
        return _error("未找到待停止的服务", 404)
    return _ok(True, "服务停止成功")


@service_api.post("/update")
def service_update():
    payload = _extract_nested_payload("serviceInfoDTO")
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


@service_api.delete("/delete")
def service_delete():
    ids_param = request.args.get("ids")
    try:
        ids = _parse_ids_from_value(ids_param)
    except ValueError as exc:
        return _error(str(exc), 400)

    if not ids:
        return _error("ids 不能为空", 400)

    with mutable_services() as services:
        before = len(services)
        services[:] = [item for item in services if int(item.get("serviceId", 0)) not in ids]
        deleted = before - len(services)

    if deleted == 0:
        return _error("未找到待删除的服务", 404)
    return _ok(True, "服务删除成功")


@service_api.route("/detail", methods=["GET", "POST"])
def service_detail():
    service_id = request.args.get("serviceId")
    if service_id in (None, ""):
        data = request.get_json(silent=True) or {}
        service_id = data.get("serviceId")

    if service_id in (None, ""):
        return _error("serviceId 不能为空", 400)

    try:
        service_id = int(service_id)
    except (TypeError, ValueError):
        return _error("serviceId 必须是整数", 400)

    services = load_services()
    service = find_service(services, service_id)
    if service is None:
        return _error("服务不存在", 404)
    return _ok(service)


def seed_service_record(service_info: Dict):
    """Internal helper reserved for future deploy API integration."""
    with mutable_services() as services:
        normalized = _normalize_service_payload(service_info)
        if "serviceId" not in normalized or normalized["serviceId"] in (None, ""):
            normalized["serviceId"] = next_service_id(services)
        services.append(normalized)
