from flask import Flask

from .flask_uploads import UploadSet, IMAGES
from .flask_uploads import configure_uploads

# 扩展 IMAGES 以支持 TIFF 格式
IMAGES_WITH_TIFF = IMAGES + ('tif', 'tiff')
photos = UploadSet('photos', IMAGES_WITH_TIFF)


def init_upload(app: Flask):
    configure_uploads(app, photos)
