import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor

from flask import Blueprint, current_app, request

from applications.common.debug_logging import compact_json_bytes, log_debug, summarize_value
from applications.common.model_assets import infer_model_backend
from applications.common.path_global import (
    fun_type_1,
    fun_type_2,
    fun_type_3,
    fun_type_4,
    fun_type_5,
    generate_dir,
    up_dir,
)
from applications.common.result_transport import create_result_manifest, normalize_chunk_size
from applications.common.utils.http import fail_api, success_api
from applications.common.utils.upload import img_url_handle
from applications.image_processing import histogram_match
from applications.interface.utils import resolve_paddle_device

analysis_api = Blueprint("analysis_api", __name__, url_prefix="/api/analysis")

SMALL_TARGET_DETECTION_MODEL_PATH = "backend/model/object_detection/mmrotate_oriented_rcnn_r50_fpn_1x_dota_le90"
TRACKING_JOB_TTL_SECONDS = 60 * 60
_TRACKING_JOB_LOCK = threading.Lock()
_TRACKING_JOBS = {}
_TRACKING_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="tracking-job")


def _get_model_info(model_path):
    from applications.interface.utils import get_model_info

    return get_model_info(model_path)


def _analysis_functions():
    from applications.interface.analysis import (
        change_detection,
        classification,
        handle,
        image_restoration,
        object_detection,
        registration,
        sam3_change_detection,
        terrain_classification,
        tracking,
    )

    return {
        "change_detection": change_detection,
        "classification": classification,
        "handle": handle,
        "image_restoration": image_restoration,
        "object_detection": object_detection,
        "registration": registration,
        "sam3_change_detection": sam3_change_detection,
        "terrain_classification": terrain_classification,
        "tracking": tracking,
    }


def _analysis_debug(route_name, req_json, **extra):
    payload_summary = {
        key: summarize_value(req_json.get(key))
        for key in ("model_path", "list", "prehandle", "denoise", "window_size", "stride", "type", "rect")
        if key in req_json
    }
    payload_summary.update(extra)
    log_debug(
        "模型推理",
        "收到推理请求",
        route=route_name,
        payload_summary=payload_summary,
        estimated_request_bytes=compact_json_bytes(req_json),
    )


def _analysis_done(route_name, started_at, **extra):
    log_debug(
        "模型推理",
        "推理请求处理完成",
        route=route_name,
        elapsed_ms=int((time.time() - started_at) * 1000),
        **extra,
    )


def _request_json():
    return request.get_json(silent=True) or {}


def _transport_success(route_name, payload, msg="成功"):
    chunk_size = normalize_chunk_size(request.headers.get("X-Geoview-Chunk-Size") or request.args.get("chunk_size"))
    manifest = create_result_manifest(payload, route=route_name, chunk_size=chunk_size)
    log_debug(
        "模型推理",
        "推理结果已写入分片传输缓存",
        route=route_name,
        result_id=manifest["result_id"],
        raw_size=manifest["raw_size"],
        compressed_size=manifest["compressed_size"],
        encoded_size=manifest["encoded_size"],
        chunk_size=manifest["chunk_size"],
        chunk_count=manifest["chunk_count"],
    )
    return success_api(msg=msg, data={"transport_manifest": manifest})


def _cleanup_tracking_jobs(now=None):
    current = now or time.time()
    expired = [
        job_id
        for job_id, job in _TRACKING_JOBS.items()
        if current - job.get("created_at", current) > TRACKING_JOB_TTL_SECONDS
    ]
    for job_id in expired:
        _TRACKING_JOBS.pop(job_id, None)


def _tracking_job_snapshot(job_id):
    with _TRACKING_JOB_LOCK:
        _cleanup_tracking_jobs()
        job = _TRACKING_JOBS.get(job_id)
        if not job:
            return None
        return {
            key: value
            for key, value in job.items()
            if key not in {"future"}
        }


def _set_tracking_job(job_id, **fields):
    with _TRACKING_JOB_LOCK:
        job = _TRACKING_JOBS.get(job_id)
        if not job:
            return
        job.update(fields)
        job["updated_at"] = time.time()


