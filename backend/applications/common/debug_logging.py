import json
import os
import time
import uuid


def _env_flag(name, default="true"):
    return str(os.getenv(name, default)).strip().lower() in {"1", "true", "yes", "on"}


def debug_enabled():
    return _env_flag("GEOVIEW_DEBUG_LOG", "true")


def new_request_id():
    return uuid.uuid4().hex[:12]


def now_ms():
    return int(time.time() * 1000)


def safe_len(value):
    try:
        return len(value)
    except Exception:
        return None


def compact_json_bytes(payload):
    try:
        return len(json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8"))
    except Exception:
        return -1


def summarize_value(value, max_text=96):
    if isinstance(value, str):
        if value.startswith("data:"):
            return {
                "type": "data-url",
                "length": len(value),
                "prefix": value[:max_text],
            }
        if len(value) > max_text:
            return f"{value[:max_text]}...<len={len(value)}>"
        return value
    if isinstance(value, list):
        return {"type": "list", "length": len(value)}
    if isinstance(value, dict):
        return {"type": "dict", "keys": list(value.keys())[:12]}
    return value


def log_debug(scope, message, **fields):
    if not debug_enabled():
        return
    suffix = ""
    if fields:
        try:
            suffix = " " + json.dumps(fields, ensure_ascii=False, default=str, separators=(",", ":"))
        except Exception:
            suffix = " " + str(fields)
    print(f"[GeoView调试][{scope}] {message}{suffix}", flush=True)
