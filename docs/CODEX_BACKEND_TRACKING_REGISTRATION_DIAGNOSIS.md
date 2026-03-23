# GeoView 后端“目标跟踪 / 配准对齐”实现诊断报告

检查日期：2026-03-23

## 1. 检查范围

本次检查只围绕 GeoView 当前仓库中与“目标跟踪（tracking）”和“配准/对齐（registration/alignment）”直接相关的后端链路，以及能影响其是否可用的前端调用、配置、部署文档、测试与已有说明文档展开，重点不是算法理论评估，而是当前实现为什么在工程上“容易不可用 / 看起来有能力但实际存在明显缺陷”。

本次实际检查的范围包括：

- 后端 API 入口：
  - `backend/applications/api/analysis.py`
  - `backend/applications/api/model.py`
- 后端业务封装：
  - `backend/applications/interface/analysis.py`
  - `backend/applications/interface/registration.py`
  - `backend/applications/interface/tracking.py`
  - `backend/applications/interface/hf_inference_caller.py`
  - `backend/applications/interface/hf_registration.py`
  - `backend/applications/interface/hf_tracking.py`
- 上传与路径处理：
  - `backend/applications/api/file.py`
  - `backend/applications/common/utils/upload.py`
  - `backend/applications/common/path_global.py`
  - `backend/applications/common/utils/http.py`
- 前端调用与页面逻辑：
  - `frontend/src/views/mainfun/Registration.vue`
  - `frontend/src/views/mainfun/Tracking.vue`
  - `frontend/src/api/upload.js`
  - `frontend/src/api/request.js`
  - `frontend/src/api/requestfile.js`
  - `frontend/src/utils/getUploadImg.js`
  - `frontend/src/views/mainfun/DetectChanges.vue`
- 文档 / 测试 / 部署：
  - `docs/Model_Usage_Dependencies.md`
  - `docs/software_test_report.md`
  - `docs/demo.md`
  - `backend/test_new_features.py`
  - `backend/requirements.txt`
  - `backend/requirements-hf.txt`
  - `Dockerfile`
  - `docker/entrypoint.sh`
  - `install.md`

另外，我还做了非常轻量的运行环境核对：

- 当前检查环境中不存在 `HFPyTorch310` 解释器路径。
- 当前检查环境中也没有 `conda` 命令。
- 当前检查环境里的 `python3` 未安装 `flask`、`cv2`、`torch`、`kornia`。

这部分只能证明“当前工作环境无法直接运行这两项能力”，不能单独证明生产环境一定如此；但结合源码和文档，足以说明这两项能力对环境前提高度敏感。

## 2. 目标跟踪逻辑在哪里

目标跟踪的主链路如下：

1. 前端页面发起请求  
   `frontend/src/views/mainfun/Tracking.vue`

2. 前端统一请求封装  
   `frontend/src/api/upload.js` 中的 `imgUpload(data, 'tracking')`

3. 后端 API 入口  
   `backend/applications/api/analysis.py` 中的 `tracking_api()`

4. 业务层封装  
   `backend/applications/interface/analysis.py` 中的 `tracking(input_path, out_dir, rect, type_)`

5. 跟踪执行器封装  
   `backend/applications/interface/tracking.py` 中的 `execute(input_path, out_dir, rect)`

6. 子进程调用器  
   `backend/applications/interface/hf_inference_caller.py` 中的 `call_hf_tracking(...)`

7. 实际算法脚本  
   `backend/applications/interface/hf_tracking.py` 中的 `run_tracking(video_path, init_rect, output_path)`

当前实际算法不是深度学习多目标时序跟踪，而是一个 OpenCV 传统单目标跟踪器包装：

- 首选 `cv2.TrackerCSRT_create()`
- 失败则退回 `cv2.TrackerMIL_create()`

并且该脚本本身明确写了“模拟/简化版”，不是完整 SOTA 跟踪实现，见：

