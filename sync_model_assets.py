#!/usr/bin/env python3
"""Sync runtime cache directories from backend/model source-of-truth assets."""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
MODEL_ROOT = REPO_ROOT / "backend" / "model"
OFFLINE_CACHE_ROOT = REPO_ROOT / "offline_cache"
HF_CACHE_ROOT = OFFLINE_CACHE_ROOT / "huggingface" / "hub"
TORCH_CACHE_ROOT = OFFLINE_CACHE_ROOT / "torch" / "hub" / "checkpoints"
PADDLE_CACHE_ROOT = OFFLINE_CACHE_ROOT / "paddle"


def unique_paths(*paths: Path) -> list[Path]:
    resolved = []
    seen = set()
    for path in paths:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        resolved.append(path)
    return resolved


def hf_cache_roots() -> list[Path]:
    runtime_hub = Path(os.environ.get("HF_HUB_CACHE", str(HF_CACHE_ROOT)))
    return unique_paths(HF_CACHE_ROOT, runtime_hub)


def torch_checkpoint_roots() -> list[Path]:
    torch_home = Path(os.environ.get("TORCH_HOME", str(OFFLINE_CACHE_ROOT / "torch")))
    return unique_paths(TORCH_CACHE_ROOT, torch_home / "hub" / "checkpoints")


def paddle_cache_roots() -> list[Path]:
    paddle_home = Path(os.environ.get("PADDLE_HOME", str(PADDLE_CACHE_ROOT)))
    paddle_cache = Path(os.environ.get("PADDLE_CACHE_DIR", str(paddle_home)))
    return unique_paths(PADDLE_CACHE_ROOT, paddle_home, paddle_cache)


def sync_path(src: Path, dst: Path) -> None:
    if src.is_dir():
        if dst.exists():
            if not dst.is_dir():
                dst.unlink()
                shutil.copytree(src, dst)
                return
            for item in src.iterdir():
                sync_path(item, dst / item.name)
            return
        shutil.copytree(src, dst)
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def sync_huggingface(verbose: bool) -> int:
    destinations = hf_cache_roots()
    for root in destinations:
        root.mkdir(parents=True, exist_ok=True)
    synced = 0
    for hub_dir in MODEL_ROOT.glob("**/hub"):
        for item in sorted(hub_dir.iterdir()):
            for root in destinations:
                target = root / item.name
                sync_path(item, target)
                if verbose:
                    print(f"[sync] HF {item} -> {target}")
            synced += 1
    return synced


def sync_loftr(verbose: bool) -> int:
    checkpoint = MODEL_ROOT / "registration" / "loftr_outdoor" / "loftr_outdoor.ckpt"
    if not checkpoint.exists():
        return 0
    for root in torch_checkpoint_roots():
        root.mkdir(parents=True, exist_ok=True)
        target = root / "loftr_outdoor.ckpt"
        sync_path(checkpoint, target)
        if verbose:
            print(f"[sync] LoFTR {checkpoint} -> {target}")
    return 1


def ensure_paddle_cache(verbose: bool) -> int:
    for root in paddle_cache_roots():
        root.mkdir(parents=True, exist_ok=True)
        if verbose:
            print(f"[sync] Paddle cache dir ready: {root}")
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
