# GeoView 页面模型来源核验说明

核验日期：2026-03-23

## 1. 核验范围与原则

本文仅核验当前仓库中已经接入到前端页面、并且会通过 `GET /api/model/list/<model_type>` 暴露给前端选择器的模型来源。

本次核验同时参考了以下两类证据：

1. 仓库内证据
   - 前端页面：`frontend/src/views/mainfun/*.vue`
   - 模型列表接口：`frontend/src/api/upload.js`
   - 后端模型注册：`backend/applications/api/model.py`
   - 后端推理入口：`backend/applications/api/analysis.py`
   - 具体推理实现：`backend/applications/interface/*.py`
   - 本地模型元数据：`backend/model/**/model.yml`
2. 公开可核实来源
   - Hugging Face 模型卡
   - OpenMMLab / MMRotate / MMSegmentation 官方页面
   - OpenCV 官方文档
   - Kornia / 原论文官方仓库
   - 官方数据集页面

本文遵循以下保守原则：

- 只写仓库内能直接确认的信息。
- 如果是本地模型，且仓库没有记录其公开发布页、训练作者或原始训练脚本，则不做臆测。
- 如果某个结论来自标签集合或命名规则，而不是模型元数据直接声明，会明确标记为“推断”。
- 如果前端提供了模型选择，但后端实际没有按所选模型切换，会单独写明。

## 2. 全局模型接入方式

所有相关页面的模型选择器都通过同一前端接口获取：

- 前端：`frontend/src/api/upload.js`
- 方法：`getCustomModel(model_type)`
- 请求：`GET /api/model/list/<model_type>`

后端统一由 `backend/applications/api/model.py` 返回模型列表，来源分为两类：

- 本地 Paddle 模型：扫描 `backend/model/<task>/...` 下的 `model.yml`
- 内置外部模型：写死在 `HUGGINGFACE_MODELS` 中，实际既包含 Hugging Face，也包含 MMRotate、MMSegmentation、OpenCV/Kornia 这类“外部依赖入口”

## 3. 页面总览

| 页面 | 前端文件 | `model_type` | 当前可选模型来源概况 |
| --- | --- | --- | --- |
| 时序变化分析 | `frontend/src/views/mainfun/DetectChanges.vue` | `change_detection` | 当前仓库仅发现 1 个本地 Paddle 变化检测模型 |
| 智能目标识别 / 目标检测 | `frontend/src/views/mainfun/DetectObjects.vue` | `object_detection` | 本地 Paddle 1 个，Hugging Face 3 个，MMRotate 1 个 |
| 地物分类 / 语义分割 | `frontend/src/views/mainfun/Segmentation.vue` | `semantic_segmentation` | 本地 Paddle 1 个，MMSegmentation 1 个 |
| 场景分类 | `frontend/src/views/mainfun/Classification.vue` | `classification` | 当前仓库仅发现 1 个本地 Paddle 分类模型 |
| 影像超分重建 / 图像还原 | `frontend/src/views/mainfun/RestoreImgs.vue` | `image_restoration` | 当前暴露 2 个 Hugging Face 超分模型；本地目录未发现可用本地模型 |
| 多模态自动配准 | `frontend/src/views/mainfun/Registration.vue` | `registration` | 前端暴露 1 个 LoFTR 入口，但后端当前实际固定使用 Kornia LoFTR `outdoor` 权重 |
| 全域目标跟踪 | `frontend/src/views/mainfun/Tracking.vue` | `tracking` | 前端暴露 1 个 `hf:opencv/csrt` 入口，但后端当前实际固定使用 OpenCV CSRT，失败时退回 MIL |

## 4. 各页面模型明细

### 4.1 时序变化分析页

- 前端文件：`frontend/src/views/mainfun/DetectChanges.vue`
- 前端取模方式：`getCustomModel('change_detection')`
- 后端推理入口：`POST /api/analysis/change_detection`
- 后端执行实现：`backend/applications/interface/change_detection.py`

#### 模型 A：本地 `BIT`

