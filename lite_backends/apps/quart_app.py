import os
import time
import inspect

from quart import Quart, Response, request

from lite_backends import common


app = Quart(__name__)


@app.before_serving
async def on_startup():
    common.startup_probe()


@app.before_request
async def before_request():
    request.geoview_request_id = common.request_id()
    request.geoview_started_at = time.time()
    common.log_request(
        request.geoview_request_id,
        request.method,
        request.path,
        request.query_string.decode("utf-8", "ignore"),
        headers=request.headers,
        client=request.headers.get("X-Forwarded-For", ""),
    )


@app.after_request
async def after_request(response):
    response.headers["X-GeoView-Request-Id"] = getattr(request, "geoview_request_id", "")
    for key, value in common.cors_headers().items():
        response.headers[key] = value
    common.log_response(
        getattr(request, "geoview_request_id", ""),
        request.method,
        request.path,
        response.status_code,
        response.headers,
        started_at=getattr(request, "geoview_started_at", 0.0),
    )
    return response


def json_response(payload: dict, status_code: int = 200):
    body, headers = common.json_bytes(payload)
    headers.update(common.cors_headers())
    return Response((chunk for chunk in [body]), status=status_code, headers=headers, content_type="application/json; charset=utf-8")


async def async_file_iter(spec):
    for chunk in common.iter_file_chunks(spec):
        yield chunk


def file_response(filename: str, forced_mode: str = ""):
    spec = common.build_file_spec(filename, request.method, request.headers.get("Range", ""), forced_mode)
    return Response(async_file_iter(spec), status=spec.status_code, headers=spec.headers, content_type=spec.media_type)


async def read_upload_file(item):
    payload = item.read()
    if inspect.isawaitable(payload):
        payload = await payload
    return payload or b""


@app.get("/api/system/ping")
async def ping():
    return json_response(common.system_ping())


@app.get("/api/history/list")
async def history_list():
    return json_response(common.history_list(request.args.get("type", ""), int(request.args.get("page", 1)), int(request.args.get("limit", 10))))


@app.delete("/api/history/batchRemove")
async def history_delete():
    return json_response(common.delete_history(((await request.get_json(silent=True)) or {}).get("ids") or []))


@app.get("/api/model/list/<model_type>")
async def model_list(model_type):
    return json_response(common.model_list(model_type))


@app.get("/api/model/huggingface/list")
async def huggingface_list():
    return json_response(common.success_api(data={}))


@app.post("/api/file/upload")
async def upload():
    files = await request.files
    form = await request.form
    file_list = files.getlist("files") or files.getlist("file")
    uploaded = [(item.filename, await read_upload_file(item)) for item in file_list]
    return json_response(common.handle_upload(uploaded, form.get("type", "")))


@app.post("/api/file/upload-video-preview")
async def upload_video_preview():
    files = await request.files
    form = await request.form
    item = files.get("file")
    if item is None:
        return json_response(common.fail_api("请选择视频文件"), 400)
    return json_response(common.handle_video_preview(item.filename, await read_upload_file(item), form.get("type", "")))


@app.route("/api/file/assets/photos/<path:filename>", methods=["GET", "HEAD"])
async def asset_direct(filename):
    return file_response(filename)


@app.route("/api/file/assets-buffered/photos/<path:filename>", methods=["GET", "HEAD"])
async def asset_buffered(filename):
    return file_response(filename, forced_mode="buffered")


@app.route("/_uploads/photos/<path:filename>", methods=["GET", "HEAD"])
async def asset_legacy(filename):
    return file_response(filename)


@app.route("/api/probe/method-asset/<path:filename>", methods=["GET", "POST", "HEAD"])
async def method_probe(filename):
    return file_response(filename)


@app.get("/api/file/assets-preview/photos/<path:filename>")
async def asset_preview(filename):
    try:
        payload = common.build_preview_payload(filename, max_size=int(request.args.get("max_size", 420)), quality=int(request.args.get("quality", 75)))
        return json_response(common.success_api(msg="图片预览生成成功", data=payload))
    except Exception as exc:
        return json_response(common.fail_api(f"图片预览生成失败: {exc}"), 500)


@app.get("/api/file/assets-transport/photos/<path:filename>")
async def asset_transport(filename):
    return json_response(common.success_api(msg="资源传输信息获取成功", data=common.build_transport(filename)))


@app.post("/api/analysis/tracking")
async def tracking():
    return json_response(common.handle_tracking((await request.get_json(silent=True)) or {}))


@app.post("/api/analysis/histogram_match")
async def histogram_match():
    return json_response(common.handle_histogram_match((await request.get_json(silent=True)) or {}))


@app.post("/api/analysis/image_pre")
async def image_pre():
    return json_response(common.handle_image_pre((await request.get_json(silent=True)) or {}))


@app.post("/api/analysis/<route_name>")
async def analysis(route_name):
    return json_response(common.handle_analysis(route_name, (await request.get_json(silent=True)) or {}))


@app.get("/api/analysis/show/<type_name>")
async def analysis_show(type_name):
    return json_response(common.history_list(type_name, int(request.args.get("page", 1)), int(request.args.get("limit", 10))))


@app.route("/", defaults={"path": ""}, methods=["OPTIONS"])
@app.route("/<path:path>", methods=["OPTIONS"])
async def options_handler(path):
    return json_response(common.success_api())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5008")))
