from applications.common.scripts.init_db import init_db


def init_script(app):
    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if uri.startswith("sqlite"):
        from pathlib import Path

        from applications.extensions import db
        from applications import models  # noqa: F401

        sqlite_path = app.config.get("SQLITE_DATABASE_PATH")
        if sqlite_path:
            Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
        with app.app_context():
            db.create_all()
        print(f"SQLite database initialized: {uri}")
        return

    init_db()
