#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

CHART_DIR="${SCRIPT_DIR}/deploy/frontend/helm/geoview-frontend"
DIST_DIR="${SCRIPT_DIR}/deploy/frontend/helm/dist"
DOC_FILE="${SCRIPT_DIR}/docs/GeoView_前端Helm部署说明.md"
VALUES_EXAMPLE="${CHART_DIR}/values-harbor-example.yaml"
MANIFEST_FILE="${SCRIPT_DIR}/deploy/frontend/helm/image-manifest.txt"

FRONTEND_IMAGE="${FRONTEND_IMAGE:-geoview-frontend:latest}"
DATE_TAG="$(date +%Y%m%d)"
CHART_VERSION="$(sed -n 's/^version: //p' "${CHART_DIR}/Chart.yaml" | head -n 1 | tr -d '\"')"
CHART_PACKAGE="${DIST_DIR}/geoview-frontend-${CHART_VERSION}.tgz"
HANDOFF_BUNDLE="${DIST_DIR}/GeoView_Frontend_Helm_Thin_${DATE_TAG}.tar.gz"
OFFLINE_BUNDLE="${OFFLINE_BUNDLE:-${SCRIPT_DIR}/deploy/frontend/dist/GeoView_Frontend_Offline_${DATE_TAG}.tar.gz}"

mkdir -p "${DIST_DIR}"
rm -f "${CHART_PACKAGE}" "${HANDOFF_BUNDLE}"

extract_image_tar_from_offline_bundle() {
    local bundle_path="$1"
    local output_tar="$2"
    local temp_dir

    temp_dir="$(mktemp -d)"
    tar -xzf "${bundle_path}" -C "${temp_dir}"
    cp "${temp_dir}/GeoView_Frontend_Offline/offline_images/geoview_frontend.tar" "${output_tar}"
    rm -rf "${temp_dir}"
}

prepare_image_tar() {
    local output_tar="$1"

    if docker image inspect "${FRONTEND_IMAGE}" >/dev/null 2>&1; then
        docker save -o "${output_tar}" "${FRONTEND_IMAGE}"
        return 0
    fi

    if [ -f "${OFFLINE_BUNDLE}" ]; then
        extract_image_tar_from_offline_bundle "${OFFLINE_BUNDLE}" "${output_tar}"
        return 0
    fi

    echo "错误：既未找到本地前端镜像 ${FRONTEND_IMAGE}，也未找到离线前端压缩包 ${OFFLINE_BUNDLE}"
    echo "请先执行 ./export_frontend_offline.sh，或提前 docker load / docker build 好 ${FRONTEND_IMAGE}"
    exit 1
}

tar -czf "${CHART_PACKAGE}" -C "${SCRIPT_DIR}/deploy/frontend/helm" geoview-frontend

TMP_DIR="$(mktemp -d)"
cleanup() {
    rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

mkdir -p "${TMP_DIR}/GeoView_Frontend_Helm_Thin/offline_images"
prepare_image_tar "${TMP_DIR}/GeoView_Frontend_Helm_Thin/offline_images/geoview_frontend.tar"
cp "${CHART_PACKAGE}" "${TMP_DIR}/GeoView_Frontend_Helm_Thin/"
cp "${VALUES_EXAMPLE}" "${TMP_DIR}/GeoView_Frontend_Helm_Thin/"
cp "${MANIFEST_FILE}" "${TMP_DIR}/GeoView_Frontend_Helm_Thin/"
cp "${DOC_FILE}" "${TMP_DIR}/GeoView_Frontend_Helm_Thin/"

tar -czf "${HANDOFF_BUNDLE}" -C "${TMP_DIR}" GeoView_Frontend_Helm_Thin

echo "=========================================="
echo "Frontend Helm chart: ${CHART_PACKAGE}"
echo "Frontend handoff bundle: ${HANDOFF_BUNDLE}"
echo "=========================================="
