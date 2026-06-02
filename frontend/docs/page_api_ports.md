# GeoView 前端页面模型推理与文件接口文档

本文档只覆盖当前前端页面实际使用的文件接口和模型推理接口。默认前端页面端口为 `3000`，后端 API 端口为 `5008`，所有接口地址均基于 `global.BASEURL`，默认形如 `http://<host>:5008/`。

## 1. 通用约定

### 1.1 端口

| 项目 | 默认端口 | 说明 |
| --- | ---: | --- |
| 前端页面 | `3000` | 开发环境读取 `config.yaml` 的 `port.frontend`；前端镜像默认把宿主 `3000` 映射到容器 `80`。 |
| 后端 API | `5008` | 文件上传、模型列表、模型推理、结果分包、资产分包都走这个端口。 |

### 1.2 分片大小

前端请求推理结果时会带：

```http
X-Geoview-Chunk-Size: 65536
```

可选值范围：`1024` 到 `262144` 字节。后端会保留一部分 JSON 元数据预算，所以实际 `chunk_size` 可能略小于请求值。

### 1.3 通用响应

成功响应：

```json
{
  "success": true,
  "code": 0,
  "msg": "成功",
  "data": {}
}
```

失败响应：

```json
{
  "success": false,
  "code": 1,
  "msg": "错误原因"
}
```

## 2. 文件接口

### 2.1 上传文件

`POST /api/file/upload`

请求类型：`multipart/form-data`

| 字段 | 类型 | 必填 | 可选值/说明 |
| --- | --- | --- | --- |
| `files` | File[] | 是 | 前端上传的图片、TIFF 或视频文件。 |
| `type` | string | 是 | 可选值见下方。 |
| `isSlice` | string/boolean | 否 | `"true"` 或 `"false"`；大图切分开关。目标跟踪和配准页面通常不传。 |

`type` 可选值：

| 值 | 当前使用页面 |
| --- | --- |
| `变化检测` | `/#/detectchanges` |
| `目标检测` | `/#/detectobjects`、`/#/registration` |
| `地物分类` | `/#/segmentation` |
| `场景分类` | `/#/classification` |
| `影像超分重建` | `/#/restoreimgs` |
| `目标跟踪` | `/#/tracking` |

后端也保留 `自动配准` 枚举，但当前前端配准页面实际上传仍使用 `目标检测`。

输出：

```json
{
  "success": true,
  "code": 0,
  "msg": "上传成功",
  "data": [
    {
      "src": "/api/file/assets/photos/...",
      "filename": "显示文件名",
      "photo_id": 123
    }
  ]
}
```

### 2.2 文件资产读取

页面不应直接把 `/api/file/assets/photos/...` 作为最终大文件展示地址。前端会通过资产分包接口读取图片、视频、轨迹 JSON，再转成 Blob URL。

#### 资产 manifest

`GET /api/transport/asset/manifest?path=<relative_path>`

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `path` | string | 是 | 相对资产路径。前端会把 `/api/file/assets/photos/a/b.png` 规整为 `a/b.png`。 |

输出：

```json
{
  "success": true,
  "code": 0,
  "data": {
    "transport": "chunked_asset_v1",
    "path": "a/b.png",
    "size": 1048576,
    "mime": "image/png",
    "filename": "b.png"
  }
}
```

#### 资产分片

`GET /api/transport/asset/chunk?path=<relative_path>&offset=<offset>&limit=<limit>`

| 参数 | 类型 | 必填 | 可选值/说明 |
| --- | --- | --- | --- |
| `path` | string | 是 | 相对资产路径。 |
| `offset` | integer | 否 | 默认 `0`。 |
| `limit` | integer | 否 | 默认按后端分片配置；前端通常传 `RESULT_CHUNK_SIZE`，范围 `1024` 到 `262144`。 |

输出：

```json
{
  "success": true,
  "code": 0,
  "data": {
    "transport": "chunked_asset_v1",
    "offset": 0,
    "next_offset": 49152,
    "size": 1048576,
    "done": false,
    "chunk": "base64..."
  }
}
```

## 3. 模型列表接口

`GET /api/model/list/<model_type>`

`model_type` 可选值：

| `model_type` | 后端期望模型类型 | 当前前端页面 |
| --- | --- | --- |
| `change_detection` | `change_detector` | `/#/detectchanges` |
| `object_detection` | `detector` | `/#/detectobjects`、`/#/registration` |
| `semantic_segmentation` | `segmenter` | `/#/segmentation` |
| `classification` | `classifier` | `/#/classification` |
| `image_restoration` | `restorer` | `/#/restoreimgs` |
| `tracking` | `tracker` | `/#/tracking` |
| `registration` | `register` | 当前前端页面未直接使用 |

