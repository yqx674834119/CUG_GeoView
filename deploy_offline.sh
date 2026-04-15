#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

APP_IMAGE="crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/cugrs:latest"
MYSQL_IMAGE="registry.openanolis.cn/openanolis/mysql:8.0.30-8.6"
APP_PULL_IMAGE="${APP_PULL_IMAGE:-crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/cugrs:latest}"
MYSQL_PULL_IMAGE="${MYSQL_PULL_IMAGE:-registry.openanolis.cn/openanolis/mysql:8.0.30-8.6}"
IMAGE_BUNDLE_TAR="${IMAGE_BUNDLE_TAR:-./offline_images/geoview_images.tar}"

ensure_cache_writable() {
    mkdir -p ./offline_cache
    if command -v docker >/dev/null 2>&1; then
        docker run --rm -v "${SCRIPT_DIR}/offline_cache:/work" alpine \
            sh -c "chown -R $(id -u):$(id -g) /work" >/dev/null 2>&1 || true
    fi
}

ensure_image() {
    local label="$1"
    local tar_path="$2"
    local local_image="$3"
    local pull_image="$4"

    if [ -f "${tar_path}" ]; then
        echo "加载 ${label} 镜像包 -> ${tar_path}"
        docker load -i "${tar_path}"
    fi

    if docker image inspect "${local_image}" >/dev/null 2>&1; then
        echo "✓ 已存在本地镜像 ${local_image}"
        return 0
    fi

    if [ -n "${pull_image}" ]; then
        echo "未发现本地镜像 ${local_image}，尝试拉取 ${pull_image}"
        docker pull "${pull_image}"
        if [ "${pull_image}" != "${local_image}" ]; then
            docker tag "${pull_image}" "${local_image}"
        fi
    fi

    if ! docker image inspect "${local_image}" >/dev/null 2>&1; then
        echo "错误：未能准备好 ${label} 镜像。"
        echo "请确认以下任一条件满足后重试："
        echo "  1. 当前目录存在 ${tar_path}"
        echo "  2. 已提前 docker pull ${pull_image}"
        echo "  3. 已提前 docker tag 到 ${local_image}"
        exit 1
    fi
}

load_bundle_image_if_exists() {
    local tar_path="$1"

    if [ -f "${tar_path}" ]; then
        echo "加载离线镜像合集 -> ${tar_path}"
        docker load -i "${tar_path}"
    fi
}

echo "=========================================="
echo "    GeoView 离线环境一键部署脚本           "
echo "=========================================="

if ! command -v docker &> /dev/null; then
    echo "错误：未安装 Docker！请先安装 Docker 和 Docker-Compose。"
    exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
    echo "错误：当前环境缺少 docker compose 插件。"
    exit 1
fi

mkdir -p ./offline_cache/huggingface ./offline_cache/torch ./offline_cache/paddle
ensure_cache_writable
python3 ./sync_model_assets.py --quiet
python3 ./audit_offline_assets.py --strict

echo ">>> [1/2] 正在加载离线 Docker 镜像..."
load_bundle_image_if_exists "${IMAGE_BUNDLE_TAR}"
ensure_image "MySQL" "./offline_images/mysql.tar" "${MYSQL_IMAGE}" "${MYSQL_PULL_IMAGE}"
ensure_image "GeoView 应用" "./offline_images/cugrs_app.tar" "${APP_IMAGE}" "${APP_PULL_IMAGE}"
echo "✓ 镜像加载完毕!"

echo ">>> [2/2] 正在拉起服务容器..."
# 使用 --no-build，避免在中转机或离线机上误触发本地构建。
docker compose up -d --no-build

echo "=========================================="
echo "✓ 部署成功！项目正在后台启动..."
echo "请等待十秒左右，您可以通过以下命令查看应用日志："
echo "   docker logs -f cugrs-app"
echo "=========================================="
