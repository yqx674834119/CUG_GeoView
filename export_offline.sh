#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

APP_IMAGE="cugrs:local-build"
MYSQL_IMAGE="registry.openanolis.cn/openanolis/mysql:8.0.30-8.6"
APP_CONTAINER="cugrs-app"
HF_DEST="${SCRIPT_DIR}/offline_cache/huggingface"
TORCH_DEST="${SCRIPT_DIR}/offline_cache/torch"
PADDLE_DEST="${SCRIPT_DIR}/offline_cache/paddle"

mode="${1:-${OFFLINE_EXPORT_MODE:-}}"

ensure_cache_writable() {
    mkdir -p "${SCRIPT_DIR}/offline_cache"
    if command -v docker >/dev/null 2>&1; then
        docker run --rm -v "${SCRIPT_DIR}/offline_cache:/work" alpine \
            sh -c "chown -R $(id -u):$(id -g) /work" >/dev/null 2>&1 || true
    fi
}

copy_dir_from_container() {
    local container="$1"
    local src_dir="$2"
    local dest_dir="$3"
    local label="$4"
    local container_source=""
    local resolved_container_source=""
    local resolved_dest_dir=""

    if ! docker container inspect "${container}" >/dev/null 2>&1; then
        return 1
    fi

    container_source="$(docker inspect -f "{{range .Mounts}}{{if eq .Destination \"${src_dir}\"}}{{.Source}}{{end}}{{end}}" "${container}" 2>/dev/null || true)"
    if [ -n "${container_source}" ] && [ -e "${container_source}" ]; then
        resolved_container_source="$(realpath "${container_source}")"
        resolved_dest_dir="$(realpath "${dest_dir}")"
        if [ "${resolved_container_source}" = "${resolved_dest_dir}" ]; then
            echo "  - ${label} 已直接挂载到 ${dest_dir}，无需重复同步"
            return 0
        fi
    fi

    if ! docker exec "${container}" sh -c "[ -d '${src_dir}' ] && find '${src_dir}' -mindepth 1 -print -quit | grep -q ." >/dev/null 2>&1; then
        return 1
    fi

    echo "  - 从运行中容器同步 ${label}: ${src_dir}"
    docker exec "${container}" sh -c "tar -C '${src_dir}' -cf - ." | tar --skip-old-files -xf - -C "${dest_dir}"
    return 0
}

copy_dir_from_volume() {
    local volume_name="$1"
    local dest_dir="$2"
    local label="$3"

    if ! docker volume inspect "${volume_name}" >/dev/null 2>&1; then
        return 1
    fi

    if ! docker run --rm -v "${volume_name}:/src:ro" alpine sh -c "find /src -mindepth 1 -print -quit | grep -q ." >/dev/null 2>&1; then
        return 1
    fi

    echo "  - 从历史卷同步 ${label}: ${volume_name}"
    docker run --rm -v "${volume_name}:/src:ro" -v "${dest_dir}:/dest" alpine sh -c "cp -a /src/. /dest/"
    return 0
}

sync_hf_cache() {
    local copied=0

    if copy_dir_from_container "${APP_CONTAINER}" "/root/.cache/huggingface" "${HF_DEST}" "HuggingFace 缓存"; then
        return 0
    fi

    copy_dir_from_volume "geoview_hf_cache" "${HF_DEST}" "HuggingFace 缓存" && copied=1
    copy_dir_from_volume "hf_cache" "${HF_DEST}" "HuggingFace 缓存" && copied=1

    if [ "${copied}" -eq 0 ]; then
        echo "  - 未发现可同步的 HuggingFace 缓存，保留当前 ${HF_DEST}"
    fi
}

sync_torch_cache() {
    local copied=0

    if copy_dir_from_container "${APP_CONTAINER}" "/root/.cache/torch" "${TORCH_DEST}" "Torch/LoFTR 缓存"; then
        return 0
    fi

    copy_dir_from_volume "geoview_torch_cache" "${TORCH_DEST}" "Torch/LoFTR 缓存" && copied=1
    copy_dir_from_volume "torch_cache" "${TORCH_DEST}" "Torch/LoFTR 缓存" && copied=1

    if [ "${copied}" -eq 0 ]; then
        echo "  - 未发现可同步的 Torch 缓存，保留当前 ${TORCH_DEST}"
    fi
}

sync_paddle_cache() {
    local copied=0

    if copy_dir_from_container "${APP_CONTAINER}" "/root/.paddle" "${PADDLE_DEST}" "Paddle 缓存"; then
        copy_dir_from_container "${APP_CONTAINER}" "/root/.cache/paddle" "${PADDLE_DEST}" "Paddle 缓存" >/dev/null 2>&1 || true
        return 0
    fi

    copy_dir_from_container "${APP_CONTAINER}" "/root/.cache/paddle" "${PADDLE_DEST}" "Paddle 缓存" && copied=1
    copy_dir_from_volume "geoview_paddle_cache" "${PADDLE_DEST}" "Paddle 缓存" && copied=1
    copy_dir_from_volume "paddle_cache" "${PADDLE_DEST}" "Paddle 缓存" && copied=1

    if [ "${copied}" -eq 0 ]; then
        echo "  - 未发现可同步的 Paddle 缓存，保留当前 ${PADDLE_DEST}"
    fi
}

echo "=========================================="
echo "    GeoView 离线部署包导出脚本 (阿里云中转版) "
echo "=========================================="

if [ -z "${mode}" ]; then
    echo "请选择您的打包模式："
    echo "[1] 完整离线打包：镜像(.tar) + 模型缓存 + 代码一起打包 (适合磁盘空间宽裕的机器)"
    echo "[2] 轻量空间中转打包：跳过镜像保存，仅提取模型及代码，并将镜像推送到阿里云 (适合当前机器磁盘不足)"
    read -r -p "请输入模式编号 [1 或 2]: " mode
fi

if [ "${mode}" != "1" ] && [ "${mode}" != "2" ]; then
    echo "错误：模式必须是 1 或 2。"
    exit 1
fi

mkdir -p ./offline_cache/huggingface
mkdir -p ./offline_cache/torch
mkdir -p ./offline_cache/paddle
mkdir -p ./offline_images
ensure_cache_writable
python3 ./sync_model_assets.py --quiet

if ! docker image inspect "${APP_IMAGE}" >/dev/null 2>&1; then
    echo "未找到镜像 ${APP_IMAGE}。请先尝试在一台有网的机器上完成构建（docker compose build）。"
    exit 1
fi

if [ "$mode" == "1" ]; then
    echo ">>> [1/3] 正在准备打包 Docker 镜像..."
    rm -f ./offline_images/*.tar
    if ! docker image inspect "${MYSQL_IMAGE}" >/dev/null 2>&1; then
        echo "未找到镜像 mysql。请确保您已经拉取过它。"
        exit 1
    fi
    echo "保存基础应用镜像 -> offline_images/cugrs_app.tar"
    docker save -o ./offline_images/cugrs_app.tar "${APP_IMAGE}"
    echo "保存 MySQL 镜像 -> offline_images/mysql.tar"
    docker save -o ./offline_images/mysql.tar "${MYSQL_IMAGE}"
    echo "✓ 镜像保存完成！"
else
    echo ">>> [1/3] 已跳过镜像体积硕大的本地保存环节！"
    rm -f ./offline_images/*.tar
    echo "--------- 阿里云镜像推送提示 ---------"
    echo "请在运行完本脚本后，手动执行以下几条命令将环境推向阿里云："
    echo "  1. 登录（若未登录）: docker login --username=13997543646yqx crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com"
    echo "  2. 打标签: docker tag ${APP_IMAGE} crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/cugrs:latest"
    echo "  3. 推送应用镜像: docker push crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/cugrs:latest"
    echo "  4. 将 MySQL 镜像同样打标并推送，或者让中转机器直接拉取官方版。"
    echo "--------------------------------------"
fi

echo ">>> [2/3] 正在同步模型缓存到 ./offline_cache"
sync_hf_cache
sync_torch_cache
sync_paddle_cache
echo "缓存目录当前大小："
du -sh ./offline_cache/huggingface ./offline_cache/torch ./offline_cache/paddle 2>/dev/null || true

echo ">>> [2.5/3] 正在校验离线部署关键模型资产"
python3 ./audit_offline_assets.py --strict
echo "✓ 关键模型资产校验通过！"

echo ">>> [3/3] 开始将此项目文件夹打包为压缩文件"
cd ..
if [ "$mode" == "1" ]; then
    OFFLINE_ZIP_NAME="GeoView_Offline_Full_$(date +%Y%m%d).tar.gz"
else
    OFFLINE_ZIP_NAME="GeoView_Offline_Thin_$(date +%Y%m%d).tar.gz"
fi
echo "正在创建压缩包 ${OFFLINE_ZIP_NAME}，请等待..."
TAR_EXCLUDES=(
    --exclude="GeoView/.git"
    --exclude="GeoView/backend/__pycache__"
    --exclude="GeoView/frontend/node_modules"
    --exclude="GeoView/miner/node_modules"
)

if [ "$mode" == "2" ]; then
    TAR_EXCLUDES+=(--exclude="GeoView/offline_images/*.tar")
fi

tar -czf "${OFFLINE_ZIP_NAME}" "${TAR_EXCLUDES[@]}" GeoView/

echo "=========================================="
echo "✓ 全部完成！离线部署包已生成： ../${OFFLINE_ZIP_NAME}"
if [ "$mode" == "2" ]; then
    echo "提示：因使用轻量打包，包内不含 Docker 镜像。"
    echo "请将本压缩包发给另一台【空间大且有网】的中转机器，并在那台机器中 pull 您阿里云的镜像后进行最后一轮合并打包。"
fi
echo "=========================================="
