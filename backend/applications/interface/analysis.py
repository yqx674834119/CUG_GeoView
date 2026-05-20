import copy
import json
import os
import time

import cv2
import numpy as np

from applications.common.path_global import fun_type_1, fun_type_2, fun_type_3, fun_type_4, fun_type_5, \
    fun_type_6, fun_type_7, generate_url, fun_type_8, up_url, generate_dir
from applications.common.visualization import (
    attach_visual_payload,
    build_visual_payload,
    extract_binary_regions,
    extract_class_regions,
    image_size_from_file,
    normalize_analysis_record,
    resolve_generated_path,
)
from applications.common.utils.upload import img_url_handle
from applications.common.storage import mirror_upload_tree
from applications.extensions import db
from applications.image_processing import histogram_match
from applications.image_processing.CLAHE import CLAHE
from applications.image_processing.gaussian_blur import gaussian_blur
from applications.image_processing.hole import hole_fill
from applications.image_processing.median_blur import median_blur
from applications.image_processing.render import batch_render
from applications.image_processing.render_seg import batch_render_seg
from applications.image_processing.resize import resize
from applications.image_processing.sharpen import sharpen
from applications.interface import change_detection as CD
from applications.interface import classification as C
from applications.interface import object_detection as OD
from applications.interface import semantic_segmentation as SS
from applications.interface import image_restoration as IR
from applications.interface.compute_variation import compute_variation
from applications.interface.draw_mask import draw_masks
from applications.models.analysis import Analysis

PADDLE_SEGMENTATION_CLASSES = ["cloud", "shadow", "snow", "water", "land"]
PADDLE_SEGMENTATION_PALETTE = [
    [0, 0, 0],
    [128, 0, 0],
    [0, 128, 0],
    [128, 128, 0],
    [0, 0, 128],
]
MMSEG_SEGMENTATION_CLASSES = ["grassland", "forest", "building", "road", "bareground", "water"]
MMSEG_SEGMENTATION_PALETTE = [
    [0, 255, 0],
    [0, 128, 0],
    [255, 0, 0],
    [255, 255, 0],
    [255, 0, 255],
    [0, 191, 255],
]


def _compact_list(values, max_items=5):
    items = list(values or [])
    return {
        "count": len(items),
        "sample": items[:max_items],
    }


def _compact_results(results, max_items=5):
    compact = []
    for item in list(results or [])[:max_items]:
        if isinstance(item, dict):
            compact.append({
                key: item.get(key)
                for key in ("after_img", "mask_path", "image_size", "class_names")
                if item.get(key) not in (None, "", [])
            })
        else:
            compact.append(item)
    return {
        "count": len(results or []),
        "sample": compact,
    }


def _compact_records(records, max_items=5):
    compact = []
    for item in list(records or [])[:max_items]:
        compact.append({
            "id": item.get("id"),
            "type": item.get("type"),
            "before_img": item.get("before_img"),
            "before_img1": item.get("before_img1"),
            "after_img": item.get("after_img"),
        })
    return {
        "count": len(records or []),
        "sample": compact,
    }


def _inference_log(scope, stage, **fields):
    try:
        payload = json.dumps(fields, ensure_ascii=False, default=str, separators=(",", ":"))
    except Exception:
        payload = str(fields)
    print(f"[GeoView推理][{scope}] {stage} {payload}", flush=True)


def save_analysis(type_,
                  pic1,
                  retPic,
                  pic2="",
                  data="{}",
                  is_hole=False,
                  checked="0,0"):
    analysis = Analysis()

    analysis.type = type_
    analysis.before_img = pic1
    analysis.before_img1 = pic2
    analysis.after_img = retPic
    analysis.data = data
    analysis.is_hole = is_hole
    analysis.checked = checked
    db.session.add(analysis)
    db.session.commit()
    mirror_upload_tree()
    payload = {
        "id": analysis.id,
        "type": analysis.type,
        "before_img": analysis.before_img,
        "before_img1": analysis.before_img1,
        "after_img": analysis.after_img,
        "data": json.loads(analysis.data) if analysis.data else {},
        "is_hole": analysis.is_hole,
        "checked": analysis.checked,
        "create_time": analysis.create_time.isoformat() if analysis.create_time else None,
    }
    return normalize_analysis_record(payload)


def _legacy_asset_bundle(before_img, after_img="", before_img1="", **extra):
    bundle = {
        "source_primary": before_img,
        "source_secondary": before_img1,
        "primary_result": after_img,
    }
    for key, value in extra.items():
        if value not in (None, ""):
            bundle[key] = value
    return bundle