def _validate_tracking_payload(req_json):
    model_path = req_json.get("model_path", "backend/model/tracking/auto")
    list_ = req_json.get("list")
    rect = req_json.get("rect")
    if not list_:
        return None, None, None, fail_api("请提供上传后的图像序列或单个视频文件")
    from applications.interface.tracking import requires_initial_rect

    try:
        need_initial_rect = requires_initial_rect(model_path)
    except Exception as exc:
        return None, None, None, fail_api(f"跟踪失败: {str(exc)}")
    from applications.common.model_assets import load_model_manifest

    manifest = load_model_manifest(model_path) or {}
    if manifest.get("runtime") == "sam3_prompt":
        prompt_text = req_json.get("prompt_text") or req_json.get("sam3_prompt") or ""
        if not prompt_text.strip():
            return None, None, None, fail_api("请提供 SAM3 文本 Prompt")
        return model_path, list_, rect, None
    if need_initial_rect:
        if not rect or len(rect) != 4:
            return None, None, None, fail_api("请提供初始跟踪框")
        try:
            rect = [int(value) for value in rect]
        except Exception:
            return None, None, None, fail_api("初始跟踪框格式错误")
        if rect[2] <= 0 or rect[3] <= 0:
            return None, None, None, fail_api("初始跟踪框宽高必须大于0")
    elif rect:
        try:
            rect = [int(value) for value in rect]
        except Exception:
            rect = None
    return model_path, list_, rect, None


def _run_tracking_job(app, job_id, model_path, list_, rect, chunk_size, prompt_text=None):
    started_at = time.time()
    _set_tracking_job(job_id, status="running", started_at=started_at, message="目标跟踪正在运行")
    try:
        with app.app_context():
            result = _analysis_functions()["tracking"](
                model_path,
                up_dir,
                generate_dir,
                list_,
                rect,
                type_=7,
                prompt_text=prompt_text,
            )
            manifest = create_result_manifest(result, route="tracking", chunk_size=chunk_size)
            _analysis_done(
                "tracking_async",
                started_at,
                job_id=job_id,
                record_count=len(result) if hasattr(result, "__len__") else -1,
                model_path=model_path,
            )
            _set_tracking_job(
                job_id,
                status="succeeded",
                finished_at=time.time(),
                message="目标跟踪完成",
                transport_manifest=manifest,
                summary={
                    "runtime_variant": result.get("runtime_variant"),
                    "method_used": result.get("method_used"),
                    "tracking": result.get("summary"),
                },
            )
    except Exception as exc:
        _set_tracking_job(
            job_id,
            status="failed",
            finished_at=time.time(),
            message=f"跟踪失败: {str(exc)}",
            error=str(exc),
            traceback=traceback.format_exc(limit=8),
        )


def _small_target_second_image(req_json):
    image_list = req_json.get("list")
    if isinstance(image_list, list):
        if len(image_list) >= 2:
            second_item = image_list[1]
            if isinstance(second_item, dict):
                return second_item.get("src") or second_item.get("second") or ""
            return second_item
        if len(image_list) == 1 and isinstance(image_list[0], dict):
            return image_list[0].get("second") or ""
    return req_json.get("second") or ""


@analysis_api.route("/change_detection", methods=["POST"])
def change_detection_api():
    req_json = _request_json()
    started_at = time.time()
    _analysis_debug("change_detection", req_json)
    model_path = req_json.get("model_path")
    if not model_path:
        return fail_api("请指定模型路径")
    window_size = int(req_json.get("window_size", 256))
    stride = int(req_json.get("stride", 128))
    if window_size <= 0 or stride <= 0:
        return fail_api("步长和窗口大小必须大于0")
    if window_size < stride:
        return fail_api("步长必须小于等于窗口大小")
    model_backend = infer_model_backend(model_path)
    if model_backend == "sam3":
        list_ = req_json.get("list")
        if list_ is None:
            return fail_api("请上传图片")
        for pair in list_:
            if "first" not in pair or "second" not in pair or pair["first"] == "" or pair["second"] == "":
                return fail_api("请求参数异常")
        try:
            records = _analysis_functions()["sam3_change_detection"](
                model_path,
                up_dir,
                generate_dir,
                list_,
                type_=1,
                prompt_text=req_json.get("prompt_text") or req_json.get("sam3_prompt"),
                confidence_threshold=float(req_json.get("confidence_threshold", 0.5)),
            )
            _analysis_done("change_detection_sam3", started_at, record_count=len(records), model_path=model_path)
            return _transport_success("change_detection", {"records": records})
        except Exception as exc:
            return fail_api(f"SAM3 变化检测失败: {str(exc)}")
    try:
        model_info = _get_model_info(model_path)
        if model_info["_Attributes"]["model_type"] != "change_detector":
            return fail_api("模型类型不正确，请检查")
    except Exception:
        return fail_api("模型不存在，请检查")
    list_ = req_json.get("list")
    step1_ = req_json.get("prehandle", 0)
    step2_ = req_json.get("denoise", 0)
    use_gpu = resolve_paddle_device(req_json)
    if step1_ not in (0, fun_type_1, fun_type_4) or step2_ not in (0, fun_type_3, fun_type_5):
        return fail_api("参数异常")
    if list_ is None:
        return fail_api("请上传图片")
    for pair in list_:
        if "first" not in pair or "second" not in pair or pair["first"] == "" or pair["second"] == "":
            return fail_api("请求参数异常")
    log_debug("模型推理", "change_detection 参数校验通过，开始执行模型推理", model_path=model_path, list_count=len(list_))
    records = _analysis_functions()["change_detection"](
        model_path,
        up_dir,
        generate_dir,
        list_,
        step1_,
        step2_,
        1,
        window_size,
        stride,
        use_gpu=use_gpu,
    )
    _analysis_done("change_detection", started_at, record_count=len(records), model_path=model_path)
    return _transport_success("change_detection", {"records": records})


