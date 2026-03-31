#!/usr/bin/env python3
"""Validate offline deployment assets before packaging or deployment."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


REPO_ROOT = Path(__file__).resolve().parent


HF_REPOS = {
    "caidas/swin2SR-classical-sr-x2-64": "HF super resolution x2",
    "caidas/swin2SR-classical-sr-x4-64": "HF super resolution x4",
    "facebook/detr-resnet-50": "HF object detection DETR",
    "microsoft/conditional-detr-resnet-50": "HF object detection Conditional DETR",
    "StephanST/WALDO30": "HF object detection WALDO30",
}

REQUIRED_FILES = {
    "CUGRS config": REPO_ROOT
    / "backend/model/semantic_segmentation/mmseg_cugrs/config.py",
    "CUGRS checkpoint": REPO_ROOT
    / "backend/model/semantic_segmentation/mmseg_cugrs/checkpoint.pth",
    "CUGRS DINOv3 backbone": REPO_ROOT
    / "backend/model/semantic_segmentation/mmseg_cugrs/support/dinov3_vitl16_pretrain_sat493m-eadcf0ff.pth",
    "CUGRS Swin backbone": REPO_ROOT
    / "backend/model/semantic_segmentation/mmseg_cugrs/support/swin_base_patch4_window7_224_20220317-e9b98025.pth",
    "MMRotate config": REPO_ROOT
    / "backend/model/object_detection/mmrotate_oriented_rcnn_r50_fpn_1x_dota_le90/config.py",
    "MMRotate checkpoint": REPO_ROOT
    / "backend/model/object_detection/mmrotate_oriented_rcnn_r50_fpn_1x_dota_le90/checkpoint.pth",
    "Paddle change detection": REPO_ROOT
    / "backend/model/change_detection/bit_256x256/model.pdmodel",
    "Paddle classification": REPO_ROOT
    / "backend/model/classification/resnet50/model.pdmodel",
    "Paddle object detection": REPO_ROOT
    / "backend/model/object_detection/paddle_yolo/model.pdmodel",
    "Paddle semantic segmentation": REPO_ROOT
    / "backend/model/semantic_segmentation/paddle_deeplabv3p/model.pdmodel",
    "LoFTR source checkpoint": REPO_ROOT
    / "backend/model/registration/loftr_outdoor/loftr_outdoor.ckpt",
}


@dataclass
class CheckResult:
    status: str
    label: str
    detail: str


def format_size(path: Path) -> str:
    size = path.stat().st_size
    units = ["B", "KB", "MB", "GB", "TB"]
    index = 0
    value = float(size)
    while value >= 1024 and index < len(units) - 1:
        value /= 1024.0
        index += 1
    return f"{value:.2f} {units[index]}"


def check_required_files() -> Iterable[CheckResult]:
    for label, path in REQUIRED_FILES.items():
        if path.exists():
            detail = str(path.relative_to(REPO_ROOT))
            if path.is_file():
                detail = f"{detail} ({format_size(path)})"
            yield CheckResult("PASS", label, detail)
        else:
            yield CheckResult("FAIL", label, f"missing: {path.relative_to(REPO_ROOT)}")


def hf_cache_dir(repo_id: str) -> Path:
    safe_name = repo_id.replace("/", "--")
    return REPO_ROOT / "offline_cache/huggingface/hub" / f"models--{safe_name}"


def check_hf_cache() -> Iterable[CheckResult]:
    for repo_id, label in HF_REPOS.items():
        cache_dir = hf_cache_dir(repo_id)
        refs_main = cache_dir / "refs/main"
        blobs_dir = cache_dir / "blobs"
        has_blob = blobs_dir.exists() and any(blobs_dir.iterdir())
        if refs_main.exists() and has_blob:
            yield CheckResult("PASS", label, str(cache_dir.relative_to(REPO_ROOT)))
        else:
            yield CheckResult(
                "FAIL",
                label,
                f"missing cache under {cache_dir.relative_to(REPO_ROOT)}",
            )


def check_loftr_cache() -> Iterable[CheckResult]:
    torch_cache = REPO_ROOT / "offline_cache/torch"
    patterns = ("**/*loftr*", "**/*outdoor*", "**/*.ckpt")
    matches: List[Path] = []
    for pattern in patterns:
        matches.extend(torch_cache.glob(pattern))
    file_matches = sorted({match for match in matches if match.is_file()})
    if file_matches:
        preview = ", ".join(str(path.relative_to(REPO_ROOT)) for path in file_matches[:3])
        yield CheckResult("PASS", "LoFTR torch cache", preview)
        return
    yield CheckResult(
        "FAIL",
        "LoFTR torch cache",
        "missing weights in offline_cache/torch",
    )


def check_cache_dirs() -> Iterable[CheckResult]:
    for name in ("offline_cache/huggingface", "offline_cache/torch", "offline_cache/paddle"):
        path = REPO_ROOT / name
        if path.exists():
            has_files = any(path.rglob("*"))
            status = "PASS" if has_files else "WARN"
            detail = str(path.relative_to(REPO_ROOT))
            if status == "WARN":
                detail += " (exists but is currently empty)"
            yield CheckResult(status, f"Cache dir {name}", detail)
        else:
            yield CheckResult("FAIL", f"Cache dir {name}", "directory does not exist")


def run_checks() -> List[CheckResult]:
    results: List[CheckResult] = []
    results.extend(check_cache_dirs())
    results.extend(check_required_files())
    results.extend(check_hf_cache())
    results.extend(check_loftr_cache())
    return results


def print_results(results: Iterable[CheckResult]) -> int:
    failures = 0
    warnings = 0
    for result in results:
        print(f"[{result.status}] {result.label}: {result.detail}")
        if result.status == "FAIL":
            failures += 1
        elif result.status == "WARN":
            warnings += 1
    print(f"\nSummary: {failures} failure(s), {warnings} warning(s).")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit with status 1 when any failure is detected",
    )
    args = parser.parse_args()

    results = run_checks()
    failures = print_results(results)
    if args.strict and failures:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
