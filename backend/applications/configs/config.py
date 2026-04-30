import logging
import os
from urllib.parse import quote_plus

from applications.common.storage import external_static_root, external_upload_root


class BaseConfig:
    SYSTEM_NAME = os.getenv('SYSTEM_NAME', 'Admin')
    # 主题面板的链接列表配置
    SYSTEM_PANEL_LINKS = []

    GEOVIEW_STATIC_ROOT = os.getenv(
        'GEOVIEW_STATIC_ROOT',
        external_static_root(),
    )
    UPLOADED_PHOTOS_DEST = os.getenv(
        'UPLOADED_PHOTOS_DEST',
        external_upload_root(),
    )
    UPLOADED_FILES_ALLOW = ['gif', 'jpg', 'png']
    PHOTO_ASSET_SERVE_MODE = os.getenv('GEOVIEW_PHOTO_ASSET_SERVE_MODE',
                                       'buffered')
    PHOTO_ASSET_CHUNK_SIZE = int(
        os.getenv('GEOVIEW_PHOTO_ASSET_CHUNK_SIZE') or 1048576)

    # JSON配置
    JSON_AS_ASCII = False

    SECRET_KEY = os.getenv('SECRET_KEY', 'dev key')

    # redis配置
    REDIS_HOST = os.getenv('REDIS_HOST') or "127.0.0.1"
    REDIS_PORT = int(os.getenv('REDIS_PORT') or 6379)

    # mysql 配置
    MYSQL_USERNAME = os.getenv('MYSQL_USERNAME') or "root"
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD') or "123456"
    MYSQL_HOST = os.getenv('MYSQL_HOST') or "127.0.0.1"
    MYSQL_PORT = int(os.getenv('MYSQL_PORT') or 3306)
    MYSQL_DATABASE = os.getenv('MYSQL_DATABASE') or "AdminFlask"

    # mysql 数据库的配置信息
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{MYSQL_USERNAME}:{quote_plus(MYSQL_PASSWORD)}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset=utf8mb4"
    # 默认日志等级
    LOG_LEVEL = logging.WARN
    #
    MAIL_SERVER = os.getenv('MAIL_SERVER') or 'smtp.qq.com'
    MAIL_USE_TLS = False
    MAIL_USE_SSL = True
    MAIL_PORT = 465
    MAIL_USERNAME = os.getenv('MAIL_USERNAME') or '123@qq.com'
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD') or 'XXXXX'  # 生成的授权码
    # 默认发件人的邮箱,这里填写和MAIL_USERNAME一致即可
    MAIL_DEFAULT_SENDER = ('admin', os.getenv('MAIL_USERNAME') or '123@qq.com')


class TestingConfig(BaseConfig):
    """ 测试配置 """
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # 内存数据库


class EmbeddedSQLiteConfig(BaseConfig):
    """单镜像离线部署配置，不依赖外部 MySQL。"""
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    LOG_LEVEL = logging.ERROR

    SQLITE_DATABASE_PATH = os.getenv(
        'SQLITE_DATABASE_PATH',
        os.path.join(BaseConfig.GEOVIEW_STATIC_ROOT, 'geoview.sqlite3'),
    )
    SQLALCHEMY_DATABASE_URI = (
        os.getenv('SQLALCHEMY_DATABASE_URI')
        or f"sqlite:///{SQLITE_DATABASE_PATH}"
    )
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {
            "check_same_thread": False,
        }
    }


class DevelopmentConfig(BaseConfig):
    """ 开发配置 """
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    SQLALCHEMY_ECHO = False


class ProductionConfig(BaseConfig):
    """生成环境配置"""
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_POOL_RECYCLE = 8

    LOG_LEVEL = logging.ERROR


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'embedded': EmbeddedSQLiteConfig,
    'production': ProductionConfig
}