@analysis_api.route("/object_detection", methods=["POST"])
def object_detection_api():
    req_json = _request_json()
    started_at = time.time()
    _analysis_debug("object_detection", req_json)
    model_path = req_json.get("model_path")
    if not model_path:
        return fail_api("请指定模型路径")
    model_backend = infer_model_backend(model_path)
    if model_backend is None:
        return fail_api("模型不存在，请检查")
    if model_backend not in ("huggingface", "mmrotate"):
        try:
            model_info = _get_model_info(model_path)
            if model_info["_Attributes"]["model_type"] != "detector":
                return fail_api("模型类型不正确，请检查")
        except Exception:
            return fail_api("模型不存在，请检查")
    list_ = req_json.get("list")
    step1_ = req_json.get("prehandle", 0)
    step2_ = req_json.get("denoise", 0)
    use_gpu = resolve_paddle_device(req_json)
    if step1_ not in (0, fun_type_2, fun_type_4) or step2_ not in (0, fun_type_3, fun_type_5):
        return fail_api("参数异常")
    if list_ is None:
        return fail_api("请上传图片")
    records = _analysis_functions()["object_detection"](
        model_path,
        up_dir,
        generate_dir,
        list_,
        step1_,
        step2_,
        2,
        use_gpu=use_gpu,
    )
    _analysis_done("object_detection", started_at, record_count=len(records), model_path=model_path)
    return _transport_success("object_detection", {"records": records})


@analysis_api.route("/small_target_detection", methods=["POST"])
def small_target_detection_api():
    req_json = _request_json()
    started_at = time.time()
    _analysis_debug("small_target_detection", req_json)
    model_path = req_json.get("model_path") or SMALL_TARGET_DETECTION_MODEL_PATH
    if model_path != SMALL_TARGET_DETECTION_MODEL_PATH:
        return fail_api("干扰环境下小尺度目标检测仅支持定向目标检测模型")
    second_image = _small_target_second_image(req_json)
    if not second_image:
        return fail_api("请上传两张图片")
    step1_ = req_json.get("prehandle", 0)
    step2_ = req_json.get("denoise", 0)
    use_gpu = resolve_paddle_device(req_json)
    if step1_ not in (0, fun_type_2, fun_type_4) or step2_ not in (0, fun_type_3, fun_type_5):
        return fail_api("参数异常")
    records = _analysis_functions()["object_detection"](
        model_path,
        up_dir,
        generate_dir,
        [second_image],
        step1_,
        step2_,
        2,
        use_gpu=use_gpu,
    )
    _analysis_done("small_target_detection", started_at, record_count=len(records), model_path=model_path)
    return _transport_success("small_target_detection", {"records": records})


@analysis_api.route("/semantic_segmentation", methods=["POST"])
def semantic_segmentation_api():
    req_json = _request_json()
    started_at = time.time()
    _analysis_debug("semantic_segmentation", req_json)
    model_path = req_json.get("model_path")
    if not model_path:
        return fail_api("请指定模型路径")
    model_backend = infer_model_backend(model_path)
    if model_backend is None:
        return fail_api("模型不存在，请检查")
    if model_backend != "mmsegmentation":
        try:
            model_info = _get_model_info(model_path)
            if model_info["_Attributes"]["model_type"] != "segmenter":
                return fail_api("模型类型不正确，请检查")
        except Exception:
            return fail_api("模型不存在，请检查")
    list_ = req_json.get("list")
    step1_ = req_json.get("prehandle", 0)
    step2_ = req_json.get("denoise", 0)
    use_gpu = resolve_paddle_device(req_json)
    if step1_ not in (0, fun_type_2, fun_type_4) or step2_ not in (0, fun_type_3, fun_type_5):
        return fail_api("参数异常")
    if not list_:
        return fail_api("请上传图片")
    try:
        records = _analysis_functions()["terrain_classification"](
            model_path,
            up_dir,
            generate_dir,
            list_,
            step1_,
            step2_,
            3,
            use_gpu=use_gpu,
        )
        _analysis_done("semantic_segmentation", started_at, record_count=len(records), model_path=model_path)
        return _transport_success("semantic_segmentation", {"records": records})
    except Exception as exc:
        return fail_api(f"推理失败: {str(exc)}")


