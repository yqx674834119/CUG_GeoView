# GeoView 交付规范

本文件给新会话快速接手用。目标是：本机验证前后端镜像，推送到 Aliyun，中转机器拉取镜像并打包到 U 盘，确保交付物可离线导入。

## 基本原则

- 不要回滚用户已有改动；先用 `git status --short` 看清楚工作区。
- 镜像必须同时维护两个 tag：明确版本 tag 和 `latest`。版本 tag 格式沿用 `YYYYMMDD-purposeN`，例如 `20260515-smalltarget2`。
- `docker-compose*.yml` 默认使用 `latest`，便于本机或现场直接拉取当前版本；交付记录、验收报告、U 盘打包命令必须使用明确版本 tag 和 digest，不能只记录 `latest`。
- 后端镜像必须包含所有模型、权重和依赖；内网部署时不能依赖公网下载。
- 后端修改后必须做 H100 GPU/API 全量回归，要求所有模型通过，不能只验证出问题的模型。
- 前端修改后必须重新构建前端镜像，并确认页面能访问后端接口。
- 本机验收按前后端分离启动：后端容器和前端容器分别启动，不启动 MySQL，不启动矿山服务。
- 每次构建并推送新的前端或后端镜像后，必须同步替换本机正在运行的对应容器到新镜像，并做健康检查；不要只完成镜像构建和推送。
- 集群对单个响应大小有限制，前后端不得新增大响应直传。所有模型分析接口必须返回 `transport_manifest`，前端通过 `/api/transport/result/<result_id>/chunk?...` 拉取分片结果；所有后端图片/视频等资产预览必须通过 `/api/transport/asset/chunk?path=...&offset=...&limit=...` 拉取，不能直接把 `/api/file/assets/photos/...` 作为最终展示地址。

## 当前镜像信息

后端仓库：

```bash
BACKEND_REGISTRY=crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/cugrs
BACKEND_TAG=20260519-trackingasync1
BACKEND_IMAGE=${BACKEND_REGISTRY}:${BACKEND_TAG}
BACKEND_LATEST_IMAGE=${BACKEND_REGISTRY}:latest
BACKEND_DIGEST=sha256:5cc04a8b3ff05a2865012951a36ba559bbc41424ad3d6fc2a9aa534b8f427df2
```

前端仓库：

```bash
FRONTEND_REGISTRY=crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/geoview-frontend
FRONTEND_TAG=20260519-trackingasync1
FRONTEND_IMAGE=${FRONTEND_REGISTRY}:${FRONTEND_TAG}
FRONTEND_LATEST_IMAGE=${FRONTEND_REGISTRY}:latest
FRONTEND_DIGEST=sha256:1fe8d4690c651cdf816c9114cc913cdac1b8415af86ac092d70be65c884b1a19
```

## Paddle 变更与当前问题

- Paddle 模型已支持前端选择 `GPU/CPU` 推理。前端通过 `paddle_device` 传参，后端统一用 `resolve_paddle_device()` 解析；`cpu` 会显式走 CPU，`gpu` 会要求容器内 Paddle CUDA 可用，不可用时拒绝静默回退。
- 前端已接入 `PaddleRuntimeSelector`。变化检测默认 `cpu`；通用遥感目标识别默认 `cpu`；其他 Paddle 页面保留按页面配置显示设备选项。
- 后端 Paddle 调用统一经过 `paddle_use_gpu()`，GPU 模式会检查 `paddle.device.is_compiled_with_cuda()`、`paddle.device.cuda.device_count()` 和 `CUDA_VISIBLE_DEVICES`，避免现场 GPU 不可用时悄悄跑 CPU。
- 后端回归脚本 `scripts/geoview_gpu_api_test.py` 支持 `--paddle-devices gpu,cpu`，后端交付回归必须同时覆盖 Paddle GPU 和 CPU。
- 不要修改或回滚历史 `Dockerfile.h100fix`；Paddle/H100 后续修复应基于当前专用 Dockerfile 或新增 Dockerfile 继续做。

