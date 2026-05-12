# 后端 API GPU 测试报告

测试时间：2026-05-10 22:17:19

测试环境：
- 容器启动参数：`docker run --gpus all`
- GPU：NVIDIA RTX A4500，显存 20470 MiB
- Paddle：2.4.2，CUDA compiled，容器内识别 GPU 数量 1
- 测试数据：`TestData`
- 原始 JSON 报告：`docs/test-results/gpu-api-report.json`

结论：GPU 环境下后端 API 回归 `28/28` 通过，失败数 `0`。上传后的图片和视频均通过 `/api/file/assets/photos/<path>` 直接取回，返回内容类型和字节数有效。

## 基础接口

| 接口 | 结果 |
| --- | --- |
| `GET /health` | 通过 |
| `GET /api/system/ping` | 通过 |
| `GET /api/model/list/change_detection` | 通过 |
| `GET /api/model/list/object_detection` | 通过 |
| `GET /api/model/list/semantic_segmentation` | 通过 |
| `GET /api/model/list/classification` | 通过 |
| `GET /api/model/list/image_restoration` | 通过 |
| `GET /api/model/list/registration` | 通过 |
| `GET /api/model/list/tracking` | 通过 |

## 上传与资源回传

| 数据 | 上传接口 | 资源回传 |
| --- | --- | --- |
| `TestData/Dec/aircraft_4.jpg` | `POST /api/file/upload` | 通过，`image/jpeg` |
| `TestData/Seg/aircraft_4.jpg` | `POST /api/file/upload` | 通过，`image/jpeg` |
| `TestData/CD/Val1/val_1.png` | `POST /api/file/upload` | 通过，`image/png` |
| `TestData/CD/Val2/val_1.png` | `POST /api/file/upload` | 通过，`image/png` |
| `TestData/val_1.png` | `POST /api/file/upload` | 通过，`image/png` |
| `TestData/val_1_2X.png` | `POST /api/file/upload` | 通过，`image/png` |
| `TestData/Tracking/official_mot17_02_frcnn_180frames_raw.mp4` | `POST /api/file/upload` | 通过，`video/mp4` |

## 模型推理接口

| 接口 | 模型 | 结果 |
| --- | --- | --- |
| `POST /api/analysis/change_detection` | `backend/model/change_detection/bit_256x256` | 通过 |
| `POST /api/analysis/object_detection` | `backend/model/object_detection/paddle_yolo` | 通过 |
| `POST /api/analysis/object_detection` | `backend/model/object_detection/hf_conditional_detr_resnet50` | 通过 |
| `POST /api/analysis/object_detection` | `backend/model/object_detection/hf_detr_resnet50` | 通过 |
| `POST /api/analysis/object_detection` | `backend/model/object_detection/hf_waldo30` | 通过 |
| `POST /api/analysis/object_detection` | `backend/model/object_detection/mmrotate_oriented_rcnn_r50_fpn_1x_dota_le90` | 通过 |
| `POST /api/analysis/semantic_segmentation` | `backend/model/semantic_segmentation/paddle_deeplabv3p` | 通过 |
| `POST /api/analysis/semantic_segmentation` | `backend/model/semantic_segmentation/mmseg_cugrs` | 通过 |
| `POST /api/analysis/classification` | `backend/model/classification/resnet50` | 通过 |
| `POST /api/analysis/image_restoration` | `backend/model/image_restoration/hf_swin2sr_x2` | 通过 |
| `POST /api/analysis/image_restoration` | `backend/model/image_restoration/hf_swin2sr_x4` | 通过 |
| `POST /api/analysis/registration` | `backend/model/registration/auto` | 通过 |
| `POST /api/analysis/registration` | `backend/model/registration/loftr_outdoor` | 通过 |
| `POST /api/analysis/registration` | `backend/model/registration/opencv` | 通过 |
| `POST /api/analysis/tracking` | `backend/model/tracking/auto` | 通过 |
| `POST /api/analysis/tracking` | `backend/model/tracking/botsort` | 通过 |
| `POST /api/analysis/tracking` | `backend/model/tracking/botsort_official` | 通过 |
| `POST /api/analysis/tracking` | `backend/model/tracking/csrt` | 通过 |
| `POST /api/analysis/tracking` | `backend/model/tracking/kcf` | 通过 |

备注：本报告只记录 GPU 环境测试结果；CPU 回归结果不作为本次交付依据。

## 2026-05-11 前端图片显示与推理日志复测

测试环境：
- 后端：`geoview-backend-local`，`http://127.0.0.1:5008`，`--gpus all`
- 前端：`geoview-frontend-local`，`http://127.0.0.1:3000`
- 前端构建：`npm run build` 通过，当前加载 `js/app.3442924c.js`
- 测试数据：`TestData/Seg/aircraft_4.jpg`

复测结果：

| 检查项 | 结果 |
| --- | --- |
| `GET http://127.0.0.1:5008/health` | 通过，返回 `status: ok` |
| `GET http://127.0.0.1:5008/api/model/list/change_detection` | 通过 |
| 前端地物分类上传流程 | 通过，上传后页面直接显示 `结果统计总览` 和单条结果 |
| 前端结果图渲染 | 通过，原图与预测图均生成真实 `<img>`，尺寸 `512x512`，无纯占位图 |
| 结果图资源回传 | 通过，原图、预测图、mask 均由后端 `/api/file/assets/...` 返回 200 |
| 后端推理日志 | 通过，包含 request、input-normalized、preprocess-resize、model-execute-start、subprocess completed、stdout/stderr tail、model-execute-done、records-saved |

本次复测使用 MMSegmentation 模型 `backend/model/semantic_segmentation/mmseg_cugrs`，后端执行命令包含 `--device cuda:0`。其中一次前端触发的 MMSeg GPU 推理耗时约 `225.799s`，接口最终成功返回；这属于 GPU 慢请求，不计为 CPU 测试结果。
