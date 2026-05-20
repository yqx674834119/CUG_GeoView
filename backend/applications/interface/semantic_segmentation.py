import os
import os.path as osp
from collections import Counter

import cv2
import numpy as np
import paddlers as pdrs
from paddlers.tasks.utils.visualize import get_color_map_list
from skimage.io import imsave

from applications.common.model_assets import infer_model_backend, resolve_model_dir
from applications.common.path_global import md5_name, generate_url
from applications.interface.utils import paddle_use_gpu


def is_mmseg_model(model_path: str) -> bool:
    """
    判断是否是 MMSegmentation 模型
    
    MMSegmentation 模型的标识:
    - model_path 以 "mmseg:" 前缀开头 (如 "mmseg:cc-ln/CUGRS")
    """
    return infer_model_backend(model_path) == "mmsegmentation"


def get_mmseg_model_id(model_path: str) -> str:
    """
    从 model_path 中提取 MMSegmentation 模型 ID
    
    "mmseg:cc-ln/CUGRS" -> "cc-ln/CUGRS"
    """
    if model_path.startswith("mmseg:"):
        return model_path[6:]  # 去掉 "mmseg:" 前缀
    return model_path


def execute_paddle(model_path, data_path, out_dir, test_names, use_gpu=True):
    """使用 PaddleRS 执行语义分割推理"""
    image_list = [osp.join(data_path, name) for name in test_names]
    predictor = pdrs.deploy.Predictor(str(resolve_model_dir(model_path)),
                                      use_gpu=paddle_use_gpu(use_gpu))
    pred = predictor.predict(image_list)
    ims = [i['label_map'] for i in pred]
    temps = list()
    lut = np.array(get_color_map_list(256))
    for idx, im in zip(range(len(image_list)), ims):
        im = lut[im]
        new_name = md5_name(test_names[idx])
        mask_name = f"mask_{os.path.splitext(new_name)[0]}.png"
        imsave(osp.join(out_dir, new_name), np.uint8(im))
        imsave(osp.join(out_dir, mask_name), np.uint8(ims[idx]))
        temps.append({
            "after_img": generate_url + new_name,
            "mask_path": generate_url + mask_name,
            "class_names": ["cloud", "shadow", "snow", "water", "land"],
            "palette": [
                [0, 0, 0],
                [128, 0, 0],
                [0, 128, 0],
                [128, 128, 0],
                [0, 0, 128],
            ],
        })
    return temps


def execute_mmseg(model_path, data_path, out_dir, test_names):
    """使用 MMSegmentation 执行语义分割推理（通过 subprocess 调用）"""
    from applications.interface import mmseg_inference_caller
    
    return mmseg_inference_caller.execute(
        model_ref=model_path,
        data_path=data_path,
        out_dir=out_dir,
        names=test_names
    )


def execute(model_path, data_path, out_dir, test_names, use_gpu=True):
    """
    统一的执行接口 - 自动路由到 Paddle 或 MMSegmentation
    
    :param model_path: 模型路径
        - Paddle 模型: 本地目录路径 (如 "model/semantic_segmentation/...")
        - MMSegmentation 模型: "mmseg:" 前缀 + 模型ID (如 "mmseg:cc-ln/CUGRS")
    :param data_path: 数据文件夹路径
    :param out_dir: 结果保存路径
    :param test_names: 待处理文件名列表
    :return: 生成的图片 URL 列表
    """
    if is_mmseg_model(model_path):
        model_id = get_mmseg_model_id(model_path)
        print(f"[SemanticSegmentation] 使用 MMSegmentation 模型: {model_path}", flush=True)
        return execute_mmseg(model_path, data_path, out_dir, test_names)
    else:
        print(f"[SemanticSegmentation] 使用 Paddle 模型: {model_path}", flush=True)
        return execute_paddle(model_path, data_path, out_dir, test_names, use_gpu=use_gpu)
