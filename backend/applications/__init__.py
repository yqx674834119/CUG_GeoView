import os
import sys
from datetime import datetime, timezone

from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from applications.api import register_api
from applications.common.storage import ensure_storage_dirs, primary_upload_root
from applications.configs.config import config
from applications.extensions import db, init_plugs

_curr_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.normpath(os.path.join(_curr_dir, "../../PaddleRS")))


def create_app(config_name=None):
    app = Flask(__name__)
    selected_config = config_name or os.getenv("GEOVIEW_CONFIG", "embedded")
    app.config.from_object(config.get(selected_config, config["embedded"]))
    app.config["JSON_AS_ASCII"] = False
    CORS(app)

    ensure_storage_dirs()
    init_plugs(app)
    from applications import models  # noqa: F401

    db.create_all()

    @app.route("/health", methods=["GET"])
    def health():
        upload_dir = primary_upload_root()
        return jsonify({
            "success": True,
            "status": "ok",
            "service": "geoview-backend",
            "version": "3.0.0",
            "time": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "storage": {
                "upload_dir": upload_dir,
                "upload_dir_exists": os.path.isdir(upload_dir),
            },
        })

    @app.teardown_appcontext
    def _db_session_cleanup(_exception=None):
        db.remove()

    @app.errorhandler(Exception)
    def _error_handler(exc):
        if isinstance(exc, HTTPException):
            return jsonify({
                "success": False,
                "code": exc.code,
                "msg": exc.description,
            }), exc.code
        if os.getenv("GEOVIEW_DEBUG_ERRORS", "0").lower() in {"1", "true", "yes"}:
            raise exc
        return jsonify({
            "success": False,
            "code": 500,
            "msg": f"后端出现异常：{str(exc)}",
        }), 500

    register_api(app)
    print(
        "[GeoView] backend ready "
        f"upload_dir={primary_upload_root()} "
        f"database={os.getenv('GEOVIEW_CONFIG', selected_config)}",
        flush=True,
    )
    return app