def _source_entry(asset_path, absolute_path=None, filename=None):
    entry = {"asset_path": asset_path}
    if filename:
        entry["filename"] = filename
    if absolute_path:
        entry.update(image_size_from_file(absolute_path))
    return entry


def _label_histogram(detections):
    histogram = {}
    for item in detections:
        label = item.get("label") or "unknown"
        histogram[label] = histogram.get(label, 0) + 1
    return dict(sorted(histogram.items()))


def _score_stats(detections):
    scores = [float(item.get("score", 0.0)) for item in detections if item.get("score") is not None]
    if not scores:
        return {"mean_score": 0.0, "max_score": 0.0, "min_score": 0.0}
    return {
        "mean_score": round(float(sum(scores) / len(scores)), 4),
        "max_score": round(float(max(scores)), 4),
        "min_score": round(float(min(scores)), 4),
    }


def _round_matrix(matrix):
    if matrix is None:
        return None
    array = np.asarray(matrix, dtype=float)
    return json.loads(json.dumps(np.round(array, 6).tolist()))


def _transform_corners(matrix, transform_type, width, height):
    if matrix is None or width <= 0 or height <= 0:
        return []
    source = np.array([
        [0.0, 0.0],
        [float(width), 0.0],
        [float(width), float(height)],
        [0.0, float(height)],
    ], dtype=np.float32)
    array = np.asarray(matrix, dtype=np.float32)
    try:
        if transform_type == "homography" and array.shape == (3, 3):
            projected = cv2.perspectiveTransform(source.reshape(-1, 1, 2), array).reshape(-1, 2)
        elif array.shape == (2, 3):
            projected = cv2.transform(source.reshape(-1, 1, 2), array).reshape(-1, 2)
        else:
            return []
    except Exception:
        return []
    return [[round(float(point[0]), 3), round(float(point[1]), 3)] for point in projected]


def _load_mask_array(path):
    if not path or not os.path.exists(path):
        return None
    return cv2.imread(path, cv2.IMREAD_UNCHANGED)


def _build_restoration_metrics(before_path, after_path):
    before = image_size_from_file(before_path)
    after = image_size_from_file(after_path)
    metrics = {
        "input_width": before.get("width"),
        "input_height": before.get("height"),
        "output_width": after.get("width"),
        "output_height": after.get("height"),
    }
    if before.get("width") and after.get("width"):
        metrics["scale_x"] = round(after["width"] / max(before["width"], 1), 4)
    if before.get("height") and after.get("height"):
        metrics["scale_y"] = round(after["height"] / max(before["height"], 1), 4)
    return metrics


