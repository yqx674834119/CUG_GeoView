import os
import time

from aiohttp import web

from lite_backends import common


@web.middleware
async def debug_middleware(request, handler):
    req_id = common.request_id()
    started = time.time()
    common.log_request(
        req_id,
        request.method,
        request.path,
        request.query_string,
        headers=request.headers,
        client=request.headers.get("X-Forwarded-For", request.remote or ""),
    )
    response = await handler(request)
    response.headers["X-GeoView-Request-Id"] = req_id
    for key, value in common.cors_headers().items():
        response.headers[key] = value
    common.log_response(req_id, request.method, request.path, response.status, response.headers, started_at=started)
    return response


async def json_response(payload: dict, status: int = 200):
    body, headers = common.json_bytes(payload)
    headers.update(common.cors_headers())
    resp = web.StreamResponse(status=status, headers=headers)
    await resp.prepare(_current_request.get())
    await resp.write(body)
    await resp.write_eof()
    return resp


class RequestContext:
    def __init__(self):
        self.request = None

    def set(self, request):
        self.request = request

    def get(self):
        return self.request


_current_request = RequestContext()


async def stream_json(request, payload: dict, status: int = 200):
    body, headers = common.json_bytes(payload)
    headers.update(common.cors_headers())
    resp = web.StreamResponse(status=status, headers=headers)
    await resp.prepare(request)
    await resp.write(body)
    await resp.write_eof()
    return resp


async def file_response(request, filename: str, forced_mode: str = ""):
    spec = common.build_file_spec(filename, request.method, request.headers.get("Range", ""), forced_mode)
    resp = web.StreamResponse(status=spec.status_code, headers={**spec.headers, **common.cors_headers()})
    await resp.prepare(request)
    for chunk in common.iter_file_chunks(spec):
        await resp.write(chunk)
    await resp.write_eof()
    return resp


async def parse_multipart(request):
    reader = await request.multipart()
    files = []
    fields = {}
    async for part in reader:
        if part.filename:
            files.append((part.filename, await part.read(decode=False), part.name))
        else:
            fields[part.name] = (await part.text())
    return files, fields


async def ping(request):
    return await stream_json(request, common.system_ping())


async def history_list(request):
    return await stream_json(request, common.history_list(request.query.get("type", ""), int(request.query.get("page", 1)), int(request.query.get("limit", 10))))


async def history_delete(request):
    payload = await request.json() if request.can_read_body else {}
    return await stream_json(request, common.delete_history((payload or {}).get("ids") or []))


async def model_list(request):
    return await stream_json(request, common.model_list(request.match_info["model_type"]))


async def huggingface_list(request):
    return await stream_json(request, common.success_api(data={}))


async def upload(request):
    files, fields = await parse_multipart(request)
    selected = [(name, body) for name, body, field in files if field in ("files", "file")]
    return await stream_json(request, common.handle_upload(selected, fields.get("type", "")))


async def upload_video_preview(request):
    files, fields = await parse_multipart(request)
    selected = [(name, body) for name, body, field in files if field == "file"]
    if not selected:
        return await stream_json(request, common.fail_api("请选择视频文件"), 400)
    name, body = selected[0]
    return await stream_json(request, common.handle_video_preview(name, body, fields.get("type", "")))


async def asset_direct(request):
    return await file_response(request, request.match_info["filename"])


async def asset_buffered(request):
    return await file_response(request, request.match_info["filename"], forced_mode="buffered")


async def asset_legacy(request):
    return await file_response(request, request.match_info["filename"])


async def method_probe(request):
    return await file_response(request, request.match_info["filename"])


async def asset_preview(request):
    try:
        payload = common.build_preview_payload(request.match_info["filename"], max_size=int(request.query.get("max_size", 420)), quality=int(request.query.get("quality", 75)))
        return await stream_json(request, common.success_api(msg="图片预览生成成功", data=payload))
    except Exception as exc:
        return await stream_json(request, common.fail_api(f"图片预览生成失败: {exc}"), 500)


async def asset_transport(request):
    return await stream_json(request, common.success_api(msg="资源传输信息获取成功", data=common.build_transport(request.match_info["filename"])))


async def tracking(request):
    payload = await request.json() if request.can_read_body else {}
    return await stream_json(request, common.handle_tracking(payload or {}))


async def histogram_match(request):
    payload = await request.json() if request.can_read_body else {}
    return await stream_json(request, common.handle_histogram_match(payload or {}))


async def image_pre(request):
    payload = await request.json() if request.can_read_body else {}
    return await stream_json(request, common.handle_image_pre(payload or {}))


async def analysis(request):
    payload = await request.json() if request.can_read_body else {}
    return await stream_json(request, common.handle_analysis(request.match_info["route_name"], payload or {}))


async def analysis_show(request):
    return await stream_json(request, common.history_list(request.match_info["type_name"], int(request.query.get("page", 1)), int(request.query.get("limit", 10))))


async def options_handler(request):
    return await stream_json(request, common.success_api())


def create_app():
    common.startup_probe()
    app = web.Application(middlewares=[debug_middleware])
    app.router.add_get("/api/system/ping", ping)
    app.router.add_get("/api/history/list", history_list)
    app.router.add_delete("/api/history/batchRemove", history_delete)
    app.router.add_get("/api/model/list/{model_type}", model_list)
    app.router.add_get("/api/model/huggingface/list", huggingface_list)
    app.router.add_post("/api/file/upload", upload)
    app.router.add_post("/api/file/upload-video-preview", upload_video_preview)
    app.router.add_route("*", "/api/file/assets/photos/{filename:.*}", asset_direct)
    app.router.add_route("*", "/api/file/assets-buffered/photos/{filename:.*}", asset_buffered)
    app.router.add_route("*", "/_uploads/photos/{filename:.*}", asset_legacy)
    app.router.add_route("*", "/api/probe/method-asset/{filename:.*}", method_probe)
    app.router.add_get("/api/file/assets-preview/photos/{filename:.*}", asset_preview)
    app.router.add_get("/api/file/assets-transport/photos/{filename:.*}", asset_transport)
    app.router.add_post("/api/analysis/tracking", tracking)
    app.router.add_post("/api/analysis/histogram_match", histogram_match)
    app.router.add_post("/api/analysis/image_pre", image_pre)
    app.router.add_post("/api/analysis/{route_name}", analysis)
    app.router.add_get("/api/analysis/show/{type_name}", analysis_show)
    app.router.add_route("OPTIONS", "/{path:.*}", options_handler)
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host="0.0.0.0", port=int(os.getenv("PORT", "5008")))
