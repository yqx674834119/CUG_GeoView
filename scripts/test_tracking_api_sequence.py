#!/usr/bin/env python3
"""
Run real GeoView tracking API smoke tests with any local image sequence directory.
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
    parser = argparse.ArgumentParser(
        description="Smoke-test GeoView tracking API with a local image sequence directory.")
    parser.add_argument("--sequence-dir", required=True, help="Directory containing ordered image frames.")
    parser.add_argument("--num-frames", type=int, default=8)
    parser.add_argument(
        "--model-path",
        action="append",
        default=None,
        help=(
            "Optional tracking model path to evaluate. Repeat to test multiple models. "
            "Defaults to both botsort_official and botsort engineering."
        ),
    )
    return parser.parse_args()


def prepare_uploaded_frames(sequence_dir: Path, num_frames: int):
    upload_dir = REPO_ROOT / "static" / "upload"
    upload_dir.mkdir(parents=True, exist_ok=True)

    selected = sorted(sequence_dir.glob("*.jpg"))[:num_frames]
    if len(selected) < 2:
        raise RuntimeError(f"Need at least 2 .jpg frames under {sequence_dir}")

    token = f"api_seq_{uuid.uuid4().hex[:8]}"
    uploaded_names = []
    for index, src in enumerate(selected, start=1):
        target_name = f"{token}_{index:03d}{src.suffix.lower()}"
        shutil.copy2(src, upload_dir / target_name)
        uploaded_names.append(target_name)
    return uploaded_names


def infer_variant(model_path: str):
    if "botsort_official" in model_path:
        return "official"
    if "botsort" in model_path:
        return "engineering"
    return "unknown"


def main():
    args = parse_args()
    sequence_dir = Path(args.sequence_dir).resolve()
    if not sequence_dir.is_dir():
        raise RuntimeError(f"Sequence directory not found: {sequence_dir}")

    uploaded_names = prepare_uploaded_frames(sequence_dir, args.num_frames)

    import sys

    sys.path.insert(0, str(BACKEND_ROOT))
    from applications import create_app
    from applications.extensions import db

    app = create_app("testing")
    app.config["PROPAGATE_EXCEPTIONS"] = True
    client = app.test_client()

    model_paths = args.model_path or [
        "backend/model/tracking/botsort_official",
        "backend/model/tracking/botsort",
    ]
    report = {
        "sequence_dir": str(sequence_dir),
        "frames": uploaded_names,
        "results": {},
    }

    with app.app_context():
        db.create_all()

        for model_path in model_paths:
            expected_variant = infer_variant(model_path)
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
            if expected_variant != "unknown" and variant != expected_variant:
                raise RuntimeError(
                    f"{model_path} returned runtime_variant={variant}, expected {expected_variant}"
                )

            report["results"][model_path] = {
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
