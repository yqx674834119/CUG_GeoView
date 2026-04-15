#!/usr/bin/env python3
"""
Run real GeoView tracking API smoke tests with MOT17 sample frames.
"""

from __future__ import annotations

import argparse
import json
import shutil
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"


def parse_args():
    parser = argparse.ArgumentParser(description="Smoke-test GeoView tracking API with MOT17 frames.")
    parser.add_argument("--runtime-root", default="/home/livablecity/geoview_runtime")
    parser.add_argument("--sequence", default="MOT17-02-FRCNN")
    parser.add_argument("--num-frames", type=int, default=8)
    return parser.parse_args()


def prepare_uploaded_frames(sequence_dir: Path, num_frames: int):
    upload_dir = REPO_ROOT / "static" / "upload"
    upload_dir.mkdir(parents=True, exist_ok=True)

    selected = sorted(sequence_dir.glob("*.jpg"))[:num_frames]
    if len(selected) < 2:
        raise RuntimeError(f"Need at least 2 frames under {sequence_dir}")

    token = f"mot17_api_{uuid.uuid4().hex[:8]}"
    uploaded_names = []
    for index, src in enumerate(selected, start=1):
        target_name = f"{token}_{index:03d}{src.suffix.lower()}"
        shutil.copy2(src, upload_dir / target_name)
        uploaded_names.append(target_name)
    return uploaded_names


def main():
    args = parse_args()
    runtime_root = Path(args.runtime_root).resolve()
    sequence_dir = runtime_root / "datasets" / "MOT17" / "train" / args.sequence / "img1"
    if not sequence_dir.is_dir():
        raise RuntimeError(f"MOT17 sequence not found: {sequence_dir}")

    uploaded_names = prepare_uploaded_frames(sequence_dir, args.num_frames)

    import sys

    sys.path.insert(0, str(BACKEND_ROOT))
    from applications import create_app
    from applications.extensions import db

    app = create_app("testing")
    app.config["PROPAGATE_EXCEPTIONS"] = True
    client = app.test_client()

    report = {
        "sequence": args.sequence,
        "frames": uploaded_names,
        "results": {},
    }

    with app.app_context():
        db.create_all()

        for model_path, expected_variant in [
            ("backend/model/tracking/botsort_official", "official"),
            ("backend/model/tracking/botsort", "engineering"),
        ]:
            payload = {
                "model_path": model_path,
                "list": uploaded_names,
            }
            response = client.post("/api/analysis/tracking", json=payload)
            data = json.loads(response.data)
            if data.get("code") != 0:
                raise RuntimeError(f"{model_path} failed: {data}")

            body = data["data"]
            variant = body.get("runtime_variant")
            if variant != expected_variant:
                raise RuntimeError(
                    f"{model_path} returned runtime_variant={variant}, expected {expected_variant}"
                )

            report["results"][expected_variant] = {
                "model_path": model_path,
                "runtime_variant": variant,
                "method_used": body.get("method_used"),
                "summary": body.get("summary"),
                "preview_path": body.get("preview_path"),
                "trajectory_path": body.get("trajectory_path"),
                "output_video_path": body.get("output_video_path"),
                "mot_result_path": body.get("mot_result_path"),
            }

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