输出：

```json
{
  "success": true,
  "code": 0,
  "data": [
    {
      "model_path": "backend/model/...",
      "model_type": "detector",
      "model_name": "模型展示名",
      "backend": "paddle",
      "description": "模型说明"
    }
  ]
}
```

`backend` 常见值：`paddle`、`mmrotate`、`mmsegmentation`、`huggingface`、`tracking`、`sam3`。

## 4. 模型推理接口通用字段

### 4.1 `paddle_device`

Paddle 模型可传：

| 值 | 说明 |
| --- | --- |
| `cpu` | 强制 CPU 推理。 |
| `gpu` | 要求容器内 Paddle CUDA 可用；不可用时后端拒绝，不静默回退。 |

非 Paddle 模型传该字段通常无实际影响。

### 4.2 `prehandle`

| 值 | 含义 | 当前页面 |
| ---: | --- | --- |
| `0` | 不做预处理 | 所有相关页面默认值 |
| `1` | 直方图匹配 | 变化检测 |
| `2` | CLAHE | 目标检测、地物分类的预处理预览 |
| `4` | 锐化 | 变化检测、目标检测、地物分类的预处理预览 |

### 4.3 `denoise`

| 值 | 含义 | 当前页面 |
| ---: | --- | --- |
| `0` | 不做去噪 | 默认值 |
| `3` | 平滑处理 | 变化检测、目标检测、地物分类 |
| `5` | 高斯滤波 | 变化检测、目标检测、地物分类 |

### 4.4 结果分包接口

所有模型推理接口都会返回 `transport_manifest`，前端再拉取真实结果。

`GET /api/transport/result/<result_id>/chunk?offset=<offset>&limit=<limit>`

| 参数 | 类型 | 必填 | 可选值/说明 |
| --- | --- | --- | --- |
| `result_id` | string | 是 | 推理接口返回的 manifest ID。 |
| `offset` | integer | 否 | 默认 `0`。 |
| `limit` | integer | 否 | 前端通常传 `RESULT_CHUNK_SIZE`，范围 `1024` 到 `262144`。 |

分片输出：

```json
{
  "success": true,
  "code": 0,
  "data": {
    "transport": "chunked_result_v2",
    "result_id": "uuid",
    "offset": 0,
    "next_offset": 65280,
    "limit": 65280,
    "encoded_size": 100000,
    "done": false,
    "chunk": "base64..."
  }
}
```

前端处理方式：拼接所有 `chunk`，base64 解码，gzip 解压，再 `JSON.parse()`。普通页面由 `request()` 拦截器自动完成；目标跟踪异步任务成功后手动调用同一套逻辑。

## 5. 前端页面接口明细

### 5.1 变化检测 `/#/detectchanges`

#### 模型列表

`GET /api/model/list/change_detection`

#### 上传

`POST /api/file/upload`

| 字段 | 值 |
| --- | --- |
| `type` | `变化检测` |
| `isSlice` | `"true"` 或 `"false"` |
| `files` | A 期或 B 期图片列表，页面会分别上传两组文件。 |

#### 推理

`POST /api/analysis/change_detection`

输入：

```json
{
  "window_size": 256,
  "stride": 128,
  "list": [
    { "first": "/api/file/assets/photos/a.png", "second": "/api/file/assets/photos/b.png" }
  ],
  "prehandle": 0,
  "denoise": 0,
  "model_path": "backend/model/...",
  "paddle_device": "cpu",
  "prompt_text": "vehicle"
}
```

字段可选值：

| 字段 | 可选值/约束 |
| --- | --- |
| `window_size` | 正整数，默认 `256`。 |
| `stride` | 正整数，默认 `128`；必须小于等于 `window_size`。 |
| `list[].first` | A 期上传返回的 `src`。 |
| `list[].second` | B 期上传返回的 `src`。 |
| `prehandle` | `0`、`1`、`4`。 |
| `denoise` | `0`、`3`、`5`。 |
| `paddle_device` | `cpu`、`gpu`。 |
| `prompt_text` | SAM3 模型使用；页面预设为 `vehicle`、`ship`、`airplane`、`building`、`storage tank`，也可自定义。 |

解包后的输出：

