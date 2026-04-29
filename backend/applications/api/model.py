from __future__ import annotations

import os
from pathlib import Path

from flask import Blueprint

from applications.common.model_assets import (MODEL_ROOT, load_model_manifest,
                                              resolve_repo_path,
                                              to_public_model_path)
from applications.common.utils.http import fail_api, success_api
from applications.interface.utils import get_model_info


model_api = Blueprint("model_api", __name__, url_prefix="/api/model")


MODEL_TYPES = {
    "change_detection": "change_detector",
    "classification": "classifier",
    "image_restoration": "restorer",
    "object_detection": "detector",
    "semantic_segmentation": "segmenter",
    "registration": "register",
    "tracking": "tracker",
}


PADDLE_MODEL_METADATA = {
    "BIT": {
        "name": "建筑物变化专用模型",
        "desc": "基于Transformer架构。特点：擅长捕捉建筑物等规则物体的变化，抗干扰能力强。",
    },
    "CDNet": {
        "name": "通用地表变化检测",
        "desc": "经典深度网络。特点：结构简单，适用于一般性的地表变化检测。",
    },
    "FC-EF": {
        "name": "快速变化检测",
        "desc": "特点：计算量小，速度快，适用于大范围快速普查。",
    },
    "FC-Siam-conc": {
        "name": "敏感变化检测",
        "desc": "特点：保留了更多通道特征，对颜色变化敏感。",
    },
    "FC-Siam-diff": {
        "name": "形状变化检测",
        "desc": "特点：直接比较特征差异，对只有形状改变的目标更敏感。",
    },
    "CondenseNetV2": {
        "name": "移动端场景分类",
        "desc": "特点：模型轻量，推理速度极快，适合资源受限环境。",
    },
    "ResNet50": {
        "name": "高精度场景分类",
        "desc": "特点：深层网络，特征提取能力强，分类准确率高。",
    },
    "FCOS": {
        "name": "密集小目标检测",
        "desc": "特点：无锚框设计，对重叠目标和密集小目标检测效果优秀。",
    },
    "YOLOv3": {
        "name": "实时通用目标检测",
        "desc": "特点：检测速度极快，适用于对实时性要求高的场景。",
    },
    "PPYOLO": {
        "name": "通用遥感目标识别",
        "desc": "特点：PaddleRS优化的YOLO系列模型，针对遥感图像优化，速度与精度平衡好。",
    },
    "DeepLabV3P": {
        "name": "高精度地物分类",
        "desc": "支持类别：云、阴影、雪、水体、陆地。特点：能有效处理多尺度物体，边界分割精细。",
    },
    "UNet": {
        "name": "通用地物分类",
        "desc": "特点：结构对称，对边缘信息的保留较好，适用于医学或简单遥感图像。",
    },
    "DRN": {
        "name": "图像清晰化重建",
        "desc": "用途：将低分辨率模糊图像重建为高分辨率清晰图像。",
    },
    "ESRGAN": {
        "name": "照片级纹理增强",
        "desc": "用途：生成逼真的纹理细节，显著提升图像的主观视觉质量。",
    },
    "LesRCNN": {
        "name": "智能去噪修复",
        "desc": "用途：去除图像中的噪点和云雾干扰，还原真实地表细节。",
    },
}


def official_botsort_available(manifest: dict) -> bool:
    repo_dir = resolve_repo_path(
        manifest.get("official_repo_dir")
        or "backend/runtime/BoT-SORT"
    )
    return Path(repo_dir).is_dir()


def manifest_entry_enabled(manifest: dict) -> bool:
    if manifest.get("disabled") is True:
        return False
    if manifest.get("backend") == "tracking" and manifest.get("runtime") == "botsort_official":
        return official_botsort_available(manifest)
    return True


def iter_model_dirs(model_type: str):
    model_dir = MODEL_ROOT / model_type
    if not model_dir.exists():
        return []
    return sorted(path for path in model_dir.iterdir() if path.is_dir())


def build_manifest_entry(model_dir: Path, expected_type: str):
    manifest = load_model_manifest(model_dir)
    if manifest is None or manifest.get("model_type") != expected_type:
        return None
    if not manifest_entry_enabled(manifest):
        return None
    return {
        "model_path": to_public_model_path(model_dir),
        "model_type": manifest["model_type"],
        "model_name": manifest["model_name"],
        "backend": manifest["backend"],
        "description": manifest.get("description", "暂无详细描述"),
    }


def build_paddle_entry(model_dir: Path, expected_type: str):
    try:
        model_info = get_model_info(str(model_dir))
    except Exception:
        return None

    if model_info["_Attributes"]["model_type"] != expected_type:
        return None

    raw_model_name = model_info.get("Model", model_dir.name)
    metadata = PADDLE_MODEL_METADATA.get(raw_model_name) or PADDLE_MODEL_METADATA.get(
        model_dir.name)
    friendly_name = metadata["name"] if metadata else raw_model_name
    description = metadata["desc"] if metadata else "暂无详细描述"
    return {
        "model_path": to_public_model_path(model_dir),
        "model_type": model_info["_Attributes"]["model_type"],
        "model_name": friendly_name,
        "backend": "paddle",
        "description": description,
    }


def get_directory_models(model_type: str, expected_type: str):
    model_list = []
    for model_dir in iter_model_dirs(model_type):
        entry = build_manifest_entry(model_dir, expected_type)
        if entry is None:
            entry = build_paddle_entry(model_dir, expected_type)
        if entry is not None:
            model_list.append(entry)
    return model_list


@model_api.get("/list/<string:model_type>")
def get_model_list(model_type):
    if model_type not in MODEL_TYPES:
        return fail_api("模型类型不正确")

    expected_type = MODEL_TYPES[model_type]
    model_list = get_directory_models(model_type, expected_type)
    return success_api(data=model_list)


@model_api.get("/huggingface/list")
def get_huggingface_model_list():
    grouped = {}
    for model_type, expected_type in MODEL_TYPES.items():
        grouped[model_type] = [
            item for item in get_directory_models(model_type, expected_type)
            if item.get("backend") == "huggingface"
        ]
    return success_api(data=grouped)
