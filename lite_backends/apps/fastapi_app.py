import os
import time
from typing import List

import uvicorn
from fastapi import Body, FastAPI, File, Form, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from lite_backends import common


app = FastAPI(title="GeoView Lite FastAPI Transport Diagnostics", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Length", "Content-Range", "Accept-Ranges", "X-GeoView-Request-Id", "X-GeoView-Disk-Size", "X-GeoView-Bytes-Sent", "X-GeoView-Json-Bytes"],
)


@app.on_event("startup")
async def on_startup():
    common.startup_probe()


@app.middleware("http")
async def request_debug_middleware(request: Request, call_next):
    req_id = common.request_id()
    started = time.time()
    common.log_request(
        req_id,
        request.method,
        request.url.path,
        request.url.query,
        headers=dict(request.headers),
        client=request.client.host if request.client else "",
    )
    response = await call_next(request)
    response.headers["X-GeoView-Request-Id"] = req_id
    common.log_response(req_id, request.method, request.url.path, response.status_code, dict(response.headers), started_at=started)
    return response


def json_response(payload: dict, status_code: int = 200):
    body, headers = common.json_bytes(payload)
    return StreamingResponse(iter([body]), status_code=status_code, media_type="application/json; charset=utf-8", headers=headers)


def file_response(filename: str, request: Request, forced_mode: str = ""):
    spec = common.build_file_spec(filename, request.method, request.headers.get("range", ""), forced_mode)
    return StreamingResponse(common.iter_file_chunks(spec), status_code=spec.status_code, media_type=spec.media_type, headers=spec.headers)


@app.get("/api/system/ping")
async def ping():
    return json_response(common.system_ping())


@app.get("/api/history/list")
async def history_list(type: str = Query(default=""), page: int = Query(default=1), limit: int = Query(default=10)):
    return json_response(common.history_list(type or "", page, limit))


@app.delete("/api/history/batchRemove")
async def history_delete(payload: dict = Body(default={})):
    return json_response(common.delete_history(payload.get("ids") or []))


@app.get("/api/model/list/{model_type}")
async def model_list(model_type: str):
    return json_response(common.model_list(model_type))


@app.get("/api/model/huggingface/list")
async def huggingface_list():
    return json_response(common.success_api(data={}))


@app.post("/api/file/upload")
async def upload(files: List[UploadFile] = File(default=[]), type: str = Form(default="")):
    uploaded = [(item.filename, await item.read()) for item in files]
    return json_response(common.handle_upload(uploaded, type))


@app.post("/api/file/upload-video-preview")
async def upload_video_preview(file: UploadFile = File(...), type: str = Form(default="")):
    return json_response(common.handle_video_preview(file.filename, await file.read(), type))


@app.api_route("/api/file/assets/photos/{filename:path}", methods=["GET", "HEAD"])
async def asset_direct(filename: str, request: Request):
    return file_response(filename, request)


@app.api_route("/api/file/assets-buffered/photos/{filename:path}", methods=["GET", "HEAD"])
async def asset_buffered(filename: str, request: Request):
    return file_response(filename, request, forced_mode="buffered")


@app.api_route("/_uploads/photos/{filename:path}", methods=["GET", "HEAD"])
async def asset_legacy(filename: str, request: Request):
    return file_response(filename, request)


@app.api_route("/api/probe/method-asset/{filename:path}", methods=["GET", "POST", "HEAD"])
async def method_probe(filename: str, request: Request):
    return file_response(filename, request)


@app.get("/api/file/assets-preview/photos/{filename:path}")
async def asset_preview(filename: str, max_size: int = Query(default=420), quality: int = Query(default=75)):
    try:
        payload = common.build_preview_payload(filename, max_size=max_size, quality=quality)
        return json_response(common.success_api(msg="图片预览生成成功", data=payload))
    except Exception as exc:
        return json_response(common.fail_api(f"图片预览生成失败: {exc}"), status_code=500)


@app.get("/api/file/assets-transport/photos/{filename:path}")
async def asset_transport(filename: str):
    return json_response(common.success_api(msg="资源传输信息获取成功", data=common.build_transport(filename)))


@app.post("/api/analysis/tracking")
async def tracking(payload: dict = Body(default={})):
    return json_response(common.handle_tracking(payload))


@app.post("/api/analysis/histogram_match")
async def histogram_match(payload: dict = Body(default={})):
    return json_response(common.handle_histogram_match(payload))


@app.post("/api/analysis/image_pre")
async def image_pre(payload: dict = Body(default={})):
    return json_response(common.handle_image_pre(payload))


@app.post("/api/analysis/{route_name}")
async def analysis(route_name: str, payload: dict = Body(default={})):
    return json_response(common.handle_analysis(route_name, payload))


@app.get("/api/analysis/show/{type_name}")
async def analysis_show(type_name: str, page: int = Query(default=1), limit: int = Query(default=10)):
    return json_response(common.history_list(type_name, page, limit))


@app.options("/{path:path}")
async def options_handler(path: str):
    return json_response(common.success_api())


if __name__ == "__main__":
    uvicorn.run("lite_backends.apps.fastapi_app:app", host="0.0.0.0", port=int(os.getenv("PORT", "5008")), log_level="info")

