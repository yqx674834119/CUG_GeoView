from flask import Blueprint, request, jsonify

from applications.common.utils import upload as upload_curd, type_utils
from applications.common.utils.http import fail_api
from applications.common.utils.tiff_processor import is_tiff_file, MAX_TIFF_SIZE_MB

file_api = Blueprint('file_api', __name__, url_prefix='/api/file')


#   上传接口
@file_api.post('/upload')
def upload_api():
    if 'files' in request.files:
        type_ = request.form['type']
        to_type = type_utils.str_to_type(type_)
        photos = request.files.getlist("files")
        
        # 预检查文件大小 (特别是 TIFF 文件)
        for photo in photos:
            if is_tiff_file(photo.filename):
                # 获取文件大小
                photo.seek(0, 2)  # 移动到文件末尾
                size_bytes = photo.tell()
                photo.seek(0)  # 重置到开头
                
                size_mb = size_bytes / (1024 * 1024)
                if size_mb > MAX_TIFF_SIZE_MB:
                    return fail_api(f"TIFF 文件 '{photo.filename}' 大小 ({size_mb:.1f}MB) 超过限制 ({MAX_TIFF_SIZE_MB}MB)")
        
        data = list()
        for photo in photos:
            mime = photo.content_type
            try:
                file_url, photo_id = upload_curd.upload_one(
                    photo=photo, mime=mime, type_=to_type)
                data.append({
                    "src": file_url,
                    "filename": photo.filename,
                    "photo_id": photo_id
                })
            except ValueError as e:
                # TIFF 处理失败
                return fail_api(str(e))
            except Exception as e:
                return fail_api(f"文件上传失败: {str(e)}")
        
        res = {"msg": "上传成功", "code": 0, "success": True, "data": data}
        return jsonify(res)
    return fail_api("请选择文件")

