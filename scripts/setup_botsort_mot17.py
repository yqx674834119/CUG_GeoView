#!/usr/bin/env python3
"""
Setup helper for GeoView dual BoT-SORT runtime and MOT17 assets.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


RUNTIME_ROOT = Path("/home/livablecity/geoview_runtime")
REPO_ROOT = Path(__file__).resolve().parents[1]
MOT17_URL = "https://motchallenge.net/data/MOT17.zip"
BYTE_TRACK_ABLATION = "https://drive.google.com/file/d/1iqhM-6V_r1FpOlOzrdP_Ejshgk0DxOob/view?usp=sharing"
BYTE_TRACK_X_MOT17 = "https://drive.google.com/file/d/1P4mY0Yyd3PPTybgZkjMYhFri88nTmJX5/view?usp=sharing"
MOT17_SBS_S50 = "https://drive.google.com/file/d/1QZFWpoa80rqo7O-HXmlss8J8CnS7IUsN/view?usp=sharing"


def run(cmd, cwd: Path | None = None):
    print("[run]", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def pip_install(env_name: str, *packages: str, cwd: Path | None = None):
    run([
        "conda",
        "run",
        "-n",
        env_name,
        "pip",
        "install",
        "--no-cache-dir",
        *packages,
    ], cwd=cwd)


def ensure_repo(path: Path, repo_url: str):
    if path.exists():
        print(f"[skip] repo exists: {path}", flush=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    run(["git", "clone", repo_url, str(path)])


def ensure_file_download(url: str, output: Path):
    if output.exists() and output.stat().st_size > 0:
        print(f"[skip] file exists: {output}", flush=True)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    run(["wget", "-O", str(output), url])


def ensure_gdrive_download(url: str, output: Path):
    if output.exists() and output.stat().st_size > 0:
        print(f"[skip] file exists: {output}", flush=True)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    run([sys.executable, "-m", "pip", "install", "gdown"])
    run([sys.executable, "-m", "gdown", "--fuzzy", url, "-O", str(output)])


def ensure_unzip(zip_path: Path, output_dir: Path):
    if output_dir.exists() and any(output_dir.iterdir()):
        print(f"[skip] unzip target exists: {output_dir}", flush=True)
        return
    output_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(output_dir.parent)


def conda_env_exists(name: str) -> bool:
    result = subprocess.run(["conda", "env", "list"],
                            capture_output=True,
                            text=True,
                            check=True)
    return any(line.split() and line.split()[0] == name
               for line in result.stdout.splitlines()
               if not line.startswith("#"))


def ensure_official_env(repo_dir: Path, env_name: str):
    if conda_env_exists(env_name):
        print(f"[skip] conda env exists: {env_name}", flush=True)
        return

    run(["conda", "create", "-y", "-n", env_name, "python=3.7"])
    pip_install(
        env_name,
        "torch==1.11.0+cu113",
        "torchvision==0.12.0+cu113",
        "--extra-index-url",
        "https://download.pytorch.org/whl/cu113",
    )
    pip_install(env_name, "-r", "requirements.txt", cwd=repo_dir)
    run(["conda", "run", "-n", env_name, "python", "setup.py", "develop"], cwd=repo_dir)
    pip_install(
        env_name,
        "cython",
        "cython_bbox",
        "faiss-cpu",
        "opencv-contrib-python<4.11",
        "pycocotools",
    )


def ensure_engineering_env(env_name: str):
    if conda_env_exists(env_name):
        print(f"[skip] conda env exists: {env_name}", flush=True)
        return

    run(["conda", "create", "-y", "-n", env_name, "python=3.10"])
    pip_install(
        env_name,
        "torch==2.1.2",
        "torchvision==0.16.2",
        "--index-url",
        "https://download.pytorch.org/whl/cu118",
    )
    pip_install(
        env_name,
        "-r",
        "backend/requirements-hf.txt",
        cwd=REPO_ROOT,
    )
    pip_install(
        env_name,
        "transformers==4.36.2",
        "huggingface_hub",
        "timm",
        "ultralytics",
        "opencv-python<4.11",
        "opencv-python-headless<4.11",
        "numpy<2",
    )


def parse_args():
    parser = argparse.ArgumentParser(description="Setup dual BoT-SORT runtime and MOT17 assets.")
    parser.add_argument("--runtime-root", default=str(RUNTIME_ROOT))
    parser.add_argument("--official-env", default="BoTSORTOfficial37")
    parser.add_argument("--hf-env", default="HFPyTorch310")
    parser.add_argument("--skip-env", action="store_true")
    parser.add_argument("--skip-mot17", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    runtime_root = Path(args.runtime_root).resolve()
    botsort_repo = runtime_root / "BoT-SORT"
    trackeval_repo = runtime_root / "TrackEval"
    mot_zip = runtime_root / "downloads" / "MOT17.zip"
    mot_root = runtime_root / "datasets" / "MOT17"
    pretrained_dir = botsort_repo / "pretrained"

    ensure_repo(botsort_repo, "https://github.com/NirAharon/BoT-SORT.git")
    ensure_repo(trackeval_repo, "https://github.com/JonathonLuiten/TrackEval.git")

    if not args.skip_mot17:
        ensure_file_download(MOT17_URL, mot_zip)
        ensure_unzip(mot_zip, mot_root)

    ensure_gdrive_download(BYTE_TRACK_ABLATION, pretrained_dir / "bytetrack_ablation.pth.tar")
    ensure_gdrive_download(BYTE_TRACK_X_MOT17, pretrained_dir / "bytetrack_x_mot17.pth.tar")
    ensure_gdrive_download(MOT17_SBS_S50, pretrained_dir / "mot17_sbs_S50.pth")

    if not args.skip_env:
        ensure_engineering_env(args.hf_env)
        ensure_official_env(botsort_repo, args.official_env)

    print("\nSetup complete.", flush=True)
    print(f"BoT-SORT repo: {botsort_repo}", flush=True)
    print(f"TrackEval repo: {trackeval_repo}", flush=True)
    print(f"MOT17 root: {mot_root}", flush=True)


if __name__ == "__main__":
    main()
