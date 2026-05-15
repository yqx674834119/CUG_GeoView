# GeoView 交付规范

本文件给新会话快速接手用。目标是：本机验证前后端镜像，推送到 Aliyun，中转机器拉取镜像并打包到 U 盘，确保交付物可离线导入。

## 基本原则

- 不要回滚用户已有改动；先用 `git status --short` 看清楚工作区。
- 镜像必须使用明确 tag，不使用 `latest`。tag 格式沿用 `YYYYMMDD-purposeN`，例如 `20260515-h100fix1`。
- 后端镜像必须包含所有模型、权重和依赖；内网部署时不能依赖公网下载。
- 后端修改后必须做 H100 GPU/API 全量回归，要求所有模型通过，不能只验证出问题的模型。
- 前端修改后必须重新构建前端镜像，并确认页面能访问后端接口。

## 当前镜像信息

后端仓库：

```bash
BACKEND_REGISTRY=crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/cugrs
BACKEND_TAG=20260515-h100fix1
BACKEND_IMAGE=${BACKEND_REGISTRY}:${BACKEND_TAG}
BACKEND_DIGEST=sha256:b427b0a507da6527c42bb98af928397676090f9f6453001f083b45b1219e2e11
```

前端镜像仓库以当前 `docker-compose`、Helm values 或 `deploy/frontend/helm/image-manifest.txt` 为准；不要臆造 tag，先查现有配置。

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
  bash -lc 'cd /app && python scripts/geoview_gpu_api_test.py --output runtime/gpu-api-report.json --tracking-frames 3 --tracking-width 640'
```

通过标准：所有模型通过，例如当前基线是 `25 passed / 0 failed`。如果测试脚本新增模型，必须以新增后的总数全部通过为准。

前端必须检查：

```bash
npm --prefix frontend run build
```

如果前端镜像或 Helm 配置变更，还要本机启动前后端容器，访问页面，并确认 `/health`、`/api/system/ping` 正常：

```bash
curl -fsS http://127.0.0.1:5008/health
curl -fsS http://127.0.0.1:5008/api/system/ping
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
docker push ${BACKEND_IMAGE}
docker image inspect ${BACKEND_IMAGE} --format '{{json .RepoDigests}} {{json .Config.Cmd}}'
```

前端镜像同样使用明确 tag 构建、推送，并同步更新 compose/Helm/manifest 中引用的 tag。

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
sudo mount /dev/sdX1 /mnt/geoview_usb
USB_DIR=/mnt/geoview_usb
```

按实际前端镜像替换 `FRONTEND_IMAGE`、`FRONTEND_TAG`、`USB_DIR`。下面命令会直接导出压缩包到 U 盘，不在中转机本地额外生成未压缩 tar：

```bash
BACKEND_REGISTRY=crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/cugrs
BACKEND_TAG=20260515-h100fix1
BACKEND_IMAGE=${BACKEND_REGISTRY}:${BACKEND_TAG}

FRONTEND_IMAGE=替换为前端镜像完整地址:tag
FRONTEND_TAG=替换为前端tag
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