@analysis_api.route("/classification", methods=["POST"])
def classification_api():
    req_json = _request_json()
    started_at = time.time()
    _analysis_debug("classification", req_json)
    model_path = req_json.get("model_path")
    if not model_path:
        return fail_api("请指定模型路径")
    try:
        model_info = _get_model_info(model_path)
        if model_info["_Attributes"]["model_type"] != "classifier":
            return fail_api("模型类型不正确，请检查")
    except Exception:
        return fail_api("模型不存在，请检查")
    img_list = req_json.get("list")
    if img_list is None:
        return fail_api("请上传图片")
    use_gpu = resolve_paddle_device(req_json)
    records = _analysis_functions()["classification"](model_path, up_dir, img_list, 4, use_gpu=use_gpu)
    _analysis_done("classification", started_at, record_count=len(records), model_path=model_path)
    return _transport_success("classification", {"records": records})


@analysis_api.route("/image_restoration", methods=["POST"])
def image_restoration_api():
    req_json = _request_json()
    started_at = time.time()
    _analysis_debug("image_restoration", req_json)
    model_path = req_json.get("model_path")
    if not model_path:
        return fail_api("请指定模型路径")
    img_list = req_json.get("list")
    if not img_list:
        return fail_api("请上传图片")
    use_gpu = resolve_paddle_device(req_json)
    model_backend = infer_model_backend(model_path)
    if model_backend is None:
        return fail_api("模型不存在，请检查")
    if model_backend != "huggingface":
        try:
            model_info = _get_model_info(model_path)
            if model_info["_Attributes"]["model_type"] != "restorer":
                return fail_api("模型类型不正确，请检查")
        except Exception:
            return fail_api("模型不存在，请检查")
    try:
        records = _analysis_functions()["image_restoration"](
            model_path,
            up_dir,
            generate_dir,
            img_list,
            5,
            use_gpu=use_gpu,
        )
        _analysis_done("image_restoration", started_at, record_count=len(records), model_path=model_path)
        return _transport_success("image_restoration", {"records": records})
    except Exception as exc:
        return fail_api(f"推理失败: {str(exc)}")


@analysis_api.route("/registration", methods=["POST"])
def registration_api():
    req_json = _request_json()
    started_at = time.time()
    _analysis_debug("registration", req_json)
    list_ = req_json.get("list")
    model_path = req_json.get("model_path", "backend/model/registration/auto")
    if not list_:
        return fail_api("请上传图片")
    for pair in list_:
        if "first" not in pair or "second" not in pair or not pair["first"] or not pair["second"]:
            return fail_api("请求参数异常")
    try:
        records = _analysis_functions()["registration"](model_path, up_dir, generate_dir, list_, type_=6)
        return _transport_success(
            "registration",
            {
                "records": records,
                "summary": {
                    "total_pairs": len(list_),
                    "success_pairs": len(records),
                    "failed_pairs": len(list_) - len(records),
                    "model_path": model_path,
                },
            },
            msg=f"配准完成，共 {len(records)}/{len(list_)} 对成功",
        )
    except Exception as exc:
        return fail_api(f"配准失败: {str(exc)}")
    finally:
        try:
            _analysis_done("registration", started_at, record_count=len(records) if 'records' in locals() else 0, model_path=model_path)
        except Exception:
            pass


@analysis_api.route("/tracking", methods=["POST"])
def tracking_api():
    req_json = _request_json()
    started_at = time.time()
    _analysis_debug("tracking", req_json)
    model_path, list_, rect, error = _validate_tracking_payload(req_json)
    if error:
        return error
    try:
        result = _analysis_functions()["tracking"](
            model_path,
            up_dir,
            generate_dir,
            list_,
            rect,
            type_=7,
            prompt_text=req_json.get("prompt_text") or req_json.get("sam3_prompt"),
        )
        _analysis_done("tracking", started_at, record_count=len(result) if hasattr(result, "__len__") else -1, model_path=model_path)
        return _transport_success("tracking", result)
    except Exception as exc:
        return fail_api(f"跟踪失败: {str(exc)}")


