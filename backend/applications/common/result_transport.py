import base64
import gzip
import json
import math
import threading
import time
import uuid


DEFAULT_CHUNK_SIZE = 64 * 1024
MAX_CHUNK_SIZE = 256 * 1024
RESULT_TTL_SECONDS = 30 * 60

_LOCK = threading.Lock()
_RESULTS = {}


def _cleanup(now=None):
    current = now or time.time()
    expired = [
        result_id
        for result_id, item in _RESULTS.items()
        if current - item["created_at"] > RESULT_TTL_SECONDS
    ]
    for result_id in expired:
        _RESULTS.pop(result_id, None)


def normalize_chunk_size(value):
    try:
        size = int(value)
    except Exception:
        return DEFAULT_CHUNK_SIZE
    return max(1024, min(size, MAX_CHUNK_SIZE))


def response_payload_budget(value):
    size = normalize_chunk_size(value)
    return max(64, size - 256)


def create_result_manifest(payload, route="", chunk_size=None):
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    compressed = gzip.compress(raw)
    encoded = base64.b64encode(compressed).decode("ascii")
    result_id = uuid.uuid4().hex
    size = len(encoded)
    effective_chunk_size = response_payload_budget(chunk_size)
    created_at = time.time()
    with _LOCK:
        _cleanup(created_at)
        _RESULTS[result_id] = {
            "created_at": created_at,
            "route": route,
            "encoded": encoded,
            "raw_size": len(raw),
            "compressed_size": len(compressed),
        }
    return {
        "transport": "chunked_result_v2",
        "result_id": result_id,
        "route": route,
        "encoding": "gzip+base64+json",
        "encoded_size": size,
        "raw_size": len(raw),
        "compressed_size": len(compressed),
        "chunk_size": effective_chunk_size,
        "chunk_count": int(math.ceil(size / effective_chunk_size)) if size else 0,
        "expires_in_seconds": RESULT_TTL_SECONDS,
    }


def get_result_chunk(result_id, offset=0, limit=None):
    try:
        start = max(0, int(offset))
    except Exception:
        start = 0
    size = response_payload_budget(limit)
    with _LOCK:
        _cleanup()
        item = _RESULTS.get(result_id)
        if not item:
            return None
        encoded = item["encoded"]
        end = min(len(encoded), start + size)
        return {
            "transport": "chunked_result_v2",
            "result_id": result_id,
            "offset": start,
            "next_offset": end,
            "limit": size,
            "encoded_size": len(encoded),
            "done": end >= len(encoded),
            "chunk": encoded[start:end],
        }
