from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPO_ROOT / "backend"
SAM3_WORKER = BACKEND_ROOT / "scripts" / "sam3_prompt_worker.py"

DEFAULT_SAM3_PYTHON = "/opt/conda/envs/SAM312/bin/python"
DEFAULT_SAM3_CHECKPOINT = "/opt/geoview-models/sam3/sam3.1_multiplex.pt"

PROMPT_ALIASES = {
    "车辆": "vehicle",
    "车": "vehicle",
    "汽车": "vehicle",
    "vehicle": "vehicle",
    "vehicles": "vehicle",
    "船只": "ship",
    "船": "ship",
    "舰船": "ship",
    "ship": "ship",
    "ships": "ship",
    "飞机": "airplane",
    "airplane": "airplane",
    "aircraft": "airplane",
    "建筑物": "building",
    "建筑": "building",
    "building": "building",
    "buildings": "building",
    "储气罐": "storage tank",
    "油罐": "storage tank",
    "储罐": "storage tank",
    "storage tank": "storage tank",
    "tank": "storage tank",
}


class Sam3RuntimeError(RuntimeError):
    pass


def normalize_prompt(prompt_text: str) -> str:
    prompt = str(prompt_text or "").strip()
    if not prompt:
        raise Sam3RuntimeError("请提供 SAM3 文本 Prompt")
    return PROMPT_ALIASES.get(prompt.lower(), PROMPT_ALIASES.get(prompt, prompt))


def resolve_checkpoint(manifest: Dict[str, Any] | None = None) -> str:
    manifest = manifest or {}
    checkpoint = (
        os.getenv("GEOVIEW_SAM3_CHECKPOINT")
        or manifest.get("checkpoint_path")
        or DEFAULT_SAM3_CHECKPOINT
    )
    if not os.path.exists(checkpoint):
        raise Sam3RuntimeError(
            f"SAM3 checkpoint 不存在: {checkpoint}；请确认镜像已内置 sam3.1_multiplex.pt"
        )
    return checkpoint


def _worker_python() -> str:
    return os.getenv("GEOVIEW_SAM3_PYTHON") or DEFAULT_SAM3_PYTHON


def _run_worker(payload: Dict[str, Any], timeout_seconds: int = 7200) -> Dict[str, Any]:
    python_bin = _worker_python()
    if not os.path.exists(python_bin):
        raise Sam3RuntimeError(
            f"SAM3 Python 环境不存在: {python_bin}；请使用 Dockerfile.sam3 构建镜像"
        )
    if not SAM3_WORKER.exists():
        raise Sam3RuntimeError(f"SAM3 worker 不存在: {SAM3_WORKER}")

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False)
        input_path = file.name

    env = os.environ.copy()
    pythonpath_items = [str(BACKEND_ROOT), str(REPO_ROOT)]
    if env.get("PYTHONPATH"):
        pythonpath_items.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_items)
    env.setdefault("TRANSFORMERS_OFFLINE", "1")
    env.setdefault("HF_DATASETS_OFFLINE", "1")
    env.setdefault("HF_HUB_OFFLINE", "1")

    try:
        completed = subprocess.run(
            [python_bin, str(SAM3_WORKER), "--input", input_path],
            cwd=str(BACKEND_ROOT),
            env=env,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    finally:
        try:
            os.remove(input_path)
        except OSError:
            pass

    if completed.returncode != 0:
        stderr = (completed.stderr or completed.stdout or "").strip()
        raise Sam3RuntimeError(f"SAM3 推理失败: {stderr[-4000:]}")
    stdout = (completed.stdout or "").strip()
    if not stdout:
        raise Sam3RuntimeError("SAM3 推理未返回结果")
    try:
        return json.loads(stdout.splitlines()[-1])
    except json.JSONDecodeError as exc:
        raise Sam3RuntimeError(f"SAM3 推理结果解析失败: {stdout[-1000:]}") from exc


def run_image_prompt_jobs(
    jobs: Iterable[Dict[str, str]],
    prompt_text: str,
    checkpoint_path: str,
    confidence_threshold: float = 0.5,
    device: str = "cuda",
) -> List[Dict[str, Any]]:
    prompt = normalize_prompt(prompt_text)
    result = _run_worker(
        {
            "mode": "image",
            "prompt_text": prompt,
            "checkpoint_path": checkpoint_path,
            "confidence_threshold": confidence_threshold,
            "device": device,
            "jobs": list(jobs),
        }
    )
    return result.get("results") or []


def run_video_prompt_tracking(
    *,
    frame_dir: str,
    output_video_path: str,
    preview_path: str,
    trajectory_path: str,
    prompt_text: str,
    checkpoint_path: str,
    model_path: str,
    fps: float = 8.0,
    confidence_threshold: float = 0.5,
) -> Dict[str, Any]:
    prompt = normalize_prompt(prompt_text)
    return _run_worker(
        {
            "mode": "video",
            "prompt_text": prompt,
            "checkpoint_path": checkpoint_path,
            "confidence_threshold": confidence_threshold,
            "frame_dir": frame_dir,
            "output_video_path": output_video_path,
            "preview_path": preview_path,
            "trajectory_path": trajectory_path,
            "model_path": model_path,
            "fps": fps,
        }
    )
