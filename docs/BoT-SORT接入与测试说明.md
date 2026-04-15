# BoT-SORT 双版本接入与测试说明

更新日期：2026-04-08

## 1. 本次实现结论

当前 GeoView 的跟踪页只保留两个可执行版本：

1. `BoT-SORT 官方原始版（ReID）`
2. `BoT-SORT 工程集成版（Ultralytics + WALDO30）`

两者都属于“检测 + 关联”的多目标跟踪，但技术栈不同：

1. 官方版使用 `NirAharon/BoT-SORT` 原始技术栈，默认配置为 `BoT-SORT-ReID`
2. 工程版使用 `Ultralytics BoT-SORT`，默认检测器为 `StephanST/WALDO30`

前端已改为只展示这两个选项，且两者都不需要手工框选初始目标。

## 2. 环境与运行时

### 2.1 工程版

环境名：

`HFPyTorch310`

用途：

1. 运行 `Ultralytics + WALDO30` 工程版
2. 由主服务通过子进程调用

### 2.2 官方版

环境名：

`BoTSORTOfficial37`

用途：

1. 运行 `BoT-SORT + YOLOX + FastReID + TrackEval`
2. 对接官方 `MOT17` 验证流程

说明：

官方 README 参考环境原本更接近 `torch 1.11 + cu113`，但在本机上该组合无法识别 GPU，因此本次实际落地改为：

`torch 1.13.1 + cu117`

这是为了保证 RTX A4500 在当前机器上可以正常跑官方版验证，不改变你仓库主服务环境。

## 3. 当前前端行为

跟踪页现状如下：

1. 仅显示 `BoT-SORT 官方原始版（ReID）`
2. 仅显示 `BoT-SORT 工程集成版（Ultralytics + WALDO30）`
3. 不再显示 `auto / CSRT / KCF / 待审查占位项`
4. 页面文案改为上传时序图像序列即可运行
5. 两个版本统一提示“无需手工框选初始目标”

## 4. 关键脚本

### 4.1 资源准备

脚本：

`scripts/setup_botsort_mot17.py`

职责：

1. 准备 `MOT17.zip`
2. 准备官方 `BoT-SORT` 仓库
3. 准备 `TrackEval`
4. 下载官方检测和 ReID 权重

### 4.2 一键评测

脚本：

`scripts/evaluate_botsort_mot17.py`

职责：

1. 官方版跑 `MOT17 val`
2. 工程版跑同一套 `MOT17 val`
3. 统一通过 `TrackEval` 计算 `MOTA / IDF1 / HOTA`
4. 输出统一报告 JSON

新增参数：

`--reuse-existing`

用途：

复用已有跟踪结果，只重新跑 `TrackEval` 汇总，避免每次重跑全部序列。

### 4.3 接口可用性验证

脚本：

`scripts/test_tracking_api_mot17.py`

职责：

1. 从 `MOT17` 抽样标准序列帧
2. 调用现有 tracking API
3. 分别验证官方版和工程版
4. 校验 `runtime_variant / method_used / 视频 / 预览图 / 轨迹`

## 5. 数据与权重位置

运行时工作目录默认放在仓库外：

`/home/livablecity/geoview_runtime`

关键内容包括：

1. `datasets/MOT17`
2. `BoT-SORT`
3. `TrackEval`
4. `eval/mot17_dual_botsort`

工程版默认权重已经切换为当前实现中的强权重：

`WALDO30_yolov8l-p2_1024x1024.pt`

不再使用之前的轻量版 `WALDO30_yolov8n_640x640.pt` 作为默认值。

## 6. 推荐执行命令

### 6.1 准备资源

```bash
python scripts/setup_botsort_mot17.py \
  --runtime-root /home/livablecity/geoview_runtime \
  --official-env BoTSORTOfficial37 \
  --hf-env HFPyTorch310
```

### 6.2 运行双版本评测

首次全量执行：

```bash
python scripts/evaluate_botsort_mot17.py \
  --runtime-root /home/livablecity/geoview_runtime \
  --official-env BoTSORTOfficial37 \
  --hf-env HFPyTorch310
```

