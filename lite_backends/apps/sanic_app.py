import os
import time

from sanic import Sanic, response
from sanic.response import ResponseStream

from lite_backends import common


app = Sanic("geoview_lite_sanic")


@app.before_server_start
async def on_startup(_app, _loop):
    common.startup_probe()


@app.middleware("request")
async def before_request(request):
    request.ctx.geoview_request_id = common.request_id()
    request.ctx.geoview_started_at = time.time()
    common.log_request(
        request.ctx.geoview_request_id,
        request.method,
        request.path,
        request.query_string,
        headers=request.headers,
        client=request.headers.get("x-forwarded-for", request.remote_addr or ""),
    )
    if request.method == "OPTIONS":
        return response.raw(
            b"",
            status=204,
            headers=common.cors_headers(),
            content_type="text/plain; charset=utf-8",
        )


@app.middleware("response")
async def after_request(request, resp):
    resp.headers["X-GeoView-Request-Id"] = getattr(request.ctx, "geoview_request_id", "")
    for key, value in common.cors_headers().items():
        resp.headers[key] = value
    common.log_response(
        getattr(request.ctx, "geoview_request_id", ""),
        request.method,
        request.path,
        resp.status,
        resp.headers,
        started_at=getattr(request.ctx, "geoview_started_at", 0.0),
    )


async def json_response(payload: dict, status: int = 200):
    body, headers = common.json_bytes(payload)
    headers.update(common.cors_headers())

    async def stream_fn(stream):
        await stream.write(body)

    return ResponseStream(stream_fn, status=status, headers=headers, content_type="application/json; charset=utf-8")


async def file_response(request, filename: str, forced_mode: str = ""):
    spec = common.build_file_spec(filename, request.method, request.headers.get("range", ""), forced_mode)

    async def stream_fn(stream):
        for chunk in common.iter_file_chunks(spec):
            await stream.write(chunk)

    return ResponseStream(stream_fn, status=spec.status_code, headers=spec.headers, content_type=spec.media_type)


def get_file_list(request, field):
    value = request.files.get(field)
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


@app.get("/api/system/ping")
async def ping(request):
    return await json_response(common.system_ping())


@app.get("/api/history/list")
async def history_list(request):
    return await json_response(common.history_list(request.args.get("type", ""), int(request.args.get("page", 1)), int(request.args.get("limit", 10))))


@app.delete("/api/history/batchRemove")
async def history_delete(request):
    return await json_response(common.delete_history((request.json or {}).get("ids") or []))


@app.get("/api/model/list/<model_type:str>")
async def model_list(request, model_type):
    return await json_response(common.model_list(model_type))


@app.get("/api/model/huggingface/list")
async def huggingface_list(request):
    return await json_response(common.success_api(data={}))


@app.post("/api/file/upload")
async def upload(request):
    files = get_file_list(request, "files") or get_file_list(request, "file")
    uploaded = [(item.name or "upload.bin", item.body or b"") for item in files]
    return await json_response(common.handle_upload(uploaded, request.form.get("type", "")))


@app.post("/api/file/upload-video-preview")
async def upload_video_preview(request):
    files = get_file_list(request, "file")
    if not files:
        return await json_response(common.fail_api("请选择视频文件"), 400)
    item = files[0]
    return await json_response(common.handle_video_preview(item.name or "upload.mp4", item.body or b"", request.form.get("type", "")))


@app.route("/api/file/assets/photos/<filename:path>", methods=["GET", "HEAD"])
async def asset_direct(request, filename):
    return await file_response(request, filename)


@app.route("/api/file/assets-buffered/photos/<filename:path>", methods=["GET", "HEAD"])
async def asset_buffered(request, filename):
    return await file_response(request, filename, forced_mode="buffered")


@app.route("/_uploads/photos/<filename:path>", methods=["GET", "HEAD"])
async def asset_legacy(request, filename):
    return await file_response(request, filename)


@app.route("/api/probe/method-asset/<filename:path>", methods=["GET", "POST", "HEAD"])
async def method_probe(request, filename):
    return await file_response(request, filename)


@app.get("/api/file/assets-preview/photos/<filename:path>")
async def asset_preview(request, filename):
    try:
        payload = common.build_preview_payload(filename, max_size=int(request.args.get("max_size", 420)), quality=int(request.args.get("quality", 75)))
        return await json_response(common.success_api(msg="图片预览生成成功", data=payload))
    except Exception as exc:
        return await json_response(common.fail_api(f"图片预览生成失败: {exc}"), 500)


@app.get("/api/file/assets-transport/photos/<filename:path>")
async def asset_transport(request, filename):
    return await json_response(common.success_api(msg="资源传输信息获取成功", data=common.build_transport(filename)))


@app.post("/api/analysis/tracking")
async def tracking(request):
    return await json_response(common.handle_tracking(request.json or {}))


@app.post("/api/analysis/histogram_match")
async def histogram_match(request):
    return await json_response(common.handle_histogram_match(request.json or {}))


@app.post("/api/analysis/image_pre")
async def image_pre(request):
    return await json_response(common.handle_image_pre(request.json or {}))


@app.post("/api/analysis/<route_name:str>")
async def analysis(request, route_name):
    return await json_response(common.handle_analysis(route_name, request.json or {}))


@app.get("/api/analysis/show/<type_name:str>")
async def analysis_show(request, type_name):
    return await json_response(common.history_list(type_name, int(request.args.get("page", 1)), int(request.args.get("limit", 10))))


@app.options("/<path:path>")
async def options_handler(request, path):
    return await json_response(common.success_api())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5008")), single_process=True, access_log=True)
