#!/usr/bin/env python3
"""
Download helper for public tracking / anomaly datasets used by GeoView.

Default behavior is intentionally lightweight:
1. Only downloads public assets that are confirmed to stay below 1 GB.
2. Large full datasets require explicit --allow-large.
3. WALDO30 defaults to the strongest engineering weight for BoT-SORT testing.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Dict, Iterable, List, Optional


VISDRONE_MOT_FILES = {
    "train": "https://drive.google.com/file/d/1-qX2d-P1Xr64ke6nTdlm33om1VxCUTSh/view?usp=sharing",
    "val": "https://drive.google.com/file/d/1rqnKe9IgU_crMaxRoel9_nuUsMEBBVQu/view?usp=sharing",
    "test-dev": "https://drive.google.com/open?id=14z8Acxopj1d86-qhsF1NwS4Bv3KYa4Wu",
    "test-challenge": "https://drive.google.com/file/d/1I0nn6dVKctzDE5YJ3q9qOlhKLiSIDAxF/view?usp=sharing",
}


DATASET_CATALOG: Dict[str, Dict[str, object]] = {
    "a2seek_preview": {
        "type": "hf_dataset",
        "repo_id": "Hayneyday/A2Seek_Preview",
        "dirname": "A2Seek_Preview",
        "size_mb": 200.57,
        "lightweight": True,
        "note": (
            "Official Hugging Face preview subset. The public repo metadata reports "
            "about 200.57 MB in total, suitable for lightweight testing."
        ),
    },
    "waldo30": {
        "type": "hf_model_files",
        "repo_id": "StephanST/WALDO30",
        "dirname": "WALDO30",
        "files_by_variant": {
            "n": ["WALDO30_yolov8n_640x640.pt"],
            "m": ["WALDO30_yolov8m_640x640.pt"],
            "l": ["WALDO30_yolov8l-p2_1024x1024.pt"],
            "all": [
                "WALDO30_yolov8n_640x640.pt",
                "WALDO30_yolov8m_640x640.pt",
                "WALDO30_yolov8l-p2_1024x1024.pt",
            ],
        },
        "variant_sizes_mb": {
            "n": 6.00,
            "m": 49.66,
            "l": None,
            "all": None,
        },
        "lightweight": True,
        "note": (
            "Optional detector weights for GeoView BoT-SORT. Default variant is "
            "yolov8l-p2_1024x1024 for best engineering performance."
        ),
    },
    "satvideodt_toolkit": {
        "type": "git",
        "repo_url": "https://github.com/zf020114/SatVedioDTkit.git",
        "dirname": "SatVedioDTkit",
        "lightweight": True,
        "note": "Official SatVideoDT toolkit repository, used for evaluation and format conversion.",
    },
    "viso": {
        "type": "gdown_file",
        "url": "https://drive.google.com/file/d/11G0pqEMletzPtueGbgD-Pq9stQAcvpWw/view?usp=sharing",
        "dirname": "VISO",
        "lightweight": False,
        "note": "Full official dataset archive. Large download, blocked unless --allow-large is set.",
    },
    "satvideodt": {
        "type": "gdown_folder",
        "url": "https://drive.google.com/drive/folders/1iRg72Bre4QagbqxcYevcgDoDV5oR-c23?usp=sharing",
        "dirname": "SatVideoDT",
        "lightweight": False,
        "note": "Full official dataset folder. Large download, blocked unless --allow-large is set.",
    },
    "ootb": {
        "type": "gdown_folder",
        "url": "https://drive.google.com/drive/folders/1sLZuvXByB5uliZJvWfiLx5NT9P7BWg39?hl=zh-cn",
        "dirname": "OOTB",
        "lightweight": False,
        "note": "Full official dataset folder. Large download, blocked unless --allow-large is set.",
    },
    "visdrone_mot": {
        "type": "gdown_multi",
        "files": VISDRONE_MOT_FILES,
        "dirname": "VisDrone-MOT",
        "default_splits": ["val"],
        "lightweight": False,
        "note": "Full official splits. Large download, blocked unless --allow-large is set.",
    },
    "a2seek": {
        "type": "hf_dataset",
        "repo_id": "Hayneyday/A2Seek",
        "dirname": "A2Seek",
        "lightweight": False,
        "note": "Full official dataset. Large download, blocked unless --allow-large is set.",
    },
}


def require_module(name: str):
    try:
        return __import__(name)
    except ImportError as exc:
        raise SystemExit(
            f"Missing dependency '{name}'. Install it first, e.g. `pip install {name}`."
        ) from exc


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def download_gdrive_file(url: str, out_dir: Path):
    gdown = require_module("gdown")
    ensure_dir(out_dir)
    return gdown.download(url=url, output=str(out_dir), quiet=False, fuzzy=True)


def download_gdrive_folder(url: str, out_dir: Path):
    gdown = require_module("gdown")
    ensure_dir(out_dir)
    return gdown.download_folder(url=url,
                                 output=str(out_dir),
                                 quiet=False,
                                 use_cookies=False)


def snapshot_hf_dataset(repo_id: str, out_dir: Path, allow_patterns: Optional[List[str]] = None):
    hf = require_module("huggingface_hub")
    ensure_dir(out_dir)
    kwargs = {
        "repo_id": repo_id,
        "repo_type": "dataset",
        "local_dir": str(out_dir),
        "local_dir_use_symlinks": False,
    }
    if allow_patterns:
        kwargs["allow_patterns"] = allow_patterns
    return hf.snapshot_download(**kwargs)


def download_hf_model_files(repo_id: str, files: Iterable[str], out_dir: Path):
    hf = require_module("huggingface_hub")
    ensure_dir(out_dir)
    saved = []
    for filename in files:
        saved.append(
            hf.hf_hub_download(repo_id=repo_id,
                               filename=filename,
                               local_dir=str(out_dir),
                               local_dir_use_symlinks=False))
    return saved


def clone_repo(repo_url: str, out_dir: Path):
    if out_dir.exists() and any(out_dir.iterdir()):
        print(f"[skip] {out_dir} already exists and is not empty.", flush=True)
        return str(out_dir)
    ensure_dir(out_dir.parent)
    subprocess.run(["git", "clone", repo_url, str(out_dir)], check=True)
    return str(out_dir)


def dataset_choices() -> List[str]:
    return sorted(DATASET_CATALOG.keys())


def default_datasets() -> List[str]:
    return ["a2seek_preview", "waldo30", "satvideodt_toolkit"]


def describe_dataset(name: str, config: Dict[str, object], waldo_variant: str) -> str:
    kind = str(config["type"])
    size_mb = config.get("size_mb")
    if name == "waldo30":
        size_mb = config["variant_sizes_mb"][waldo_variant]
    size_text = f"{size_mb:.2f} MB" if isinstance(size_mb, (int, float)) else "size unknown / large"
    level = "lightweight" if config.get("lightweight") else "large"
    return f"{name:18} {level:10} {size_text:18} {kind:14} {config['note']}"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Download helper for GeoView tracking datasets and assets.")
    parser.add_argument(
        "--dataset",
        nargs="+",
        default=default_datasets(),
        choices=dataset_choices(),
        help="One or more datasets/assets to download. Default only includes lightweight items.",
    )
    parser.add_argument(
        "--splits",
        nargs="+",
        default=None,
        help="Optional splits for visdrone_mot. Default: val.",
    )
    parser.add_argument(
        "--output-dir",
        default="datasets",
        help="Target root directory. Default: ./datasets",
    )
    parser.add_argument(
        "--waldo30-variant",
        default="l",
        choices=["n", "m", "l", "all"],
        help="Weight variant for WALDO30. Default: l.",
    )
    parser.add_argument(
        "--allow-large",
        action="store_true",
        help="Allow downloading the large full datasets in the catalog.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print the catalog and exit.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned actions without downloading.",
    )
    return parser.parse_args()


def list_catalog(waldo_variant: str):
    print("Available datasets/assets:")
    for name in dataset_choices():
        print(describe_dataset(name, DATASET_CATALOG[name], waldo_variant))


def guard_large_dataset(dataset_name: str, config: Dict[str, object], allow_large: bool):
    if config.get("lightweight"):
        return
    if allow_large:
        return
    raise SystemExit(
        f"'{dataset_name}' is a large full dataset and is blocked by default. "
        "Use --allow-large only when the machine has enough disk and memory."
    )


def main():
    args = parse_args()
    root = Path(args.output_dir).resolve()
    ensure_dir(root)

    if args.list:
        list_catalog(args.waldo30_variant)
        return

    for dataset_name in args.dataset:
        config = DATASET_CATALOG[dataset_name]
        target_dir = root / str(config["dirname"])
        print(f"\n=== {dataset_name} -> {target_dir}")
        print(f"note: {config['note']}")

        if args.dry_run:
            if (not config.get("lightweight")) and (not args.allow_large):
                print("[blocked] Large dataset. Re-run with --allow-large to actually download it.")
            continue

        guard_large_dataset(dataset_name, config, args.allow_large)

        kind = config["type"]
        if kind == "gdown_file":
            download_gdrive_file(str(config["url"]), target_dir)
        elif kind == "gdown_folder":
            download_gdrive_folder(str(config["url"]), target_dir)
        elif kind == "gdown_multi":
            requested_splits = args.splits or list(config["default_splits"])
            available = config["files"]
            for split in requested_splits:
                if split not in available:
                    raise SystemExit(
                        f"Unsupported visdrone_mot split '{split}'. Available: {', '.join(sorted(available))}"
                    )
                split_dir = target_dir / split
                print(f"[download] VisDrone-MOT split: {split}")
                download_gdrive_file(str(available[split]), split_dir)
        elif kind == "hf_dataset":
            snapshot_hf_dataset(str(config["repo_id"]), target_dir)
        elif kind == "hf_model_files":
            files = list(config["files_by_variant"][args.waldo30_variant])
            download_hf_model_files(str(config["repo_id"]), files, target_dir)
        elif kind == "git":
            clone_repo(str(config["repo_url"]), target_dir)
        else:
            raise SystemExit(f"Unsupported dataset type: {kind}")

    print("\nDone.")


if __name__ == "__main__":
    main()
