#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

FRONTEND_IMAGE="${FRONTEND_IMAGE:-geoview-frontend:latest}"
FRONTEND_PULL_IMAGE="${FRONTEND_PULL_IMAGE:-}"
FRONTEND_TAR="${SCRIPT_DIR}/offline_images/geoview_frontend.tar"

load_env_file() {
    if [ -f "${SCRIPT_DIR}/frontend.env" ]; then
        set -a
        # shellcheck disable=SC1091
        . "${SCRIPT_DIR}/frontend.env"
        set +a
    fi
}

ensure_image() {
    if [ -f "${FRONTEND_TAR}" ]; then
        echo "加载前端镜像包 -> ${FRONTEND_TAR}"
        docker load -i "${FRONTEND_TAR}"
    fi

    if docker image inspect "${FRONTEND_IMAGE}" >/dev/null 2>&1; then
        echo "✓ 已存在本地镜像 ${FRONTEND_IMAGE}"
        return 0
    fi

    if [ -n "${FRONTEND_PULL_IMAGE}" ]; then
        echo "未发现本地镜像，尝试拉取 ${FRONTEND_PULL_IMAGE}"
        docker pull "${FRONTEND_PULL_IMAGE}"
        if [ "${FRONTEND_PULL_IMAGE}" != "${FRONTEND_IMAGE}" ]; then
            docker tag "${FRONTEND_PULL_IMAGE}" "${FRONTEND_IMAGE}"
        fi
    fi

    if ! docker image inspect "${FRONTEND_IMAGE}" >/dev/null 2>&1; then
        echo "错误：未能准备好前端镜像 ${FRONTEND_IMAGE}"
        echo "请确认以下任一条件满足后重试："
        echo "  1. 当前目录存在 ${FRONTEND_TAR}"
        echo "  2. 已提前 docker pull ${FRONTEND_PULL_IMAGE}"
        echo "  3. 已提前 docker tag 到 ${FRONTEND_IMAGE}"
        exit 1
    fi
}

echo "=========================================="
echo "    GeoView 独立前端离线部署脚本         "
echo "=========================================="

if ! command -v docker >/dev/null 2>&1; then
    echo "错误：未安装 Docker。"
    exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
    echo "错误：当前环境缺少 docker compose 插件。"
    exit 1
fi

load_env_file
ensure_image

docker compose -f docker-compose.frontend.yml up -d --no-build

echo "=========================================="
echo "✓ 独立前端容器已启动。"
echo "如果后端 IP 不是当前浏览器访问主机，请先复制 frontend.env.example 为 frontend.env 并设置 GEOVIEW_BACKEND_URL。"
echo "=========================================="