@analysis_api.route("/tracking/async", methods=["POST", "OPTIONS"])
def tracking_async_api():
    if request.method == "OPTIONS":
        return success_api(msg="ok", data={})

    req_json = _request_json()
    started_at = time.time()
    _analysis_debug("tracking_async", req_json)
    model_path, list_, rect, error = _validate_tracking_payload(req_json)
    if error:
        return error

    job_id = uuid.uuid4().hex
    now = time.time()
    with _TRACKING_JOB_LOCK:
        _cleanup_tracking_jobs(now)
        _TRACKING_JOBS[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "message": "目标跟踪任务已提交",
            "model_path": model_path,
            "created_at": now,
            "updated_at": now,
            "expires_in_seconds": TRACKING_JOB_TTL_SECONDS,
        }

    chunk_size = normalize_chunk_size(request.headers.get("X-Geoview-Chunk-Size") or request.args.get("chunk_size"))
    future = _TRACKING_EXECUTOR.submit(
        _run_tracking_job,
        current_app._get_current_object(),
        job_id,
        model_path,
        list_,
        rect,
        chunk_size,
        req_json.get("prompt_text") or req_json.get("sam3_prompt"),
    )
    with _TRACKING_JOB_LOCK:
        if job_id in _TRACKING_JOBS:
            _TRACKING_JOBS[job_id]["future"] = future
    _analysis_done("tracking_async", started_at, job_id=job_id, model_path=model_path)
    return success_api(msg="目标跟踪任务已提交", data=_tracking_job_snapshot(job_id))


@analysis_api.route("/tracking/jobs/<job_id>", methods=["GET", "OPTIONS"])
def tracking_job_status_api(job_id):
    if request.method == "OPTIONS":
        return success_api(msg="ok", data={})

    job = _tracking_job_snapshot(job_id)
    if not job:
        return fail_api("目标跟踪任务不存在或已过期")
    if job.get("status") in {"queued", "running"}:
        started_at = job.get("started_at") or job.get("created_at") or time.time()
        job["elapsed_sec"] = round(time.time() - started_at, 1)
    return success_api(msg=job.get("message") or "成功", data=job)


@analysis_api.route("/histogram_match", methods=["POST"])
def pre_handle():
    req_json = _request_json()
    started_at = time.time()
    _analysis_debug("histogram_match", req_json)
    list_ = req_json.get("list")
    step1_ = req_json.get("prehandle")
    if list_ is None:
        return fail_api("请上传图片")
    if step1_ not in (1, 4):
        return fail_api("请求参数异常")
    for pair in list_:
        if "first" not in pair or "second" not in pair or pair["first"] == "" or pair["second"] == "":
            return fail_api("请求参数异常")
        pair["first"] = img_url_handle(pair["first"])
        pair["second"] = img_url_handle(pair["second"])
    if step1_ == fun_type_1:
        match = histogram_match.gram_match(list_, up_dir, generate_dir)
    else:
        match = []
        for pair in list_:
            temps = [pair["first"], pair["second"]]
            imgs1 = _analysis_functions()["handle"](fun_type_4, temps, up_dir, generate_dir)
            match.append({"first": pair["first"], "first1": imgs1[0], "second": pair["second"], "second1": imgs1[1]})
    _analysis_done("histogram_match", started_at, record_count=len(match))
    return _transport_success("histogram_match", match)


@analysis_api.route("/image_pre", methods=["POST"])
def image_pre():
    req_json = _request_json()
    started_at = time.time()
    _analysis_debug("image_pre", req_json)
    list_ = req_json.get("list")
    step1_ = req_json.get("prehandle")
    type_ = req_json.get("type")
    if list_ is None:
        return fail_api("请上传图片")
    if step1_ not in (2, 4):
        return fail_api("请求参数异常")
    imgs = []
    if type_ == 1:
        for pair in list_:
            if "first" not in pair or "second" not in pair or pair["first"] == "" or pair["second"] == "":
                return fail_api("请求参数异常")
        for pair in list_:
            temps = [img_url_handle(pair["first"]), img_url_handle(pair["second"])]
            imgs1 = _analysis_functions()["handle"](fun_type_4, temps, up_dir, generate_dir)
            imgs.append({"first": pair["first"], "first1": imgs1[0], "second": pair["second"], "second1": imgs1[1]})
    else:
        temps = [img_url_handle(pair) for pair in list_]
        imgs = _analysis_functions()["handle"](step1_, temps, up_dir, generate_dir)
        for i, img in enumerate(imgs):
            imgs[i] = f"/api/file/assets/photos/res/{img}"
    _analysis_done("image_pre", started_at, record_count=len(imgs))
    return _transport_success("image_pre", imgs)
