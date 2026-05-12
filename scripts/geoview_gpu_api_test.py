#!/usr/bin/env python3
"""Run GeoView backend API checks in a GPU-enabled runtime."""

from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
TESTDATA_ROOT = REPO_ROOT / "TestData"


MODEL_CASES = {
    "change_detection": [
        "backend/model/change_detection/bit_256x256",
    ],
    "object_detection": [
        "backend/model/object_detection/paddle_yolo",
        "backend/model/object_detection/hf_conditional_detr_resnet50",
        "backend/model/object_detection/hf_detr_resnet50",
        "backend/model/object_detection/hf_waldo30",
        "backend/model/object_detection/mmrotate_oriented_rcnn_r50_fpn_1x_dota_le90",
    ],
    "semantic_segmentation": [
        "backend/model/semantic_segmentation/paddle_deeplabv3p",
        "backend/model/semantic_segmentation/mmseg_cugrs",
    ],
    "classification": [
        "backend/model/classification/resnet50",
    ],
    "image_restoration": [
        "backend/model/image_restoration/hf_swin2sr_x2",
        "backend/model/image_restoration/hf_swin2sr_x4",
    ],
    "registration": [
        "backend/model/registration/auto",
        "backend/model/registration/loftr_outdoor",
    ],
    "tracking": [
        "backend/model/tracking/auto",
        "backend/model/tracking/botsort",
        "backend/model/tracking/botsort_official",
    ],
}


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="docs/test-results/gpu-api-report.json")
    parser.add_argument("--tracking-frames", type=int, default=6)
    parser.add_argument("--tracking-width", type=int, default=960)
    return parser.parse_args()


