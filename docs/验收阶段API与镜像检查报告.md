# GeoView 验收阶段 API 与镜像检查报告

生成时间：2026-05-11

## 1. 图像/视频请求方式

结论：通过。

- 上传入口保留为 `/api/file/upload`，使用 `multipart/form-data` 上传文件。
- 资源读取入口保留为 `/api/file/assets/photos/<path>` 和兼容入口 `/_uploads/photos/<path>`。
- 后端资源发送使用 Flask `send_file`，实现为：读取文件到 `BytesIO`，`seek(0)`，再 `send_file(...)`。
- 复杂图片/视频传输逻辑已移除：未保留 base64、data URL、JSON 图片/视频播放器、JSON visualization 传输模式。
- 最终 API 测试回读资源 MIME 校验通过：`image/png` 26 个、`image/jpeg` 17 个、`video/mp4` 3 个、`application/json` 3 个、`text/plain` 1 个；图片/视频/JSON 扩展名与 MIME 不匹配数量为 0。

扫描命令：

```bash
rg -n "base64|data:image|data:video|JsonImageVisualizer|TrackingJsonPlayer|asset_transport|preview_data_url|json_visualization|visualization_modes.*json|JSON 模式|json_only|/api/history|api/history|/api/analysis/show|历史记录" backend/applications frontend/src --glob '!frontend/src/assets/css/icons-new.css' --glob '!backend/model/**' --glob '!backend/runtime/**' -S
```

结果：无匹配。

## 2. 历史记录模块清除

结论：通过。

- 后端 `history` API 源码已删除，API 注册表中不再注册 history blueprint。
- 前端 `history` 页面、路由、API 文件已删除。
- 旧的 `/api/analysis/show/<type>` 历史查询入口已删除。
- 残留的 `__pycache__` 和空目录已清理。

扫描命令：

```bash
find backend/applications frontend/src -path '*history*' -o -path '*History*'
```

结果：无输出。

## 3. 后端镜像前端测试模式与健康检查

结论：通过。

- 后端镜像环境变量默认开启 `GEOVIEW_FRONTEND_ENABLED=true`。
- 后端镜像暴露 `5008` 和 `3000`，可同时启动后端和前端测试服务。
- 已移除后端镜像启动诊断脚本和复杂启动检查，仅保留基本启动信息。
- 健康检查入口：`GET /health`。
- `/health` 返回字段：`success`、`status`、`service`、`version`、`time`、`storage.upload_dir`、`storage.upload_dir_exists`。
- 前端右上角已加入 BaseURL 控件，显示当前 baseurl，支持运行时修改，兼容 `http://127.0.0.1:5008` 和 `172.20.20.xxx/xxx/5008/` 这类部署路径。

## 4. 纯 API GPU 测试

结论：通过。

最终报告：`docs/test-results/gpu-api-report-20260511-gpu-only-final-rerun.json`

运行环境：

- Docker GPU 容器内执行。
- `nvidia-smi` 可用。
- Paddle：`2.4.2`，`cuda_compiled=true`，`device_count=1`。
- PaddleRS 测试主环境未安装 torch；HF/MM/BoT-SORT 子进程分别在 PyTorch/MMSeg/BoTSORT conda 环境执行，日志中确认 `--device cuda` 或 `--device cuda:0`。

结果汇总：

- 总用例：25
- 通过：25
- 失败：0

已测试接口：

- `GET /health`
- `GET /api/system/ping`
- `GET /api/model/list/change_detection`
- `GET /api/model/list/object_detection`
- `GET /api/model/list/semantic_segmentation`
- `GET /api/model/list/classification`
- `GET /api/model/list/image_restoration`
- `GET /api/model/list/registration`
- `GET /api/model/list/tracking`
- `POST /api/analysis/change_detection`
- `POST /api/analysis/object_detection`
- `POST /api/analysis/semantic_segmentation`
- `POST /api/analysis/classification`
- `POST /api/analysis/image_restoration`
- `POST /api/analysis/registration`
- `POST /api/analysis/tracking`

已测试模型：

- 变化检测：`bit_256x256`
- 目标检测：`paddle_yolo`、`hf_conditional_detr_resnet50`、`hf_detr_resnet50`、`hf_waldo30`、`mmrotate_oriented_rcnn_r50_fpn_1x_dota_le90`
- 地物分类：`paddle_deeplabv3p`、`mmseg_cugrs`
- 场景分类：`resnet50`
- 图像复原：`hf_swin2sr_x2`、`hf_swin2sr_x4`
- 自动配准：`auto`、`loftr_outdoor`
- 目标跟踪：`auto`、`botsort`、`botsort_official`

GPU 强制策略：

- Paddle/HF/MMRotate/MMSeg/LoFTR/BoT-SORT 均拒绝 CPU fallback。
- OpenCV 配准、CSRT、KCF 属于 CPU 传统算法，已从可用模型列表禁用；直接调用会返回禁用错误。
- `tracking/auto` 已改为 GPU BoT-SORT。
- `registration/auto` 只走 GPU LoFTR，不再回退 OpenCV。

## 5. 镜像自包含检查

结论：通过。

后端镜像检查项：

- `/app/frontend/node_modules` 存在。
- `/app/frontend/dist` 存在。
- 后端模型权重存在，例如 `/app/backend/model/semantic_segmentation/mmseg_cugrs/checkpoint.pth`。
- Dockerfile 已改为构建阶段执行 `npm ci --no-audit` 和 `npm run build`，运行时不需要联网安装前端依赖。

前端镜像检查项：

- `/usr/share/nginx/html/index.html` 存在。
- `/docker-entrypoint.d/40-geoview-runtime-config.sh` 存在。
- `/usr/share/nginx/html/runtime-config.js` 可由入口脚本生成。