def change_detection(model_path,
                     data_path,
                     out_dir,
                     names,
                     step1,
                     step2,
                     type_,
                     window_size=256,
                     stride=128,
                     use_gpu=True):
    """
    变化检测
    :param model_path: 静态图模型路径
    :param data_path: 图片数据路径，路径中有名称为A和B的两个文件夹分别存储不同时相的图片（1024，1024），且相应图片名称相同
    :param out_dir:图片保存路径
    :param window_size:滑窗大小
    :param stride:步长
    :return:
    """
    print("变化检测----------------->start")
    started_at = time.time()
    _inference_log("变化检测", "request", model_path=model_path, prehandle=step1, denoise=step2, window_size=window_size, stride=stride, use_gpu=use_gpu, pairs=_compact_list(names), data_path=data_path, output_dir=out_dir)
    imgs = list()
    imgs1 = list()
    temp_names = copy.deepcopy(names)
    for pair in names:
        pair["first"] = img_url_handle(pair["first"])
        pair['second'] = img_url_handle(pair['second'])
        imgs.append(pair["first"])
        imgs1.append(pair["second"])
    _inference_log("变化检测", "input-normalized", first_files=_compact_list(imgs), second_files=_compact_list(imgs1))

    # 1.直图or锐化
    if step1 != 0:
        if step1 == fun_type_1:
            imgs = handle(step1, names, data_path, data_path)
        else:
            imgs = handle(step1, imgs, data_path, data_path)
            imgs1 = handle(step1, imgs1, data_path, data_path)
        _inference_log("变化检测", "preprocess-primary", mode=step1, first_files=_compact_list(imgs), second_files=_compact_list(imgs1))
    # 2.平滑or滤波
    if step2 != 0:
        imgs = handle(step2, imgs, data_path, data_path)
        imgs1 = handle(step2, imgs1, data_path, data_path)
        _inference_log("变化检测", "preprocess-denoise", mode=step2, first_files=_compact_list(imgs), second_files=_compact_list(imgs1))

    # 3.resize
    resizes = resize(data_path, data_path, imgs, mode=0)
    resizes1 = resize(data_path, data_path, imgs1, mode=0)
    _inference_log("变化检测", "preprocess-resize", first_files=_compact_list(resizes), second_files=_compact_list(resizes1))
    i = 0
    for pair in names:
        pair["first"] = resizes[i]
        pair["second"] = resizes1[i]
        i += 1
    # 3.检测对比，带地址的文件名，纯文件名
    _inference_log("变化检测", "model-execute-start", model_path=model_path, pairs=_compact_list(names), window_size=window_size, stride=stride)
    retPics, filenames = CD.execute(
        model_path,
        data_path,
        out_dir,
        names,
        window_size=window_size,
        stride=stride,
        use_gpu=use_gpu)
    _inference_log("变化检测", "model-execute-done", elapsed_sec=round(time.time() - started_at, 3), result_images=_compact_list(retPics), mask_files=_compact_list(filenames))
    # 4.检测渲染
    res = handle(fun_type_6, filenames, out_dir, out_dir)
    _inference_log("变化检测", "render-done", rendered=_compact_list(res))
    # 5.入库
    records = []
    i = 0
    for pair in temp_names:
        first_ = up_url + resizes[i]
        second_ = pair['second']
        retPic = retPics[i]
        rendered_mask_path = os.path.join(out_dir, filenames[i])
        mask, count, areas = draw_masks(rendered_mask_path)
        mask_name = os.path.splitext(filenames[i])[0] + "_mask.png"
        mask_full_path = os.path.join(out_dir, mask_name)
        cv2.imwrite(mask_full_path, mask)
        res[i]["mask"] = generate_url + mask_name
        res[i]["count"] = count
        
        # Calculate statistics
        total_area = sum(areas) if areas else 0
        avg_area = total_area / count if count > 0 else 0
        
        # Categorize changes
        small_changes = len([a for a in areas if a < 100])
        medium_changes = len([a for a in areas if 100 <= a <= 500])
        large_changes = len([a for a in areas if a > 500])
        
        res[i]["total_area"] = total_area
        res[i]["avg_area"] = avg_area
        res[i]["size_distribution"] = {
            "small": small_changes,
            "medium": medium_changes,
            "large": large_changes
        }
        res[i]["top_changes"] = sorted(areas, reverse=True)[:10] if areas else []
        
        res[i]["fractional_variation"] = compute_variation(
            os.path.join(out_dir, filenames[i]))
        after_img, data = hole_handle(out_dir, out_dir + "hole/", [retPic])
        res[i]["hole"] = after_img
        res[i]["hole_style"] = handle(
            fun_type_6, [os.path.basename(after_img)],
            out_dir + "hole/",
            out_dir + "hole/",
            prefix="hole")[0]
        mask, count, areas_hole = draw_masks(
            os.path.join(out_dir + "hole/", os.path.basename(after_img)))
        cv2.imwrite(
            os.path.join(
                out_dir + "hole/",
                os.path.splitext(os.path.basename(after_img))[0] + "_mask.png"),
            mask)
        res[i]["mask_hole"] = generate_url + "hole/" + os.path.splitext(
            os.path.basename(after_img))[0] + "_mask.png"
        res[i]["count_hole"] = count
        
        # Calculate statistics for hole-filled result
        total_area_hole = sum(areas_hole) if areas_hole else 0
        avg_area_hole = total_area_hole / count if count > 0 else 0
        
        small_changes_hole = len([a for a in areas_hole if a < 100])
        medium_changes_hole = len([a for a in areas_hole if 100 <= a <= 500])
        large_changes_hole = len([a for a in areas_hole if a > 500])
        
        res[i]["total_area_hole"] = total_area_hole
        res[i]["avg_area_hole"] = avg_area_hole
        res[i]["size_distribution_hole"] = {
            "small": small_changes_hole,
            "medium": medium_changes_hole,
            "large": large_changes_hole
        }
        res[i]["top_changes_hole"] = sorted(areas_hole, reverse=True)[:10] if areas_hole else []

        res[i]["fractional_variation_hole"] = compute_variation(
            os.path.join(generate_dir + "hole/", os.path.basename(after_img)))
        primary_regions = extract_binary_regions(_load_mask_array(mask_full_path))
        hole_mask_full_path = os.path.join(
            out_dir + "hole/",
            os.path.splitext(os.path.basename(after_img))[0] + "_mask.png")
        hole_regions = extract_binary_regions(_load_mask_array(hole_mask_full_path))
        payload = build_visual_payload(
            analysis_type="变化检测",
            renderer="change_detection",
            source={
                "primary": _source_entry(first_, os.path.join(data_path, resizes[i]), filenames[i]),
                "secondary": _source_entry(second_, os.path.join(data_path, img_url_handle(second_)), img_url_handle(second_)),
            },
            result={
                "regions": primary_regions,
                "mask_path": res[i]["mask"],
                "hole_regions": hole_regions,
                "mask_hole_path": res[i]["mask_hole"],
            },
            metrics={
                "change_count": count,
                "total_area": total_area,
                "avg_area": round(avg_area, 2),
                "size_distribution": res[i]["size_distribution"],
                "fractional_variation": res[i]["fractional_variation"],
                "change_count_hole": res[i]["count_hole"],
                "total_area_hole": total_area_hole,
                "avg_area_hole": round(avg_area_hole, 2),
                "size_distribution_hole": res[i]["size_distribution_hole"],
                "fractional_variation_hole": res[i]["fractional_variation_hole"],
            },
            legacy_assets=_legacy_asset_bundle(
                before_img=first_,
                before_img1=second_,
                after_img=retPic,
                hole_path=after_img,
                rendered_path=res[i].get("hole_style"),
            ),
        )
        data = json.dumps(attach_visual_payload(res[i], payload), ensure_ascii=False)
        records.append(save_analysis(
            type_,
            first_,
            retPic,
            pic2=second_,
            data=data,
            checked=str(step1) + "," + str(step2),
            is_hole=True))
        i += 1
    _inference_log("变化检测", "records-saved", elapsed_sec=round(time.time() - started_at, 3), records=_compact_records(records))
    print("变化检测----------------->end")
    return records


