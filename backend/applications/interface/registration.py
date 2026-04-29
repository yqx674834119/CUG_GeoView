import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import rasterio

from applications.common.model_assets import (load_model_manifest,
                                              resolve_model_dir)
from applications.common.path_global import generate_url, md5_name, up_url

try:
    import torch
    import kornia.feature as KF

    HAS_KORNIA = True
except Exception:
    torch = None
    KF = None
    HAS_KORNIA = False


_LOFTR_CACHE: Dict[str, object] = {}
LOFTR_CHECKPOINT = resolve_model_dir(
    "backend/model/registration/loftr_outdoor") / "loftr_outdoor.ckpt"


@dataclass
class PreparedImage:
    path: str
    filename: str
    rgb: np.ndarray
    feature_gray: np.ndarray


@dataclass
class RegistrationCandidate:
    method: str
    transform_type: str
    matrix: np.ndarray
    match_count: int
    inlier_count: int
    inlier_ratio: float
    rmse: Optional[float]


class RegistrationError(RuntimeError):
    pass


def execute(model_path: str, data_path: str, out_dir: str,
            names: List[dict]) -> List[dict]:
    """
    Execute multi-modal image registration.

    Input pairs use the existing project convention:
    - first: fixed/reference image url or basename
    - second: moving image url or basename
    """
    os.makedirs(out_dir, exist_ok=True)

    results = []
    for pair in names:
        fixed_name = os.path.basename(pair["first"])
        moving_name = os.path.basename(pair["second"])
        pair_name = pair.get("pair_name") or _derive_pair_name(
            fixed_name, moving_name)
        fixed_path = os.path.join(data_path, fixed_name)
        moving_path = os.path.join(data_path, moving_name)

        try:
            if not os.path.exists(fixed_path):
                raise RegistrationError(f"参考影像不存在: {fixed_name}")
            if not os.path.exists(moving_path):
                raise RegistrationError(f"待配准影像不存在: {moving_name}")

            result = register_pair(
                fixed_path=fixed_path,
                moving_path=moving_path,
                out_dir=out_dir,
                pair_name=pair_name,
                requested_model_path=model_path,
            )
        except Exception as exc:
            result = {
                "status": "error",
                "requested_model_path": model_path,
                "method_used": None,
                "transform_type": None,
                "match_count": 0,
                "inlier_count": 0,
                "inlier_ratio": 0.0,
                "rmse": None,
                "transform_matrix": None,
                "output_path": None,
                "overlay_path": None,
                "checkerboard_path": None,
                "message": str(exc),
            }

        result["fixed_input"] = up_url + fixed_name
        result["moving_input"] = up_url + moving_name
        result["fixed_name"] = fixed_name
        result["moving_name"] = moving_name
        result["pair_name"] = pair_name
        results.append(result)

    return results