def run_text(cmd: List[str]) -> Dict[str, Any]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        return {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def gpu_environment() -> Dict[str, Any]:
    env = {"nvidia_smi": run_text(["nvidia-smi"])}
    try:
        import torch

        env["torch"] = {
            "version": getattr(torch, "__version__", "unknown"),
            "cuda_available": bool(torch.cuda.is_available()),
            "device_count": int(torch.cuda.device_count()),
            "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "",
        }
    except Exception as exc:
        env["torch"] = {"error": str(exc)}
    try:
        import paddle

        compiled = bool(paddle.device.is_compiled_with_cuda())
        env["paddle"] = {
            "version": getattr(paddle, "__version__", "unknown"),
            "cuda_compiled": compiled,
            "device_count": int(paddle.device.cuda.device_count()) if compiled else 0,
        }
    except Exception as exc:
        env["paddle"] = {"error": str(exc)}
    return env


def assert_gpu(env: Dict[str, Any]):
    torch_ok = env.get("torch", {}).get("cuda_available") is True
    paddle_ok = env.get("paddle", {}).get("device_count", 0) > 0
    if not (torch_ok or paddle_ok):
        raise RuntimeError("GPU is not visible inside this runtime; aborting GPU API tests.")


def open_app():
    sys.path.insert(0, str(BACKEND_ROOT))
    os.environ.setdefault("GEOVIEW_CONFIG", "embedded")
    os.environ.setdefault("GEOVIEW_DEBUG_LOG", "false")
    os.environ.setdefault("GEOVIEW_ASSET_DEBUG", "0")
    os.environ.setdefault("UPLOADED_PHOTOS_DEST", str(REPO_ROOT / "static" / "upload"))
    os.environ.setdefault("GEOVIEW_EXTERNAL_STATIC_ROOT", str(REPO_ROOT / "static"))
    os.environ.setdefault("GEOVIEW_INTERNAL_STATIC_ROOT", str(BACKEND_ROOT / "static"))

    from applications import create_app
    from applications.extensions import db

    app = create_app("testing")
    app.config["PROPAGATE_EXCEPTIONS"] = True
    client = app.test_client()
    ctx = app.app_context()
    ctx.push()
    db.create_all()
    return app, client, ctx


def response_json(response) -> Dict[str, Any]:
    try:
        return response.get_json(silent=True) or json.loads(response.data.decode("utf-8"))
    except Exception:
        return {"raw": response.data[:300].decode("utf-8", errors="replace")}


def compact_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        compact = {}
        for key, value in payload.items():
            if key in {"data", "records", "record"}:
                compact[key] = compact_payload(value)
            elif key in {"msg", "code", "success", "status", "summary", "runtime_variant", "method_used"}:
                compact[key] = compact_payload(value)
        return compact
    if isinstance(payload, list):
        return {"count": len(payload), "sample": compact_payload(payload[0]) if payload else None}
    return payload


def asset_paths(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, item in value.items():
            if key.endswith("_path") or key.endswith("_img") or key in {"src", "href", "mask", "mask_path"}:
                if isinstance(item, str) and item.startswith("/api/file/assets/photos/"):
                    yield item
            yield from asset_paths(item)
    elif isinstance(value, list):
        for item in value:
            yield from asset_paths(item)


def check_assets(client, payload: Any) -> List[Dict[str, Any]]:
    seen = []
    for path in sorted(set(asset_paths(payload))):
        response = client.get(path)
        seen.append({
            "path": path,
            "status": response.status_code,
            "content_type": response.content_type,
            "bytes": len(response.data),
            "ok": response.status_code == 200 and len(response.data) > 0,
        })
    return seen


def upload(client, path: Path, analysis_type: str) -> Dict[str, Any]:
    with path.open("rb") as source:
        response = client.post(
            "/api/file/upload",
            data={
                "type": analysis_type,
                "files": (io.BytesIO(source.read()), path.name),
            },
            content_type="multipart/form-data",
        )
    body = response_json(response)
    if response.status_code != 200 or body.get("code") != 0:
        raise RuntimeError(f"upload failed for {path}: {body}")
    item = body["data"][0]
    asset = client.get(item["src"])
    if asset.status_code != 200 or not asset.data:
        raise RuntimeError(f"uploaded asset is not readable: {item['src']}")
    return item


def call_case(client, name: str, method: str, path: str, payload: Optional[dict] = None) -> Dict[str, Any]:
    started = time.time()
    try:
        if method == "GET":
            response = client.get(path)
        else:
            response = client.post(path, json=payload or {})
        body = response_json(response)
        assets = check_assets(client, body)
        ok = response.status_code == 200 and body.get("code", 0) == 0 and body.get("success", True) is not False
        return {
            "name": name,
            "path": path,
            "status": "passed" if ok else "failed",
            "http_status": response.status_code,
            "duration_sec": round(time.time() - started, 2),
            "summary": compact_payload(body),
            "asset_checks": assets,
        }
    except Exception as exc:
        return {
            "name": name,
            "path": path,
            "status": "failed",
            "duration_sec": round(time.time() - started, 2),
            "error": str(exc),
        }


def prepare_tracking_frames(width: int, count: int) -> List[Path]:
    import cv2

    video_path = TESTDATA_ROOT / "Tracking" / "official_mot17_02_frcnn_180frames_raw.mp4"
    frame_dir = REPO_ROOT / "runtime" / "gpu-api-test-frames"
    if frame_dir.exists():
        shutil.rmtree(str(frame_dir))
    frame_dir.mkdir(parents=True, exist_ok=True)

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"unable to open tracking video: {video_path}")
    frames = []
    index = 0
    stride = 30
    while len(frames) < count:
        ok, frame = capture.read()
        if not ok:
            break
        if index % stride == 0:
            if width > 0 and frame.shape[1] > width:
                height = int(round(frame.shape[0] * (width / float(frame.shape[1]))))
                frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
            output = frame_dir / f"frame_{len(frames) + 1:03d}.jpg"
            if not cv2.imwrite(str(output), frame):
                raise RuntimeError(f"unable to write frame: {output}")
            frames.append(output)
        index += 1
    capture.release()
    if len(frames) < 2:
        raise RuntimeError("tracking frame extraction produced fewer than 2 frames")
    return frames


def main():
    args = parse_args()
    env = gpu_environment()
    assert_gpu(env)
    _, client, ctx = open_app()

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "gpu_environment": env,
        "testdata_root": str(TESTDATA_ROOT),
        "cases": [],
    }

    try:
        uploads = {
            "aircraft": upload(client, TESTDATA_ROOT / "Dec" / "aircraft_4.jpg", "目标检测"),
            "seg": upload(client, TESTDATA_ROOT / "Seg" / "aircraft_4.jpg", "地物分类"),
            "cd_a": upload(client, TESTDATA_ROOT / "CD" / "Val1" / "val_1.png", "变化检测"),
            "cd_b": upload(client, TESTDATA_ROOT / "CD" / "Val2" / "val_1.png", "变化检测"),
            "val": upload(client, TESTDATA_ROOT / "val_1.png", "图像复原"),
            "val_2x": upload(client, TESTDATA_ROOT / "val_1_2X.png", "自动配准"),
            "video": upload(client, TESTDATA_ROOT / "Tracking" / "official_mot17_02_frcnn_180frames_raw.mp4", "目标跟踪"),
        }
        tracking_frames = [
            upload(client, frame, "目标跟踪")
            for frame in prepare_tracking_frames(args.tracking_width, args.tracking_frames)
        ]
        report["upload_assets"] = uploads
        report["tracking_frame_count"] = len(tracking_frames)

        for path in ["/health", "/api/system/ping"]:
            report["cases"].append(call_case(client, path, "GET", path))
        for model_type in MODEL_CASES:
            report["cases"].append(call_case(client, f"model_list:{model_type}", "GET", f"/api/model/list/{model_type}"))

        for model_path in MODEL_CASES["change_detection"]:
            report["cases"].append(call_case(client, f"change_detection:{model_path}", "POST", "/api/analysis/change_detection", {
                "model_path": model_path,
                "list": [{"first": uploads["cd_a"]["src"], "second": uploads["cd_b"]["src"]}],
                "prehandle": 0,
                "denoise": 0,
                "window_size": 256,
                "stride": 128,
            }))

        for model_path in MODEL_CASES["object_detection"]:
            report["cases"].append(call_case(client, f"object_detection:{model_path}", "POST", "/api/analysis/object_detection", {
                "model_path": model_path,
                "list": [uploads["aircraft"]["src"]],
                "prehandle": 0,
                "denoise": 0,
            }))

        for model_path in MODEL_CASES["semantic_segmentation"]:
            report["cases"].append(call_case(client, f"semantic_segmentation:{model_path}", "POST", "/api/analysis/semantic_segmentation", {
                "model_path": model_path,
                "list": [uploads["seg"]["src"]],
                "prehandle": 0,
                "denoise": 0,
            }))

        for model_path in MODEL_CASES["classification"]:
            report["cases"].append(call_case(client, f"classification:{model_path}", "POST", "/api/analysis/classification", {
                "model_path": model_path,
                "list": [uploads["aircraft"]["src"]],
            }))

        for model_path in MODEL_CASES["image_restoration"]:
            report["cases"].append(call_case(client, f"image_restoration:{model_path}", "POST", "/api/analysis/image_restoration", {
                "model_path": model_path,
                "list": [uploads["val"]["src"]],
            }))

        for model_path in MODEL_CASES["registration"]:
            report["cases"].append(call_case(client, f"registration:{model_path}", "POST", "/api/analysis/registration", {
                "model_path": model_path,
                "list": [{"first": uploads["val"]["src"], "second": uploads["val_2x"]["src"]}],
            }))

        tracking_srcs = [item["src"] for item in tracking_frames]
        for model_path in MODEL_CASES["tracking"]:
            payload = {
                "model_path": model_path,
                "list": tracking_srcs,
            }
            if model_path.endswith(("/auto", "/csrt", "/kcf")):
                payload["rect"] = [120, 80, 80, 120]
            report["cases"].append(call_case(client, f"tracking:{model_path}", "POST", "/api/analysis/tracking", payload))

    finally:
        ctx.pop()

    passed = sum(1 for item in report["cases"] if item["status"] == "passed")
    failed = sum(1 for item in report["cases"] if item["status"] == "failed")
    report["summary"] = {
        "total": len(report["cases"]),
        "passed": passed,
        "failed": failed,
    }

    output_path = REPO_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False))
    if failed:
        print(f"GPU API report written with failures: {output_path}", file=sys.stderr)
    else:
        print(f"GPU API report written: {output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