def hole_handle(data_path, out_dir, names):
    url_handle(names)
    # 1.孔洞处理
    res = handle(fun_type_8, names, data_path, out_dir)
    # 4.检测渲染
    res1 = handle(fun_type_6, res, out_dir, out_dir)
    return generate_url + "hole/" + res[0], res1[0]


def url_handle(imgs):
    j = 0
    for pair in imgs:
        imgs[j] = img_url_handle(pair)
        j += 1


def object_detection(model_path, data_path, out_dir, names, step1, step2,
                     type_, use_gpu=True):
    """
    目标检测
    :param model_path:
    :param data_path:
    :param out_dir:
    :return:
    """
    print("目标检测----------------->start", flush=True)
    started_at = time.time()
    _inference_log("目标检测", "request", model_path=model_path, prehandle=step1, denoise=step2, use_gpu=use_gpu, input=_compact_list(names), data_path=data_path, output_dir=out_dir)
    imgs = list()
    temp_names = copy.deepcopy(names)
    for j, pair in enumerate(names):
        names[j] = img_url_handle(pair)
        imgs.append(names[j])
    _inference_log("目标检测", "input-normalized", files=_compact_list(imgs))

    # 3.resize
    resizes = resize(data_path, data_path, imgs, mode=3)
    for i, pair in enumerate(imgs):
        imgs[i] = resizes[i]
    _inference_log("目标检测", "preprocess-resize", files=_compact_list(resizes))

    # 1.CLAHE or 锐化
    if step1 != 0:
        imgs = handle(step1, imgs, data_path, data_path)
        _inference_log("目标检测", "preprocess-primary", mode=step1, files=_compact_list(imgs))
    # 2.平滑or滤波
    if step2 != 0:
        imgs = handle(step2, imgs, data_path, data_path)
        _inference_log("目标检测", "preprocess-denoise", mode=step2, files=_compact_list(imgs))

    # 4. 目标检测
    _inference_log("目标检测", "model-execute-start", model_path=model_path, files=_compact_list(imgs))
    retPics = OD.execute(model_path, data_path, out_dir, imgs, use_gpu=use_gpu)
    _inference_log("目标检测", "model-execute-done", elapsed_sec=round(time.time() - started_at, 3), outputs=_compact_results(retPics))
    # 5.入库
    records = []
    for i, pair in enumerate(resizes):
        first_ = up_url + pair
        result_item = retPics[i] if i < len(retPics) else {}
        if isinstance(result_item, str):
            result_item = {"after_img": result_item, "detections": []}
        retPic = result_item.get("after_img", "")
        detections = result_item.get("detections", []) or []
        payload = build_visual_payload(
            analysis_type="目标检测",
            renderer="object_detection",
            source={
                "primary": _source_entry(first_, os.path.join(data_path, pair), pair),
            },
            result={
                "detections": detections,
                "image_size": result_item.get("image_size") or image_size_from_file(os.path.join(data_path, pair)),
            },
            metrics={
                "detection_count": len(detections),
                "label_histogram": _label_histogram(detections),
                **_score_stats(detections),
            },
            legacy_assets=_legacy_asset_bundle(before_img=first_, after_img=retPic),
        )
        data = json.dumps(attach_visual_payload({}, payload), ensure_ascii=False)
        records.append(save_analysis(
            type_,
            first_,
            retPic,
            pic2="",
            data=data,
            checked=str(step1) + "," + str(step2)))
    _inference_log("目标检测", "records-saved", elapsed_sec=round(time.time() - started_at, 3), records=_compact_records(records))
    print("目标检测----------------->end", flush=True)
    return records


