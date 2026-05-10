import os

from marshmallow import Schema
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker
from sqlalchemy.pool import StaticPool

from applications.configs.config import config


def _config_name():
    return os.getenv("GEOVIEW_CONFIG", "embedded")


def _config_object():
    return config.get(_config_name(), config["embedded"])


def database_uri():
    return os.getenv("SQLALCHEMY_DATABASE_URI") or _config_object().SQLALCHEMY_DATABASE_URI


def _engine_options(uri):
    if uri.startswith("sqlite:///:memory:"):
        return {
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        }
    if uri.startswith("sqlite:///"):
        sqlite_path = uri.replace("sqlite:///", "", 1)
        return {"connect_args": {"check_same_thread": False}}
    return {
        "pool_pre_ping": True,
        "pool_recycle": int(os.getenv("SQLALCHEMY_POOL_RECYCLE", "1800")),
    }


engine = create_engine(database_uri(), **_engine_options(database_uri()))
SessionLocal = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine)
)
Base = declarative_base()
Base.query = SessionLocal.query_property()


class _Database:
    Model = Base
    session = SessionLocal

    def __getattr__(self, name):
        import sqlalchemy as sa

        if hasattr(sa, name):
            return getattr(sa, name)
        raise AttributeError(name)

    def init_app(self, app):
        return None

    def create_all(self):
        Base.metadata.create_all(bind=engine)

    def remove(self):
        SessionLocal.remove()


class _Marshmallow:
    Schema = Schema

    def init_app(self, app):
        return None


db = _Database()
ma = _Marshmallow()


def init_databases(app=None):
    db.create_all()
