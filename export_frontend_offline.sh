#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

FRONTEND_IMAGE="${FRONTEND_IMAGE:-geoview-frontend:latest}"
BUILD_MODE="${GEOVIEW_FRONTEND_BUILD_MODE:-auto}"
DIST_DIR="${SCRIPT_DIR}/deploy/frontend/dist"
DATE_TAG="$(date +%Y%m%d)"
IMAGE_TAR_NAME="geoview_frontend.tar"
BUNDLE_NAME="GeoView_Frontend_Offline_${DATE_TAG}.tar.gz"

build_frontend_image_with_clean_config() {
    local clean_docker_config
    clean_docker_config="$(mktemp -d)"
    printf '{"auths":{}}\n' > "${clean_docker_config}/config.json"
    DOCKER_CONFIG="${clean_docker_config}" DOCKER_BUILDKIT=0 docker build -f Dockerfile.frontend -t "${FRONTEND_IMAGE}" .
    rm -rf "${clean_docker_config}"
}

build_frontend_image_from_local_dist() {
    local temp_context

    if ! command -v busybox >/dev/null 2>&1; then
        echo "错误：无法使用本地 busybox 兜底构建前端镜像。"
        exit 1
    fi

    echo "公共基础镜像不可用，切换为本地 dist + busybox 的离线构建方案..."
    (
        cd "${SCRIPT_DIR}/frontend"
        npm run build
    )

    temp_context="$(mktemp -d)"
    mkdir -p "${temp_context}/www" "${temp_context}/docker"
    cp /usr/bin/busybox "${temp_context}/busybox"
    cp "${SCRIPT_DIR}/docker/frontend-entrypoint.sh" "${temp_context}/docker/frontend-entrypoint.sh"
    cp -R "${SCRIPT_DIR}/frontend/dist/." "${temp_context}/www/"

    cat > "${temp_context}/Dockerfile" <<'EOF'
FROM scratch

COPY busybox /bin/busybox
COPY docker/frontend-entrypoint.sh /entrypoint.sh
COPY www /www

ENV GEOVIEW_WEB_ROOT=/www \
    GEOVIEW_START_HTTPD=true \
    GEOVIEW_HTTP_PORT=80

EXPOSE 80

ENTRYPOINT ["/bin/busybox", "sh", "/entrypoint.sh"]
EOF

    DOCKER_BUILDKIT=0 docker build -t "${FRONTEND_IMAGE}" "${temp_context}"
    rm -rf "${temp_context}"
}

build_frontend_image() {
    if [ "${BUILD_MODE}" = "local" ]; then
        build_frontend_image_from_local_dist
        return 0
    fi

    if docker build -f Dockerfile.frontend -t "${FRONTEND_IMAGE}" .; then
        return 0
    fi

    echo "BuildKit 构建失败，尝试使用经典 docker build 重新构建..."
    if build_frontend_image_with_clean_config; then
        return 0
    fi

    if [ "${BUILD_MODE}" = "standard" ]; then
        echo "错误：标准镜像构建失败，且当前模式禁止本地离线兜底。"
        exit 1
    fi

    build_frontend_image_from_local_dist
}

echo "=========================================="
echo "    GeoView 独立前端离线包导出脚本       "
echo "=========================================="

if ! command -v docker >/dev/null 2>&1; then
    echo "错误：未安装 Docker。"
    exit 1
fi

mkdir -p "${DIST_DIR}"
rm -f "${DIST_DIR}/${BUNDLE_NAME}"

echo ">>> [1/3] 构建独立前端镜像 ${FRONTEND_IMAGE}"
build_frontend_image

TMP_DIR="$(mktemp -d)"
cleanup() {
    rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

PACKAGE_DIR="${TMP_DIR}/GeoView_Frontend_Offline"
mkdir -p "${PACKAGE_DIR}/offline_images"

echo ">>> [2/3] 导出前端镜像为离线文件"
docker save -o "${PACKAGE_DIR}/offline_images/${IMAGE_TAR_NAME}" "${FRONTEND_IMAGE}"

cp docker-compose.frontend.yml "${PACKAGE_DIR}/"
cp deploy_frontend_offline.sh "${PACKAGE_DIR}/"
cp frontend.env.example "${PACKAGE_DIR}/frontend.env.example"
cp docs/GeoView_独立前端Docker部署说明.md "${PACKAGE_DIR}/"

cat > "${PACKAGE_DIR}/image-manifest.txt" <<EOF
${FRONTEND_IMAGE}
EOF

echo ">>> [3/3] 打包压缩文件 ${BUNDLE_NAME}"
tar -czf "${DIST_DIR}/${BUNDLE_NAME}" -C "${TMP_DIR}" GeoView_Frontend_Offline

echo "=========================================="
echo "✓ 前端离线压缩包已生成：${DIST_DIR}/${BUNDLE_NAME}"
echo "=========================================="
