import json
import os
import tempfile
from contextlib import contextmanager
from threading import Lock
from typing import Dict, List, Optional

from flask import current_app


_STORE_LOCK = Lock()


def _default_store_path() -> str:
    base_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../../data"))
    os.makedirs(base_dir, exist_ok=True)
    return os.path.join(base_dir, "online_services.json")


def get_store_path() -> str:
    configured = current_app.config.get("ONLINE_SERVICE_STORE")
    path = configured or _default_store_path()
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    return path


def ensure_store() -> str:
    path = get_store_path()
    if not os.path.exists(path):
        _atomic_write(path, [])
    return path


def _atomic_write(path: str, payload: List[Dict]) -> None:
    fd, temp_path = tempfile.mkstemp(prefix="service_registry_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def load_services() -> List[Dict]:
    path = ensure_store()
    with _STORE_LOCK:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
    if isinstance(data, list):
        return data
    return []


def save_services(services: List[Dict]) -> None:
    path = ensure_store()
    with _STORE_LOCK:
        _atomic_write(path, services)


def next_service_id(services: List[Dict]) -> int:
    max_id = 0
    for service in services:
        try:
            max_id = max(max_id, int(service.get("serviceId", 0)))
        except (TypeError, ValueError):
            continue
    return max_id + 1


def find_service(services: List[Dict], service_id: int) -> Optional[Dict]:
    for service in services:
        try:
            if int(service.get("serviceId")) == int(service_id):
                return service
        except (TypeError, ValueError):
            continue
    return None


@contextmanager
def mutable_services():
    services = load_services()
    yield services
    save_services(services)