```json
{
  "records": [
    {
      "id": 1,
      "type": "变化检测",
      "before_img": "/api/file/assets/photos/...",
      "before_img1": "/api/file/assets/photos/...",
      "after_img": "/api/file/assets/photos/...",
      "data": {
        "mask": "/api/file/assets/photos/...",
        "mask_hole": "/api/file/assets/photos/...",
        "count": 10,
        "total_area": 1234,
        "avg_area": 123.4,
        "fractional_variation": 2.5
      }
    }
  ]
}
```

#### 变化检测预处理

`POST /api/analysis/histogram_match`

输入：

```json
{
  "list": [
    { "first": "/api/file/assets/photos/a.png", "second": "/api/file/assets/photos/b.png" }
  ],
  "prehandle": 1
}
```

`prehandle` 可选值：

| 值 | 说明 |
| ---: | --- |
| `1` | 直方图匹配。 |
| `4` | 锐化。 |

输出为分包结果，解包后是图片对数组。

### 5.2 目标检测 `/#/detectobjects`

#### 模型列表

`GET /api/model/list/object_detection`

当前页面从返回列表中只保留：

| 模型路径 | 说明 |
| --- | --- |
| `backend/model/object_detection/mmrotate_oriented_rcnn_r50_fpn_1x_dota_le90` | Oriented RCNN 定向目标检测。 |
| `backend/model/object_detection/paddle_yolo` | Paddle YOLO，页面默认 `paddle_device=cpu`。 |

#### 上传

`POST /api/file/upload`

| 字段 | 值 |
| --- | --- |
| `type` | `目标检测` |
| `isSlice` | `"true"` 或 `"false"` |
| `files` | 图片列表。 |

#### 推理

`POST /api/analysis/object_detection`

输入：

```json
{
  "list": ["/api/file/assets/photos/a.png"],
  "prehandle": 0,
  "denoise": 0,
  "model_path": "backend/model/object_detection/...",
  "paddle_device": "gpu"
}
```

字段可选值：

| 字段 | 可选值/约束 |
| --- | --- |
| `list[]` | 上传返回的 `src`。 |
| `prehandle` | `0`、`2`、`4`。 |
| `denoise` | `0`、`3`、`5`。 |
| `paddle_device` | `cpu`、`gpu`。 |

解包后的输出：

```json
{
  "records": [
    {
      "id": 1,
      "type": "目标检测",
      "before_img": "/api/file/assets/photos/...",
      "after_img": "/api/file/assets/photos/...",
      "visual_payload": {
        "result": {
          "image_size": { "width": 1024, "height": 1024 },
          "detections": [
            {
              "label": "object",
              "score": 0.9,
              "box": [0, 0, 100, 100],
              "polygon": [[0, 0], [100, 0], [100, 100], [0, 100]]
            }
          ]
        }
      }
    }
  ]
}
```

#### 目标检测预处理预览

`POST /api/analysis/image_pre`

输入：

```json
{
  "list": ["/api/file/assets/photos/a.png"],
  "prehandle": 2,
  "type": 4
}
```

`prehandle` 可选值：`2` 表示 CLAHE，`4` 表示锐化。输出为分包结果，解包后是预处理图片路径数组。

### 5.3 地物分类/语义分割 `/#/segmentation`

#### 模型列表

`GET /api/model/list/semantic_segmentation`

当前页面只保留：

```text
backend/model/semantic_segmentation/mmseg_cugrs
```

#### 上传

`POST /api/file/upload`

| 字段 | 值 |
| --- | --- |
| `type` | `地物分类` |
| `isSlice` | `"true"` 或 `"false"` |
| `files` | 图片列表。 |

#### 推理

`POST /api/analysis/semantic_segmentation`

输入：

```json
{
  "list": ["/api/file/assets/photos/a.png"],
  "prehandle": 0,
  "denoise": 0,
  "model_path": "backend/model/semantic_segmentation/mmseg_cugrs",
  "paddle_device": "gpu"
}
```

字段可选值：

| 字段 | 可选值/约束 |
| --- | --- |
| `list[]` | 上传返回的 `src`。 |
| `prehandle` | `0`、`2`、`4`。 |
| `denoise` | `0`、`3`、`5`。 |
| `paddle_device` | `cpu`、`gpu`。 |

解包后的输出：

```json
{
  "records": [
    {
      "id": 1,
      "type": "地物分类",
      "before_img": "/api/file/assets/photos/...",
      "after_img": "/api/file/assets/photos/..."
    }
  ]
}
```

