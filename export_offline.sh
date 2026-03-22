#!/bin/bash
set -e

echo "=========================================="
echo "    GeoView 离线部署包导出脚本 (阿里云中转版) "
echo "=========================================="

echo "请选择您的打包模式："
echo "[1] 完整离线打包：镜像(.tar) + 模型缓存 + 代码一起打包 (适合磁盘空间宽裕的机器)"
echo "[2] 轻量空间中转打包：跳过镜像保存，仅提取模型及代码，并将镜像推送到阿里云 (适合当前机器磁盘不足)"
read -p "请输入模式编号 [1 或 2]: " mode

mkdir -p ./offline_cache/huggingface
mkdir -p ./offline_cache/torch
mkdir -p ./offline_cache/paddle
mkdir -p ./offline_images

if ! docker image inspect cugrs:local-build >/dev/null 2>&1; then
    echo "未找到镜像 cugrs:local-build。请先尝试在一台有网的机器上完成构建（docker compose build）。"
    exit 1
fi

if [ "$mode" == "1" ]; then
    echo ">>> [1/3] 正在准备打包 Docker 镜像..."
    if ! docker image inspect registry.openanolis.cn/openanolis/mysql:8.0.30-8.6 >/dev/null 2>&1; then
        echo "未找到镜像 mysql。请确保您已经拉取过它。"
        exit 1
    fi
    echo "保存基础应用镜像 -> offline_images/cugrs_app.tar"
    docker save -o ./offline_images/cugrs_app.tar cugrs:local-build
    echo "保存 MySQL 镜像 -> offline_images/mysql.tar"
    docker save -o ./offline_images/mysql.tar registry.openanolis.cn/openanolis/mysql:8.0.30-8.6
    echo "✓ 镜像保存完成！"
else
    echo ">>> [1/3] 已跳过镜像体积硕大的本地保存环节！"
    echo "--------- 阿里云镜像推送提示 ---------"
    echo "请在运行完本脚本后，手动执行以下几条命令将环境推向阿里云："
    echo "  1. 登录（若未登录）: docker login --username=13997543646yqx crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com"
    echo "  2. 打标签: docker tag cugrs:local-build crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/cugrs:latest"
    echo "  3. 推送应用镜像: docker push crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/cugrs:latest"
    echo "  4. 将 MySQL 镜像同样打标并推送，或者让中转机器直接拉取官方版。"
    echo "--------------------------------------"
fi

echo ">>> [2/3] 正在从旧的具名数据卷中提取模型文件至 ./offline_cache"
docker run --rm -v hf_cache:/src -v $(pwd)/offline_cache/huggingface:/dest alpine sh -c "cp -a /src/. /dest/ 2>/dev/null || true"
docker run --rm -v torch_cache:/src -v $(pwd)/offline_cache/torch:/dest alpine sh -c "cp -a /src/. /dest/ 2>/dev/null || true"
docker run --rm -v paddle_cache:/src -v $(pwd)/offline_cache/paddle:/dest alpine sh -c "cp -a /src/. /dest/ 2>/dev/null || true"
echo "✓ 模型缓存提取结束！"

echo ">>> [3/3] 开始将此项目文件夹打包为压缩文件"
cd ..
if [ "$mode" == "1" ]; then
    OFFLINE_ZIP_NAME="GeoView_Offline_Full_$(date +%Y%m%d).tar.gz"
else
    OFFLINE_ZIP_NAME="GeoView_Offline_Thin_$(date +%Y%m%d).tar.gz"
fi
echo "正在创建压缩包 ${OFFLINE_ZIP_NAME}，请等待..."
tar -czf ${OFFLINE_ZIP_NAME} --exclude="GeoView/.git" --exclude="GeoView/backend/__pycache__" --exclude="GeoView/frontend/node_modules" --exclude="GeoView/miner/node_modules" GeoView/

echo "=========================================="
echo "✓ 全部完成！离线部署包已生成： ../${OFFLINE_ZIP_NAME}"
if [ "$mode" == "2" ]; then
    echo "提示：因使用轻量打包，包内不含 Docker 镜像。"
    echo "请将本压缩包发给另一台【空间大且有网】的中转机器，并在那台机器中 pull 您阿里云的镜像后进行最后一轮合并打包。"
fi
echo "=========================================="
