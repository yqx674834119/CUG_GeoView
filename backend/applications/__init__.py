import os
import sys
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from applications.api import system_api
from applications.common.debug_logging import log_debug, new_request_id
from applications.common.storage import ensure_storage_dirs
from applications.extensions import db, init_plugs

_curr_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.normpath(os.path.join(_curr_dir, "../../PaddleRS")))


def create_app(config_name=None):
    app = FastAPI(title="GeoView Backend", version="2.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def _startup():
        ensure_storage_dirs()
        init_plugs(app)
        from applications import models  # noqa: F401

        db.create_all()
        log_debug(
            "后端启动",
            "FastAPI 应用启动完成，数据库表已确认，静态目录已确认",
            static_external=os.getenv("GEOVIEW_EXTERNAL_STATIC_ROOT", ""),
            static_internal=os.getenv("GEOVIEW_INTERNAL_STATIC_ROOT", ""),
            upload_dest=os.getenv("UPLOADED_PHOTOS_DEST", ""),
            asset_mode=os.getenv("GEOVIEW_PHOTO_ASSET_SERVE_MODE", "buffered"),
            workers=os.getenv("GEOVIEW_BACKEND_WORKERS", "1"),
        )

    @app.middleware("http")
    async def _request_debug_logging(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or new_request_id()
        request.state.request_id = request_id
        started_at = time.time()
        log_debug(
            "后端请求",
            "收到前端/客户端请求",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query=str(request.url.query),
            client=request.client.host if request.client else "",
            user_agent=request.headers.get("user-agent", "")[:160],
            request_content_length=request.headers.get("content-length", ""),
            range=request.headers.get("range", ""),
        )
        try:
            response = await call_next(request)
        except Exception as exc:
            log_debug(
                "后端请求",
                "请求处理抛出异常",
                request_id=request_id,
                path=request.url.path,
                error=str(exc),
                elapsed_ms=int((time.time() - started_at) * 1000),
            )
            raise
        response.headers["X-GeoView-Request-Id"] = request_id
        log_debug(
            "后端请求",
            "请求处理完成",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            response_content_length=response.headers.get("content-length", ""),
            content_range=response.headers.get("content-range", ""),
            accept_ranges=response.headers.get("accept-ranges", ""),
            elapsed_ms=int((time.time() - started_at) * 1000),
        )
        return response

    @app.middleware("http")
    async def _db_session_cleanup(request: Request, call_next):
        try:
            return await call_next(request)
        finally:
            db.remove()

    @app.exception_handler(Exception)
    async def _error_handler(request: Request, exc: Exception):
        if os.getenv("GEOVIEW_DEBUG_ERRORS", "0").lower() in {"1", "true", "yes"}:
            raise exc
        return JSONResponse(
            status_code=500,
            content={"success": False, "code": 500, "msg": f"后端出现异常：{str(exc)}"},
        )

    system_api(app)
    return app