| 字段 | 内容 |
| --- | --- |
| 仓库目录 | `backend/model/change_detection/bit_256*256` |
| 前端显示文案 | `BIT - 建筑物变化专用模型` |
| 模型全称 | `BIT` |
| 来源类型 | 本地导出模型 |
| 实际推理栈 | PaddleRS `pdrs.deploy.Predictor` |
| 可直接确认的结构信息 | `model.yml` 只明确写了 `Model: BIT`、`model_type: change_detector`、`num_classes: 2`、固定输入尺寸 `3x256x256` |
| 可直接确认的特点 | 二分类变化检测；执行时使用 `slider_predict` 做滑窗推理，窗口与步长由页面参数控制 |
| 官网 / 模型卡 | 仓库内未记录该导出模型对应的公开发布页，未查到可直接绑定到该本地目录的官方模型卡 |
| 训练数据集 | 仓库内未记录 |
| 数据集 URL | 仓库内未记录 |
| 证据 | `backend/model/change_detection/bit_256*256/model.yml`；`backend/applications/interface/change_detection.py` |

说明：

- `backend/applications/api/model.py` 给这个模型补了“基于 Transformer 架构”的展示文案，但这属于界面元数据，不足以单独证明该本地导出目录对应哪一个公开发布版本。
- 因为用户明确要求不要对本地模型瞎编，所以这里不继续外推到具体论文或公开 checkpoint。

### 4.2 智能目标识别 / 目标检测页

- 前端文件：`frontend/src/views/mainfun/DetectObjects.vue`
- 前端取模方式：`getCustomModel('object_detection')`
- 后端推理入口：`POST /api/analysis/object_detection`
- 后端执行实现：`backend/applications/interface/object_detection.py`

#### 模型 A：本地 `PPYOLO`

| 字段 | 内容 |
| --- | --- |
| 仓库目录 | `backend/model/object_detection/yolo` |
| 前端显示文案 | `PPYOLO - 通用遥感目标识别` |
| 模型全称 | `PPYOLO` |
| 来源类型 | 本地导出模型 |
| 实际推理栈 | PaddleRS `pdrs.deploy.Predictor` |
| 可直接确认的结构信息 | `model.yml` 写明 `Model: PPYOLO`，backbone 为 `ResNet50_vd_dcn`，输入尺寸 `608x608` |
| 可直接确认的类别 | `aircraft`、`oiltank`、`overpass`、`playground` |
| 可直接确认的特点 | 4 类目标检测，本地 Paddle 导出目录可直接用于后端推理 |
| 官网 / 模型卡 | 仓库内未记录该导出模型对应的公开发布页，无法确认其是否来自某个公开 PaddleDetection / PaddleRS checkpoint |
| 训练数据集 | 仓库内未记录 |
| 数据集 URL | 仓库内未记录 |
| 证据 | `backend/model/object_detection/yolo/model.yml`；`backend/applications/interface/object_detection.py` |

#### 模型 B：`facebook/detr-resnet-50`

| 字段 | 内容 |
| --- | --- |
| 模型选择值 | `hf:facebook/detr-resnet-50` |
| 前端显示文案 | `facebook/detr-resnet-50 - 全局上下文目标检测` |
| 模型全称 | DETR ResNet-50 |
| 来源类型 | Hugging Face 模型卡 + Facebook Research 官方 DETR 项目 |
| 实际推理栈 | 本仓库通过 `transformers` 的 `AutoImageProcessor` + `AutoModelForObjectDetection` 加载 |
| 架构 / 依赖 | Hugging Face Transformers；DETR（End-to-End Object Detection with Transformers），ResNet-50 backbone |
| 主要特点 | 端到端目标检测；不使用传统 NMS/anchor 管线；适合用全局注意力建模场景上下文 |
| 官网 / 模型卡 | 模型卡：https://huggingface.co/facebook/detr-resnet-50 ；官方仓库：https://github.com/facebookresearch/detr |
| 训练数据集 | COCO 2017 |
| 数据集 URL | https://cocodataset.org/ |
| 证据 | `backend/applications/api/model.py`；`backend/applications/interface/hf_object_detection.py` |

