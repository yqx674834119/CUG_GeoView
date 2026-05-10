from applications.extensions import db


def init_script(app=None):
    from applications import models  # noqa: F401

    db.create_all()
