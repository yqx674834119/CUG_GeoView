#!/usr/bin/env python
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from contextlib import suppress


PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
    "/w8AAgMBgJ8L8JQAAAAASUVORK5CYII="
)

VIDEO_HEADERS = {"Range": "bytes=0-255"}


def env_flag(name, default):
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def ensure_parent(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def write_probe_png(path):
    ensure_parent(path)
    with open(path, "wb") as file:
        file.write(PNG_BYTES)


def write_probe_mp4(path):
    ensure_parent(path)
    ffmpeg = shutil_which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is not available in the container")

    cmd = [
        ffmpeg,
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=black:s=64x64:d=1",
        "-movflags",
        "+faststart",
        "-pix_fmt",
        "yuv420p",
        path,
    ]
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=180,
    )
    if result.returncode != 0 or not os.path.isfile(path):
        raise RuntimeError(f"ffmpeg failed to create probe mp4: {result.stderr}")


def shutil_which(name):
    for directory in os.getenv("PATH", "").split(os.pathsep):
        candidate = os.path.join(directory, name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return ""


def fetch(url, headers=None, timeout=15):
    request = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
        return {
            "status": response.status,
            "headers": dict(response.headers.items()),
            "body_length": len(body),
        }


def wait_for_ping(base_url, timeout_seconds):
    ping_url = f"{base_url}/api/system/ping"
    deadline = time.time() + timeout_seconds
    last_error = ""
    while time.time() < deadline:
        try:
            payload = fetch(ping_url, timeout=5)
            if payload["status"] == 200:
                return {"ok": True, "url": ping_url}
        except Exception as exc:  # pragma: no cover - startup diagnostics only
            last_error = str(exc)
        time.sleep(1)
    return {"ok": False, "url": ping_url, "error": last_error or "timeout"}


def evaluate_binary_response(result, expected_status, expected_length=None,
                             require_range=False):
    headers = {key.lower(): value for key, value in result.get("headers", {}).items()}
    content_length = int(headers.get("content-length", "0") or "0")
    checks = {
        "status_ok": result.get("status") == expected_status,
        "body_length_matches_header": content_length == result.get("body_length"),
    }
    if expected_length is not None:
        checks["body_length_matches_expected"] = result.get(
            "body_length") == expected_length
    if require_range:
        checks["accept_ranges_present"] = headers.get("accept-ranges") == "bytes"
        checks["content_range_present"] = bool(headers.get("content-range"))
    return checks


def summarize_failure(prefix, checks):
    failed = [name for name, ok in checks.items() if not ok]
    if not failed:
        return ""
    return f"{prefix} failed checks: {', '.join(failed)}"


def build_results():
    runtime_log_dir = os.getenv("RUNTIME_LOG_DIR", "/tmp/geoview-logs")
    diagnostics_path = os.getenv(
        "GEOVIEW_BACKEND_DIAGNOSTICS_PATH",
        os.path.join(runtime_log_dir, "backend-startup-diagnostics.json"),
    )
    base_url = os.getenv(
        "GEOVIEW_BACKEND_DIAGNOSTIC_BASE_URL",
        f"http://127.0.0.1:{os.getenv('BACKEND_PORT', '5008')}",
    ).rstrip("/")
    upload_dest = os.getenv("UPLOADED_PHOTOS_DEST", "/app/backend/static/upload")
    serve_mode = os.getenv("GEOVIEW_PHOTO_ASSET_SERVE_MODE", "buffered")
    strict = env_flag("GEOVIEW_STRICT_STARTUP_DIAGNOSTICS", "true")
    wait_timeout = int(os.getenv("GEOVIEW_DIAGNOSTICS_WAIT_TIMEOUT", "60"))

    probe_dir = os.path.join(upload_dest, "res")
    png_name = "geoview_startup_probe.png"
    mp4_name = "geoview_startup_probe.mp4"
    png_path = os.path.join(probe_dir, png_name)
    mp4_path = os.path.join(probe_dir, mp4_name)

    results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "base_url": base_url,
        "uploaded_photos_dest": upload_dest,
        "photo_asset_serve_mode": serve_mode,
        "diagnostics_path": diagnostics_path,
        "strict_mode": strict,
        "supported_api_prefixes": {
            "image": "/api/file/assets/photos/",
            "buffered_image": "/api/file/assets-buffered/photos/",
            "legacy": "/_uploads/photos/",
        },
        "checks": {},
        "warnings": [],
        "errors": [],
        "pass": False,
    }

    wait_result = wait_for_ping(base_url, wait_timeout)
    results["checks"]["backend_ping"] = wait_result
    if not wait_result.get("ok"):
        results["errors"].append(
            f"backend ping failed: {wait_result.get('error', 'unknown error')}")
        return results

    os.makedirs(probe_dir, exist_ok=True)
    write_probe_png(png_path)
    write_probe_mp4(mp4_path)

    png_size = os.path.getsize(png_path)
    mp4_size = os.path.getsize(mp4_path)
    results["probe_files"] = {
        "png_path": png_path,
        "png_size": png_size,
        "mp4_path": mp4_path,
        "mp4_size": mp4_size,
    }

    checks = {
        "image_direct": {
            "url": f"{base_url}/api/file/assets/photos/res/{png_name}",
            "expected_status": 200,
            "expected_length": png_size,
        },
        "image_buffered": {
            "url": f"{base_url}/api/file/assets-buffered/photos/res/{png_name}",
            "expected_status": 200,
            "expected_length": png_size,
        },
        "video_direct_range": {
            "url": f"{base_url}/api/file/assets/photos/res/{mp4_name}",
            "expected_status": 206,
            "expected_length": 256,
            "headers": VIDEO_HEADERS,
            "require_range": True,
        },
        "video_buffered_range": {
            "url": f"{base_url}/api/file/assets-buffered/photos/res/{mp4_name}",
            "expected_status": 206,
            "expected_length": 256,
            "headers": VIDEO_HEADERS,
            "require_range": True,
        },
        "legacy_image_route": {
            "url": f"{base_url}/_uploads/photos/res/{png_name}",
            "expected_status": 200,
            "expected_length": png_size,
            "legacy_only": True,
        },
    }

    supported_failures = []
    for name, meta in checks.items():
        entry = {"url": meta["url"]}
        try:
            response = fetch(meta["url"], headers=meta.get("headers"))
            entry.update(response)
            entry["evaluation"] = evaluate_binary_response(
                response,
                meta["expected_status"],
                expected_length=meta["expected_length"],
                require_range=meta.get("require_range", False),
            )
        except urllib.error.HTTPError as exc:
            entry["status"] = exc.code
            entry["error"] = str(exc)
            entry["evaluation"] = {"status_ok": False}
        except Exception as exc:  # pragma: no cover - startup diagnostics only
            entry["status"] = None
            entry["error"] = str(exc)
            entry["evaluation"] = {"status_ok": False}

        entry["passed"] = all(entry["evaluation"].values())
        results["checks"][name] = entry

        if meta.get("legacy_only"):
            if not entry["passed"]:
                results["warnings"].append(
                    "legacy _uploads route is not healthy; clients must use "
                    "/api/file/assets/... or /api/file/assets-buffered/..."
                )
            continue

        if not entry["passed"]:
            supported_failures.append(summarize_failure(name, entry["evaluation"]))

    if supported_failures:
        results["errors"].extend(supported_failures)
        results["errors"].append(
            "supported asset API failed local loopback diagnostics; this would "
            "risk image/video transfer truncation in deployment"
        )
    else:
        results["pass"] = True

    return results


def write_results(path, payload):
    ensure_parent(path)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def main():
    results = build_results()
    diagnostics_path = results["diagnostics_path"]
    write_results(diagnostics_path, results)

    print("[diag][backend] asset diagnostics summary", flush=True)
    print(f"[diag][backend] pass={results['pass']}", flush=True)
    print(f"[diag][backend] diagnostics_path={diagnostics_path}", flush=True)
    print(f"[diag][backend] uploaded_photos_dest={results['uploaded_photos_dest']}",
          flush=True)
    print(f"[diag][backend] photo_asset_serve_mode={results['photo_asset_serve_mode']}",
          flush=True)

    for name, entry in results.get("checks", {}).items():
        status = entry.get("status", "n/a")
        passed = entry.get("passed", entry.get("ok"))
        print(f"[diag][backend] check={name} status={status} pass={passed}",
              flush=True)

    for warning in results.get("warnings", []):
        print(f"[diag][backend] warning={warning}", flush=True)
    for error in results.get("errors", []):
        print(f"[diag][backend] error={error}", flush=True)

    if results["strict_mode"] and not results["pass"]:
        print("[diag][backend] strict diagnostics failed; exiting with code 1",
              flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