复用已有结果重新汇总：

```bash
python scripts/evaluate_botsort_mot17.py \
  --runtime-root /home/livablecity/geoview_runtime \
  --official-env BoTSORTOfficial37 \
  --hf-env HFPyTorch310 \
  --reuse-existing
```

### 6.3 验证接口

```bash
conda run -n PaddleRS37 python scripts/test_tracking_api_mot17.py \
  --runtime-root /home/livablecity/geoview_runtime
```

## 7. 本机实测结果

基于 `MOT17 val` 的 `TrackEval` 实测结果如下：

| 版本 | MOTA | IDF1 | HOTA | 是否满足 `MOTA>=0.70 && IDF1>=0.70` |
| --- | ---: | ---: | ---: | --- |
| 官方版 `BoT-SORT-ReID` | `0.78527` | `0.82058` | `0.69305` | 是 |
| 工程版 `Ultralytics + WALDO30` | `0.04758` | `0.12089` | `0.15098` | 否 |

对照官方 README 中 `BoT-SORT-ReID` 在 `MOT17 test` 声称成绩：

1. `MOTA = 0.805`
2. `IDF1 = 0.802`
3. `HOTA = 0.650`

当前本机官方版在 `MOT17 val` 上的结果与官方公开表现基本一致，且满足你的阈值要求。

工程版不满足阈值，原因非常明确：

1. `WALDO30` 不是为 `MOT17 pedestrian` 域专门训练
2. 在 `MOT17` 抽样接口实测中，工程版几乎没有稳定检出 `person`
3. 检测域偏移导致跟踪关联几乎无从发挥

## 8. 异常事件 Precision 指标说明

本轮正式验证数据为 `MOT17`，该数据集不包含异常事件标签，因此：

1. `异常事件检出 Precision >= 0.65` 本轮未评测
2. 结论必须写为 `Not Evaluated on MOT17`
3. 不能据此宣称已经满足异常预警指标

## 9. 接口实测结论

`scripts/test_tracking_api_mot17.py` 已实测通过，结论如下：

1. 官方版接口可调用成功
2. 工程版接口可调用成功
3. 两者都不要求传 `rect`
4. 两者都能返回视频、预览图和轨迹产物
5. 返回体 `runtime_variant` 正确区分为 `official / engineering`

其中抽样 `MOT17-02-FRCNN` 前 8 帧时：

1. 官方版产出 `165` 个 `person` 检测，`21` 条轨迹
2. 工程版仅产出 `1` 个低置信目标，且类别偏成 `Building`

这与最终 `MOT17` 指标表现是一致的。

## 10. 最终建议

如果你要在当前系统中保留两个版本并给前端使用，建议这样理解：

1. `BoT-SORT 官方原始版（ReID）` 作为正式高性能版本
2. `BoT-SORT 工程集成版（Ultralytics + WALDO30）` 作为遥感检测器联调版本

如果验收口径严格按你给的：

1. `MOTA >= 0.70`
2. `IDF1 >= 0.70`

那么当前只有官方版达标，工程版不达标。

## 11. 主要产物

评测总报告：

`/home/livablecity/geoview_runtime/eval/mot17_dual_botsort/dual_botsort_mot17_report.json`

官方版汇总：

`/home/livablecity/geoview_runtime/eval/mot17_dual_botsort/trackeval_output/botsort_official_reid/pedestrian_summary.txt`

工程版汇总：

`/home/livablecity/geoview_runtime/eval/mot17_dual_botsort/trackeval_output/botsort_engineering/pedestrian_summary.txt`

## 12. 参考链接

1. BoT-SORT 官方：<https://github.com/NirAharon/BoT-SORT>
2. MOT17 数据集：<https://motchallenge.net/data/MOT17.zip>
3. TrackEval 官方：<https://github.com/JonathonLuiten/TrackEval>
4. WALDO30 模型卡：<https://huggingface.co/StephanST/WALDO30>