#### 模型 C：`microsoft/conditional-detr-resnet-50`

| 字段 | 内容 |
| --- | --- |
| 模型选择值 | `hf:microsoft/conditional-detr-resnet-50` |
| 前端显示文案 | `microsoft/conditional-detr-resnet-50 - 加速训练目标检测` |
| 模型全称 | Conditional DETR ResNet-50 |
| 来源类型 | Hugging Face 模型卡 + Conditional DETR 官方仓库 |
| 实际推理栈 | 本仓库通过 `transformers` 的 `AutoImageProcessor` + `AutoModelForObjectDetection` 加载 |
| 架构 / 依赖 | Hugging Face Transformers；Conditional DETR，ResNet-50 backbone |
| 主要特点 | 在 DETR 基础上引入 conditional cross-attention，以更快收敛和更稳定的定位作为主要卖点 |
| 官网 / 模型卡 | 模型卡：https://huggingface.co/microsoft/conditional-detr-resnet-50 ；官方仓库：https://github.com/Atten4Vis/ConditionalDETR |
| 训练数据集 | COCO 2017 |
| 数据集 URL | https://cocodataset.org/ |
| 证据 | `backend/applications/api/model.py`；`backend/applications/interface/hf_object_detection.py` |

#### 模型 D：`StephanST/WALDO30`

| 字段 | 内容 |
| --- | --- |
| 模型选择值 | `hf:StephanST/WALDO30` |
| 前端显示文案 | `StephanST/WALDO30 - 航拍多目标识别` |
| 模型全称 | WALDO30 |
| 来源类型 | Hugging Face 仓库 |
| 实际推理栈 | 本仓库会优先尝试 `transformers`，失败后回退到 Ultralytics；对于 `WALDO30`，代码会专门下载 `WALDO30_yolov8m_640x640.pt` 或 `WALDO30_yolov8n_640x640.pt`，因此实际更接近 Ultralytics YOLO 权重加载 |
| 架构 / 依赖 | Hugging Face Hub 作为权重来源；本仓库实际执行依赖 Ultralytics YOLO |
| 主要特点 | 面向航拍 / 俯视视角目标检测；模型卡描述为基于合成与半合成训练数据构建的 30 类场景 |
| 官网 / 模型卡 | 模型卡：https://huggingface.co/StephanST/WALDO30 |
| 训练数据集 | 模型卡明确说明训练数据集未公开发布，且权重 repo 未附带独立官方数据集主页 |
| 数据集 URL | 无公开 URL 可核实 |
| 证据 | `backend/applications/interface/hf_object_detection.py`；Hugging Face 模型卡 |

说明：

- 这里不能把 `WALDO30` 直接写成“标准 Hugging Face Transformers 检测模型”，因为本仓库实际上是通过 Ultralytics 加载其 `.pt` 权重文件。

#### 模型 E：`mmrotate:oriented_rcnn_r50_fpn_1x_dota_le90`

| 字段 | 内容 |
| --- | --- |
| 模型选择值 | `mmrotate:oriented_rcnn_r50_fpn_1x_dota_le90` |
| 前端显示文案 | `oriented_rcnn_r50_fpn_1x_dota_le90 - 定向目标检测 (Oriented RCNN)` |
| 模型全称 | Oriented R-CNN, ResNet-50 + FPN, 1x schedule, DOTA, `le90` angle version |
| 来源类型 | MMRotate 模型配置名 |
| 实际推理栈 | `mmrotate_inference.py` 中通过 `mim download mmrotate --config oriented_rcnn_r50_fpn_1x_dota_le90` 下载配置与权重，再由 MMRotate 推理 |
| 架构 / 依赖 | OpenMMLab MMRotate；Oriented R-CNN；ResNet-50 backbone；FPN neck |
| 主要特点 | 面向遥感旋转框检测；适合任意方向目标和密集排布目标 |
| 官网 / 模型卡 | MMRotate：https://github.com/open-mmlab/mmrotate ；文档 / 模型页可从 MMRotate 文档中检索该配置名 |
| 训练数据集 | DOTA（由配置名直接体现） |
| 数据集 URL | https://captain-whu.github.io/DOTA/dataset.html |
| 证据 | `backend/applications/api/model.py`；`backend/applications/interface/mmrotate_inference.py` |

