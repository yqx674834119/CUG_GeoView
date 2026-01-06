import os
import json

from flask import Blueprint

from applications.common.utils.http import success_api, fail_api
from applications.interface.utils import get_model_info

model_api = Blueprint('model_api', __name__, url_prefix='/api/model')


# HuggingFace 内置模型列表
HUGGINGFACE_MODELS = {
    "image_restoration": [
        {
            "model_path": "hf:caidas/swin2SR-classical-sr-x2-64",
            "model_type": "restorer",
            "model_name": "Swin2SR (2x超分)",
            "backend": "huggingface",
            "description": "HuggingFace Swin2SR 2倍超分辨率模型"
        },
        {
            "model_path": "hf:caidas/swin2SR-classical-sr-x4-64",
            "model_type": "restorer",
            "model_name": "Swin2SR (4x超分)",
            "backend": "huggingface",
            "description": "HuggingFace Swin2SR 4倍超分辨率模型"
        }
    ],
    "object_detection": [
        {
            "model_path": "hf:facebook/detr-resnet-50",
            "model_type": "detector",
            "model_name": "Facebook DETR-ResNet-50",
            "backend": "huggingface",
            "description": "DEtection TRansformer (DETR) model trained on COCO 2017. ResNet-50 backbone."
        }
    ],
    "semantic_segmentation": [
        {
            "model_path": "mmseg:cc-ln/CUGRS",
            "model_type": "segmenter",
            "model_name": "CUGRS (DinoV3+Swin 6类地物)",
            "backend": "mmsegmentation",
            "description": "MMSeg DinoV3+SwinTransformer，6类地物分类（草地、林地、建筑、道路、裸地、水体）"
        }
    ]
}


def get_paddle_models(model_type, expected_type):
    """获取 Paddle 模型列表"""
    model_list = []
    model_dir = "model/{}".format(model_type)
    
    if os.path.exists(model_dir):
        for dirname in os.listdir(model_dir):
            dirpath = os.path.join(model_dir, dirname)
            if not os.path.isdir(dirpath):
                continue
            try:
                model_info = get_model_info(dirpath)
                if model_info["_Attributes"]["model_type"] == expected_type:
                    model_list.append({
                        "model_path": dirpath,
                        "model_type": model_info["_Attributes"]["model_type"],
                        "model_name": model_info["Model"],
                        "backend": "paddle"
                    })
            except Exception as e:
                print(f"[Model] 跳过无效模型目录 {dirpath}: {e}")
                continue
    
    return model_list


def get_huggingface_models(model_type):
    """获取 HuggingFace 模型列表"""
    return HUGGINGFACE_MODELS.get(model_type, [])


@model_api.get('/list/<string:model_type>')
def get_model_list(model_type):
    types_list = {
        "change_detection": "change_detector",
        "classification": "classifier",
        "image_restoration": "restorer",
        "object_detection": "detector",
        "semantic_segmentation": "segmenter"
    }
    if model_type not in types_list:
        return fail_api("模型类型不正确")
    
    expected_type = types_list[model_type]
    model_list = []
    
    # 1. 获取 Paddle 模型
    paddle_models = get_paddle_models(model_type, expected_type)
    model_list.extend(paddle_models)
    
    # 2. 获取 HuggingFace 模型
    hf_models = get_huggingface_models(model_type)
    model_list.extend(hf_models)
    
    return success_api(data=model_list)


@model_api.get('/huggingface/list')
def get_huggingface_model_list():
    """获取所有可用的 HuggingFace 模型"""
    return success_api(data=HUGGINGFACE_MODELS)
