#!/usr/bin/env python3
import argparse
import json
import os
import sys
from pathlib import Path

import requests


def show(name, ok, detail=""):
    mark = "PASS" if ok else "FAIL"
    print(f"[GeoView轻量后端测试] {mark} {name} {detail}", flush=True)
    if not ok:
        raise AssertionError(name)


def headers_summary(response):
    return {
        "status": response.status_code,
        "content_length": response.headers.get("Content-Length", ""),
        "transfer_encoding": response.headers.get("Transfer-Encoding", ""),
        "content_range": response.headers.get("Content-Range", ""),
        "x_disk_size": response.headers.get("X-GeoView-Disk-Size", ""),
        "x_json_bytes": response.headers.get("X-GeoView-Json-Bytes", ""),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--sample-file", default="TestData/CD/Val1/val_1.png")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    ping = requests.get(f"{base}/api/system/ping", timeout=10)
    show("system ping", ping.status_code == 200 and ping.json().get("code") == 0, json.dumps(headers_summary(ping), ensure_ascii=False))

    history = requests.get(f"{base}/api/history/list", params={"page": 1, "limit": 10}, timeout=20)
    payload = history.json()
    show("history list", history.status_code == 200 and payload.get("code") == 0 and len(payload.get("data") or []) >= 5, json.dumps(headers_summary(history), ensure_ascii=False))
    first = payload["data"][0]
    asset = first.get("before_img") or "/api/file/assets/photos/cd_val1_2_3mb.png"

    for record_type in ["变化检测", "目标检测", "地物分类", "场景分类", "影像超分重建", "自动配准", "目标跟踪"]:
        typed_history = requests.get(f"{base}/api/history/list", params={"type": record_type, "page": 1, "limit": 10}, timeout=20)
        typed_payload = typed_history.json()
        show(
            f"history filter {record_type}",
            typed_history.status_code == 200 and typed_payload.get("code") == 0 and len(typed_payload.get("data") or []) >= 1,
            json.dumps(headers_summary(typed_history), ensure_ascii=False),
        )

    for show_type in ["变化检测", "目标检测", "地物分类", "场景分类", "影像超分重建", "自动配准", "目标跟踪"]:
        show_history = requests.get(f"{base}/api/analysis/show/{show_type}", params={"page": 1, "limit": 10}, timeout=20)
        show_payload = show_history.json()
        show(
            f"analysis show {show_type}",
            show_history.status_code == 200 and show_payload.get("code") == 0 and len(show_payload.get("data") or []) >= 1,
            json.dumps(headers_summary(show_history), ensure_ascii=False),
        )

    direct = requests.get(f"{base}{asset}", timeout=30)
    show("asset direct", direct.status_code == 200 and len(direct.content) > 100000, json.dumps({**headers_summary(direct), "bytes": len(direct.content)}, ensure_ascii=False))

    buffered_path = asset.replace("/api/file/assets/photos/", "/api/file/assets-buffered/photos/")
    buffered = requests.get(f"{base}{buffered_path}", timeout=30)
    show("asset buffered", buffered.status_code == 200 and len(buffered.content) > 100000, json.dumps({**headers_summary(buffered), "bytes": len(buffered.content)}, ensure_ascii=False))

    preview_rel = asset.split("/api/file/assets/photos/", 1)[-1]
    preview = requests.get(f"{base}/api/file/assets-preview/photos/{preview_rel}", params={"max_size": 420}, timeout=30)
    preview_payload = preview.json()
    show("asset preview", preview.status_code == 200 and preview_payload.get("data", {}).get("data_url", "").startswith("data:"), json.dumps(headers_summary(preview), ensure_ascii=False))

    video = requests.get(f"{base}/api/file/assets/photos/tracking_12mb.mp4", headers={"Range": "bytes=0-255"}, timeout=20)
    show("video range", video.status_code == 206 and len(video.content) == 256, json.dumps({**headers_summary(video), "bytes": len(video.content)}, ensure_ascii=False))

    sample = Path(args.sample_file)
    with sample.open("rb") as file:
        upload = requests.post(
            f"{base}/api/file/upload",
            files=[("files", (sample.name, file, "image/png"))],
            data={"type": "目标检测"},
            timeout=30,
        )
    upload_payload = upload.json()
    show("file upload", upload.status_code == 200 and upload_payload.get("data", [{}])[0].get("src"), json.dumps(headers_summary(upload), ensure_ascii=False))
    uploaded_src = upload_payload["data"][0]["src"]

    analysis = requests.post(
        f"{base}/api/analysis/object_detection",
        json={"model_path": "/lite/model/object_detection/mock", "list": [uploaded_src], "prehandle": 0, "denoise": 0},
        timeout=30,
    )
    analysis_payload = analysis.json()
    show("pseudo analysis", analysis.status_code == 200 and analysis_payload.get("data", {}).get("records"), json.dumps(headers_summary(analysis), ensure_ascii=False))

    method_probe = requests.post(f"{base}/api/probe/method-asset/cd_val1_2_3mb.png", timeout=30)
    if method_probe.status_code != 404:
        show("method probe POST", method_probe.status_code == 200 and len(method_probe.content) > 100000, json.dumps({**headers_summary(method_probe), "bytes": len(method_probe.content)}, ensure_ascii=False))
    else:
        print("[GeoView轻量后端测试] SKIP method probe POST 仅 FastAPI 变体实现", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[GeoView轻量后端测试] FAIL 测试失败: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)