说明：

- 该模型不是 Hugging Face 模型，而是 MMRotate 模型动物园入口。
- “ResNet-50 + FPN + DOTA + le90”来自配置名本身，可视为 MMRotate 的标准命名规则，不是本文主观猜测。

### 4.3 地物分类 / 语义分割页

- 前端文件：`frontend/src/views/mainfun/Segmentation.vue`
- 前端取模方式：`getCustomModel('semantic_segmentation')`
- 后端推理入口：`POST /api/analysis/semantic_segmentation`
- 后端执行实现：`backend/applications/interface/semantic_segmentation.py`

#### 模型 A：本地 `DeepLabV3P`

| 字段 | 内容 |
| --- | --- |
| 仓库目录 | `backend/model/semantic_segmentation/deeplab` |
| 前端显示文案 | `DeepLabV3P - 高精度地物分类` |
| 模型全称 | `DeepLabV3P` |
| 来源类型 | 本地导出模型 |
| 实际推理栈 | PaddleRS `pdrs.deploy.Predictor` |
| 可直接确认的结构信息 | `model.yml` 写明 `Model: DeepLabV3P`、`model_type: segmenter`、固定输入 `512x512` |
| 可直接确认的类别 | `cloud`、`shadow`、`snow`、`water`、`land` |
| 可直接确认的特点 | 5 类分割，本地 Paddle 模型 |
| 官网 / 模型卡 | 仓库内未记录该导出模型对应的公开发布页 |
| 训练数据集 | 仓库内未记录 |
| 数据集 URL | 仓库内未记录 |
| 证据 | `backend/model/semantic_segmentation/deeplab/model.yml`；`backend/applications/interface/semantic_segmentation.py` |

#### 模型 B：`mmseg:cc-ln/CUGRS`

| 字段 | 内容 |
| --- | --- |
| 模型选择值 | `mmseg:cc-ln/CUGRS` |
| 前端显示文案 | `cc-ln/CUGRS - 多要素地物分类` |
| 模型全称 | 仓库内展示名为 `cc-ln/CUGRS`；当前实现实际使用本地自定义 MMSeg 配置与本地 checkpoint |
| 来源类型 | 本地自定义 MMSegmentation 模型接入，不是在线拉取 Hugging Face 模型 |
| 实际推理栈 | `backend/applications/interface/mmseg_inference_caller.py` 将 `cc-ln/CUGRS` 固定映射到本地 `backend/model/mmseg_config/dinov3_swinV1.py` 和 `backend/model/mmseg_config/model.pth`，再由 `mmseg_segmentation.py` 在 MMSeg 环境中推理 |
| 架构 / 依赖 | MMSegmentation `EncoderDecoder`；backbone 为自定义 `DINOv3SwinEncoder`，其中同时加载 DINOv3 和 Swin 预训练权重；decode head 为 `UPerHead`；auxiliary head 为 `FCNHead` |
| 可直接确认的类别 | `grassland`、`forest`、`building`、`road`、`bareground`、`water` |
| 主要特点 | 6 类地物分割；本地配置明确采用 DINOv3 特征分支与 Swin 分支融合 |
| 官网 / 模型卡 | 截至本次核验，未查到 `cc-ln/CUGRS` 对应的可独立核实公开模型卡；当前仓库内能确认的是“本地配置 + 本地权重” |
| 训练数据集 | 本地配置里只看到内部路径 `data_root = '/home/featurize/data/yunnan_dataset'`，未提供公开数据集说明 |
| 数据集 URL | 未查到可核实公开 URL |
| 证据 | `backend/applications/interface/mmseg_inference_caller.py`；`backend/model/mmseg_config/dinov3_swinV1.py`；`backend/applications/interface/mmseg_segmentation.py` |

说明：

