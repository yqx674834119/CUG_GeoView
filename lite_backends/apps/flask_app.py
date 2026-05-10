import os
import time

from flask import Flask, Response, jsonify, request

from lite_backends import common


app = Flask(__name__)
common.startup_probe()


@app.before_request
def before_request():
    request.geoview_request_id = common.request_id()
    request.geoview_started_at = time.time()
    common.log_request(
        request.geoview_request_id,
        request.method,
        request.path,
        request.query_string.decode("utf-8", "ignore"),
        headers=request.headers,
        client=request.headers.get("X-Forwarded-For", request.remote_addr or ""),
    )


@app.after_request
def after_request(response):
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
    return Response((body,), status=status_code, headers=headers, mimetype="application/json")


def file_response(filename: str, forced_mode: str = ""):
    spec = common.build_file_spec(filename, request.method, request.headers.get("Range", ""), forced_mode)
    return Response(common.iter_file_chunks(spec), status=spec.status_code, headers=spec.headers, mimetype=spec.media_type, direct_passthrough=True)


@app.route("/api/system/ping")
def ping():
    return json_response(common.system_ping())


@app.route("/api/history/list")
def history_list():
    return json_response(common.history_list(request.args.get("type", ""), int(request.args.get("page", 1)), int(request.args.get("limit", 10))))


@app.route("/api/history/batchRemove", methods=["DELETE"])
def history_delete():
    return json_response(common.delete_history((request.get_json(silent=True) or {}).get("ids") or []))


@app.route("/api/model/list/<model_type>")
def model_list(model_type):
    return json_response(common.model_list(model_type))


@app.route("/api/model/huggingface/list")
def huggingface_list():
    return json_response(common.success_api(data={}))


@app.route("/api/file/upload", methods=["POST"])
def upload():
    file_list = request.files.getlist("files") or request.files.getlist("file")
    uploaded = [(item.filename, item.read()) for item in file_list]
    return json_response(common.handle_upload(uploaded, request.form.get("type", "")))


@app.route("/api/file/upload-video-preview", methods=["POST"])
def upload_video_preview():
    item = request.files.get("file")
    if item is None:
        return json_response(common.fail_api("请选择视频文件"), 400)
    return json_response(common.handle_video_preview(item.filename, item.read(), request.form.get("type", "")))


@app.route("/api/file/assets/photos/<path:filename>", methods=["GET", "HEAD"])
def asset_direct(filename):
    return file_response(filename)


@app.route("/api/file/assets-buffered/photos/<path:filename>", methods=["GET", "HEAD"])
def asset_buffered(filename):
    return file_response(filename, forced_mode="buffered")


@app.route("/_uploads/photos/<path:filename>", methods=["GET", "HEAD"])
def asset_legacy(filename):
    return file_response(filename)


@app.route("/api/probe/method-asset/<path:filename>", methods=["GET", "POST", "HEAD"])
def method_probe(filename):
    return file_response(filename)


@app.route("/api/file/assets-preview/photos/<path:filename>")
def asset_preview(filename):
    try:
        payload = common.build_preview_payload(filename, max_size=int(request.args.get("max_size", 420)), quality=int(request.args.get("quality", 75)))
        return json_response(common.success_api(msg="图片预览生成成功", data=payload))
    except Exception as exc:
        return json_response(common.fail_api(f"图片预览生成失败: {exc}"), 500)


@app.route("/api/file/assets-transport/photos/<path:filename>")
def asset_transport(filename):
    return json_response(common.success_api(msg="资源传输信息获取成功", data=common.build_transport(filename)))


@app.route("/api/analysis/tracking", methods=["POST"])
def tracking():
    return json_response(common.handle_tracking(request.get_json(silent=True) or {}))


@app.route("/api/analysis/histogram_match", methods=["POST"])
def histogram_match():
    return json_response(common.handle_histogram_match(request.get_json(silent=True) or {}))


@app.route("/api/analysis/image_pre", methods=["POST"])
def image_pre():
    return json_response(common.handle_image_pre(request.get_json(silent=True) or {}))


@app.route("/api/analysis/<route_name>", methods=["POST"])
def analysis(route_name):
    return json_response(common.handle_analysis(route_name, request.get_json(silent=True) or {}))


@app.route("/api/analysis/show/<type_name>")
def analysis_show(type_name):
    return json_response(common.history_list(type_name, int(request.args.get("page", 1)), int(request.args.get("limit", 10))))


@app.route("/", defaults={"path": ""}, methods=["OPTIONS"])
@app.route("/<path:path>", methods=["OPTIONS"])
def options_handler(path):
    return json_response(common.success_api())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5008")), threaded=True)