def terrain_classification(model_path, data_path, out_dir, names, step1, step2,
                           type_, use_gpu=True):
    """
    地物分类
    :param model_path:
    :param data_path:
    :param out_dir:
    :return:
    """
    print("地物分类----------------->start")
    started_at = time.time()
    _inference_log("地物分类", "request", model_path=model_path, prehandle=step1, denoise=step2, use_gpu=use_gpu, input=_compact_list(names), data_path=data_path, output_dir=out_dir)
    imgs = list()
    temp_names = copy.deepcopy(names)
    for j, pair in enumerate(names):
        names[j] = img_url_handle(pair)
        imgs.append(names[j])
    _inference_log("地物分类", "input-normalized", files=_compact_list(imgs))
    # 3.resize
    resizes = resize(data_path, data_path, imgs, mode=2)
    for i, pair in enumerate(imgs):
        imgs[i] = resizes[i]
    _inference_log("地物分类", "preprocess-resize", files=_compact_list(resizes))

    # 1.CLAHE or 锐化
    if step1 != 0:
        imgs = handle(step1, imgs, data_path, data_path)
        _inference_log("地物分类", "preprocess-primary", mode=step1, files=_compact_list(imgs))
    # 2.平滑or滤波
    if step2 != 0:
        imgs = handle(step2, imgs, data_path, data_path)
        _inference_log("地物分类", "preprocess-denoise", mode=step2, files=_compact_list(imgs))

    # 4. 地物分类
    _inference_log("地物分类", "model-execute-start", model_path=model_path, files=_compact_list(imgs))
    retPics = SS.execute(model_path, data_path, out_dir, imgs, use_gpu=use_gpu)
    _inference_log("地物分类", "model-execute-done", elapsed_sec=round(time.time() - started_at, 3), outputs=_compact_results(retPics))
    
    # 5.入库
    records = []
    for i, pair in enumerate(resizes):
        first_ = up_url + pair
        result_item = retPics[i] if i < len(retPics) else {}
        if isinstance(result_item, str):
            result_item = {"after_img": result_item}
        retPic = result_item.get("after_img", "")
        mask_path = result_item.get("mask_path")
        mask_abs_path = resolve_generated_path(mask_path) if mask_path else ""
        class_names = result_item.get("class_names") or (
            MMSEG_SEGMENTATION_CLASSES if str(retPic).endswith(".png") and "pred_" in str(retPic)
            else PADDLE_SEGMENTATION_CLASSES
        )
        palette = result_item.get("palette") or (
            MMSEG_SEGMENTATION_PALETTE if class_names == MMSEG_SEGMENTATION_CLASSES
            else PADDLE_SEGMENTATION_PALETTE
        )
        segmentation_data = extract_class_regions(
            _load_mask_array(mask_abs_path),
            class_names=class_names,
            palette=palette,
        ) if mask_abs_path else {"classes": [], "totals": {}}
        payload = build_visual_payload(
            analysis_type="地物分类",
            renderer="semantic_segmentation",
            source={"primary": _source_entry(first_, os.path.join(data_path, pair), pair)},
            result={
                "classes": segmentation_data.get("classes", []),
                "mask_path": mask_path,
                "image_size": segmentation_data.get("image_size") or image_size_from_file(os.path.join(data_path, pair)),
            },
            metrics={
                "class_totals": segmentation_data.get("totals", {}),
                "pixel_count": segmentation_data.get("pixel_count"),
            },
            legacy_assets=_legacy_asset_bundle(before_img=first_, after_img=retPic),
        )
        data = json.dumps(attach_visual_payload({}, payload), ensure_ascii=False)
        records.append(save_analysis(
            type_,
            first_,
            retPic,
            pic2="",
            data=data,
            checked=str(step1) + "," + str(step2)))
    _inference_log("地物分类", "records-saved", elapsed_sec=round(time.time() - started_at, 3), records=_compact_records(records))
    print("地物分类----------------->end")
    return records


