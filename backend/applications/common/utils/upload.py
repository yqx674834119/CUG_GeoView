import os
import os.path as osp
import uuid

from flask import current_app
from sqlalchemy import desc

from applications.common.curd import model_to_dicts
from applications.extensions import db
from applications.extensions.init_upload import photos
from applications.models import Photo
from applications.schemas import PhotoOutSchema


def get_photo(page, limit):
    photo = Photo.query.order_by(desc(Photo.create_time)).paginate(
        page=page, per_page=limit, error_out=False)
    count = Photo.query.count()
    data = model_to_dicts(schema=PhotoOutSchema, data=photo.items)
    return data, count


def upload_one(photo, mime, type_=0):
    """
    上传单个文件
    
    如果是 TIFF 文件，会自动转换为 PNG 格式
    """
    from applications.common.utils.tiff_processor import is_tiff_file, process_uploaded_tiff
    
    filename = photos.save(photo, name=str(uuid.uuid4()) + ".")
    upload_url = current_app.config.get("UPLOADED_PHOTOS_DEST")
    full_path = os.path.join(upload_url, filename)
    
    # 如果是 TIFF 文件，进行预处理转换为 PNG
    if is_tiff_file(filename):
        try:
            print(f"[Upload] 检测到 TIFF 文件: {filename}, 开始转换...")
            png_filename = process_uploaded_tiff(full_path, upload_url)
            # 删除原始 TIFF 文件以节省空间
            os.remove(full_path)
            filename = png_filename
            full_path = os.path.join(upload_url, filename)
            mime = 'image/png'  # 更新 MIME 类型
            print(f"[Upload] TIFF 转换完成: {filename}")
        except Exception as e:
            # 转换失败，删除文件并抛出异常
            if os.path.exists(full_path):
                os.remove(full_path)
            raise ValueError(f"TIFF 文件处理失败: {str(e)}")
    
    file_url = '/_uploads/photos/' + filename
    size = os.path.getsize(full_path)
    photo = Photo(
        name=filename, href=file_url, mime=mime, size=size, type=type_)
    db.session.add(photo)
    db.session.commit()
    return file_url, photo.id


def delete_photo_by_id(_id):
    photo_name = Photo.query.filter_by(id=_id).first().name
    photo = Photo.query.filter_by(id=_id).delete()
    db.session.commit()
    upload_url = current_app.config.get("UPLOADED_PHOTOS_DEST")
    os.remove(upload_url + '/' + photo_name)
    return photo


def img_url_handle(url):
    return osp.basename(url)
    # return url[url.rfind("/") + 1:len(url)]