def register_pair(fixed_path: str, moving_path: str, out_dir: str,
                  pair_name: str,
                  requested_model_path: str) -> dict:
    fixed_image = _prepare_image(fixed_path)
    moving_image = _prepare_image(moving_path)
    fixed_match_gray, moving_match_gray = _prepare_matching_inputs(
        fixed_image.feature_gray,
        moving_image.feature_gray,
    )

    request_mode = _normalize_model_path(requested_model_path)
    candidates: List[RegistrationCandidate] = []
    failures: List[str] = []

    if request_mode in ("auto", "loftr"):
        try:
            loftr_candidate = _match_with_loftr(fixed_match_gray, moving_match_gray)
            if loftr_candidate is not None:
                candidates.append(loftr_candidate)
        except Exception as exc:
            failures.append(f"LoFTR 不可用: {exc}")

        try:
            external_candidate = _match_with_external_loftr(
                fixed_path=fixed_path,
                moving_path=moving_path,
            )
            if external_candidate is not None:
                candidates.append(external_candidate)
        except Exception as exc:
            failures.append(f"外部 LoFTR 不可用: {exc}")
            if request_mode == "loftr" and not candidates:
                raise

    if request_mode in ("auto", "opencv"):
        opencv_candidate = _match_with_opencv(fixed_match_gray, moving_match_gray)
        if opencv_candidate is not None:
            candidates.append(opencv_candidate)
        elif request_mode == "opencv":
            failures.append("OpenCV 特征匹配未能估计有效变换")

    if not candidates:
        detail = "；".join(failures) if failures else "未找到足够稳定的匹配点"
        raise RegistrationError(f"{pair_name} 配准失败: {detail}")

    best = max(candidates, key=lambda item: (item.inlier_count, item.inlier_ratio))
    registered = _warp_rgb(moving_image.rgb, best.matrix, best.transform_type,
                           fixed_image.rgb.shape[1], fixed_image.rgb.shape[0])
    overlay = _build_overlay(fixed_image.rgb, registered)
    checkerboard = _build_checkerboard(fixed_image.rgb, registered)

    registered_name = md5_name(f"registration_{pair_name}_registered.png")
    overlay_name = md5_name(f"registration_{pair_name}_overlay.png")
    checkerboard_name = md5_name(f"registration_{pair_name}_checkerboard.png")

    registered_path = os.path.join(out_dir, registered_name)
    overlay_path = os.path.join(out_dir, overlay_name)
    checkerboard_path = os.path.join(out_dir, checkerboard_name)

    _save_rgb(registered_path, registered)
    _save_rgb(overlay_path, overlay)
    _save_rgb(checkerboard_path, checkerboard)

    return {
        "status": "success",
        "requested_model_path": requested_model_path,
        "method_used": best.method,
        "transform_type": best.transform_type,
        "match_count": int(best.match_count),
        "inlier_count": int(best.inlier_count),
        "inlier_ratio": round(float(best.inlier_ratio), 4),
        "rmse": round(float(best.rmse), 4) if best.rmse is not None else None,
        "transform_matrix": _matrix_to_list(best.matrix),
        "output_path": generate_url + registered_name,
        "overlay_path": generate_url + overlay_name,
        "checkerboard_path": generate_url + checkerboard_name,
    }


def _prepare_image(path: str) -> PreparedImage:
    rgb = _load_rgb_image(path)
    feature_gray = _build_feature_gray(rgb)
    return PreparedImage(
        path=path,
        filename=os.path.basename(path),
        rgb=rgb,
        feature_gray=feature_gray,
    )


def _load_rgb_image(path: str) -> np.ndarray:
    ext = os.path.splitext(path)[1].lower()
    if ext in {".tif", ".tiff"}:
        with rasterio.open(path) as dataset:
            array = dataset.read()
        if array.size == 0:
            raise RegistrationError(f"无法读取影像: {path}")
        return _multiband_to_rgb(array)

    image = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if image is None:
        raise RegistrationError(f"无法读取影像: {path}")
    if image.ndim == 2:
        image = np.stack([image] * 3, axis=-1)
    elif image.shape[2] == 4:
        image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    if image.dtype != np.uint8:
        image = _normalize_to_uint8(image)
    return image


def _multiband_to_rgb(array: np.ndarray) -> np.ndarray:
    bands = array.shape[0]
    if bands >= 3:
        rgb = np.stack([array[0], array[1], array[2]], axis=-1)
    elif bands == 2:
        mean_band = ((array[0].astype(np.float32) + array[1].astype(np.float32)) /
                     2.0)
        rgb = np.stack([array[0], array[1], mean_band], axis=-1)
    else:
        rgb = np.stack([array[0], array[0], array[0]], axis=-1)
    return _normalize_to_uint8(rgb)