def classification(model_path, data_path, names, type, use_gpu=True):
    """
    场景分类
    :param model_path: 模型存储目录
    :param data_path: 待推理图片存储目录
    :param names: 待推理图片列表
    :param type: 功能类别
    :return:
    """
    print("场景分类----------------->start")
    started_at = time.time()
    _inference_log("场景分类", "request", model_path=model_path, use_gpu=use_gpu, input=_compact_list(names), data_path=data_path)
    imgs = list()
    for j, pair in enumerate(names):
        names[j] = img_url_handle(pair)
        imgs.append(names[j])
    _inference_log("场景分类", "input-normalized", files=_compact_list(imgs))
    # 1. 场景分类
    _inference_log("场景分类", "model-execute-start", model_path=model_path, files=_compact_list(imgs))
    result = C.execute(model_path, data_path, imgs, use_gpu=use_gpu)
    _inference_log("场景分类", "model-execute-done", elapsed_sec=round(time.time() - started_at, 3), outputs=_compact_list(result))
    # 2.入库
    records = []
    for i, pair in enumerate(names):
        first_ = up_url + pair
        ret = {}
        for j in range(0, len(result[i]["label_names_map"])):
            ret[result[i]["label_names_map"][j]] = result[i]["scores_map"][j]
        score_items = [
            {"label": label, "score": float(score)}
            for label, score in ret.items()
        ]
        score_items.sort(key=lambda item: item["score"], reverse=True)
        payload = build_visual_payload(
            analysis_type="场景分类",
            renderer="scene_classification",
            source={"primary": _source_entry(first_, os.path.join(data_path, pair), pair)},
            result={"scores": score_items},
            metrics={
                "top_label": score_items[0]["label"] if score_items else "",
                "top_score": score_items[0]["score"] if score_items else 0.0,
            },
            legacy_assets=_legacy_asset_bundle(before_img=first_, after_img=""),
        )
        data = json.dumps(attach_visual_payload(ret, payload), ensure_ascii=False)
        records.append(save_analysis(type, first_, "", pic2="", data=data))
    _inference_log("场景分类", "records-saved", elapsed_sec=round(time.time() - started_at, 3), records=_compact_records(records))
    print("场景分类----------------->end")
    return records


def image_restoration(model_path, data_path, out_dir, names, type_, use_gpu=True):
    """
    图像复原
    :param model_path:
    :param data_path:
    :param out_dir:
    :return:
    """
    print("图像复原----------------->start")
    started_at = time.time()
    _inference_log("图像复原", "request", model_path=model_path, use_gpu=use_gpu, input=_compact_list(names), data_path=data_path, output_dir=out_dir)
    imgs = list()
    for j, pair in enumerate(names):
        names[j] = img_url_handle(pair)
        imgs.append(names[j])
    _inference_log("图像复原", "input-normalized", files=_compact_list(imgs))

    # 1. 图像复原
    _inference_log("图像复原", "model-execute-start", model_path=model_path, files=_compact_list(imgs))
    retPics = IR.execute(model_path, data_path, out_dir, imgs, use_gpu=use_gpu)
    _inference_log("图像复原", "model-execute-done", elapsed_sec=round(time.time() - started_at, 3), outputs=_compact_results(retPics))
    # 2.入库
    records = []
    for i, pair in enumerate(names):
        first_ = up_url + pair
        result_item = retPics[i] if i < len(retPics) else {}
        if isinstance(result_item, str):
            result_item = {"after_img": result_item}
        retPic = result_item.get("after_img", "")
        before_path = os.path.join(data_path, pair)
        after_path = resolve_generated_path(retPic)
        metrics = _build_restoration_metrics(before_path, after_path)
        metrics.update(result_item.get("metrics") or {})
        payload = build_visual_payload(
            analysis_type="影像超分重建",
            renderer="image_restoration",
            source={"primary": _source_entry(first_, before_path, pair)},
            result={
                "simulation_mode": "local_interpolation_preview",
                "output_size": image_size_from_file(after_path),
            },
            metrics=metrics,
            capabilities={
                "frontend_render_exact": False,
                "frontend_render_note": "前端展示后端生成的结果资源 URL。",
            },
            legacy_assets=_legacy_asset_bundle(before_img=first_, after_img=retPic),
        )
        data = json.dumps(attach_visual_payload({}, payload), ensure_ascii=False)
        records.append(save_analysis(type_, first_, retPic, pic2="", data=data))
    _inference_log("图像复原", "records-saved", elapsed_sec=round(time.time() - started_at, 3), records=_compact_records(records))
    print("图像复原----------------->end")
    return records


