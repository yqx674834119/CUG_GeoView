import json
import time

from flask import Blueprint, request

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
from applications.common.utils.http import fail_api, success_api
from applications.common.utils.upload import img_url_handle
from applications.image_processing import histogram_match

analysis_api = Blueprint("analysis_api", __name__, url_prefix="/api/analysis")


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
    try:
        model_info = _get_model_info(model_path)
        if model_info["_Attributes"]["model_type"] != "change_detector":
            return fail_api("模型类型不正确，请检查")
    except Exception:
        return fail_api("模型不存在，请检查")
    list_ = req_json.get("list")
    step1_ = req_json.get("prehandle", 0)
    step2_ = req_json.get("denoise", 0)
    if step1_ not in (0, fun_type_1, fun_type_4) or step2_ not in (0, fun_type_3, fun_type_5):
        return fail_api("参数异常")
    if list_ is None:
        return fail_api("请上传图片")
    for pair in list_:
        if "first" not in pair or "second" not in pair or pair["first"] == "" or pair["second"] == "":
            return fail_api("请求参数异常")
    log_debug("模型推理", "change_detection 参数校验通过，开始执行模型推理", model_path=model_path, list_count=len(list_))
    records = _analysis_functions()["change_detection"](model_path, up_dir, generate_dir, list_, step1_, step2_, 1, window_size, stride)
    _analysis_done("change_detection", started_at, record_count=len(records), model_path=model_path)
    return success_api(data={"records": records})


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
    if step1_ not in (0, fun_type_2, fun_type_4) or step2_ not in (0, fun_type_3, fun_type_5):
        return fail_api("参数异常")
    if list_ is None:
        return fail_api("请上传图片")
    records = _analysis_functions()["object_detection"](model_path, up_dir, generate_dir, list_, step1_, step2_, 2)
    _analysis_done("object_detection", started_at, record_count=len(records), model_path=model_path)
    return success_api(data={"records": records})


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
    if step1_ not in (0, fun_type_2, fun_type_4) or step2_ not in (0, fun_type_3, fun_type_5):
        return fail_api("参数异常")
    if not list_:
        return fail_api("请上传图片")
    try:
        records = _analysis_functions()["terrain_classification"](model_path, up_dir, generate_dir, list_, step1_, step2_, 3)
        _analysis_done("semantic_segmentation", started_at, record_count=len(records), model_path=model_path)
        return success_api(data={"records": records})
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
    records = _analysis_functions()["classification"](model_path, up_dir, img_list, 4)
    _analysis_done("classification", started_at, record_count=len(records), model_path=model_path)
    return success_api(data={"records": records})


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
        records = _analysis_functions()["image_restoration"](model_path, up_dir, generate_dir, img_list, 5)
        _analysis_done("image_restoration", started_at, record_count=len(records), model_path=model_path)
        return success_api(data={"records": records})
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
        return success_api(
            msg=f"配准完成，共 {len(records)}/{len(list_)} 对成功",
            data={
                "records": records,
                "summary": {
                    "total_pairs": len(list_),
                    "success_pairs": len(records),
                    "failed_pairs": len(list_) - len(records),
                    "model_path": model_path,
                },
            },
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
    model_path = req_json.get("model_path", "backend/model/tracking/auto")
    list_ = req_json.get("list")
    rect = req_json.get("rect")
    if not list_:
        return fail_api("请提供上传后的图像序列或单个视频文件")
    from applications.interface.tracking import requires_initial_rect

    try:
        need_initial_rect = requires_initial_rect(model_path)
    except Exception as exc:
        return fail_api(f"跟踪失败: {str(exc)}")
    if need_initial_rect:
        if not rect or len(rect) != 4:
            return fail_api("请提供初始跟踪框")
        try:
            rect = [int(value) for value in rect]
        except Exception:
            return fail_api("初始跟踪框格式错误")
        if rect[2] <= 0 or rect[3] <= 0:
            return fail_api("初始跟踪框宽高必须大于0")
    elif rect:
        try:
            rect = [int(value) for value in rect]
        except Exception:
            rect = None
    try:
        result = _analysis_functions()["tracking"](model_path, up_dir, generate_dir, list_, rect, type_=7)
        _analysis_done("tracking", started_at, record_count=len(result) if hasattr(result, "__len__") else -1, model_path=model_path)
        return success_api(data=result)
    except Exception as exc:
        return fail_api(f"跟踪失败: {str(exc)}")


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
    return success_api(data=match)


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
    return success_api(data=imgs)