## 本机修改后的自检

后端必须检查：

```bash
git status --short
docker run --rm --gpus all ${BACKEND_IMAGE} nvidia-smi
```

H100 相关修改必须确认后端镜像能在 GPU 上运行，并且所有模型的 API 回归通过。BoT-SORT 官方环境和 Oriented RCNN/MMCV 是历史风险点，需要额外确认 `sm_90`，但通过标准仍然是全量模型通过：

```bash
docker run --rm --gpus all ${BACKEND_IMAGE} bash -lc '
/opt/conda/envs/BoTSORTOfficial37/bin/python - <<PY
import torch
print(torch.__version__, torch.version.cuda, torch.cuda.get_arch_list())
assert "sm_90" in torch.cuda.get_arch_list()
print((torch.zeros(1, device="cuda") + 1).cpu().tolist())
PY
so=$(/opt/conda/envs/MMSeg310/bin/python -c "import mmcv._ext; print(mmcv._ext.__file__)")
/usr/local/cuda-11.8/bin/cuobjdump --list-elf "$so" | grep -q sm_90
echo "mmcv sm_90 ok"
'
```

完整后端 H100 回归：

```bash
docker run --rm --gpus all \
  -v /data/geoview:/data/geoview \
  -v "$PWD/TestData:/app/TestData:ro" \
  -v "$PWD/scripts/geoview_gpu_api_test.py:/app/scripts/geoview_gpu_api_test.py:ro" \
  ${BACKEND_IMAGE} \
  bash -lc 'cd /app && python scripts/geoview_gpu_api_test.py --output runtime/gpu-api-report.json --tracking-frames 3 --tracking-width 640 --paddle-devices gpu,cpu'
```

通过标准：所有模型通过，例如当前基线是 `30 passed / 0 failed`，其中 Paddle 模型需要同时覆盖 `gpu,cpu`。如果测试脚本新增模型，必须以新增后的总数全部通过为准。

前端必须检查：

```bash
npm --prefix frontend run build
```

如果前端镜像或 Helm 配置变更，还要本机启动前后端容器，访问页面，并确认 `/health`、`/api/system/ping` 正常：

```bash
docker rm -f cugrs-app cugrs-mysql cugrs-backend geoview-frontend 2>/dev/null || true
docker compose pull backend
docker compose -f docker-compose.frontend.yml pull frontend
docker compose up -d backend
docker compose -f docker-compose.frontend.yml up -d frontend
curl -fsS http://127.0.0.1:5008/health
curl -fsS http://127.0.0.1:5008/api/system/ping
curl -fsSI http://127.0.0.1:3000/
```

## 构建和推送

后端构建或提交镜像后，确认默认启动命令不是 `sleep infinity`：

```bash
docker inspect ${BACKEND_IMAGE} --format 'Cmd={{json .Config.Cmd}}'
```

应为：

```text
Cmd=["entrypoint.sh"]
```

推送：

```bash
docker login crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com
docker tag ${BACKEND_IMAGE} ${BACKEND_LATEST_IMAGE}
docker push ${BACKEND_IMAGE}
docker push ${BACKEND_LATEST_IMAGE}
docker image inspect ${BACKEND_IMAGE} --format '{{json .RepoDigests}} {{json .Config.Cmd}}'
docker image inspect ${BACKEND_LATEST_IMAGE} --format '{{json .RepoDigests}} {{json .Config.Cmd}}'
```

前端镜像同样使用明确版本 tag 构建，再打 `latest` 并推送两个 tag。`docker-compose*.yml` 使用 `latest`；Helm values、manifest 和 U 盘打包命令使用明确版本 tag。

```bash
docker tag ${FRONTEND_IMAGE} ${FRONTEND_LATEST_IMAGE}
docker push ${FRONTEND_IMAGE}
docker push ${FRONTEND_LATEST_IMAGE}
docker image inspect ${FRONTEND_IMAGE} --format '{{json .RepoDigests}} {{json .Config.Cmd}}'
docker image inspect ${FRONTEND_LATEST_IMAGE} --format '{{json .RepoDigests}} {{json .Config.Cmd}}'
```

