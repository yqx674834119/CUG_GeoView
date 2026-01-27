# GeoView 智能遥感解译平台 - 数据收集与任务分配文档

本文档用于指导数据收集任务，旨在为 GeoView 平台的全面测试提供高质量的遥感数据支持。
请负责数据收集的同事严格按照各类别的要求（来源、年份、数量、格式）进行收集。

## 1. 任务综述 (Overview)

**目的:** 对 GeoView 平台的五大核心功能（变化检测、目标检测、地物分类、场景分类、图像复原）进行真实场景下的压力测试与效果验证。
**数据原则:** 优先使用 **Sentinel-2 (哨兵2号)** 真实数据，辅以高质量开源数据集。
**交付格式:** 原始数据应包含 TIF (16bit) 与 JPG/PNG (8bit) 两种格式。

---

## 2. 变化检测 (Change Detection) 数据收集

**目标:** 收集前后两个时相的影像，用于检测地表变化（新建建筑、水体变化、植被破坏等）。

### 2.1 数据要求
*   **数据源:**
    *   **首选:** Sentinel-2 L2A 级数据 (ESA Copernicus Hub / GEE)。
    *   **补充:** Google Earth 历史影像 (用于人眼视觉对比验证)。
    *   **开源数据集:** LEVIR-CD (建筑变化), OSCD (城市变化)。
*   **时间跨度:** 间隔 **1-3年** 的影像对。
    *   *示例:* 2020年 vs 2023年。
*   **采集数量:** **30-50 对**。
*   **重点场景:**
    *   **城市扩张:** 城乡结合部的新建楼盘、道路。
    *   **自然资源:** 湖泊干涸/扩张、森林砍伐。
    *   **灾害:** 洪水淹没区域（前后对比）。

### 2.2 推荐开源数据集下载 (备用)
*   **LEVIR-CD:** [https://github.com/rcdaudt/DSIFN](https://github.com/rcdaudt/DSIFN) (建筑变化，高分辨率，可作为跨尺度测试)
*   **OSCD (Onera Satellite Change Detection):** [https://rcdaudt.github.io/oscd/](https://rcdaudt.github.io/oscd/) (基于 Sentinel-2，**强烈推荐**)

---

## 3. 目标检测 (Object Detection) 数据收集

**目标:** 收集包含特定人造或自然目标的影像，用于测试检测模型的准确率。

### 3.1 数据要求
*   **数据源:**
    *   DOTA v1.0 / v1.5 / v2.0 (最权威的遥感目标检测库)。
    *   DIOR Dataset。
*   **目标类别 (Class):**
    *   **飞机 (Plane)**: 机场区域。
    *   **油罐 (Storage Tank)**: 工业区。
    *   **船只 (Ship)**: 港口、海面。
    *   **桥梁 (Bridge)**: 河流交汇处。
    *   **车辆 (Vehicle)**: 需高分辨率影像 (可选测试)。
*   **采集数量:** 每个类别至少 **20 张** 典型图像。

### 3.2 推荐开源数据集下载
*   **DOTA (A Large-scale Dataset for Object Detection in Aerial Images):**
    *   [https://captain-whu.github.io/DOTA/](https://captain-whu.github.io/DOTA/)
    *   *注意:* DOTA 数据通常很大，只需下载 Validation Set 的一部分即可。

---

## 4. 地物分类 (Semantic Segmentation) 数据收集

**目标:** 收集像素级标注的影像，用于土地覆盖分类测试。

### 4.1 数据要求
*   **数据源:** Sentinel-2。
*   **场景:** 包含丰富地物类型的区域（同时包含水体、农田、森林、建筑）。
*   **采集数量:** **10-20 张** 大幅面影像 (1024x1024 或更大)。
*   **开源数据集参考:**
    *   **DeepGlobe Land Cover Classification Challenge**
    *   **GID (Gaofen Image Dataset)** (用于高分影像测试)

### 4.2 推荐 Sentinel-2 样片下载
*   请在 Copernicus Hub 下载 L2A 级数据，并提取 TCI (True Color), Band 4 (Red), Band 8 (NIR) 等波段。

---

## 5. 场景分类 (Scene Classification) 数据收集

**目标:** 收集代表特定场景类别的切片影像。

### 5.1 数据要求
*   **数据源:** AID (Aerial Image Dataset), UCMerced_LandUse。
*   **类别:**
    *   商业区 (Commercial)
    *   高密度住宅区 (Dense Residential)
    *   森林 (Forest)
    *   农田 (Farmland)
    *   港口 (Port)
    *   沙滩 (Beach)
*   **采集数量:** 每个类别 **10 张**。

### 5.2 推荐开源数据集下载
*   **AID Dataset:** [https://captain-whu.github.io/AID/](https://captain-whu.github.io/AID/)
*   **UC Merced Land Use Dataset:** [http://weegee.vision.ucmerced.edu/datasets/landuse.html](http://weegee.vision.ucmerced.edu/datasets/landuse.html)

---

## 6. 图像复原 (Image Restoration) 数据收集

**目标:** 收集低质量（模糊、噪声、低分辨率）影像，测试超分和去噪效果。

### 6.1 数据要求
*   **类型 A (去噪):** 含有真实感噪声的遥感影像（或人为添加高斯/椒盐噪声的 Sentinel-2 影像）。
*   **类型 B (超分辨率):** 低分辨率 Sentinel-2 影像 (如 60m 分辨率波段) 或人为下采样的影像。
*   **采集数量:** **20 张**。

---

## 7. 任务分配与交付表 (Task Assignment)

| 任务模块 | 负责人 | 截止日期 | 数据量要求 | 备注 |
| :--- | :--- | :--- | :--- | :--- |
| **变化检测 (CD)** | 待定 | TBD | 50 对 | 重点关注 OSCD 数据集 |
| **目标检测 (OD)** | 待定 | TBD | 100 张 | 需覆盖 DOTA 主要类别 |
| **地物分类 (Seg)** | 待定 | TBD | 20 张 | 需包含 Sentinel-2 L2A TIF 原图 |
| **场景分类 (Cls)** | 待定 | TBD | 60 张 | 6个类别，每类10张 |
| **图像复原 (IR)** | 待定 | TBD | 20 张 | 包含模糊和噪声对比组 |

**交付方式:**
请将收集的数据整理至共享网盘/服务器，并按照 `backend/test_data_comprehensive/` 的目录结构命名：
*   `/change_detection/`
*   `/object_detection/`
*   ...
