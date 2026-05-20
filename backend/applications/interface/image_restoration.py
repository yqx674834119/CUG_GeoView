import os
import os.path as osp

from skimage.io import imsave

from applications.common.model_assets import (infer_model_backend,
                                              load_hf_config,
                                              load_model_manifest,
                                              resolve_model_dir)
from applications.common.path_global import generate_url
from applications.interface.utils import paddle_use_gpu


def is_huggingface_model(model_path):
    """
    判断是否是 HuggingFace 模型
    
    HuggingFace 模型的标识:
    - model_path 以 "hf:" 前缀开头 (如 "hf:caidas/swin2SR-classical-sr-x2-64")
    - 或者 model_path 目录下存在 hf_config.json 文件
    """
    return infer_model_backend(model_path) == "huggingface"


def get_huggingface_model_id(model_path):
    """
    从 model_path 中提取 HuggingFace 模型 ID
    
    支持格式:
    - "hf:caidas/swin2SR-classical-sr-x2-64" -> "caidas/swin2SR-classical-sr-x2-64"
    - 本地目录包含 hf_config.json -> 从配置中读取
    """
    if model_path.startswith("hf:"):
        return model_path[3:]  # 去掉 "hf:" 前缀

    config = load_hf_config(model_path)
    if config:
        return config.get("model_id", "")

    manifest = load_model_manifest(model_path)
    if manifest:
        return manifest.get("model_id", "")

    return ""


def execute_paddle(model_path, data_path, out_dir, names, use_gpu=True):
    """使用 PaddleRS 执行推理"""
    import paddlers as pdrs
    
    temps = list()
    image_list = [osp.join(data_path, name) for name in names]
    predictor = pdrs.deploy.Predictor(model_dir=str(resolve_model_dir(model_path)),
                                      use_gpu=paddle_use_gpu(use_gpu))
    pred = predictor.predict(image_list)
    imgs = [im['res_map'] for im in pred]
    for name, im in zip(names, imgs):
        imsave(osp.join(out_dir, name), im)
        height, width = im.shape[:2]
        temps.append({
            "after_img": generate_url + name,
            "image_size": {
                "width": int(width),
                "height": int(height),
            },
        })
    return temps


def execute_huggingface(model_id, data_path, out_dir, names):
    """使用 HuggingFace 执行推理（通过 subprocess 调用）"""
    from applications.interface import hf_inference_caller
    
    return hf_inference_caller.execute(
        model_id=model_id,
        data_path=data_path,
        out_dir=out_dir,
        names=names
    )


def execute(model_path, data_path, out_dir, names, use_gpu=True):
    """
    统一的执行接口 - 自动路由到 Paddle 或 HuggingFace
    
    :param model_path: 模型路径
        - Paddle 模型: 本地目录路径 (如 "model/image_restoration/DRNet")
        - HuggingFace 模型: "hf:" 前缀 + 模型ID (如 "hf:caidas/swin2SR-classical-sr-x2-64")
    :param data_path: 数据文件夹路径，里面只包含图片
    :param out_dir: 结果保存路径
    :param names: 待处理文件名列表
    :return: 生成的图片 URL 列表
    """
    if is_huggingface_model(model_path):
        model_id = get_huggingface_model_id(model_path)
        if not model_id:
            raise ValueError(f"无法解析 HuggingFace 模型 ID: {model_path}")
        print(f"[ImageRestoration] 使用 HuggingFace 模型: {model_id}", flush=True)
        return execute_huggingface(model_id, data_path, out_dir, names)
    else:
        print(f"[ImageRestoration] 使用 Paddle 模型: {model_path}", flush=True)
        return execute_paddle(model_path, data_path, out_dir, names, use_gpu=use_gpu)