def registration(model_path, data_path, out_dir, names, type_):
    """
    多模态自动配准
    """
    import applications.interface.registration as REG
    
    print("自动配准----------------->start")
    started_at = time.time()
    _inference_log("自动配准", "request", model_path=model_path, input=_compact_list(names), data_path=data_path, output_dir=out_dir)
    for j, pair in enumerate(names):
        names[j]["first"] = img_url_handle(pair["first"])
        names[j]["second"] = img_url_handle(pair["second"])
    _inference_log("自动配准", "input-normalized", pairs=_compact_list(names))
        
    # Execute registration
    _inference_log("自动配准", "model-execute-start", model_path=model_path, pairs=_compact_list(names))
    results = REG.execute(model_path, data_path, out_dir, names)
    _inference_log("自动配准", "model-execute-done", elapsed_sec=round(time.time() - started_at, 3), outputs=_compact_results(results))
    
    # Save to database
    records = []
    for i, pair in enumerate(names):
        result = results[i]
        if result.get("status") != "success":
            continue
        first_ = up_url + pair["first"]
        second_ = up_url + pair["second"]
        ret_pic = result["output_path"]
        moving_abs_path = os.path.join(data_path, pair["first"])
        fixed_abs_path = os.path.join(data_path, pair["second"])
        moving_size = image_size_from_file(moving_abs_path)
        metadata = {
            "pair_name": result.get("pair_name"),
            "method_used": result.get("method_used"),
            "transform_type": result.get("transform_type"),
            "match_count": result.get("match_count"),
            "inlier_count": result.get("inlier_count"),
            "inlier_ratio": result.get("inlier_ratio"),
            "rmse": result.get("rmse"),
            "transform_matrix": _round_matrix(result.get("transform_matrix")),
            "overlay_path": result.get("overlay_path"),
            "checkerboard_path": result.get("checkerboard_path"),
        }
        payload = build_visual_payload(
            analysis_type="自动配准",
            renderer="registration",
            source={
                "primary": _source_entry(first_, moving_abs_path, pair["first"]),
                "secondary": _source_entry(second_, fixed_abs_path, pair["second"]),
            },
            result={
                "transform_type": metadata.get("transform_type"),
                "transform_matrix": metadata.get("transform_matrix"),
                "moving_corners_on_fixed": _transform_corners(
                    metadata.get("transform_matrix"),
                    metadata.get("transform_type"),
                    moving_size.get("width", 0),
                    moving_size.get("height", 0),
                ),
            },
            metrics={
                "match_count": metadata.get("match_count"),
                "inlier_count": metadata.get("inlier_count"),
                "inlier_ratio": metadata.get("inlier_ratio"),
                "rmse": metadata.get("rmse"),
            },
            legacy_assets=_legacy_asset_bundle(
                before_img=first_,
                before_img1=second_,
                after_img=ret_pic,
                overlay_path=metadata.get("overlay_path"),
                checkerboard_path=metadata.get("checkerboard_path"),
            ),
        )
        data = json.dumps(attach_visual_payload(metadata, payload), ensure_ascii=False)
        records.append(save_analysis(
            type_,
            first_,
            ret_pic,
            pic2=second_,
            data=data,
        ))
        
    _inference_log("自动配准", "records-saved", elapsed_sec=round(time.time() - started_at, 3), records=_compact_records(records))
    print("自动配准----------------->end")
    return records


