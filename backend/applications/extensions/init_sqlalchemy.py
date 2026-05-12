import os

from marshmallow import Schema
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker
from sqlalchemy.pool import StaticPool

from applications.configs.config import config

Base = declarative_base()
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False))
Base.query = SessionLocal.query_property()

_engine = None
_engine_uri = None


def _config_name():
    return os.getenv("GEOVIEW_CONFIG", "embedded")


def _config_object():
    return config.get(_config_name(), config["embedded"])


def database_uri(app=None):
    if app is not None and app.config.get("SQLALCHEMY_DATABASE_URI"):
        return app.config["SQLALCHEMY_DATABASE_URI"]
    return os.getenv("SQLALCHEMY_DATABASE_URI") or _config_object().SQLALCHEMY_DATABASE_URI


def _engine_options(uri):
    if uri.startswith("sqlite:///:memory:"):
        return {
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        }
    if uri.startswith("sqlite:///"):
        sqlite_path = uri.replace("sqlite:///", "", 1)
        parent = os.path.dirname(sqlite_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        return {"connect_args": {"check_same_thread": False}}
    return {
        "pool_pre_ping": True,
        "pool_recycle": int(os.getenv("SQLALCHEMY_POOL_RECYCLE", "1800")),
    }


def get_engine(app=None):
    global _engine, _engine_uri
    uri = database_uri(app)
    if _engine is None or _engine_uri != uri:
        if _engine is not None:
            SessionLocal.remove()
            _engine.dispose()
        _engine = create_engine(uri, **_engine_options(uri))
        _engine_uri = uri
        SessionLocal.configure(bind=_engine)
    return _engine


class _Database:
    Model = Base
    session = SessionLocal

    def __getattr__(self, name):
        import sqlalchemy as sa

        if hasattr(sa, name):
            return getattr(sa, name)
        raise AttributeError(name)

    def init_app(self, app):
        get_engine(app)

    def create_all(self, app=None):
        Base.metadata.create_all(bind=get_engine(app))

    def remove(self):
        SessionLocal.remove()


class _Marshmallow:
    Schema = Schema

    def init_app(self, app):
        return None


db = _Database()
ma = _Marshmallow()


def init_databases(app=None):
    db.init_app(app)
    db.create_all(app)
