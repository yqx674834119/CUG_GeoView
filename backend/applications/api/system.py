import json
import os
from contextlib import suppress

from flask import Blueprint, current_app

from applications.common.path_global import (FILE_ASSET_API_PREFIX,
                                             LEGACY_FILE_ASSET_PREFIX)
from applications.common.storage import (external_static_root,
                                         internal_static_root,
                                         storage_read_order)
from applications.common.utils.http import success_api

system_api_blueprint = Blueprint("system_api_blueprint",
                                 __name__,
                                 url_prefix="/api/system")


def _diagnostics_path():
    return os.getenv(
        "GEOVIEW_BACKEND_DIAGNOSTICS_PATH",
        "/tmp/geoview-logs/backend-startup-diagnostics.json",
    )


def _read_diagnostics_payload():
    path = _diagnostics_path()
    payload = {"path": path, "exists": os.path.isfile(path)}
    if not payload["exists"]:
        return payload

    with suppress(Exception):
        with open(path, "r", encoding="utf-8") as file:
            payload["data"] = json.load(file)
    return payload


@system_api_blueprint.get("/ping")
def ping():
    return success_api(data={
        "status": "ok",
        "photo_asset_mode": current_app.config.get("PHOTO_ASSET_SERVE_MODE"),
        "photo_asset_chunk_size": current_app.config.get(
            "PHOTO_ASSET_CHUNK_SIZE"),
        "uploaded_photos_dest": current_app.config.get(
            "UPLOADED_PHOTOS_DEST"),
        "external_static_root": external_static_root(),
        "internal_static_root": internal_static_root(),
        "asset_read_order": [store for store, _ in storage_read_order()],
        "preferred_asset_prefix": FILE_ASSET_API_PREFIX,
        "legacy_asset_prefix": LEGACY_FILE_ASSET_PREFIX,
        "diagnostics": _read_diagnostics_payload(),
    })


@system_api_blueprint.get("/diagnostics/assets")
def asset_diagnostics():
    return success_api(data=_read_diagnostics_payload())
