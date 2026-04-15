from flask import Flask

from .flask_uploads import UploadSet, IMAGES
from .flask_uploads import configure_uploads

# 扩展上传类型以支持 TIFF 与常见视频格式
TRACKING_MEDIA = IMAGES + (
    'tif',
    'tiff',
    'mp4',
    'avi',
    'mov',
    'mkv',
    'm4v',
    'webm',
    'mpg',
    'mpeg',
)
photos = UploadSet('photos', TRACKING_MEDIA)


def init_upload(app: Flask):
    configure_uploads(app, photos)
