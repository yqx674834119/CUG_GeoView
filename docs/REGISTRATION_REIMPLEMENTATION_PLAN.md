# GeoView 配准功能重构说明

## 目标

本次重构的目标不是一次性把 ESA SNAP 全流程搬进 GeoView，而是先把“多模态配准”从不可用状态重建为一个**能上传、能自动配对、能返回结果、能入库、能下载**的工程基线。

重点场景：

- Sentinel-1 / Sentinel-2 风格的 SAR-光学配准
- 遥感切片级快速对齐与人工复核
- 先解决前后端闭环，再逐步接入更重的外部流水线

## 当前一阶段实现

### 前端

- 保持 GeoView 现有两段式上传风格：先 `/api/file/upload`，再 `/api/analysis/registration`
- 注册页支持参考影像 / 待配准影像双列表上传
- 前端先做自动配对预览：
  - 优先按文件名去扩展名精确匹配
  - 匹配不到时按剩余顺序回退
- 页面直接展示四类结果：
  - 参考影像
  - 待配准影像
  - 配准结果
  - 叠加预览

### 后端

- 新注册接口契约：
  - `POST /api/analysis/registration`
  - 入参：
    - `model_path`
    - `list: [{ first, second, pair_name, pairing_strategy }]`
  - 其中：
    - `first` = 参考影像
    - `second` = 待配准影像
- 当前输出：
  - `output_path`：配准后的 moving 结果
  - `overlay_path`：参考影像与结果叠加图
  - `checkerboard_path`：棋盘格复核图
  - `fixed_input / moving_input`：前端结果页回显原始输入所需路径
  - `method_used / transform_type / match_count / inlier_count / rmse`
- 批量模式为**逐对处理**：
  - 单对失败不会中断整批
  - 响应内保留 `status` 和 `message`
  - 历史记录只写入成功结果
- 成功结果写入历史记录：
  - `before_img` = fixed
  - `before_img1` = moving
  - `after_img` = registered moving
  - `data` = 核心配准元数据

### 算法策略

- `builtin:registration:auto`
  - 优先尝试 Kornia LoFTR
  - 若环境不满足或匹配失败，自动回退 OpenCV
- `builtin:registration:opencv`
  - 使用 SIFT/ORB/AKAZE + RANSAC 估计单应或仿射
- `hf:kornia/loftr`
  - 强制走 LoFTR 路线

为了提高 SAR-光学匹配稳定性，当前并不是直接对原图做关键点，而是先做：

- 灰度化
- CLAHE 增强
- Sobel 梯度幅值融合

这比直接拿原始 RGB 做 ORB 更适合当前“先把功能做可用”的目标。

## 为什么现在不直接强依赖 SNAP

Sentinel-1 真正工程化配准通常离不开 SNAP 图处理图谱，例如：

- 轨道文件更新
- 热噪声去除
- 辐射定标
- TOPS Split / Deburst
- Back-Geocoding / Co-registration
- Terrain Correction

但这些步骤会带来几个现实问题：

- 依赖重，部署链路明显变复杂
- 需要明确产品级输入约束，而当前 GeoView 前端还是通用图片/切片上传模式
- 一旦把 SNAP 直接塞进首版，很容易出现“接口在，但日常根本跑不通”的情况

因此本次采用分阶段路线：

- 阶段 1：先完成切片级可用配准基线
- 阶段 2：接入 AROSICS 作为地理配准增强选项
- 阶段 3：对 Sentinel-1 原始产品接 pyroSAR + SNAP 图编排

## 后续扩展建议

### 阶段 2：AROSICS 扩展

适合做成后端新增模型项，例如：

- `builtin:registration:arosics-global`
- `builtin:registration:arosics-local`

适用场景：

- 已具备较稳定的地理参考
- 目标是做更稳健的全局/局部纠偏
- 需要输出位移场或更可信的亚像素修正

### 阶段 3：pyroSAR + SNAP

建议新增单独流水线，而不是污染当前轻量接口：

- `pipeline:s1-s2-snap-coreg`
- 由后台任务或离线作业调度
- 输入应升级为产品目录或标准 SAFE 包，而不是单张 png/jpg

这条路线更适合：

- Sentinel-1 SAFE + Sentinel-2 L1C/L2A
- 带 DEM / 投影 / 地理纠正约束的正式生产流程
- 批量任务和长时运行

## API 约定

请求示例：

```json
{
  "model_path": "builtin:registration:auto",
  "list": [
    {
      "first": "/_uploads/photos/fixed_a.tif",
      "second": "/_uploads/photos/moving_a.tif",
      "pair_name": "fixed_a__moving_a",
      "pairing_strategy": "同名匹配"
    }
  ]
}
```

响应示例：

```json
{
  "code": 0,
  "msg": "配准完成，共 1/1 对成功",
  "data": {
    "results": [
      {
        "status": "success",
        "pair_name": "fixed_a__moving_a",
        "fixed_input": "/_uploads/photos/fixed_a.tif",
        "moving_input": "/_uploads/photos/moving_a.tif",
        "method_used": "kornia_loftr",
        "transform_type": "homography",
        "output_path": "/_uploads/photos/res/xxx_registered.png",
        "overlay_path": "/_uploads/photos/res/xxx_overlay.png",
        "checkerboard_path": "/_uploads/photos/res/xxx_checkerboard.png"
      }
    ],
    "summary": {
      "total_pairs": 1,
      "success_pairs": 1,
      "failed_pairs": 0
    }
  }
}
```

## 当前限制

- 当前输出以**可视化配准结果**为主，不保证完整保留原始 GeoTIFF 地理参考
- 还没有接入 SNAP 的 SAR 专项预处理链
- LoFTR 依赖 Torch/Kornia，环境不满足时会自动回退 OpenCV
- 当前是批内同步处理，不是异步任务队列

## 参考资料

- ESA SNAP Toolbox: https://step.esa.int/main/toolboxes/snap/
- pyroSAR 文档: https://pyrosar.readthedocs.io/en/latest/
- AROSICS 文档: https://danschef.git-pages.gfz-potsdam.de/arosics/doc/
- Kornia Feature / LoFTR: https://kornia.readthedocs.io/en/latest/feature.html
