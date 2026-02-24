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
            "model_name": "两倍细节增强",
            "backend": "huggingface",
            "description": "用途：2倍超分辨率重建。特点：基于Swin Transformer，能较好地恢复图像高频细节，适合轻微模糊图像。"
        },
        {
            "model_path": "hf:caidas/swin2SR-classical-sr-x4-64",
            "model_type": "restorer",
            "model_name": "四倍高清重建",
            "backend": "huggingface",
            "description": "用途：4倍超分辨率重建。特点：即使在放大倍数很高的情况下，仍保持较好的结构一致性，适合低分辨率图像。"
        }
    ],
    "object_detection": [
        {
            "model_path": "hf:facebook/detr-resnet-50",
            "model_type": "detector",
            "model_name": "全局上下文目标检测",
            "backend": "huggingface",
            "description": "用途：通用目标检测。特点：端到端Transformer架构，全局上下文理解能力强，适合检测大场景下的物体。"
        },
        {
            "model_path": "hf:microsoft/conditional-detr-resnet-50",
            "model_type": "detector",
            "model_name": "加速训练目标检测",
            "backend": "huggingface",
            "description": "用途：通用目标检测。特点：训练收敛速度比传统DETR快6.7倍，采用条件交叉注意力机制，定位更精准。"
        },
        {
            "model_path": "hf:StephanST/WALDO30",
            "model_type": "detector",
            "model_name": "航拍多目标识别",
            "backend": "huggingface",
            "description": "用途：航拍图像目标检测。支持类别：车辆、人员、建筑、船只、自行车、集装箱、卡车、油罐、挖掘机、太阳能板、公交等12类民用目标。"
        },
        {
            "model_path": "mmrotate:oriented_rcnn_r50_fpn_1x_dota_le90",
            "model_type": "detector",
            "model_name": "定向目标检测 (Oriented RCNN)",
            "backend": "mmrotate",
            "description": "用途：针对航拍图像中的旋转目标进行检测。特点：Oriented R-CNN 算法，DOTA 数据集训练，能够准确检测任意方向的密集排列物体。"
        }
    ],
    "semantic_segmentation": [
        {
            "model_path": "mmseg:cc-ln/CUGRS",
            "model_type": "segmenter",
            "model_name": "多要素地物分类",
            "backend": "mmsegmentation",
            "description": "用途：地物分类。支持类别：草地、林地、建筑、道路、裸地、水体。特点：结合DinoV3自监督特征和SwinTransformer，适合遥感复杂场景，泛化性强。"
        }
    ],
    "registration": [
        {
            "model_path": "hf:kornia/loftr",
            "model_type": "register",
            "model_name": "LoFTR 深度特征配准",
            "backend": "kornia",
            "description": "用途：多模态/大视角差异图像自动配准。特点：基于Transformer的局部特征匹配，无需检测关键点，对弱纹理和重复纹理鲁棒性强。"
        }
    ],
    "tracking": [
        {
            "model_path": "hf:opencv/csrt",
            "model_type": "tracker",
            "model_name": "CSRT 目标跟踪",
            "backend": "opencv",
            "description": "用途：单目标持续跟踪。特点：判别相关滤波器(DCF)与通道和空间可靠性(CSR)结合，适应目标形变和遮挡，精度较高。"
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
                    # 获取原始模型名称
                    raw_model_name = model_info.get("Model", dirname)
                    
                    # 定义模型元数据映射 (Friendly Name & Description)
                    PADDLE_MODEL_METADATA = {
                        # Change Detection
                        "BIT": {"name": "建筑物变化专用模型", "desc": "基于Transformer架构。特点：擅长捕捉建筑物等规则物体的变化，抗干扰能力强。"},
                        "CDNet": {"name": "通用地表变化检测", "desc": "经典深度网络。特点：结构简单，适用于一般性的地表变化检测。"},
                        "FC-EF": {"name": "快速变化检测", "desc": "特点：计算量小，速度快，适用于大范围快速普查。"},
                        "FC-Siam-conc": {"name": "敏感变化检测", "desc": "特点：保留了更多通道特征，对颜色变化敏感。"},
                        "FC-Siam-diff": {"name": "形状变化检测", "desc": "特点：直接比较特征差异，对只有形状改变的目标更敏感。"},
                        
                        # Classification
                        "CondenseNetV2": {"name": "移动端场景分类", "desc": "特点：模型轻量，推理速度极快，适合资源受限环境。"},
                        "ResNet50": {"name": "高精度场景分类", "desc": "特点：深层网络，特征提取能力强，分类准确率高。"},
                        
                        # Object Detection
                        "FCOS": {"name": "密集小目标检测", "desc": "特点：无锚框设计，对重叠目标和密集小目标检测效果优秀。"},
                        "YOLOv3": {"name": "实时通用目标检测", "desc": "特点：检测速度极快，适用于对实时性要求高的场景。"},
                        "PPYOLO": {"name": "通用遥感目标识别", "desc": "特点：PaddleRS优化的YOLO系列模型，针对遥感图像优化，速度与精度平衡好。"},
                        
                        # Segmentation
                        "DeepLabV3P": {"name": "高精度地物分类", "desc": "支持类别：云、阴影、雪、水体、陆地。特点：能有效处理多尺度物体，边界分割精细。"},
                        "UNet": {"name": "通用地物分类", "desc": "特点：结构对称，对边缘信息的保留较好，适用于医学或简单遥感图像。"},
                        
                        # Restoration
                        "DRN": {"name": "图像清晰化重建", "desc": "用途：将低分辨率模糊图像重建为高分辨率清晰图像。"},
                        "ESRGAN": {"name": "照片级纹理增强", "desc": "用途：生成逼真的纹理细节，显著提升图像的主观视觉质量。"},
                        "LesRCNN": {"name": "智能去噪修复", "desc": "用途：去除图像中的噪点和云雾干扰，还原真实地表细节。"}
                    }
                    
                    # 查找匹配的元数据 (优先匹配 Model 字段，其次匹配目录名)
                    meta = PADDLE_MODEL_METADATA.get(raw_model_name) or PADDLE_MODEL_METADATA.get(dirname)
                    
                    if meta:
                        friendly_name = meta["name"]
                        description = meta["desc"]
                    else:
                        friendly_name = raw_model_name
                        description = "暂无详细描述"

                    model_list.append({
                        "model_path": dirpath,
                        "model_type": model_info["_Attributes"]["model_type"],
                        "model_name": friendly_name,
                        "description": description,
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
        "semantic_segmentation": "segmenter",
        "registration": "register",
        "tracking": "tracker"
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