- 这里不要简单写成“来自 Hugging Face 的 `cc-ln/CUGRS` 模型”。当前代码并不是去下载 `cc-ln/CUGRS`，而是把这个字符串当作一个逻辑 ID，再映射到仓库自带的本地 config/checkpoint。
- 该实现中确实能确认用了 MMSegmentation、DINOv3、Swin、UPerHead，但无法从现有仓库材料中确认这个最终 checkpoint 的公开发布页与公开训练集说明。

### 4.4 场景分类页

- 前端文件：`frontend/src/views/mainfun/Classification.vue`
- 前端取模方式：`getCustomModel('classification')`
- 后端推理入口：`POST /api/analysis/classification`
- 后端执行实现：`backend/applications/interface/classification.py`

#### 模型 A：本地 `ResNet50_vd`

| 字段 | 内容 |
| --- | --- |
| 仓库目录 | `backend/model/classification/resnet` |
| 前端显示文案 | `ResNet50_vd - ResNet50_vd` |
| 模型全称 | `ResNet50_vd` |
| 来源类型 | 本地导出模型 |
| 实际推理栈 | PaddleRS `pdrs.deploy.Predictor` |
| 可直接确认的结构信息 | `model.yml` 写明 `Model: ResNet50_vd`、`model_type: classifier`、输入 `256x256`、类别数 `21` |
| 可直接确认的类别 | `agricultural`、`airplane`、`baseballdiamond`、`beach`、`buildings`、`chaparral`、`denseresidential`、`forest`、`freeway`、`golfcourse`、`harbor`、`intersection`、`mediumresidential`、`mobilehomepark`、`overpass`、`parkinglot`、`river`、`runway`、`sparseresidential`、`storagetanks`、`tenniscourt` |
| 主要特点 | 21 类场景分类，本地 Paddle 分类模型 |
| 官网 / 模型卡 | 仓库内未记录该导出模型的公开发布页 |
| 训练数据集 | [推断] 以上 21 个类别与 UC Merced Land Use Dataset 的标准 21 类完全一致，但 `model.yml` 未显式写明训练集名称 |
| 数据集 URL | [推断对应官方页] https://vision.ucmerced.edu/datasets/ |
| 证据 | `backend/model/classification/resnet/model.yml`；`backend/applications/interface/classification.py` |

说明：

- 这里可以说“高度疑似使用 UC Merced Land Use 类别体系”，但不能把它写成已被仓库明确证明的训练集来源。

### 4.5 影像超分重建 / 图像还原页

- 前端文件：`frontend/src/views/mainfun/RestoreImgs.vue`
- 前端取模方式：`getCustomModel('image_restoration')`
- 后端推理入口：`POST /api/analysis/image_restoration`
- 后端执行实现：`backend/applications/interface/image_restoration.py`

当前仓库状态说明：

- `backend/model/image_restoration/` 目录下没有发现可供 `get_paddle_models()` 扫描的本地可用恢复模型目录。
- 因此当前页面实际暴露给前端选择器的，是 `backend/applications/api/model.py` 中写死的 2 个 Hugging Face 超分模型。

#### 模型 A：`caidas/swin2SR-classical-sr-x2-64`

| 字段 | 内容 |
| --- | --- |
| 模型选择值 | `hf:caidas/swin2SR-classical-sr-x2-64` |
| 前端显示文案 | `caidas/swin2SR-classical-sr-x2-64 - 两倍细节增强` |
| 模型全称 | Swin2SR Classical Image Super-Resolution x2 |
| 来源类型 | Hugging Face 模型卡 |
| 实际推理栈 | `hf_super_resolution.py` 中使用 `Swin2SRImageProcessor` + `Swin2SRForImageSuperResolution` |
| 架构 / 依赖 | Hugging Face Transformers；Swin2SR |
| 主要特点 | 2 倍超分辨率重建；Transformer-based 图像超分 |
| 官网 / 模型卡 | 模型卡：https://huggingface.co/caidas/swin2SR-classical-sr-x2-64 ；官方仓库：https://github.com/mv-lab/swin2sr |
| 训练数据集 | 官方 Swin2SR 仓库说明其经典超分任务主要使用 DIV2K 与 Flickr2K；但该具体 Hugging Face 卡片未单独枚举 x2 checkpoint 的训练集明细 |
| 数据集 URL | DIV2K 官方页：https://data.vision.ee.ethz.ch/cvl/DIV2K/ ；Flickr2K 的稳定官方页面未在本次核验中单独确认 |
| 证据 | `backend/applications/interface/hf_super_resolution.py`；Hugging Face 模型卡；Swin2SR 官方仓库 |

