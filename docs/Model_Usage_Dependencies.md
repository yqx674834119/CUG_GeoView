# 平台模型使用说明与依赖项

为了更直观地展示 GeoView 项目中各个功能模块所依赖的后端模型情况，特梳理了以下细致的模型信息清单，包含页面名称、模型类别、模型名称、作用、输入输出以及对应的路径（在线/本机）与缓存信息。

## 详细模型清单表

| 页面名称 | 模型类别 | 模型名称 | 作用与特点 | 输入与输出 | 路径与存储位置 (在线地址 / 缓存或本机路径) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **智能目标识别**<br>(`DetectObjects.vue`) | 检测器<br>`detector` | **全局上下文目标检测**<br>(`facebook/detr-resnet-50`) | **通用目标检测**。端到端Transformer架构，全局上下文理解能力强，适合检测大场景下的物体。 | **输入**: 单/多张被选中的影像图及分析模式。<br>**输出**: 带有检测红框及置信度的渲染图，以及标注数据信息。 | **类型**: 在线预训练模型 (HuggingFace)<br>**地址**: [facebook/detr-resnet-50](https://huggingface.co/facebook/detr-resnet-50)<br>**缓存**: `/root/.cache/huggingface/` |
| | | **加速训练目标检测**<br>(`microsoft/conditional-detr-resnet-50`) | **通用目标检测**。采用条件交叉注意力机制，定位更精准。 | 同上 | **类型**: 在线预训练模型 (HuggingFace)<br>**地址**: [conditional-detr](https://huggingface.co/microsoft/conditional-detr-resnet-50)<br>**缓存**: `/root/.cache/huggingface/` |
| | | **航拍多目标识别**<br>(`StephanST/WALDO30`) | **航拍图像目标检测**。YOLOv8架构，支持识别车辆、建筑、船只等12类民用目标。 | 同上 | **类型**: 在线预训练模型 (HuggingFace)<br>**地址**: [StephanST/WALDO30](https://huggingface.co/StephanST/WALDO30)<br>**缓存**: `/root/.cache/huggingface/` |
| | | **定向目标检测**<br>(`oriented_rcnn_r50_fpn_1x_dota_le90`) | **航拍图像旋转目标检测**。Oriented R-CNN，基于DOTA数据集训练，适用于密集排列物体。 | 同上 | **类型**: 在线预训练模型 (MMRotate)<br>**地址**: [MMRotate Model Zoo](https://github.com/open-mmlab/mmrotate)<br>**缓存**: `/root/.cache/torch/` 等 |
| | | **YOLO目标检测**<br>(`yolo`) | **通用遥感目标识别及快速检测**。针对遥感图像优化，在处理推理速度和定位精度方面有很好的权衡。 | 同上 | **类型**: 本地模型 (Paddle)<br>**本地路径**: `model/object_detection/yolo` |
| **地物分类**<br>(`Segmentation.vue`) | 分割模型<br>`segmenter` | **多要素地物分类**<br>(`cc-ln/CUGRS`) | **地物分类**。结合DinoV3和SwinTransformer，支持对草地、林地、建筑、道路、水体等做精确分割。 | **输入**: 待分类影像。<br>**输出**: 基于类别不同颜色进行涂色映射的分割图。 | **类型**: 在线预训练模型 (MMSegmentation)<br>**请求标识**: `mmseg:cc-ln/CUGRS`<br>**缓存**: `/root/.cache/huggingface/` |
| | | **高精度地物分类**<br>(`deeplab`) | **通用的逐像素分割判定**。拥有精细的边缘信息提取及较好的泛化性表现。 | 同上 | **类型**: 本地模型 (Paddle)<br>**本地路径**: `model/semantic_segmentation/deeplab` |
| **时序变化分析**<br>(`DetectChanges.vue`) | 变化检测<br>`change_detector` | **建筑物变化专用模型**<br>(`bit_256*256`) | **特征匹配及变化检测**。擅长捕捉场景下规则建筑物的变化，基于BIT(Bitemporal Image Transformer)对抗模型提取差值特征并产生结果。 | **输入**: 包含 `first` 和 `second` 的不同同坐标配对影像对集合，设定分析的窗口大小、步长及增强项参数。<br>**输出**: 生成二值化的图像变化蒙版，并产生相关的像素变化数量或对象百分比分析结果。 | **类型**: 本地模型 (Paddle)<br>**本地路径**: `model/change_detection/bit_256*256` |
| **图像清晰化重建**<br>(`RestoreImgs.vue`) | 重建器<br>`restorer` | **两倍细节增强**<br>(`caidas/swin2SR-classical-sr-x2-64`) | **图像超分辨率 (2x)**。基于Swin Transformer，优秀的高频细节恢复能力。 | **输入**: 低分辨率或感官模糊度较高的照片。<br>**输出**: 算法恢复和像素清晰度重建后的图片文件地址 URL 。 | **类型**: 在线预训练模型 (HuggingFace)<br>**地址**: [caidas/swin2SR...x2](https://huggingface.co/caidas/swin2SR-classical-sr-x2-64)<br>**缓存**: `/root/.cache/huggingface/` |
| | | **四倍高清重建**<br>(`caidas/swin2SR-classical-sr-x4-64`) | **图像超分辨率 (4x)**。高放大倍数下的结构一致性补偿。 | 同上 | **类型**: 在线预训练模型 (HuggingFace)<br>**地址**: [caidas/swin2SR...x4](https://huggingface.co/caidas/swin2SR-classical-sr-x4-64)<br>**缓存**: `/root/.cache/huggingface/` |
| **场景分类**<br>(`Classification.vue`) | 场景分类<br>`classifier` | **高精度场景分类**<br>(`resnet`) | **全局场景判别**。提取整副图片的总体特征进而分类图像的主题。 | **输入**: 全局目标图。<br>**输出**: 单张图片的预分类总标签与对应的置信度权重百分比。 | **类型**: 本地模型 (Paddle)<br>**本地路径**: `model/classification/resnet` |
| **多模态自动配准**<br>(`Registration.vue`) | 配准器<br>`register` | **LoFTR 深度特征配准**<br>(`kornia/loftr`) | **多视角图片关联**。基于弱特征匹配算法，跨模态自动找出相似拼接位置并实现配准。 | **输入**: `first` 和 `second` 两张待配准融合图片。<br>**输出**: 图片配对匹配点显示与带特征描绘的融合图。 | **类型**: 在线预训练模型 (HuggingFace)<br>**地址**: [kornia/loftr](https://huggingface.co/kornia/loftr)<br>**缓存**: `/root/.cache/huggingface/` |
| **全域静态目标跟踪**<br>(`Tracking.vue`) | 跟踪追踪<br>`tracker` | **CSRT 目标跟踪**<br>(`opencv/csrt`) | **单目标持续追踪预警**。判别滤波器(DCF)以适配长序列或形变目标的稳定跟踪。 | **输入**: 输入视频/图像序列及首帧手动标记边界框 (b-box) 的四个基准点。<br>**输出**: 在视频每一帧锁定标记出目标的跟踪框信息响应及帧片段返回。 | **类型**: 在线或内置基础调用算法 (OpenCV/HF)<br>**地址**: 通常作为库内置计算调用获取<br>**缓存**: 无需额外的大体积权重存放 |

## 总结说明

- **挂载建议**: `docker-compose.yml` 中已新增 `/root/.cache/huggingface/` 和 `/root/.cache/torch/`，以及 `/root/.paddle/` 的数据卷 (volume) 挂载，这三种目录是以上各算法库默认离线并缓存**在线模型文件**所处的地方。
- **本地映射**: 以 `model/` 开处的类别，如 `model/change_detection/bit_256*256` 均为代码部署内部确切存在的模型，其内包含 `model.yml` 及所需参数。
