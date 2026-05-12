# 导入需要用到的库
import os.path as osp

import paddle
import numpy as np
from skimage.io import imsave
from paddlers.models.ppdet.utils.colormap import colormap

import paddlers as pdrs
from paddlers.transforms import decode_image
from paddlers.tasks.utils.visualize import visualize_detection

from applications.common.model_assets import (infer_model_backend,
                                              load_hf_config,
                                              load_model_manifest,
                                              resolve_model_dir)
from applications.common.path_global import md5_name, generate_url
from applications.interface.utils import paddle_use_gpu


def execute(model_path, data_path, out_dir, names, threshold=0.2):
    """
    :param model_path: 模型路径
    :param data_path: 数据文件夹路径，里面只包含图片
    :param out_dir: 结果保存路径
    :param names: 待处理文件名列表
    :param threshold: 阈值
    """

    model_backend = infer_model_backend(model_path)

    # 检查是否为 HuggingFace 模型
    if model_backend == "huggingface":
        from applications.interface.hf_inference_caller import call_hf_object_detection
        if model_path.startswith("hf:"):
            model_id = model_path[3:]
        else:
            hf_config = load_hf_config(model_path) or {}
            manifest = load_model_manifest(model_path) or {}
            model_id = hf_config.get("model_id") or manifest.get("model_id", "")
        if not model_id:
            raise ValueError(f"无法解析 HuggingFace 模型 ID: {model_path}")
        return call_hf_object_detection(
            model_id=model_id,
            data_path=data_path,
            out_dir=out_dir,
            names=names
        )

    # 检查是否为 MMRotate 模型 (e.g., mmrotate:oriented_rcnn_r50_fpn_1x_dota_le90)
    if model_backend == "mmrotate":
        from applications.interface.mmseg_inference_caller import call_mmrotate_inference
        return call_mmrotate_inference(
            model_ref=model_path,
            data_path=data_path,
            out_dir=out_dir,
            names=names
        )

    model_dir = str(resolve_model_dir(model_path))
    image_list = [osp.join(data_path, name) for name in names]
    predictor = pdrs.deploy.Predictor(model_dir=model_dir, use_gpu=paddle_use_gpu())
    pred = predictor.predict(image_list)
    ims = [decode_image(i) for i in image_list]
    temps = list()
    with paddle.no_grad():
        for idx, im in zip(range(len(names)), ims):
            vis = im
            detections = []
            if len(pred[idx]) > 0:
                vis = visualize_detection(
                    np.array(vis),
                    pred[idx],
                    threshold=threshold,
                    save_dir=None)
                for detection in pred[idx]:
                    bbox = detection.get("bbox", [])
                    if len(bbox) >= 4:
                        x, y, w, h = bbox[:4]
                        box = [
                            round(float(x), 2),
                            round(float(y), 2),
                            round(float(x + w), 2),
                            round(float(y + h), 2),
                        ]
                    else:
                        box = [round(float(value), 2) for value in bbox]
                    detections.append({
                        "label": str(detection.get("category", detection.get("category_id", "unknown"))),
                        "score": round(float(detection.get("score", 0.0)), 4),
                        "box": box,
                    })
            name = names[idx]
            new_name = md5_name(name)
            imsave(osp.join(out_dir, new_name), vis)
            temps.append({
                "after_img": generate_url + new_name,
                "detections": detections,
                "image_size": {
                    "width": int(np.array(im).shape[1]),
                    "height": int(np.array(im).shape[0]),
                },
            })
    return temps
