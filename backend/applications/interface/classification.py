import os.path as osp

import paddlers as pdrs
from paddlers.transforms import decode_image

from applications.common.model_assets import resolve_model_dir
from applications.interface.utils import paddle_use_gpu


def execute(model_path, data_path, names):
    image_list = [osp.join(data_path, name) for name in names]
    ims = [decode_image(i) for i in image_list]
    predictor = pdrs.deploy.Predictor(str(resolve_model_dir(model_path)),
                                      use_gpu=paddle_use_gpu())
    temps = predictor.predict(ims)
    return temps
