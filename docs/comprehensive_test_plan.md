# 全面测试计划与遥感数据指南

本文档旨在为 GeoView 智能遥感解译平台提供全面的测试指导，重点关注 Sentinel-2 数据及开源遥感数据集的测试应用。

## 1. 测试目标
确保平台核心功能（变化检测、目标检测、地物分类等）能够正确处理：
1. **Sentinel-2 多光谱/真彩色数据**（支持 TIF 和 JPG 格式）。
2. **开源遥感数据集**（如 DOTA, LEVIR-CD 等常见格式）。
3. **高并发与异常情况**下的系统稳定性。

---

## 2. 测试数据准备

为了方便测试，我们提供了两种数据源方案：

### 方案 A: 使用内置模拟数据生成器 (推荐快速验证)
我们编写了一个脚本，用于生成模拟 Sentinel-2 风格的测试数据（包含 TIF 和 JPG 格式）。
这些数据模拟了城市、森林、水体等典型遥感场景，并包含特定的测试目标（如飞机、油罐）。

**生成方法:**
在项目根目录下运行：
```bash
python3 backend/prepare_comprehensive_data.py
```
**数据输出目录:** `backend/test_data_comprehensive/`
- `change_detection/`: 双时相变化检测数据 (T1/T2)
- `object_detection/`: 包含模拟飞机和油罐的目标检测数据
- `semantic_segmentation/`: 混合地物分类数据
- `scene_classification/`: 典型场景分类数据
- `image_restoration/`: 模糊和噪声图像

### 方案 B: 使用真实开源遥感数据 (深度验证)
对于生产环境测试，建议下载少量的真实 Sentinel-2 数据切片。

**推荐数据源:**
1. **Sentinel-2 官方样片 (Copernicus Open Access Hub)**
   - 下载 L2A 级产品 (经过大气校正)。
   - 提取 TCI (True Color Image) 10m 分辨率波段用于测试。
2. **LEVIR-CD (变化检测)**
   - 适合测试建筑变化检测。
   - [下载地址 (GitHub)](https://github.com/rcdaudt/DSIFN)
3. **DOTA (目标检测)**
   - 包含飞机、船只、车辆等。
   - [官网](https://captain-whu.github.io/DOTA/)
4. **DeepGlobe (地物分类)**
   - 土地覆盖分类挑战赛数据。

---

## 3. 功能测试流程 (Walkthrough)

### 3.1 变化检测 (Change Detection)
**目标:** 识别两期影像中的地表变化（如城市扩张、植被减少）。
**测试数据:** `backend/test_data_comprehensive/change_detection/`
- `city_expansion_T1.tif` (前时相)
- `city_expansion_T2.tif` (后时相)

**测试步骤:**
1. 选择功能模块 "智能解译" -> "变化检测"。
2. 点击上传 "时相1" 和 "时相2" 图片。
3. 选择 `BIT_LEVIR` 或 `TinyCD` 模型。
4. 参数设置:
   - 预处理: 选择 "直方图匹配" (消除光照差异)。
   - 窗口大小: 256.
5. 点击 "开始解译"。
6. **预期结果:** 结果页面应高亮显示新增的建筑区域（模拟数据中为红色方块区域）。

### 3.2 目标检测 (Object Detection)
**目标:** 识别影像中的特定目标（飞机、油罐）。
**测试数据:** `backend/test_data_comprehensive/object_detection/`
- `airport_simulation.jpg` (模拟机场)
- `oil_storage_simulation.tif` (模拟油库，TIF格式)

**测试步骤:**
1. 切换至 "目标检测" 模块。
2. 上传 `airport_simulation.jpg`。
3. 模型选择: 推荐 `YOLO` 系列或 `Oriented R-CNN` (如有)。
4. 预处理: 可选 "锐化" 增强边缘。
5. 点击 "开始检测"。
6. **预期结果:** 系统应框选出图中的 "十" 字形模拟飞机目标。

### 3.3 地物分类 (Semantic Segmentation)
**目标:** 对影像进行像素级分类（水体、植被、建筑等）。
**测试数据:** `backend/test_data_comprehensive/semantic_segmentation/land_cover_sample.tif`

**测试步骤:**
1. 切换至 "地物分类" 模块。
2. 上传测试图片。
3. 模型选择: `UNet` 或 `DeepLabV3+`。
4. 点击 "开始解译"。
5. **预期结果:** 输出彩色掩膜图，不同颜色代表不同地物（模拟数据中蓝色为水体，绿色为森林，灰色为城市）。

### 3.4 场景分类 (Scene Classification)
**目标:** 识别整张影像的场景类别（如 "商业区", "森林", "港口"）。
**测试数据:** `backend/test_data_comprehensive/scene_classification/`

**测试步骤:**
1. 切换至 "场景分类" 模块。
2. 批量上传 `scene_urban.jpg` 和 `scene_forest.jpg`。
3. 点击 "开始分类"。
4. **预期结果:** 列表显示每张图的预测类别，准确率应较高。

### 3.5 图像复原 (Image Restoration)
**目标:** 去除影像噪声或提升分辨率。
**测试数据:** `backend/test_data_comprehensive/image_restoration/`
- `blurred_input.jpg` (模糊)
- `noisy_input.jpg` (噪声)

**测试步骤:**
1. 切换至 "图像复原" 模块。
2. 上传 `noisy_input.jpg`。
3. 选择去噪模型 (如 `DRNet` 或 `Restormer`)。
4. 点击 "开始复原"。
5. **预期结果:** 输出图像的噪点明显减少，纹理更清晰。

---

## 4. 自动化测试脚本

为了提高测试效率，我们提供了自动化 API 测试脚本。

**运行方式:**
1. 确保后端服务已启动:
   ```bash
   python app.py
   ```
2. 在另一个终端运行测试:
   ```bash
   python backend/test_api_comprehensive.py
   ```

该脚本将自动遍历上述所有接口，验证从上传到推理的全流程状态码和返回格式。

---

## 5. Docker 部署注意事项

针对 Sentinel-2 TIF 数据处理，请确保 Docker 环境中包含了 GDAL 库。
我们已在 `Dockerfile` 中确认安装了 `gdal` 和 `paddlepaddle`/`pytorch` 相关依赖。

如果您在测试 TIF 文件时遇到 "Driver not found" 错误，请检查 `LD_LIBRARY_PATH` 环境变量是否包含了 GDAL 的库路径。