镜像推送后必须同步替换本机正在运行的容器。后端变更只重启后端，前端变更只重启前端；如果两者都变更，则分别重启：

```bash
docker compose pull backend
docker compose up -d --force-recreate backend
docker compose -f docker-compose.frontend.yml pull frontend
docker compose -f docker-compose.frontend.yml up -d --force-recreate frontend
curl -fsS http://127.0.0.1:5008/health
curl -fsS http://127.0.0.1:5008/api/system/ping
curl -fsSI http://127.0.0.1:3000/
```

## 中转机器打包到 U 盘
只负责给出中转机打包命令，用于交付。中转机器只负责从 Aliyun 拉取前后端精确 tag，直接把压缩镜像包写入 U 盘，并生成校验文件。不在本文件描述内网部署。

如果中转机空间不足，可以先清空 Docker 容器、镜像、缓存。该操作会删除中转机上所有 Docker 数据，只能在确认不是生产机、且数据可丢弃时执行：

```bash
docker rm -f $(docker ps -aq) 2>/dev/null || true
docker system prune -a --volumes -f
docker builder prune -a -f
docker system df
```

U 盘建议格式化为 `exFAT`，避免 FAT32 单文件 4GB 限制。以下命令会清空整个 U 盘，必须先用 `lsblk` 确认设备名，示例中 `/dev/sdX1` 需要替换为真实分区：

```bash
lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT,MODEL
sudo umount /dev/sdX1 2>/dev/null || true
sudo mkfs.exfat -n GEOVIEW /dev/sdX1
sudo mkdir -p /mnt/geoview_usb
sudo mount -o uid=$(id -u),gid=$(id -g),umask=022 /dev/sdX1 /mnt/geoview_usb
USB_DIR=/mnt/geoview_usb
touch ${USB_DIR}/write_test && rm ${USB_DIR}/write_test
```

按实际前端镜像替换 `FRONTEND_IMAGE`、`FRONTEND_TAG`、`USB_DIR`。下面命令会直接导出压缩包到 U 盘，不在中转机本地额外生成未压缩 tar：

```bash
BACKEND_REGISTRY=crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/cugrs
BACKEND_TAG=20260517-paddlefix1
BACKEND_IMAGE=${BACKEND_REGISTRY}:${BACKEND_TAG}

FRONTEND_REGISTRY=crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/geoview-frontend
FRONTEND_TAG=20260517-paddlefix1
FRONTEND_IMAGE=${FRONTEND_REGISTRY}:${FRONTEND_TAG}
USB_DIR=/mnt/geoview_usb

docker login crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com

docker pull ${BACKEND_IMAGE}
docker pull ${FRONTEND_IMAGE}

docker save ${BACKEND_IMAGE} | gzip -1 > ${USB_DIR}/cugrs_backend_${BACKEND_TAG}.tar.gz
docker save ${FRONTEND_IMAGE} | gzip -1 > ${USB_DIR}/cugrs_frontend_${FRONTEND_TAG}.tar.gz

cd ${USB_DIR}
sha256sum cugrs_backend_${BACKEND_TAG}.tar.gz > cugrs_backend_${BACKEND_TAG}.tar.gz.sha256
sha256sum cugrs_frontend_${FRONTEND_TAG}.tar.gz > cugrs_frontend_${FRONTEND_TAG}.tar.gz.sha256

ls -lh cugrs_backend_${BACKEND_TAG}.tar.gz* cugrs_frontend_${FRONTEND_TAG}.tar.gz*
sync
```

## 完成标准

- 前端页面可访问，后端 API 健康检查通过。
- 后端 H100 GPU/API 全量回归通过，所有模型未回退。
- 前后端镜像均已推送 Aliyun，tag 和 digest 有记录。
- 中转机器已在 U 盘中产出前后端 `.tar.gz` 和 `.sha256` 文件。
