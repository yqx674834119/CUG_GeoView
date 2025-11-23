# 导入需要用到的库
import os.path as osp
import time
import os
import traceback
import platform

import paddle
import numpy as np
from skimage.io import imsave
from paddlers.models.ppdet.utils.colormap import colormap

import paddlers as pdrs
from paddlers.transforms import decode_image
from paddlers.tasks.utils.visualize import visualize_detection

from applications.common.path_global import md5_name, generate_url


def execute(model_path, data_path, out_dir, names, threshold=0.2):
    """
    :param model_path: 模型路径
    :param data_path: 数据文件夹路径，里面只包含图片
    :param out_dir: 结果保存路径
    :param names: 待处理文件名列表
    :param threshold: 阈值
    """
    image_list = [osp.join(data_path, name) for name in names]
    print("[OD-DEBUG] 开始执行，模型目录:", model_path, flush=True)
    print("[OD-DEBUG] 数据目录:", data_path, flush=True)
    print("[OD-DEBUG] 输出目录:", out_dir, flush=True)
    print("[OD-DEBUG] 待处理图片数量:", len(image_list), flush=True)
    for i, p in enumerate(image_list[:10]):
        print("[OD-DEBUG] 输入样本", i, p, "存在:" , osp.exists(p))
    try:
        files = sorted([f for f in os.listdir(model_path)])
        print("[OD-DEBUG] 模型目录文件:", files[:20], flush=True)
    except Exception as e:
        print("[OD-DEBUG] 无法列出模型目录:", e, flush=True)
    try:
        pv = getattr(paddle, "__version__", "unknown")
        prsv = getattr(pdrs, "__version__", "unknown")
        print("[OD-DEBUG] 版本 paddle:", pv, " paddlers:", prsv, flush=True)
    except Exception:
        pass
    try:
        print("[OD-DEBUG] 平台:", platform.platform(), flush=True)
        print("[OD-DEBUG] CUDA编译:", paddle.device.is_compiled_with_cuda(), flush=True)
        try:
            print("[OD-DEBUG] GPU数量:", paddle.device.cuda.device_count(), flush=True)
        except Exception as e:
            print("[OD-DEBUG] 获取GPU数量失败:", e, flush=True)
        print("[OD-DEBUG] CUDA_VISIBLE_DEVICES:", os.environ.get("CUDA_VISIBLE_DEVICES"), flush=True)
        print("[OD-DEBUG] FLAGS_selected_gpus:", os.environ.get("FLAGS_selected_gpus"), flush=True)
    except Exception as e:
        print("[OD-DEBUG] 设备探测失败:", e, flush=True)
    t0 = time.time()
    try:
        compiled = False
        gpu_count = 0
        try:
            compiled = paddle.device.is_compiled_with_cuda()
            gpu_count = paddle.device.cuda.device_count() if compiled else 0
        except Exception:
            compiled = False
            gpu_count = 0
        cvd = os.environ.get("CUDA_VISIBLE_DEVICES")
        fsg = os.environ.get("FLAGS_selected_gpus")
        use_gpu = bool(compiled and gpu_count > 0 and (cvd is None or str(cvd).strip() != ""))
        print("[OD-DEBUG] 初始化预测器(use_gpu=", use_gpu, ", compiled=", compiled, ", gpu_count=", gpu_count, ", CUDA_VISIBLE_DEVICES=", cvd, ")", sep="", flush=True)
        predictor = pdrs.deploy.Predictor(model_dir=model_path, use_gpu=use_gpu)
        print("[OD-DEBUG] 预测器初始化完成，用时秒:", round(time.time() - t0, 3), flush=True)
    except Exception:
        print("[OD-DEBUG] 预测器初始化失败:\n", traceback.format_exc(), flush=True)
        raise
    t1 = time.time()
    try:
        print("[OD-DEBUG] 开始预测，图片数量:", len(image_list), flush=True)
        pred = predictor.predict(image_list)
        print("[OD-DEBUG] 预测完成，用时秒:", round(time.time() - t1, 3), flush=True)
    except Exception:
        print("[OD-DEBUG] 预测过程异常:\n", traceback.format_exc(), flush=True)
        raise
    t2 = time.time()
    ims = []
    try:
        ims = [decode_image(i) for i in image_list]
        print("[OD-DEBUG] 解码完成，用时秒:", round(time.time() - t2, 3), flush=True)
        if len(ims) > 0:
            s = ims[0]
            try:
                print("[OD-DEBUG] 首张图像形状:", np.array(s).shape, "dtype:", np.array(s).dtype, flush=True)
            except Exception:
                pass
    except Exception:
        print("[OD-DEBUG] 图像解码异常:\n", traceback.format_exc(), flush=True)
        raise
    temps = list()
    t3 = time.time()
    try:
        with paddle.no_grad():
            for idx, im in zip(range(len(names)), ims):
                vis = im
                if len(pred[idx]) > 0:
                    vis = visualize_detection(
                        np.array(vis),
                        pred[idx],
                        threshold=threshold,
                        save_dir=None)
                name = names[idx]
                new_name = md5_name(name)
                imsave(osp.join(out_dir, new_name), vis)
                temps.append(generate_url + new_name)
        print("[OD-DEBUG] 可视化与保存完成，用时秒:", round(time.time() - t3, 3), flush=True)
    except Exception:
        print("[OD-DEBUG] 可视化或保存异常:\n", traceback.format_exc(), flush=True)
        raise
    print("[OD-DEBUG] 全流程完成，总时长秒:", round(time.time() - t0, 3), flush=True)
    return temps
