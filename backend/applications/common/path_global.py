import hashlib
import os
import random

from applications.common.storage import (external_static_root,
                                         external_upload_root)


def _with_trailing_slash(value):
    return value if value.endswith("/") else value + "/"


STATIC_ROOT = os.getenv("GEOVIEW_STATIC_ROOT", external_static_root())
UPLOADED_PHOTOS_DEST = os.getenv(
    "UPLOADED_PHOTOS_DEST",
    external_upload_root(),
)
FILE_ASSET_API_PREFIX = "/api/file/assets/photos/"
LEGACY_FILE_ASSET_PREFIX = "/_uploads/photos/"

# 上传文件地址
up_dir = _with_trailing_slash(UPLOADED_PHOTOS_DEST)
# 生成的文件地址
generate_dir = _with_trailing_slash(os.path.join(UPLOADED_PHOTOS_DEST, "res"))
# 网络地址
generate_url = FILE_ASSET_API_PREFIX + "res/"
up_url = FILE_ASSET_API_PREFIX


def md5_name(name):
    nname = hashlib.md5(str(random.random()).encode()).hexdigest() + "_" + name
    if len(nname) > 100:
        nname = hashlib.md5(str(random.random()).encode()).hexdigest(
        ) + "." + name.split(".")[1]
    return nname


"""
 1=直方图匹配，
 2=对比度自适应直方图均衡化(CLAHE)，
 3=平滑(中值滤波)，
 4=锐化，
 5=高斯滤波
 6=变化检测渲染，
 7=目标提取渲染，
 8=孔洞填充(用于变化检测结果图处理)
"""
fun_type_1 = 1
fun_type_2 = 2
fun_type_3 = 3
fun_type_4 = 4
fun_type_5 = 5
fun_type_6 = 6
fun_type_7 = 7
fun_type_8 = 8
