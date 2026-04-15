from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPO_ROOT / "backend"
MODEL_ROOT = BACKEND_ROOT / "model"
MODEL_MANIFEST_NAME = "model_manifest.json"
HF_CONFIG_NAME = "hf_config.json"


LEGACY_MODEL_PATHS = {
    "hf:caidas/swin2SR-classical-sr-x2-64":
    "backend/model/image_restoration/hf_swin2sr_x2",
    "hf:caidas/swin2SR-classical-sr-x4-64":
    "backend/model/image_restoration/hf_swin2sr_x4",
    "hf:facebook/detr-resnet-50":
    "backend/model/object_detection/hf_detr_resnet50",
    "hf:microsoft/conditional-detr-resnet-50":
    "backend/model/object_detection/hf_conditional_detr_resnet50",
    "hf:StephanST/WALDO30":
    "backend/model/object_detection/hf_waldo30",
    "mmrotate:oriented_rcnn_r50_fpn_1x_dota_le90":
    "backend/model/object_detection/mmrotate_oriented_rcnn_r50_fpn_1x_dota_le90",
    "mmseg:cc-ln/CUGRS":
    "backend/model/semantic_segmentation/mmseg_cugrs",
    "builtin:registration:auto": "backend/model/registration/auto",
    "builtin:registration:opencv": "backend/model/registration/opencv",
    "hf:kornia/loftr": "backend/model/registration/loftr_outdoor",
    "builtin:tracking:auto": "backend/model/tracking/auto",
    "builtin:tracking:botsort": "backend/model/tracking/botsort",
    "builtin:tracking:botsort_engineering": "backend/model/tracking/botsort",
    "builtin:tracking:botsort_official": "backend/model/tracking/botsort_official",
    "builtin:tracking:csrt": "backend/model/tracking/csrt",
    "builtin:tracking:kcf": "backend/model/tracking/kcf",
}


def legacy_model_path(model_path: str) -> Optional[str]:
    return LEGACY_MODEL_PATHS.get(model_path)


def resolve_repo_path(raw_path: str | Path) -> Path:
    if isinstance(raw_path, Path):
        path = raw_path
    else:
        path = Path(str(raw_path))

    if path.is_absolute():
        return path

    text = path.as_posix()
    candidates = []
    if text.startswith("backend/"):
        candidates.append(REPO_ROOT / path)
    elif text.startswith("model/") or text.startswith("static/"):
        candidates.append(BACKEND_ROOT / path)
    else:
        candidates.extend([
            BACKEND_ROOT / path,
            REPO_ROOT / path,
            Path.cwd() / path,
        ])

    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()

    return candidates[0].resolve() if candidates else path.resolve()


def resolve_model_dir(model_path: str | Path) -> Path:
    if isinstance(model_path, Path):
        return resolve_repo_path(model_path)
    return resolve_repo_path(legacy_model_path(model_path) or model_path)


def to_public_model_path(model_path: str | Path) -> str:
    resolved = resolve_model_dir(model_path)
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(model_path)


def model_manifest_path(model_path: str | Path) -> Path:
    return resolve_model_dir(model_path) / MODEL_MANIFEST_NAME


def hf_config_path(model_path: str | Path) -> Path:
    return resolve_model_dir(model_path) / HF_CONFIG_NAME


def load_model_manifest(model_path: str | Path) -> Optional[Dict[str, Any]]:
    manifest_path = model_manifest_path(model_path)
    if not manifest_path.exists():
        return None
    with open(manifest_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    data.setdefault("model_path", to_public_model_path(manifest_path.parent))
    return data


def load_hf_config(model_path: str | Path) -> Optional[Dict[str, Any]]:
    config_path = hf_config_path(model_path)
    if not config_path.exists():
        return None
    with open(config_path, "r", encoding="utf-8") as file:
        return json.load(file)


def load_paddle_model_info(model_path: str | Path) -> Dict[str, Any]:
    model_dir = resolve_model_dir(model_path)
    model_info_path = model_dir / "model.yml"
    if not model_info_path.exists():
        raise FileNotFoundError(
            f"There is no file named model.yml in {model_dir}.")
    with open(model_info_path, "r", encoding="utf-8") as file:
        return yaml.load(file.read(), Loader=yaml.Loader)


def infer_model_backend(model_path: str | Path) -> Optional[str]:
    if isinstance(model_path, str) and model_path.startswith(("hf:", "mmseg:", "mmrotate:", "builtin:")):
        if model_path.startswith("hf:"):
            return "huggingface"
        if model_path.startswith("mmseg:"):
            return "mmsegmentation"
        if model_path.startswith("mmrotate:"):
            return "mmrotate"
        if model_path.startswith("builtin:registration:"):
            return "registration"
        if model_path.startswith("builtin:tracking:"):
            return "tracking"

    manifest = load_model_manifest(model_path)
    if manifest is not None:
        return manifest.get("backend")

    if hf_config_path(model_path).exists():
        return "huggingface"

    model_info_path = resolve_model_dir(model_path) / "model.yml"
    if model_info_path.exists():
        return "paddle"
    return None
