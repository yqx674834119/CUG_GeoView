#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

HARBOR_REGISTRY="${HARBOR_REGISTRY:-172.20.20.243:8443}"
HARBOR_USER="${HARBOR_USER:-admin}"
HARBOR_PASSWORD="${HARBOR_PASSWORD:-Hc@Cloud01}"

PROJECT="${PROJECT:-}"
APP_VERSION="${APP_VERSION:-$(date +%Y%m%d)}"

APP_SOURCE_IMAGE="${APP_SOURCE_IMAGE:-crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/cugrs:latest}"
MYSQL_SOURCE_IMAGE="${MYSQL_SOURCE_IMAGE:-registry.openanolis.cn/openanolis/mysql:8.0.30-8.6}"

APP_IMAGE_TAR="${APP_IMAGE_TAR:-${SCRIPT_DIR}/offline_images/cugrs_app.tar}"
MYSQL_IMAGE_TAR="${MYSQL_IMAGE_TAR:-${SCRIPT_DIR}/offline_images/mysql.tar}"

CHART_DIR="${SCRIPT_DIR}/deploy/helm/geoview"
DIST_DIR="${SCRIPT_DIR}/deploy/helm/dist"
DOC_DIR="${SCRIPT_DIR}/docs"

DRY_RUN="${DRY_RUN:-0}"

choose_container_cli() {
    if command -v nerdctl >/dev/null 2>&1; then
        CONTAINER_CLI="nerdctl"
    else
        echo "错误：未找到 nerdctl。"
        echo "根据当前交付规范，镜像上传 Harbor 必须使用 nerdctl。"
        exit 1
    fi
}