#### 模型 B：`caidas/swin2SR-classical-sr-x4-64`

| 字段 | 内容 |
| --- | --- |
| 模型选择值 | `hf:caidas/swin2SR-classical-sr-x4-64` |
| 前端显示文案 | `caidas/swin2SR-classical-sr-x4-64 - 四倍高清重建` |
| 模型全称 | Swin2SR Classical Image Super-Resolution x4 |
| 来源类型 | Hugging Face 模型卡 |
| 实际推理栈 | `hf_super_resolution.py` 中使用 `Swin2SRImageProcessor` + `Swin2SRForImageSuperResolution` |
| 架构 / 依赖 | Hugging Face Transformers；Swin2SR |
| 主要特点 | 4 倍超分辨率重建；更适合较低分辨率输入的大倍数放大 |
| 官网 / 模型卡 | 模型卡：https://huggingface.co/caidas/swin2SR-classical-sr-x4-64 ；官方仓库：https://github.com/mv-lab/swin2sr |
| 训练数据集 | 与上面 x2 条目相同：Swin2SR 官方仓库说明经典超分任务主要使用 DIV2K 与 Flickr2K，但 x4 这张 Hugging Face 卡片未额外单列训练集说明 |
| 数据集 URL | DIV2K 官方页：https://data.vision.ee.ethz.ch/cvl/DIV2K/ ；Flickr2K 稳定官方页面未在本次核验中单独确认 |
| 证据 | `backend/applications/interface/hf_super_resolution.py`；Hugging Face 模型卡；Swin2SR 官方仓库 |

### 4.6 多模态自动配准页

- 前端文件：`frontend/src/views/mainfun/Registration.vue`
- 前端取模方式：`getCustomModel('registration')`
- 后端推理入口：`POST /api/analysis/registration`
- 后端执行实现：`backend/applications/interface/registration.py`

#### 模型 A：`hf:kornia/loftr`

| 字段 | 内容 |
| --- | --- |
| 模型选择值 | `hf:kornia/loftr` |
| 前端显示文案 | `kornia/loftr - LoFTR 深度特征配准` |
| 模型全称 | LoFTR（Local Feature TRansformer） |
| 来源类型 | 前端模型列表中登记为 `hf:kornia/loftr`，但当前后端实现并不是下载 Hugging Face 模型，而是直接调用 Kornia 内置 LoFTR |
| 实际推理栈 | `backend/applications/interface/hf_registration.py` 中固定执行 `KF.LoFTR(pretrained='outdoor')` |
| 架构 / 依赖 | Kornia；LoFTR Transformer 特征匹配 |
| 主要特点 | 免关键点检测的局部特征匹配；适合弱纹理、重复纹理和较大视角差异图像配准 |
| 官网 / 模型卡 | Kornia 文档：https://kornia.readthedocs.io/en/latest/models/loftr.html ；官方仓库：https://github.com/zju3dv/LoFTR |
| 训练数据集 | LoFTR 官方项目公开使用了 ScanNet 与 MegaDepth 等数据集；但当前仓库只明确写死了 `pretrained='outdoor'`，并未在代码中再次说明该 preset 对应的精确训练集映射 |
| 数据集 URL | ScanNet：https://www.scan-net.org/ ；MegaDepth：https://www.cs.cornell.edu/projects/megadepth/ |
| 证据 | `backend/applications/api/model.py`；`backend/applications/interface/registration.py`；`backend/applications/interface/hf_registration.py` |

非常重要的实现备注：

- 当前 `registration_api()` 并没有把前端选中的 `model_path` 传入 `registration()`。
- 也就是说，虽然页面上存在模型选择器，但当前实现实际上固定使用 `Kornia LoFTR outdoor`，并不会根据前端选择切换模型。