#### 地物分类预处理预览

`POST /api/analysis/image_pre`

输入与目标检测预处理一致：

```json
{
  "list": ["/api/file/assets/photos/a.png"],
  "prehandle": 2,
  "type": 4
}
```

`prehandle` 可选值：`2`、`4`。

### 5.4 场景分类 `/#/classification`

#### 模型列表

`GET /api/model/list/classification`

#### 上传

`POST /api/file/upload`

| 字段 | 值 |
| --- | --- |
| `type` | `场景分类` |
| `isSlice` | `"true"` 或 `"false"` |
| `files` | 图片列表。 |

#### 推理

`POST /api/analysis/classification`

输入：

```json
{
  "list": ["/api/file/assets/photos/a.png"],
  "model_path": "backend/model/classification/...",
  "paddle_device": "gpu"
}
```

字段可选值：

| 字段 | 可选值/约束 |
| --- | --- |
| `list[]` | 上传返回的 `src`。 |
| `paddle_device` | `cpu`、`gpu`。 |

解包后的输出：

```json
{
  "records": [
    {
      "id": 1,
      "type": "场景分类",
      "before_img": "/api/file/assets/photos/...",
      "data": {
        "airport": 0.92,
        "industrial": 0.03
      }
    }
  ]
}
```

### 5.5 影像超分重建 `/#/restoreimgs`

#### 模型列表

`GET /api/model/list/image_restoration`

#### 上传

`POST /api/file/upload`

| 字段 | 值 |
| --- | --- |
| `type` | `影像超分重建` |
| `isSlice` | `"true"` 或 `"false"` |
| `files` | 图片列表。 |

#### 推理

`POST /api/analysis/image_restoration`

输入：

```json
{
  "list": ["/api/file/assets/photos/a.png"],
  "model_path": "backend/model/image_restoration/...",
  "paddle_device": "gpu"
}
```

字段可选值：

| 字段 | 可选值/约束 |
| --- | --- |
| `list[]` | 上传返回的 `src`。 |
| `paddle_device` | `cpu`、`gpu`。 |

解包后的输出：

```json
{
  "records": [
    {
      "id": 1,
      "type": "影像超分重建",
      "before_img": "/api/file/assets/photos/...",
      "after_img": "/api/file/assets/photos/..."
    }
  ]
}
```

### 5.6 多模态配准/小目标检测 `/#/registration`

当前页面名称是配准流程，但实际提交后端的是小目标检测接口。前端先在浏览器本地对第二张光学图做预处理，再把参考图和预处理后的待检图一起上传。

#### 模型列表

`GET /api/model/list/object_detection`

当前页面只保留：

```text
backend/model/object_detection/mmrotate_oriented_rcnn_r50_fpn_1x_dota_le90
```

#### 上传

`POST /api/file/upload`

| 字段 | 值 |
| --- | --- |
| `type` | `目标检测` |
| `files` | 两个文件：参考图、预处理后的待检图。 |

#### 推理

`POST /api/analysis/small_target_detection`

输入：

```json
{
  "model_path": "backend/model/object_detection/mmrotate_oriented_rcnn_r50_fpn_1x_dota_le90",
  "list": [
    "/api/file/assets/photos/fixed.png",
    "/api/file/assets/photos/preprocessed_moving.png"
  ],
  "prehandle": 0,
  "denoise": 0
}
```

字段可选值：

| 字段 | 可选值/约束 |
| --- | --- |
| `model_path` | 只能是 `backend/model/object_detection/mmrotate_oriented_rcnn_r50_fpn_1x_dota_le90`。 |
| `list` | 至少 2 个上传 `src`；后端实际取第二张图做检测。 |
| `prehandle` | `0`、`2`、`4`。当前页面传 `0`。 |
| `denoise` | `0`、`3`、`5`。当前页面传 `0`。 |

解包后的输出：

```json
{
  "records": [
    {
      "id": 1,
      "type": "目标检测",
      "before_img": "/api/file/assets/photos/...",
      "after_img": "/api/file/assets/photos/...",
      "visual_payload": {
        "result": {
          "detections": []
        }
      }
    }
  ]
}
```

### 5.7 目标跟踪 `/#/tracking`

#### 模型列表

`GET /api/model/list/tracking`

当前页面从返回列表中只保留模型路径包含以下片段的模型：

| 片段 | 说明 |
| --- | --- |
| `/tracking/botsort_official` | BoT-SORT official 跟踪。 |
| `/tracking/sam3_prompt` | SAM3 文本提示跟踪。 |