- [backend/applications/interface/hf_tracking.py](/home/livablecity/GeoView/backend/applications/interface/hf_tracking.py#L6)
- [backend/applications/interface/hf_tracking.py](/home/livablecity/GeoView/backend/applications/interface/hf_tracking.py#L7)
- [backend/applications/interface/hf_tracking.py](/home/livablecity/GeoView/backend/applications/interface/hf_tracking.py#L8)

## 3. 配准 / 对齐逻辑在哪里

配准链路如下：

1. 前端页面发起请求  
   `frontend/src/views/mainfun/Registration.vue`

2. 前端统一请求封装  
   `frontend/src/api/upload.js` 中的 `imgUpload(data, 'registration')`

3. 后端 API 入口  
   `backend/applications/api/analysis.py` 中的 `registration_api()`

4. 业务层封装  
   `backend/applications/interface/analysis.py` 中的 `registration(data_path, out_dir, names, type_)`

5. 配准执行器封装  
   `backend/applications/interface/registration.py` 中的 `execute(data_path, out_dir, names)`

6. 子进程调用器  
   `backend/applications/interface/hf_inference_caller.py` 中的 `call_hf_registration(...)`

7. 实际算法脚本  
   `backend/applications/interface/hf_registration.py` 中的 `register_pair(img1_path, img2_path, output_path, device='cuda')`

当前实际算法是：

- 使用 Kornia LoFTR 提取匹配点
- 固定 `pretrained='outdoor'`
- 用 `cv2.findHomography(..., cv2.RANSAC, 5.0)` 估计单应矩阵
- 用 `cv2.warpPerspective` 把第一张图扭到第二张图坐标系

见：

- [backend/applications/interface/hf_registration.py](/home/livablecity/GeoView/backend/applications/interface/hf_registration.py#L22)
- [backend/applications/interface/hf_registration.py](/home/livablecity/GeoView/backend/applications/interface/hf_registration.py#L35)
- [backend/applications/interface/hf_registration.py](/home/livablecity/GeoView/backend/applications/interface/hf_registration.py#L54)
- [backend/applications/interface/hf_registration.py](/home/livablecity/GeoView/backend/applications/interface/hf_registration.py#L64)

## 4. 可能的根因

我认为这两个能力当前“有问题”的根因不是一个，而是至少有五类，且其中前三类是高优先级阻断项。

### 4.1 前后端协议根本不匹配，这是最直接的阻断问题

项目既有页面的数据流是：

1. 先把文件上传到 `/api/file/upload`
2. 拿到服务器侧 `src`
3. 再用 JSON 调 `/api/analysis/<fun>`

这一点在通用上传工具里写得很清楚，见：

- [frontend/src/utils/getUploadImg.js](/home/livablecity/GeoView/frontend/src/utils/getUploadImg.js#L26)
- [frontend/src/utils/getUploadImg.js](/home/livablecity/GeoView/frontend/src/utils/getUploadImg.js#L39)
- [frontend/src/utils/getUploadImg.js](/home/livablecity/GeoView/frontend/src/utils/getUploadImg.js#L43)

变化检测页面也遵循这个流程，见：

- [frontend/src/views/mainfun/DetectChanges.vue](/home/livablecity/GeoView/frontend/src/views/mainfun/DetectChanges.vue#L1121)
- [frontend/src/views/mainfun/DetectChanges.vue](/home/livablecity/GeoView/frontend/src/views/mainfun/DetectChanges.vue#L1127)
- [frontend/src/views/mainfun/DetectChanges.vue](/home/livablecity/GeoView/frontend/src/views/mainfun/DetectChanges.vue#L1158)

而注册页和跟踪页没有走这个流程：

- 注册页直接把 `FormData` 发给 `/api/analysis/registration`
- 跟踪页直接把 `FormData` 发给 `/api/analysis/tracking`

见：

- [frontend/src/views/mainfun/Registration.vue](/home/livablecity/GeoView/frontend/src/views/mainfun/Registration.vue#L196)
- [frontend/src/views/mainfun/Registration.vue](/home/livablecity/GeoView/frontend/src/views/mainfun/Registration.vue#L238)
- [frontend/src/views/mainfun/Tracking.vue](/home/livablecity/GeoView/frontend/src/views/mainfun/Tracking.vue#L207)
- [frontend/src/views/mainfun/Tracking.vue](/home/livablecity/GeoView/frontend/src/views/mainfun/Tracking.vue#L224)

但后端这两个 API 都只从 `request.json` 取值：

- `registration_api()` 读取 `request.json["list"]`
- `tracking_api()` 读取 `request.json["input_path"]` / `request.json["rect"]`

见：

- [backend/applications/api/analysis.py](/home/livablecity/GeoView/backend/applications/api/analysis.py#L251)
- [backend/applications/api/analysis.py](/home/livablecity/GeoView/backend/applications/api/analysis.py#L252)
- [backend/applications/api/analysis.py](/home/livablecity/GeoView/backend/applications/api/analysis.py#L253)
- [backend/applications/api/analysis.py](/home/livablecity/GeoView/backend/applications/api/analysis.py#L276)
- [backend/applications/api/analysis.py](/home/livablecity/GeoView/backend/applications/api/analysis.py#L277)
- [backend/applications/api/analysis.py](/home/livablecity/GeoView/backend/applications/api/analysis.py#L282)

这意味着：

- 前端送的是 multipart/form-data
- 后端等的是 application/json

这是一个非常硬的协议错位。实际症状取决于 Flask / Werkzeug 行为和请求头，但无论如何，这条链路都不是按项目既有模式实现的。

### 4.2 即使绕过协议问题，前端对返回结果的预期也和后端实际返回不一致

#### 注册页

后端注册接口成功时直接返回 `success_api()`，没有返回结果列表：

- [backend/applications/api/analysis.py](/home/livablecity/GeoView/backend/applications/api/analysis.py#L262)
- [backend/applications/api/analysis.py](/home/livablecity/GeoView/backend/applications/api/analysis.py#L265)
- [backend/applications/common/utils/http.py](/home/livablecity/GeoView/backend/applications/common/utils/http.py#L6)

但前端注册页假设 `res.data.data` 是结果数组，并直接赋值给 `resultArr`：

- [frontend/src/views/mainfun/Registration.vue](/home/livablecity/GeoView/frontend/src/views/mainfun/Registration.vue#L240)
- [frontend/src/views/mainfun/Registration.vue](/home/livablecity/GeoView/frontend/src/views/mainfun/Registration.vue#L242)

因此即便后端真的完成配准，前端“结果预览”也大概率拿不到当前调用的即时结果。

#### 跟踪页

后端跟踪接口成功时返回的 `data` 是一个字符串 URL：

- `tracking()` 返回 `video_url`
- `tracking_api()` 用 `success_api(data=res)` 直接返回这个字符串

见：

- [backend/applications/interface/analysis.py](/home/livablecity/GeoView/backend/applications/interface/analysis.py#L399)
- [backend/applications/interface/analysis.py](/home/livablecity/GeoView/backend/applications/interface/analysis.py#L418)
- [backend/applications/api/analysis.py](/home/livablecity/GeoView/backend/applications/api/analysis.py#L303)
- [backend/applications/api/analysis.py](/home/livablecity/GeoView/backend/applications/api/analysis.py#L305)

但前端跟踪页判断逻辑却要求：

- `res.data.data.results` 存在
- `res.data.data.output_path` 存在

见：

- [frontend/src/views/mainfun/Tracking.vue](/home/livablecity/GeoView/frontend/src/views/mainfun/Tracking.vue#L225)
- [frontend/src/views/mainfun/Tracking.vue](/home/livablecity/GeoView/frontend/src/views/mainfun/Tracking.vue#L230)

也就是说，就算后端返回成功 URL，前端仍可能进入“跟踪失败”分支，或者不展示结果视频。

### 4.3 跟踪页宣称支持“视频或图像序列文件夹”，但后端 API 实际没有完整支持

页面文案声称支持“视频文件或图像序列文件夹”：

- [frontend/src/views/mainfun/Tracking.vue](/home/livablecity/GeoView/frontend/src/views/mainfun/Tracking.vue#L12)

但后端 `tracking_api()` 里对 `input_path` 是 `list` 的情况只有 `TODO`，并没有真正实现：

- [backend/applications/api/analysis.py](/home/livablecity/GeoView/backend/applications/api/analysis.py#L294)
- [backend/applications/api/analysis.py](/home/livablecity/GeoView/backend/applications/api/analysis.py#L295)
- [backend/applications/api/analysis.py](/home/livablecity/GeoView/backend/applications/api/analysis.py#L296)

更关键的是，前端并没有先上传文件夹后取得一个服务器端目录路径，也没有构造 `input_path` JSON 列表；它只是把多个文件直接塞进 `FormData`。因此：

- “图像序列文件夹支持”在 UI 上存在
- 在 API 协议和服务端路径模型上并没有打通

这属于典型的“页面能力承诺大于后端真实能力”。

### 4.4 运行环境依赖极易失配，且手工部署文档与 Docker 配置不一致

两项能力都通过 `hf_inference_caller.py` 启动独立 Python 解释器：

- 优先找固定路径解释器
- 找不到则执行 `conda run -n HFPyTorch310 ...`

见：

- [backend/applications/interface/hf_inference_caller.py](/home/livablecity/GeoView/backend/applications/interface/hf_inference_caller.py#L319)
- [backend/applications/interface/hf_inference_caller.py](/home/livablecity/GeoView/backend/applications/interface/hf_inference_caller.py#L337)
- [backend/applications/interface/hf_inference_caller.py](/home/livablecity/GeoView/backend/applications/interface/hf_inference_caller.py#L411)
- [backend/applications/interface/hf_inference_caller.py](/home/livablecity/GeoView/backend/applications/interface/hf_inference_caller.py#L429)

但项目文档存在明显分叉：

- `Dockerfile` 的确创建了 `HFPyTorch310`，并安装了 `kornia` 等依赖
- `install.md` 只指导安装 `PaddleRS37` 与 `backend/requirements.txt`，没有指导创建 `HFPyTorch310`

见：

- [Dockerfile](/home/livablecity/GeoView/Dockerfile#L56)
- [Dockerfile](/home/livablecity/GeoView/Dockerfile#L63)
- [Dockerfile](/home/livablecity/GeoView/Dockerfile#L112)
- [install.md](/home/livablecity/GeoView/install.md#L3)
- [install.md](/home/livablecity/GeoView/install.md#L56)
- [install.md](/home/livablecity/GeoView/install.md#L62)

另外：

- `docker/entrypoint.sh` 只激活 `PaddleRS37`，运行时依赖子进程再跨环境调用
- `backend/requirements-hf.txt` 只列了 `torch / torchvision / transformers / pillow / numpy`，并未列出配准/跟踪真正依赖的 `kornia` 或 OpenCV contrib 能力

见：

- [docker/entrypoint.sh](/home/livablecity/GeoView/docker/entrypoint.sh#L15)
- [backend/requirements-hf.txt](/home/livablecity/GeoView/backend/requirements-hf.txt#L6)
- [backend/requirements-hf.txt](/home/livablecity/GeoView/backend/requirements-hf.txt#L10)

这会导致一个现实结果：

- Docker 镜像路径下，可能还能工作
- 非 Docker、本地 conda 手工安装、临时迁移环境，很容易直接失效

### 4.5 算法能力与产品/文档目标明显不匹配

#### 跟踪能力错位

文档宣称的跟踪是：

- “全域静态目标跟踪与预警能力”
- “融合历史时序与环境上下文支持跟踪”
- 评价指标包括 `MOTA`、`IDF1`、异常事件检测精度

见：

- [docs/software_test_report.md](/home/livablecity/GeoView/docs/software_test_report.md#L137)

但代码实现只是：

- 单目标
- 依赖人工提供初始框
- OpenCV CSRT/MIL
- 输出每帧 bbox
- 完全没有预警逻辑、没有异常检测、没有时序建模、没有 ID 保持、多目标关联、上下文建模

见：

- [backend/applications/interface/hf_tracking.py](/home/livablecity/GeoView/backend/applications/interface/hf_tracking.py#L23)
- [backend/applications/interface/hf_tracking.py](/home/livablecity/GeoView/backend/applications/interface/hf_tracking.py#L45)
- [backend/applications/interface/hf_tracking.py](/home/livablecity/GeoView/backend/applications/interface/hf_tracking.py#L90)

这不是“效果差一点”，而是能力等级根本不在一个层次。

#### 配准能力错位

文档宣称配准面向：

- 光学与 SAR 影像
- 多模态遥感
- 含地理坐标、多分辨率数据

见：

- [docs/software_test_report.md](/home/livablecity/GeoView/docs/software_test_report.md#L118)

但当前配准实现：

- 直接把两张图转灰度
- 固定使用 LoFTR `outdoor`
- 直接估单应矩阵
- 直接全图 warp
- 不使用任何地理坐标、RPC、GCP、分块、金字塔、重采样策略

见：

- [backend/applications/interface/hf_registration.py](/home/livablecity/GeoView/backend/applications/interface/hf_registration.py#L30)
- [backend/applications/interface/hf_registration.py](/home/livablecity/GeoView/backend/applications/interface/hf_registration.py#L35)
- [backend/applications/interface/hf_registration.py](/home/livablecity/GeoView/backend/applications/interface/hf_registration.py#L54)
- [backend/applications/interface/hf_registration.py](/home/livablecity/GeoView/backend/applications/interface/hf_registration.py#L64)

这意味着它更像“普通二维图像局部特征匹配 + 透视变换”，而不是“稳健的多模态遥感配准流水线”。对 SAR/光学、超大分辨率、弱纹理或局部几何形变场景都可能不稳定。

### 4.6 一些实现细节本身也容易导致失败或退化

#### 跟踪器创建逻辑写得不完整

代码在 `AttributeError` 分支里又重复调用了一次 `cv2.TrackerCSRT_create()`：

- 预期更合理的写法通常会尝试 `cv2.legacy.TrackerCSRT_create()`
- 现在这段重复调用没有实质意义

见：

- [backend/applications/interface/hf_tracking.py](/home/livablecity/GeoView/backend/applications/interface/hf_tracking.py#L45)
- [backend/applications/interface/hf_tracking.py](/home/livablecity/GeoView/backend/applications/interface/hf_tracking.py#L47)
- [backend/applications/interface/hf_tracking.py](/home/livablecity/GeoView/backend/applications/interface/hf_tracking.py#L50)

如果运行环境里的 CSRT 只暴露在 `cv2.legacy` 命名空间，那么当前代码会错误地直接回退到 MIL，甚至继续失败。

#### 配准对大图没有任何内存/尺度保护

`register_pair()` 直接读取整图进张量，随后全图 LoFTR 推理：

- [backend/applications/interface/hf_registration.py](/home/livablecity/GeoView/backend/applications/interface/hf_registration.py#L24)
- [backend/applications/interface/hf_registration.py](/home/livablecity/GeoView/backend/applications/interface/hf_registration.py#L25)

对于高分辨率遥感图，这很容易带来：

- GPU/CPU 内存压力过大
- 推理时间长
- 超时
- 匹配点质量不稳

#### 这两页还绕过了统一上传预处理能力

统一上传接口会做：

- 文件落盘
- `src` 返回
- TIFF 特殊处理 / 转换 / 切片

见：

- [backend/applications/api/file.py](/home/livablecity/GeoView/backend/applications/api/file.py#L9)
- [backend/applications/api/file.py](/home/livablecity/GeoView/backend/applications/api/file.py#L17)
- [backend/applications/common/utils/upload.py](/home/livablecity/GeoView/backend/applications/common/utils/upload.py#L33)

而注册页和跟踪页没有走这个标准入口，因此：

- TIFF 预处理能力不能被复用
- 服务端统一命名与路径返回机制不能被复用
- 后续 `img_url_handle()` 等逻辑也失去统一前提

## 5. 具体证据：文件路径 / 函数 / 代码行为

下面按问题类别列出更聚焦的证据。

### 5.1 配准接口与前端请求不兼容

证据：

- `registration_api()` 只读取 JSON 中的 `list`  
  [backend/applications/api/analysis.py](/home/livablecity/GeoView/backend/applications/api/analysis.py#L251)
- 注册页却直接组装 `FormData` 并调用 `imgUpload(formData, 'registration')`  
  [frontend/src/views/mainfun/Registration.vue](/home/livablecity/GeoView/frontend/src/views/mainfun/Registration.vue#L196)
- 注册页源码里的注释已经直接暴露出作者自己也不确定后端期望的结构  
  [frontend/src/views/mainfun/Registration.vue](/home/livablecity/GeoView/frontend/src/views/mainfun/Registration.vue#L205)

结论：

- 这是协议设计和页面实现同时失配，不是单一 bug。

### 5.2 跟踪接口与前端请求不兼容

证据：

- `tracking_api()` 只读 `request.json` 的 `input_path` 和 `rect`  
  [backend/applications/api/analysis.py](/home/livablecity/GeoView/backend/applications/api/analysis.py#L276)
- 跟踪页直接把文件和 `rect` 串进 `FormData`  
  [frontend/src/views/mainfun/Tracking.vue](/home/livablecity/GeoView/frontend/src/views/mainfun/Tracking.vue#L207)
- 没有任何一步先把视频/图片序列上传为服务器路径

结论：

- 当前前端发出的不是后端定义过的请求结构。

### 5.3 跟踪页结果展示逻辑与后端返回结构不匹配

证据：

- 后端成功后返回的是字符串 URL  
  [backend/applications/interface/analysis.py](/home/livablecity/GeoView/backend/applications/interface/analysis.py#L418)
- 前端却要求 `data.results` 和 `data.output_path`  
  [frontend/src/views/mainfun/Tracking.vue](/home/livablecity/GeoView/frontend/src/views/mainfun/Tracking.vue#L225)

结论：

- 就算跟踪脚本成功，前端也可能不显示结果。

### 5.4 注册页结果展示逻辑与后端返回结构不匹配

证据：

- 注册接口成功仅 `return success_api()`  
  [backend/applications/api/analysis.py](/home/livablecity/GeoView/backend/applications/api/analysis.py#L265)
- `success_api()` 默认 `data={}`  
  [backend/applications/common/utils/http.py](/home/livablecity/GeoView/backend/applications/common/utils/http.py#L6)
- 前端却把 `res.data.data` 当成结果数组  
  [frontend/src/views/mainfun/Registration.vue](/home/livablecity/GeoView/frontend/src/views/mainfun/Registration.vue#L242)

结论：

- 即使后端执行成功，注册页即时结果区也可能为空。

### 5.5 跟踪能力本身只是“简化版单目标传统跟踪”

证据：

- 脚本头部自述“模拟/简化版”  
  [backend/applications/interface/hf_tracking.py](/home/livablecity/GeoView/backend/applications/interface/hf_tracking.py#L7)
- 仅依赖 `CSRT/MIL`  
  [backend/applications/interface/hf_tracking.py](/home/livablecity/GeoView/backend/applications/interface/hf_tracking.py#L45)
- 输出只有 bbox 和固定 `score=1.0/0.0`  
  [backend/applications/interface/hf_tracking.py](/home/livablecity/GeoView/backend/applications/interface/hf_tracking.py#L90)

结论：

- 无法支撑“全域静态目标跟踪与预警”的产品叙述。

### 5.6 跟踪器兼容性分支写错

证据：

- `except AttributeError` 后仍再次调用 `cv2.TrackerCSRT_create()`  
  [backend/applications/interface/hf_tracking.py](/home/livablecity/GeoView/backend/applications/interface/hf_tracking.py#L47)

结论：

- 对 OpenCV 版本差异的兼容处理基本无效。

### 5.7 配准能力实际上固定为 LoFTR `outdoor`

证据：

- 注册模型列表里暴露 `hf:kornia/loftr`  
  [backend/applications/api/model.py](/home/livablecity/GeoView/backend/applications/api/model.py#L69)
- 实际脚本固定 `KF.LoFTR(pretrained='outdoor')`  
  [backend/applications/interface/hf_registration.py](/home/livablecity/GeoView/backend/applications/interface/hf_registration.py#L35)
- 项目现有核验文档也已指出页面模型选择器不会改变实际执行  
  [docs/Model_Usage_Dependencies.md](/home/livablecity/GeoView/docs/Model_Usage_Dependencies.md#L327)

结论：

- 页面上的“模型选择”在当前实现里几乎是无效 UI。

### 5.8 跟踪页模型选择器同样只是展示用

证据：

- 模型列表返回 `hf:opencv/csrt`  
  [backend/applications/api/model.py](/home/livablecity/GeoView/backend/applications/api/model.py#L78)
- `tracking_api()` 不接收也不传递 `model_path`  
  [backend/applications/api/analysis.py](/home/livablecity/GeoView/backend/applications/api/analysis.py#L282)
- 项目文档也明确指出 `tracking_api()` 未把前端 `model_path` 传入执行层  
  [docs/Model_Usage_Dependencies.md](/home/livablecity/GeoView/docs/Model_Usage_Dependencies.md#L355)

### 5.9 本地部署文档没有把所需 HF/Kornia 环境讲完整

证据：

- 安装文档只教创建 `PaddleRS37`  
  [install.md](/home/livablecity/GeoView/install.md#L3)
- 只教 `pip install -r backend/requirements.txt`  
  [install.md](/home/livablecity/GeoView/install.md#L56)
- 但子进程执行依赖 `HFPyTorch310`  
  [backend/applications/interface/hf_inference_caller.py](/home/livablecity/GeoView/backend/applications/interface/hf_inference_caller.py#L339)

结论：

- 按 `install.md` 做的本地环境，大概率无法运行这两项能力。

### 5.10 测试覆盖非常薄，只验证参数结构，不验证链路可用性

证据：

- `test_registration_api_structure()` 只测空 JSON / 空列表  
  [backend/test_new_features.py](/home/livablecity/GeoView/backend/test_new_features.py#L40)
- `test_tracking_api_structure()` 只测空 JSON  
  [backend/test_new_features.py](/home/livablecity/GeoView/backend/test_new_features.py#L54)

结论：

- 当前仓库里几乎没有可以证明这两条功能链路实际跑通的自动化证据。

## 6. 可推断的可复现症状

基于代码和文档，我认为以下症状基本可以复现，且复现门槛不高。

### 6.1 注册页点击“开始配准”后直接失败，或报请求异常

复现方式：

1. 打开注册页
2. 直接上传两组文件
3. 点击“开始配准”

原因：

- 前端发 `FormData`
- 后端按 JSON 读取 `list`

可能表现：

- 后端报参数缺失
- 请求被 Flask 视为非 JSON
- 页面提示“请求发生错误”或“配准失败”

对应证据：

- [frontend/src/views/mainfun/Registration.vue](/home/livablecity/GeoView/frontend/src/views/mainfun/Registration.vue#L238)
- [backend/applications/api/analysis.py](/home/livablecity/GeoView/backend/applications/api/analysis.py#L252)

### 6.2 跟踪页点击“开始跟踪”后直接失败

复现方式：

1. 打开跟踪页
2. 上传视频或图片序列
3. 手工框选初始框
4. 点击“开始跟踪”

原因：

- 前端发 `FormData`
- 后端需要 `input_path` JSON

可能表现：

- 页面提示“请求失败”
- 后端提示缺少输入视频/图像序列或初始框

对应证据：

- [frontend/src/views/mainfun/Tracking.vue](/home/livablecity/GeoView/frontend/src/views/mainfun/Tracking.vue#L224)
- [backend/applications/api/analysis.py](/home/livablecity/GeoView/backend/applications/api/analysis.py#L282)

### 6.3 跟踪后端即使成功，页面仍不显示结果视频

复现前提：

- 假设手工构造正确 JSON 请求，后端成功跑完

可能表现：

- 后端返回成功
- 页面仍显示“跟踪失败”或结果视频为空

原因：

- 后端返回字符串 URL
- 前端按对象结构读取 `results` / `output_path`

对应证据：

- [backend/applications/api/analysis.py](/home/livablecity/GeoView/backend/applications/api/analysis.py#L305)
- [frontend/src/views/mainfun/Tracking.vue](/home/livablecity/GeoView/frontend/src/views/mainfun/Tracking.vue#L225)

### 6.4 配准后端即使成功，注册页也不展示即时结果列表

复现前提：

- 假设手工构造正确 JSON 请求，后端成功跑完

可能表现：

- 页面提示“配准成功”
- 但 `resultArr` 为空或不是可渲染结构

原因：

- 后端没有返回结果数组
- 前端却按数组渲染

对应证据：

- [backend/applications/api/analysis.py](/home/livablecity/GeoView/backend/applications/api/analysis.py#L265)
- [frontend/src/views/mainfun/Registration.vue](/home/livablecity/GeoView/frontend/src/views/mainfun/Registration.vue#L242)

### 6.5 跟踪在某些 OpenCV 环境中会退化到 MIL，甚至直接不可用

复现前提：

- 运行环境里的 CSRT 不在顶层命名空间，或者只在 `cv2.legacy`

可能表现：

- 明明环境支持 CSRT，但代码误判不可用
- 退回到 MIL
- 精度显著下降，或进一步抛错

对应证据：

- [backend/applications/interface/hf_tracking.py](/home/livablecity/GeoView/backend/applications/interface/hf_tracking.py#L45)
- [backend/applications/interface/hf_tracking.py](/home/livablecity/GeoView/backend/applications/interface/hf_tracking.py#L50)

### 6.6 配准面对大尺寸遥感图时可能超时、OOM 或匹配不足

复现前提：

- 输入高分辨率遥感图
- 或多模态差异很强的图对

可能表现：

- 子进程运行很慢
- 超时
- “Not enough matches found.”
- “Homography estimation failed.”

对应证据：

- [backend/applications/interface/hf_registration.py](/home/livablecity/GeoView/backend/applications/interface/hf_registration.py#L48)
- [backend/applications/interface/hf_registration.py](/home/livablecity/GeoView/backend/applications/interface/hf_registration.py#L56)
- [backend/applications/interface/hf_inference_caller.py](/home/livablecity/GeoView/backend/applications/interface/hf_inference_caller.py#L304)

## 7. 按优先级排序的修复建议

下面按“先恢复基本可用，再解决能力缺口”的顺序给建议。

### P0：统一请求协议，强制两页回到项目标准上传流

建议：

1. 注册页和跟踪页都先走 `/api/file/upload`
2. 再用 JSON 调 `/api/analysis/registration` / `/api/analysis/tracking`
3. 后端 API 不再尝试直接接原始文件流，除非显式新增 multipart 支持并写清协议

原因：

- 这是当前最明确的阻断项
- 也能顺便复用 TIFF 转换、落盘、统一命名、历史记录体系

### P0：修正 API 返回结构，使前端和后端契约一致

建议：

- `registration_api()` 成功后返回配准结果数组
- `tracking_api()` 成功后返回结构化对象，例如：
  - `output_path`
  - `results`
  - `rect`

或者反过来调整前端，但必须双方一致，不能再靠“注释里的猜测”。

### P0：把跟踪页“图像序列文件夹支持”做成真功能，或者先下线文案

建议二选一：

1. 真正支持目录路径 / JSON 序列列表 / 服务端落盘后的序列引用
2. 暂时只支持单视频，并删除“图像序列文件夹”宣传

当前状态下，这个能力是 UI 虚标。

### P1：补齐并统一运行环境说明

建议：

- 明确文档中这两项能力依赖 `HFPyTorch310`
- 把 `install.md` 补到和 `Dockerfile` 一致
- 把 `backend/requirements-hf.txt` 补齐到至少包含：
  - `kornia`
  - 适配的 OpenCV 版本 / 是否需要 contrib
  - 可能的 `huggingface_hub`
  - 这两条脚本实际依赖的全部包

否则当前“手工安装指南”和“实际运行要求”是割裂的。

### P1：修正跟踪器兼容性分支

建议：

- 显式检测：
  - `cv2.TrackerCSRT_create`
  - `cv2.legacy.TrackerCSRT_create`
  - `cv2.TrackerMIL_create`
  - `cv2.legacy.TrackerMIL_create`
- 记录实际使用的 tracker 类型到日志 / 返回值

这能避免“环境支持但代码没用上”的低级问题。

### P1：把模型选择器做实，或取消伪选择器

当前两页都有模型选择 UI，但后端不消费 `model_path`。建议：

1. 要么真正传递并路由不同后端实现
2. 要么删掉前端选择器，只保留“当前实现说明”

否则用户会误以为模型可切换。

### P2：补最小可用的端到端测试

建议至少新增：

- 注册接口：上传 -> 组 pair -> 返回结果数组 -> 历史记录入库
- 跟踪接口：上传视频 -> 传初始框 -> 返回视频 URL / JSON 结果
- 前后端契约测试：验证返回字段名

仅靠“空 JSON 参数校验”不足以证明功能可用。

### P2：重新界定“跟踪”和“配准”的产品表述

建议：

- 如果短期内仍是 OpenCV CSRT 单目标方案，页面和文档应明确标注“单目标传统跟踪演示版”
- 如果短期内仍是 LoFTR + 单应矩阵方案，页面和文档应明确标注“二维图像配准演示版，不等同于完整遥感多模态几何配准”

这样至少能降低误导。

### P3：算法层升级方向

如果后续要把功能做实，建议方向如下：

- 跟踪：
  - 明确是单目标还是多目标
  - 明确是否要支持检测-跟踪联动
  - 如果目标真是长时序遥感/卫星视频，需引入更适合的时序目标跟踪或 MOT 方案，而不是仅靠 CSRT
  - “预警”需要单独的事件逻辑，不会自然从 tracker 里长出来
- 配准：
  - 明确是否真要支持 SAR/光学
  - 补充多尺度、分块、失败回退、匹配质量评分
  - 必要时引入地理坐标先验、重采样和遥感专用配准策略

## 8. 开放问题 / 不确定项

以下问题当前无法仅凭仓库内容完全确认，需要产品/开发者进一步澄清。

1. 当前生产部署是否一律走 Docker？
   如果是，那么 `HFPyTorch310` 缺失的问题在生产上可能较轻；如果存在手工部署或离线迁移，问题会明显加重。

2. 跟踪页是否本来计划只做“演示版单目标视频跟踪”？
   当前代码与“全域静态目标跟踪与预警”之间差距极大，不清楚这是过渡实现，还是需求表述没有同步收敛。

3. 配准页是否真的要求支持 SAR/光学？
   现有实现显然朝“通用二维图像特征匹配”方向走，若产品真要多模态遥感配准，现方案只能算最初级原型。

4. 当前前端页面是否有人实际联调过？
   `Registration.vue` 和 `Tracking.vue` 里有大量“猜测后端可能如何工作”的注释，这通常说明页面很可能没有完成闭环联调。

5. 历史记录是否被用作注册页/跟踪页的主要结果展示入口？
   如果前端本意是不展示即时返回，只通过历史记录回显，那也需要页面明确刷新历史，而不是直接假设 `res.data.data` 就是结果数组。

6. TIFF / 遥感原始数据是否是这两页的重要输入？
   如果是，那么当前绕过 `/api/file/upload` 的设计问题就更严重，因为它跳过了项目已有的 TIFF 处理链路。

## 结论

当前“目标跟踪”和“配准/对齐”之所以问题明显，不是单点实现瑕疵，而是三层问题叠加：

1. 前后端接口契约没有打通
2. 运行环境和部署文档没有完全对齐
3. 当前算法实现能力明显低于产品文案和测试文档的目标级别

如果只修其中一层，例如只改一点前端字段名，问题仍然会继续暴露。合理的修复顺序应当是：

1. 先修协议和返回结构
2. 再补齐环境与测试
3. 最后再决定是收缩产品承诺，还是升级算法实现