def tracking(model_path, data_path, out_dir, names, rect, type_):
    """
    目标跟踪
    """
    import applications.interface.tracking as TRACK
    
    print("目标跟踪----------------->start")
    started_at = time.time()
    _inference_log("目标跟踪", "request", model_path=model_path, input=_compact_list(names), rect=rect, data_path=data_path, output_dir=out_dir)

    _inference_log("目标跟踪", "model-execute-start", model_path=model_path, input=_compact_list(names))
    result = TRACK.execute(model_path, data_path, out_dir, names, rect)
    _inference_log("目标跟踪", "model-execute-done", elapsed_sec=round(time.time() - started_at, 3), outputs={
        "preview_path": result.get("preview_path"),
        "output_video_path": result.get("output_video_path"),
        "trajectory_path": result.get("trajectory_path"),
        "summary": result.get("summary"),
        "method_used": result.get("method_used"),
        "runtime_variant": result.get("runtime_variant"),
    })

    first_frame = result.get("first_frame_input")
    preview_path = result.get("preview_path")
    metadata = {
        "rect": rect,
        "input_mode": result.get("input_mode", "image_sequence"),
        "source_input_path": result.get("source_input_path"),
        "source_input_name": result.get("source_input_name"),
        "source_sequence_paths": result.get("source_sequence_paths") or [],
        "output_video_path": result.get("output_video_path"),
        "trajectory_path": result.get("trajectory_path"),
        "summary": result.get("summary"),
        "method_used": result.get("method_used"),
        "runtime_variant": result.get("runtime_variant"),
        "mot_result_path": result.get("mot_result_path"),
    }
    trajectory_frame_count = 0
    trajectory_sample = []
    trajectory_abs_path = resolve_generated_path(metadata.get("trajectory_path"))
    if trajectory_abs_path and os.path.exists(trajectory_abs_path):
        try:
            with open(trajectory_abs_path, "r", encoding="utf-8") as file:
                trajectory_payload = json.load(file)
            trajectory_frames = trajectory_payload.get("frames", [])
            trajectory_frame_count = len(trajectory_frames)
            trajectory_sample = trajectory_frames[:5]
        except Exception:
            trajectory_frame_count = 0
            trajectory_sample = []
    payload = build_visual_payload(
        analysis_type="目标跟踪",
        renderer="tracking",
        source={
            "primary": {"asset_path": metadata.get("source_input_path") or first_frame},
            "input_mode": metadata.get("input_mode", "image_sequence"),
            "source_input_name": metadata.get("source_input_name"),
            "sequence_asset_paths": metadata.get("source_sequence_paths") or [],
        },
        result={
            "rect": rect,
            "trajectory_frame_count": trajectory_frame_count,
            "trajectory_sample": trajectory_sample,
            "trajectory_path": metadata.get("trajectory_path"),
        },
        metrics=metadata.get("summary") or {},
        legacy_assets=_legacy_asset_bundle(
            before_img=first_frame,
            after_img=preview_path,
            video_path=metadata.get("output_video_path"),
            trajectory_path=metadata.get("trajectory_path"),
            mot_result_path=metadata.get("mot_result_path"),
        ),
    )
    data = json.dumps(attach_visual_payload(metadata, payload), ensure_ascii=False)
    record = save_analysis(
        type_,
        first_frame,
        preview_path,
        pic2="",
        data=data,
    )
    
    _inference_log("目标跟踪", "records-saved", elapsed_sec=round(time.time() - started_at, 3), records=_compact_records([record]))
    print("目标跟踪----------------->end")
    return {
        **result,
        "record": record,
    }


def handle(fun_type, imgs, src_dir, save_dir, prefix=""):
    """

    :param fun_type:
            1=变化检测渲染，
            2=对比度自适应直方图均衡化(CLAHE)，
            3=平滑(中值滤波)，
            4=目标提取渲染，
            5=直方图匹配，
            6=锐化，
            7=高斯滤波

            1=直方图匹配，
            2=对比度自适应直方图均衡化(CLAHE)，
            3=平滑(中值滤波)，
            4=锐化，
            5=高斯滤波
            6=变化检测渲染，
            7=目标提取渲染，
            8=孔洞填充(用于变化检测结果图处理)
    """
    temps = list()
    if fun_type == fun_type_1:
        temps = histogram_match.gram_match(imgs, src_dir, save_dir, False)
    elif fun_type == fun_type_2:
        temps = CLAHE(src_dir, save_dir, imgs)
    elif fun_type == fun_type_3:
        temps = median_blur(src_dir, save_dir, imgs)
    elif fun_type == fun_type_4:
        temps = sharpen(src_dir, save_dir, imgs)
        pass
    elif fun_type == fun_type_5:
        temps = gaussian_blur(src_dir, save_dir, imgs)
    elif fun_type == fun_type_6:
        temps = batch_render(src_dir, save_dir, imgs, prefix)
    elif fun_type == fun_type_7:
        temps = batch_render_seg(src_dir, save_dir, imgs)
    elif fun_type == fun_type_8:
        temps = hole_fill(src_dir, save_dir, imgs)
    return temps
