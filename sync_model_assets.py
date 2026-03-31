#!/usr/bin/env python3
"""Sync runtime cache directories from backend/model source-of-truth assets."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
MODEL_ROOT = REPO_ROOT / "backend" / "model"
OFFLINE_CACHE_ROOT = REPO_ROOT / "offline_cache"
HF_CACHE_ROOT = OFFLINE_CACHE_ROOT / "huggingface" / "hub"
TORCH_CACHE_ROOT = OFFLINE_CACHE_ROOT / "torch" / "hub" / "checkpoints"
PADDLE_CACHE_ROOT = OFFLINE_CACHE_ROOT / "paddle"


def sync_path(src: Path, dst: Path) -> None:
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def sync_huggingface(verbose: bool) -> int:
    HF_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    synced = 0
    for hub_dir in MODEL_ROOT.glob("**/hub"):
        for item in sorted(hub_dir.iterdir()):
            target = HF_CACHE_ROOT / item.name
            sync_path(item, target)
            synced += 1
            if verbose:
                print(f"[sync] HF {item} -> {target}")
    return synced


def sync_loftr(verbose: bool) -> int:
    checkpoint = MODEL_ROOT / "registration" / "loftr_outdoor" / "loftr_outdoor.ckpt"
    if not checkpoint.exists():
        return 0
    TORCH_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    target = TORCH_CACHE_ROOT / "loftr_outdoor.ckpt"
    sync_path(checkpoint, target)
    if verbose:
        print(f"[sync] LoFTR {checkpoint} -> {target}")
    return 1


def ensure_paddle_cache(verbose: bool) -> int:
    PADDLE_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    if verbose:
        print(f"[sync] Paddle cache dir ready: {PADDLE_CACHE_ROOT}")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quiet", action="store_true", help="suppress per-file output")
    args = parser.parse_args()

    verbose = not args.quiet
    hf_count = sync_huggingface(verbose)
    loftr_count = sync_loftr(verbose)
    paddle_count = ensure_paddle_cache(verbose)
    print(
        f"[sync] completed: hf_entries={hf_count}, loftr={loftr_count}, paddle_dirs={paddle_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