### 4.7 全域目标跟踪页

- 前端文件：`frontend/src/views/mainfun/Tracking.vue`
- 前端取模方式：`getCustomModel('tracking')`
- 后端推理入口：`POST /api/analysis/tracking`
- 后端执行实现：`backend/applications/interface/tracking.py`

#### 模型 A：`hf:opencv/csrt`

| 字段 | 内容 |
| --- | --- |
| 模型选择值 | `hf:opencv/csrt` |
| 前端显示文案 | `opencv/csrt - CSRT 目标跟踪` |
| 模型全称 | OpenCV TrackerCSRT |
| 来源类型 | 前端模型列表中登记为 `hf:opencv/csrt`，但当前后端实现并不是下载 Hugging Face 模型，而是直接调用 OpenCV Tracker API |
| 实际推理栈 | `backend/applications/interface/hf_tracking.py` 中调用 `cv2.TrackerCSRT_create()`；若不可用，则退回 `cv2.TrackerMIL_create()` |
| 架构 / 依赖 | OpenCV 传统跟踪器；CSR-DCF / CSRT 系列 |
| 主要特点 | 单目标跟踪；对尺度变化和一定遮挡有较好适应性；推理依赖传统相关滤波跟踪而非当前仓库内的深度学习 checkpoint |
| 官网 / 模型卡 | OpenCV 官方文档：https://docs.opencv.org/3.4/d2/da2/classcv_1_1TrackerCSRT.html |
| 训练数据集 | 不适用。当前实现调用的是 OpenCV 跟踪器 API，不存在一个在本仓库中被下载和切换的神经网络权重 |
| 数据集 URL | 不适用 |
| 证据 | `backend/applications/api/model.py`；`backend/applications/interface/tracking.py`；`backend/applications/interface/hf_tracking.py` |

非常重要的实现备注：

- 当前 `tracking_api()` 同样没有把前端选中的 `model_path` 传入 `tracking()`。
- 因而页面上虽然显示了一个“模型”，但当前实现实际上固定调用 OpenCV CSRT；`hf:` 前缀在这里更像一个前端登记字符串，而不是实际的 Hugging Face 模型依赖。

## 5. 当前仓库中无法可靠核实的项

以下内容在本次核验中不能被负责任地写成“已确认事实”：

1. 本地 `BIT` 导出目录对应的具体公开论文版本、官方仓库和训练数据集。
2. 本地 `PPYOLO` 导出目录对应的原始公开 checkpoint、训练集来源。
3. 本地 `DeepLabV3P` 导出目录对应的训练数据集来源。
4. 本地 `ResNet50_vd` 分类模型的训练集名称。根据 21 类标签可强烈怀疑是 UC Merced Land Use，但仓库没有直接写明。
5. `cc-ln/CUGRS` 是否存在独立公开模型卡。当前仓库能确认的是“逻辑 ID + 本地 config + 本地 checkpoint + 本地数据路径引用”，而不是可公开下载的官方模型页。
6. Swin2SR 两个具体 Hugging Face checkpoint 的逐项训练集明细。官方仓库给出了经典超分任务的常见训练集范围，但模型卡没有逐条展开。

## 6. 结论

如果只看“页面上的模型下拉框”，很容易误以为所有模型都来自同一种来源；但实际上当前项目里至少同时存在以下几种来源与执行方式：

- 本地 PaddleRS 导出模型
- Hugging Face 模型卡 + Transformers
- Hugging Face 仓库 + Ultralytics YOLO 权重
- MMRotate 模型动物园
- 本地自定义 MMSegmentation config/checkpoint
- Kornia 内置 LoFTR
- OpenCV TrackerCSRT

尤其需要注意两件事：

1. `Registration.vue` 与 `Tracking.vue` 虽然展示了模型选择入口，但当前后端并不会依据所选模型切换实现。
2. `semantic_segmentation` 里的 `cc-ln/CUGRS` 在当前仓库中实际是“本地 MMSeg 模型映射”，不能简单写成“在线第三方模型”。