#### 上传

`POST /api/file/upload`

| 场景 | 字段 |
| --- | --- |
| 图像序列 | `files[]` 多张图片，`type=目标跟踪`。 |
| 视频 | `files[]` 单个视频，`type=目标跟踪`。 |

输出仍为 `src/filename/photo_id`。如果后端返回 `preview_video_path`，页面优先用于视频预览；否则使用 `src`。

#### 提交异步跟踪任务

`POST /api/analysis/tracking/async?chunk_size=65536`

输入：

```json
{
  "model_path": "backend/model/tracking/botsort_official",
  "list": [
    { "src": "/api/file/assets/photos/0001.png", "filename": "0001.png" },
    { "src": "/api/file/assets/photos/0002.png", "filename": "0002.png" }
  ],
  "rect": [100, 120, 80, 60],
  "prompt_text": "vehicle"
}
```

字段可选值：

| 字段 | 可选值/约束 |
| --- | --- |
| `model_path` | 页面当前可选 BoT-SORT official 或 SAM3 prompt 模型路径。 |
| `list[].src` | 上传返回的 `src`。 |
| `list[].filename` | 上传返回的 `filename`。 |
| `rect` | `[x, y, width, height]`。需要初始框的模型必填；BoT-SORT official 和 SAM3 prompt 不要求。 |
| `prompt_text` | SAM3 prompt 必填。页面预设为 `vehicle`、`ship`、`airplane`、`building`、`storage tank`，也可自定义。 |
| `chunk_size` | 查询参数；范围 `1024` 到 `262144`。 |

提交输出：

```json
{
  "success": true,
  "code": 0,
  "data": {
    "job_id": "uuid",
    "status": "queued",
    "message": "目标跟踪任务已提交",
    "model_path": "backend/model/tracking/botsort_official",
    "expires_in_seconds": 3600
  }
}
```

`status` 可选值：

| 值 | 说明 |
| --- | --- |
| `queued` | 排队中。 |
| `running` | 运行中。 |
| `succeeded` | 已完成，响应里会带 `transport_manifest`。 |
| `failed` | 失败，响应里会带错误信息。 |

#### 查询跟踪任务

`GET /api/analysis/tracking/jobs/<job_id>`

输入：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `job_id` | path string | 是 | 提交任务返回的 ID。 |

成功且完成时输出：

```json
{
  "success": true,
  "code": 0,
  "data": {
    "job_id": "uuid",
    "status": "succeeded",
    "message": "目标跟踪完成",
    "transport_manifest": {
      "transport": "chunked_result_v2",
      "result_id": "uuid",
      "route": "tracking"
    }
  }
}
```

跟踪结果解包后：

```json
{
  "first_frame_input": "/api/file/assets/photos/...",
  "source_input_path": "/api/file/assets/photos/...",
  "preview_path": "/api/file/assets/photos/...",
  "output_video_path": "/api/file/assets/photos/...",
  "trajectory_path": "/api/file/assets/photos/...",
  "input_mode": "image_sequence",
  "runtime_variant": "botsort_official",
  "method_used": "BoT-SORT",
  "summary": {
    "total_frames": 10,
    "tracked_frames": 10,
    "lost_frames": 0,
    "mean_confidence": 0.8,
    "label_histogram": {}
  }
}
```

`input_mode` 常见值：`image_sequence`、`video`。

## 6. 页面接口速查

| 页面 | 模型列表 | 上传 `type` | 推理接口 |
| --- | --- | --- | --- |
| `/#/detectchanges` | `/api/model/list/change_detection` | `变化检测` | `/api/analysis/change_detection` |
| `/#/detectobjects` | `/api/model/list/object_detection` | `目标检测` | `/api/analysis/object_detection` |
| `/#/segmentation` | `/api/model/list/semantic_segmentation` | `地物分类` | `/api/analysis/semantic_segmentation` |
| `/#/classification` | `/api/model/list/classification` | `场景分类` | `/api/analysis/classification` |
| `/#/restoreimgs` | `/api/model/list/image_restoration` | `影像超分重建` | `/api/analysis/image_restoration` |
| `/#/registration` | `/api/model/list/object_detection` | `目标检测` | `/api/analysis/small_target_detection` |
| `/#/tracking` | `/api/model/list/tracking` | `目标跟踪` | `/api/analysis/tracking/async`、`/api/analysis/tracking/jobs/<job_id>` |
