import os
import os.path as osp

import paddlers.utils.logging as logging
import yaml
from paddlers.transforms import build_transforms

from applications.common.model_assets import resolve_model_dir


def paddle_use_gpu(use_gpu=True):
    try:
        import paddle

        if not bool(use_gpu):
            return False
        if not paddle.device.is_compiled_with_cuda():
            raise RuntimeError("Paddle 当前环境未编译 CUDA，拒绝使用 CPU 推理")
        if paddle.device.cuda.device_count() <= 0:
            raise RuntimeError("Paddle 当前环境未检测到 GPU，拒绝使用 CPU 推理")
        visible_devices = os.environ.get("CUDA_VISIBLE_DEVICES")
        if visible_devices is not None and str(visible_devices).strip() == "":
            raise RuntimeError("CUDA_VISIBLE_DEVICES 为空，拒绝使用 CPU 推理")
        return True
    except Exception:
        raise


def resolve_paddle_device(req_json):
    raw_device = req_json.get("paddle_device", req_json.get("device", "gpu"))
    if isinstance(raw_device, bool):
        return raw_device
    device = str(raw_device or "gpu").strip().lower()
    if device in ("cpu", "false", "0", "off"):
        return False
    if device in ("gpu", "true", "1", "on"):
        return True
    return True


def get_model_info(model_dir):
    model_dir = str(resolve_model_dir(model_dir))
    if not osp.exists(model_dir):
        logging.error("Directory '{}' does not exist!".format(model_dir))
    if not osp.exists(osp.join(model_dir, "model.yml")):
        raise FileNotFoundError(
            "There is no file named model.yml in {}.".format(model_dir))
    with open(osp.join(model_dir, "model.yml")) as f:
        model_info = yaml.load(f.read(), Loader=yaml.Loader)
    return model_info


def load_transformer_from_file(model_dir, exclude=None):
    exclude = exclude or []
    model_info = get_model_info(model_dir)
    if 'Transforms' in model_info:
        transform = []
        for t in model_info['Transforms']:
            if len(t.keys()) > 0 and list(t.keys())[0] not in exclude:
                transform.append(t)
        return build_transforms(transform)
    return None