def _normalize_to_uint8(image: np.ndarray) -> np.ndarray:
    image = np.nan_to_num(image.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    if image.ndim == 2:
        return _robust_channel_normalize(image)

    channels = []
    for index in range(image.shape[2]):
        channels.append(_robust_channel_normalize(image[:, :, index]))
    return np.stack(channels, axis=-1)


def _robust_channel_normalize(channel: np.ndarray) -> np.ndarray:
    valid = channel[np.isfinite(channel)]
    if valid.size == 0:
        return np.zeros(channel.shape, dtype=np.uint8)

    low, high = np.percentile(valid, [2, 98])
    if high <= low:
        low = float(valid.min())
        high = float(valid.max())
    if high <= low:
        return np.zeros(channel.shape, dtype=np.uint8)

    channel = np.clip(channel, low, high)
    channel = (channel - low) / (high - low)
    return np.clip(channel * 255.0, 0, 255).astype(np.uint8)


def _build_feature_gray(rgb: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(gray)

    grad_x = cv2.Sobel(clahe, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(clahe, cv2.CV_32F, 0, 1, ksize=3)
    grad_mag = cv2.magnitude(grad_x, grad_y)
    grad_mag = _robust_channel_normalize(grad_mag)

    return cv2.addWeighted(clahe, 0.7, grad_mag, 0.3, 0)


def _prepare_matching_inputs(fixed_gray: np.ndarray,
                             moving_gray: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    max_dim = max(
        fixed_gray.shape[0],
        fixed_gray.shape[1],
        moving_gray.shape[0],
        moving_gray.shape[1],
    )
    if max_dim <= 1536:
        return fixed_gray, moving_gray

    scale = 1536.0 / float(max_dim)
    fixed_size = (
        max(64, int(round(fixed_gray.shape[1] * scale))),
        max(64, int(round(fixed_gray.shape[0] * scale))),
    )
    moving_size = (
        max(64, int(round(moving_gray.shape[1] * scale))),
        max(64, int(round(moving_gray.shape[0] * scale))),
    )
    fixed_resized = cv2.resize(fixed_gray, fixed_size, interpolation=cv2.INTER_AREA)
    moving_resized = cv2.resize(
        moving_gray,
        moving_size,
        interpolation=cv2.INTER_AREA,
    )
    return fixed_resized, moving_resized


def _normalize_model_path(model_path: str) -> str:
    if model_path == "hf:kornia/loftr":
        return "loftr"
    if model_path in ("builtin:registration:auto", "", None):
        return "auto"
    if model_path == "builtin:registration:opencv":
        return "opencv"
    manifest = load_model_manifest(model_path)
    if manifest and manifest.get("backend") == "registration":
        return manifest.get("runtime", "auto")
    raise RegistrationError(f"不支持的配准模型: {model_path}")


def _match_with_loftr(fixed_gray: np.ndarray,
                      moving_gray: np.ndarray) -> Optional[RegistrationCandidate]:
    if not HAS_KORNIA:
        raise RegistrationError("当前环境未安装 Kornia/Torch")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    matcher = _get_loftr_matcher(device)

    fixed_tensor = torch.from_numpy(fixed_gray).float().unsqueeze(0).unsqueeze(0)
    moving_tensor = torch.from_numpy(moving_gray).float().unsqueeze(0).unsqueeze(0)
    fixed_tensor = (fixed_tensor / 255.0).to(device)
    moving_tensor = (moving_tensor / 255.0).to(device)

    with torch.inference_mode():
        correspondences = matcher({
            "image0": fixed_tensor,
            "image1": moving_tensor,
        })

    fixed_points = correspondences["keypoints0"].detach().cpu().numpy()
    moving_points = correspondences["keypoints1"].detach().cpu().numpy()

    if len(fixed_points) < 4 or len(moving_points) < 4:
        return None

    return _estimate_transform(
        method="kornia_loftr",
        src_points=moving_points,
        dst_points=fixed_points,
    )


def _match_with_external_loftr(
        fixed_path: str,
        moving_path: str) -> Optional[RegistrationCandidate]:
    script_path = os.path.join(os.path.dirname(__file__), "hf_registration.py")
    if not os.path.exists(script_path):
        raise RegistrationError("hf_registration.py 不存在")

    cmd = _build_external_loftr_cmd(
        script_path=script_path,
        fixed_path=fixed_path,
        moving_path=moving_path,
    )

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=600,
        cwd=os.path.dirname(__file__),
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RegistrationError(f"LoFTR 子进程执行失败: {detail}")

    stdout = result.stdout.strip()
    if not stdout:
        raise RegistrationError("LoFTR 子进程未返回结果")

    payload = json.loads(stdout)
    if payload.get("status") != "completed":
        raise RegistrationError(payload.get("message", "LoFTR 子进程执行未完成"))

    result_items = payload.get("results", [])
    if not result_items:
        return None

    item = result_items[0]
    if item.get("status") != "success":
        raise RegistrationError(item.get("message", "外部 LoFTR 未产出有效结果"))

    matrix = np.asarray(item.get("transform_matrix"), dtype=np.float64)
    return RegistrationCandidate(
        method=item.get("method_used", "kornia_loftr_external"),
        transform_type=item.get("transform_type", "homography"),
        matrix=matrix,
        match_count=int(item.get("match_count", 0)),
        inlier_count=int(item.get("inlier_count", 0)),
        inlier_ratio=float(item.get("inlier_ratio", 0.0) or 0.0),
        rmse=item.get("rmse"),
    )


def _build_external_loftr_cmd(script_path: str, fixed_path: str,
                              moving_path: str) -> List[str]:
    data_dir = os.path.dirname(fixed_path)
    if data_dir != os.path.dirname(moving_path):
        raise RegistrationError("外部 LoFTR 仅支持同目录下的影像对")

    pairs_json = json.dumps([{
        "first": os.path.basename(moving_path),
        "second": os.path.basename(fixed_path),
    }], ensure_ascii=False)

    candidate_paths = [
        "/opt/conda/envs/HFPyTorch310/bin/python",
        str(Path.home() / "miniconda3/envs/HFPyTorch310/bin/python"),
    ]

    for python_path in candidate_paths:
        if os.path.exists(python_path):
            return [
                python_path,
                script_path,
                "--input_dir",
                data_dir,
                "--output_dir",
                data_dir,
                "--file_pairs",
                pairs_json,
                "--device",
                "auto",
            ]

    return [
        "conda",
        "run",
        "-n",
        "HFPyTorch310",
        "python",
        script_path,
        "--input_dir",
        data_dir,
        "--output_dir",
        data_dir,
        "--file_pairs",
        pairs_json,
        "--device",
        "auto",
    ]


def _get_loftr_matcher(device: str):
    matcher = _LOFTR_CACHE.get(device)
    if matcher is not None:
        return matcher

    if LOFTR_CHECKPOINT.exists():
        matcher = KF.LoFTR(pretrained=None).to(device)
        state = torch.load(str(LOFTR_CHECKPOINT), map_location=device)
        state_dict = state.get("state_dict", state)
        matcher.load_state_dict(state_dict, strict=False)
    else:
        matcher = KF.LoFTR(pretrained="outdoor").to(device)
    matcher.eval()
    _LOFTR_CACHE[device] = matcher
    return matcher


def _match_with_opencv(fixed_gray: np.ndarray,
                       moving_gray: np.ndarray) -> Optional[RegistrationCandidate]:
    candidates = []

    if hasattr(cv2, "SIFT_create"):
        sift = cv2.SIFT_create(nfeatures=3000)
        candidate = _match_with_detector(
            fixed_gray,
            moving_gray,
            detector=sift,
            norm_type=cv2.NORM_L2,
            method_name="opencv_sift",
        )
        if candidate is not None:
            candidates.append(candidate)

    orb = cv2.ORB_create(
        nfeatures=4000,
        scaleFactor=1.2,
        nlevels=8,
        edgeThreshold=15,
        fastThreshold=7,
    )
    candidate = _match_with_detector(
        fixed_gray,
        moving_gray,
        detector=orb,
        norm_type=cv2.NORM_HAMMING,
        method_name="opencv_orb",
    )
    if candidate is not None:
        candidates.append(candidate)

    akaze = cv2.AKAZE_create()
    candidate = _match_with_detector(
        fixed_gray,
        moving_gray,
        detector=akaze,
        norm_type=cv2.NORM_HAMMING,
        method_name="opencv_akaze",
    )
    if candidate is not None:
        candidates.append(candidate)

    if not candidates:
        return None

    return max(candidates, key=lambda item: (item.inlier_count, item.inlier_ratio))


def _match_with_detector(fixed_gray: np.ndarray,
                         moving_gray: np.ndarray,
                         detector,
                         norm_type: int,
                         method_name: str) -> Optional[RegistrationCandidate]:
    fixed_keypoints, fixed_descriptors = detector.detectAndCompute(fixed_gray, None)
    moving_keypoints, moving_descriptors = detector.detectAndCompute(moving_gray, None)

    if fixed_descriptors is None or moving_descriptors is None:
        return None
    if len(fixed_keypoints) < 4 or len(moving_keypoints) < 4:
        return None

    matcher = cv2.BFMatcher(normType=norm_type, crossCheck=False)
    raw_matches = matcher.knnMatch(moving_descriptors, fixed_descriptors, k=2)

    good_matches = []
    for match_pair in raw_matches:
        if len(match_pair) < 2:
            continue
        best, second = match_pair
        if best.distance < 0.78 * second.distance:
            good_matches.append(best)

    if len(good_matches) < 4:
        return None

    src_points = np.float32(
        [moving_keypoints[match.queryIdx].pt for match in good_matches])
    dst_points = np.float32(
        [fixed_keypoints[match.trainIdx].pt for match in good_matches])

    return _estimate_transform(
        method=method_name,
        src_points=src_points,
        dst_points=dst_points,
    )


def _estimate_transform(method: str, src_points: np.ndarray,
                        dst_points: np.ndarray) -> Optional[RegistrationCandidate]:
    homography, mask = cv2.findHomography(src_points, dst_points, cv2.RANSAC, 4.0)

    if homography is not None and mask is not None:
        mask = mask.reshape(-1).astype(bool)
        inlier_count = int(mask.sum())
        match_count = int(len(mask))
        if inlier_count >= 4:
            rmse = _compute_rmse(src_points[mask], dst_points[mask], homography)
            return RegistrationCandidate(
                method=method,
                transform_type="homography",
                matrix=homography,
                match_count=match_count,
                inlier_count=inlier_count,
                inlier_ratio=(inlier_count / match_count) if match_count else 0.0,
                rmse=rmse,
            )

    affine, affine_inliers = cv2.estimateAffinePartial2D(
        src_points,
        dst_points,
        method=cv2.RANSAC,
        ransacReprojThreshold=4.0,
    )
    if affine is None or affine_inliers is None:
        return None

    affine_inliers = affine_inliers.reshape(-1).astype(bool)
    inlier_count = int(affine_inliers.sum())
    match_count = int(len(affine_inliers))
    if inlier_count < 3:
        return None

    rmse = _compute_rmse(
        src_points[affine_inliers],
        dst_points[affine_inliers],
        affine,
    )
    return RegistrationCandidate(
        method=method,
        transform_type="affine",
        matrix=affine,
        match_count=match_count,
        inlier_count=inlier_count,
        inlier_ratio=(inlier_count / match_count) if match_count else 0.0,
        rmse=rmse,
    )


def _compute_rmse(src_points: np.ndarray, dst_points: np.ndarray,
                  matrix: np.ndarray) -> Optional[float]:
    if len(src_points) == 0:
        return None

    if matrix.shape == (3, 3):
        projected = cv2.perspectiveTransform(src_points.reshape(-1, 1, 2),
                                             matrix).reshape(-1, 2)
    else:
        projected = cv2.transform(src_points.reshape(-1, 1, 2),
                                  matrix).reshape(-1, 2)
    error = np.linalg.norm(projected - dst_points, axis=1)
    return float(np.sqrt(np.mean(np.square(error))))


def _warp_rgb(image: np.ndarray, matrix: np.ndarray, transform_type: str,
              width: int, height: int) -> np.ndarray:
    if transform_type == "homography":
        return cv2.warpPerspective(
            image,
            matrix,
            (width, height),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
        )
    return cv2.warpAffine(
        image,
        matrix,
        (width, height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
    )


def _build_overlay(fixed_rgb: np.ndarray, registered_rgb: np.ndarray) -> np.ndarray:
    return cv2.addWeighted(fixed_rgb, 0.5, registered_rgb, 0.5, 0)


def _build_checkerboard(fixed_rgb: np.ndarray,
                        registered_rgb: np.ndarray) -> np.ndarray:
    height, width = fixed_rgb.shape[:2]
    block = max(32, min(height, width) // 12)
    board = np.zeros((height, width), dtype=np.uint8)
    for row in range(0, height, block):
        for col in range(0, width, block):
            index = ((row // block) + (col // block)) % 2
            board[row:row + block, col:col + block] = 255 if index == 0 else 0
    board = board[:, :, None]
    result = np.where(board == 255, fixed_rgb, registered_rgb)
    return result.astype(np.uint8)


def _save_rgb(path: str, rgb: np.ndarray) -> None:
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    cv2.imwrite(path, bgr)


def _matrix_to_list(matrix: np.ndarray) -> List[List[float]]:
    rounded = np.round(matrix.astype(float), 6)
    return json.loads(json.dumps(rounded.tolist()))


def _derive_pair_name(fixed_name: str, moving_name: str) -> str:
    fixed_stem = os.path.splitext(fixed_name)[0]
    moving_stem = os.path.splitext(moving_name)[0]
    return f"{fixed_stem}__{moving_stem}"
