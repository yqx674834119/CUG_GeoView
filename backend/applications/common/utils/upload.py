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


def upload_one(photo, mime, type_=0, enable_slicing=False):
    """
    上传单个文件
    
    如果是 TIFF 文件且开启了切片，会对大图进行切片
    返回: List[(url, id, display_name)]
    """
    from applications.common.utils.tiff_processor import is_tiff_file, process_uploaded_tiff
    
    filename = photos.save(photo, name=str(uuid.uuid4()) + ".")
    upload_url = current_app.config.get("UPLOADED_PHOTOS_DEST")
    full_path = os.path.join(upload_url, filename)
    
    # 原始文件名 (用于前端配对展示)
    original_filename = getattr(photo, 'filename', filename)
    
    # 如果是 TIFF 文件，进行预处理 (可能切片)
    processed_files = []
    
    # 只有当开启切片且是TIFF时才尝试处理
    if enable_slicing and is_tiff_file(filename):
        try:
            print(f"[Upload] 检测到 TIFF 文件: {filename}, 开启切片模式...")
            
            # process_uploaded_tiff 返回列表: [{'path': ..., 'filename': ...}]
            results = process_uploaded_tiff(full_path, upload_url, original_filename=original_filename)
            
            # 删除原始 TIFF 文件
            if os.path.exists(full_path):
                os.remove(full_path)
            
            for res in results:
                processed_files.append({
                    'filename': res['filename'],
                    'mime': 'image/png',
                    'path': res['path'],
                    'display_name': res['filename'] # 切片后的文件名作为展示名
                })
                
            print(f"[Upload] TIFF 处理完成, 生成 {len(processed_files)} 个文件")
            
        except Exception as e:
            # 失败处理
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                except:
                    pass
            raise ValueError(f"TIFF 文件处理失败: {str(e)}")
    else:
        # 非 TIFF 或未开启切片，直接使用原文件
        processed_files.append({
            'filename': filename,
            'mime': mime,
            'path': full_path,
            'display_name': original_filename # 保持原始文件名用于展示和配对
        })

    # 为每个文件创建数据库记录
    return_data = [] # List of (url, id, display_name)
    
    for p_file in processed_files:
        p_filename = p_file['filename']
        p_mime = p_file['mime']
        p_path = p_file['path']
        p_display = p_file['display_name']
        
        file_url = '/_uploads/photos/' + p_filename
        
        # 获取大小
        if os.path.exists(p_path):
            size = os.path.getsize(p_path)
        else:
            size = 0
            
        photo_record = Photo(
            name=p_filename, href=file_url, mime=p_mime, size=size, type=type_)
        db.session.add(photo_record)
        db.session.flush() # 获取 ID
        
        return_data.append((file_url, photo_record.id, p_display))
        
    db.session.commit()
    
    return return_data


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
