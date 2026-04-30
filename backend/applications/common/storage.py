import os
import shutil
import time
from contextlib import suppress


DEFAULT_EXTERNAL_STATIC_ROOT = "/data/geoview/static"
DEFAULT_INTERNAL_STATIC_ROOT = "/app/backend/static"


def _env_flag(name, default="false"):
    return str(os.getenv(name, default)).strip().lower() in {"1", "true", "yes", "on"}


def asset_debug_enabled():
    return _env_flag("GEOVIEW_ASSET_DEBUG", "0")


def log_asset(message, level="info"):
    if level == "debug" and not asset_debug_enabled():
        return
    print(f"[asset][{level}] {message}", flush=True)


def external_static_root():
    return os.path.abspath(
        os.getenv("GEOVIEW_EXTERNAL_STATIC_ROOT", DEFAULT_EXTERNAL_STATIC_ROOT)
    )


def internal_static_root():
    return os.path.abspath(
        os.getenv("GEOVIEW_INTERNAL_STATIC_ROOT", DEFAULT_INTERNAL_STATIC_ROOT)
    )


def upload_relative_root():
    return "upload"


def external_upload_root():
    return os.path.join(external_static_root(), upload_relative_root())


def internal_upload_root():
    return os.path.join(internal_static_root(), upload_relative_root())


def primary_upload_root():
    return os.path.abspath(os.getenv("UPLOADED_PHOTOS_DEST", external_upload_root()))


def configured_upload_roots():
    roots = [
        ("external", external_upload_root()),
        ("internal", internal_upload_root()),
    ]
    primary = primary_upload_root()
    if all(os.path.abspath(path) != primary for _, path in roots):
        roots.insert(0, ("primary", primary))
    return [(name, os.path.abspath(path)) for name, path in roots]


def ensure_storage_dirs():
    paths = [
        external_static_root(),
        internal_static_root(),
        external_upload_root(),
        internal_upload_root(),
        os.path.join(external_upload_root(), "res"),
        os.path.join(internal_upload_root(), "res"),
    ]
    for path in paths:
        try:
            os.makedirs(path, exist_ok=True)
            log_asset(f"ensured directory: {path}", "debug")
        except Exception as exc:
            log_asset(f"failed to ensure directory {path}: {exc}", "warning")


def _is_inside(path, root):
    path = os.path.abspath(path)
    root = os.path.abspath(root)
    return path == root or path.startswith(root + os.sep)


def _relative_to_known_upload_root(path):
    absolute_path = os.path.abspath(path)
    for _, root in configured_upload_roots():
        if _is_inside(absolute_path, root):
            return os.path.relpath(absolute_path, root).replace("\\", "/")
    return None


def safe_asset_relative_path(value):
    normalized = str(value or "").replace("\\", "/").strip()
    prefixes = (
        "/api/file/assets-preview/photos/",
        "/api/file/assets-buffered/photos/",
        "/api/file/assets/photos/",
        "/_uploads/photos/",
        "/static/upload/",
    )
    for prefix in prefixes:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
            break
    marker = "/static/upload/"
    marker_index = normalized.find(marker)
    if marker_index >= 0:
        normalized = normalized[marker_index + len(marker):]
    normalized = normalized.lstrip("/")
    parts = [part for part in normalized.split("/") if part not in ("", ".")]
    if any(part == ".." for part in parts):
        return ""
    return "/".join(parts)


def storage_read_order():
    raw_order = os.getenv("GEOVIEW_ASSET_READ_ORDER", "external,internal")
    order = [item.strip().lower() for item in raw_order.split(",") if item.strip()]
    root_map = {
        "external": external_upload_root(),
        "internal": internal_upload_root(),
        "primary": primary_upload_root(),
    }
    resolved = []
    for name in order:
        root = root_map.get(name)
        if root:
            resolved.append((name, os.path.abspath(root)))
    for name, root in configured_upload_roots():
        if all(os.path.abspath(root) != os.path.abspath(path) for _, path in resolved):
            resolved.append((name, root))
    return resolved


def resolve_asset_path(relative_path):
    normalized = safe_asset_relative_path(relative_path)
    if not normalized:
        return None
    misses = []
    for store, root in storage_read_order():
        candidate = os.path.abspath(os.path.join(root, normalized))
        if not _is_inside(candidate, root):
            misses.append({"store": store, "path": candidate, "reason": "unsafe"})
            continue
        if os.path.isfile(candidate):
            log_asset(f"resolved {normalized} from {store}: {candidate}", "debug")
            return {
                "store": store,
                "root": root,
                "relative_path": normalized,
                "absolute_path": candidate,
                "misses": misses,
            }
        misses.append({"store": store, "path": candidate, "reason": "not_found"})
    log_asset(f"asset not found: {normalized}; misses={misses}", "warning")
    return {
        "store": "",
        "root": "",
        "relative_path": normalized,
        "absolute_path": "",
        "misses": misses,
    }


def mirror_file(path):
    relative_path = _relative_to_known_upload_root(path)
    if not relative_path or not os.path.isfile(path):
        return []

    source_path = os.path.abspath(path)
    results = []
    for store, root in configured_upload_roots():
        target_path = os.path.abspath(os.path.join(root, relative_path))
        if target_path == source_path:
            continue
        try:
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            shutil.copy2(source_path, target_path)
            results.append({"store": store, "path": target_path, "ok": True})
            log_asset(f"mirrored {relative_path} to {store}: {target_path}", "debug")
        except Exception as exc:
            results.append({"store": store, "path": target_path, "ok": False, "error": str(exc)})
            log_asset(f"mirror failed for {relative_path} to {target_path}: {exc}", "warning")
    return results


def mirror_upload_tree():
    start = time.time()
    roots = configured_upload_roots()
    primary = primary_upload_root()
    if not os.path.isdir(primary):
        log_asset(f"primary upload root missing, skip tree mirror: {primary}", "warning")
        return {"copied": 0, "failed": 0, "duration_ms": 0}

    copied = 0
    failed = 0
    for dirpath, _, filenames in os.walk(primary):
        for filename in filenames:
            source_path = os.path.join(dirpath, filename)
            relative_path = os.path.relpath(source_path, primary).replace("\\", "/")
            for _, root in roots:
                target_path = os.path.abspath(os.path.join(root, relative_path))
                if os.path.abspath(source_path) == target_path:
                    continue
                with suppress(FileNotFoundError):
                    if os.path.getsize(source_path) == os.path.getsize(target_path):
                        continue
                try:
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    shutil.copy2(source_path, target_path)
                    copied += 1
                except Exception as exc:
                    failed += 1
                    log_asset(f"tree mirror failed {source_path} -> {target_path}: {exc}", "warning")
    duration_ms = int((time.time() - start) * 1000)
    log_asset(f"tree mirror completed copied={copied} failed={failed} duration_ms={duration_ms}", "info")
    return {"copied": copied, "failed": failed, "duration_ms": duration_ms}

