import os

from flask import Blueprint

from applications.common.storage import primary_upload_root
from applications.common.utils.http import success_api

system_api_blueprint = Blueprint("system_api", __name__, url_prefix="/api/system")


@system_api_blueprint.route("/ping", methods=["GET"])
def ping():
    return success_api(data={
        "status": "ok",
        "uploaded_photos_dest": primary_upload_root(),
        "debug": False,
    })


@system_api_blueprint.route("/diagnostics/assets", methods=["GET"])
def asset_diagnostics():
    return success_api(data={
        "status": "removed",
        "msg": "startup asset diagnostics were removed",
        "uploaded_photos_dest": primary_upload_root(),
        "exists": os.path.isdir(primary_upload_root()),
    })