validate_server_storage_path() {
    case "${SCRIPT_DIR}" in
        /var/lib/kubelet/*|/nfs/data/*)
            return 0
            ;;
        *)
            if [ "${DRY_RUN}" = "1" ]; then
                echo "[DRY_RUN] 当前目录 ${SCRIPT_DIR} 不在服务器规范路径下，跳过路径校验"
                return 0
            fi
            echo "错误：当前脚本目录 ${SCRIPT_DIR} 不符合服务器文件存储规范。"
            echo "请将文件放在以下任一位置后重试："
            echo "  1. /var/lib/kubelet/<你的专属目录>"
            echo "  2. /nfs/data/<你的专属目录>"
            echo "严禁在根目录或其他路径下存储和运行。"
            exit 1
            ;;
    esac
}

run_cli() {
    if [ "${DRY_RUN}" = "1" ]; then
        echo "[DRY_RUN] ${CONTAINER_CLI} $*"
        return 0
    fi
    "${CONTAINER_CLI}" "$@"
}

image_exists() {
    if [ "${DRY_RUN}" = "1" ]; then
        return 1
    fi
    "${CONTAINER_CLI}" image inspect "$1" >/dev/null 2>&1
}

ensure_image() {
    local label="$1"
    local tar_path="$2"
    local image_ref="$3"

    if image_exists "${image_ref}"; then
        echo "✓ 已存在本地${label}镜像：${image_ref}"
        return 0
    fi

    if [ -f "${tar_path}" ]; then
        echo "加载${label}镜像包 -> ${tar_path}"
        run_cli load -i "${tar_path}"
    fi

    if [ "${DRY_RUN}" = "1" ]; then
        return 0
    fi

    if ! image_exists "${image_ref}"; then
        echo "错误：未能准备好${label}镜像 ${image_ref}"
        echo "请确认以下任一条件满足后重试："
        echo "  1. 当前目录存在 ${tar_path}"
        echo "  2. 本地已提前 load 过该镜像"
        exit 1
    fi
}

package_chart() {
    local chart_version
    local chart_package

    mkdir -p "${DIST_DIR}"
    chart_version="$(sed -n 's/^version: //p' "${CHART_DIR}/Chart.yaml" | head -n 1 | tr -d '\"')"
    if [ -z "${chart_version}" ]; then
        echo "错误：无法从 ${CHART_DIR}/Chart.yaml 读取 version"
        exit 1
    fi

    chart_package="${DIST_DIR}/geoview-${chart_version}.tgz"
    rm -f "${chart_package}"
    tar -czf "${chart_package}" -C "${SCRIPT_DIR}/deploy/helm" geoview
    CHART_PACKAGE="${chart_package}"
}

generate_values_file() {
    local values_file="$1"
    cat > "${values_file}" <<EOF
app:
  image:
    repository: ${APP_TARGET_REPOSITORY}
    tag: "${APP_VERSION}"
  gpu:
    enabled: true
    count: 1
  resources:
    requests:
      cpu: "4"
      memory: "16Gi"
    limits:
      cpu: "8"
      memory: "32Gi"
  persistence:
    enabled: true
    storageClass: csi-sc
    size: 80Gi
  service:
    type: ClusterIP

mysql:
  enabled: true
  image:
    repository: ${MYSQL_TARGET_REPOSITORY}
    tag: "8.0.30-8.6"
  persistence:
    enabled: true
    storageClass: csi-sc
    size: 20Gi

imagePullSecrets: []
EOF
}

build_ready_bundle() {
    local ready_dir
    local ready_bundle

    ready_dir="$(mktemp -d)"
    ready_bundle="${DIST_DIR}/GeoView_Helm_Ready_${PROJECT}_${APP_VERSION}.tar.gz"

    mkdir -p "${ready_dir}/GeoView_Helm_Ready"
    cp "${CHART_PACKAGE}" "${ready_dir}/GeoView_Helm_Ready/"
    cp "${GENERATED_VALUES_FILE}" "${ready_dir}/GeoView_Helm_Ready/"
    cp "${DOC_DIR}/GeoView_Helm_最终交付手册.md" "${ready_dir}/GeoView_Helm_Ready/"
    cp "${DOC_DIR}/Helm_两步交付与平台部署说明.md" "${ready_dir}/GeoView_Helm_Ready/"
    cp "${DOC_DIR}/Helm_K8s_部署入门与迁移说明.md" "${ready_dir}/GeoView_Helm_Ready/"
    cp "${SCRIPT_DIR}/deploy/helm/image-manifest.txt" "${ready_dir}/GeoView_Helm_Ready/"

    tar -czf "${ready_bundle}" -C "${ready_dir}" GeoView_Helm_Ready
    rm -rf "${ready_dir}"

    READY_BUNDLE="${ready_bundle}"
}

echo "=========================================="
echo "    GeoView Helm 离线交付准备脚本         "
echo "=========================================="

if [ -z "${PROJECT}" ]; then
    echo "错误：请先设置 Harbor 项目名。"
    echo "示例：PROJECT=tenant-1-geoview APP_VERSION=20260401 ./deploy_helm_offline.sh"
    exit 1
fi

if [ ! -d "${CHART_DIR}" ]; then
    echo "错误：未找到 Helm Chart 目录 ${CHART_DIR}"
    exit 1
fi

choose_container_cli
validate_server_storage_path

APP_TARGET_REPOSITORY="${HARBOR_REGISTRY}/${PROJECT}/geoview-app"
MYSQL_TARGET_REPOSITORY="${HARBOR_REGISTRY}/${PROJECT}/mysql"
APP_TARGET_IMAGE="${APP_TARGET_REPOSITORY}:${APP_VERSION}"
MYSQL_TARGET_IMAGE="${MYSQL_TARGET_REPOSITORY}:8.0.30-8.6"
GENERATED_VALUES_FILE="${DIST_DIR}/values-harbor-${PROJECT}-${APP_VERSION}.yaml"

mkdir -p "${DIST_DIR}"

echo ">>> [1/4] 准备本地镜像"
ensure_image "GeoView 应用" "${APP_IMAGE_TAR}" "${APP_SOURCE_IMAGE}"
ensure_image "MySQL" "${MYSQL_IMAGE_TAR}" "${MYSQL_SOURCE_IMAGE}"

echo ">>> [2/4] 登录 Harbor 并推送镜像"
run_cli login "${HARBOR_REGISTRY}" -u "${HARBOR_USER}" -p "${HARBOR_PASSWORD}"
run_cli tag "${APP_SOURCE_IMAGE}" "${APP_TARGET_IMAGE}"
run_cli tag "${MYSQL_SOURCE_IMAGE}" "${MYSQL_TARGET_IMAGE}"
run_cli push "${APP_TARGET_IMAGE}"
run_cli push "${MYSQL_TARGET_IMAGE}"

echo ">>> [3/4] 打包 Helm Chart"
package_chart

echo ">>> [4/4] 生成平台部署推荐配置"
generate_values_file "${GENERATED_VALUES_FILE}"
build_ready_bundle

echo "=========================================="
echo "✓ Helm 离线交付准备完成"
echo
echo "容器工具: ${CONTAINER_CLI}"
echo "GeoView 应用镜像: ${APP_TARGET_IMAGE}"
echo "MySQL 镜像: ${MYSQL_TARGET_IMAGE}"
echo "Helm 包: ${CHART_PACKAGE}"
echo "推荐 values: ${GENERATED_VALUES_FILE}"
echo "交付包: ${READY_BUNDLE}"
echo
echo "下一步请在服务运维平台（172.20.20.241）执行："
echo "  1. 创建命名空间"
echo "  2. 上传 Helm 包：$(basename "${CHART_PACKAGE}")"
echo "  3. 参考 $(basename "${GENERATED_VALUES_FILE}") 修改 values.yaml"
echo "  4. 选择命名空间并完成部署"
echo "=========================================="
