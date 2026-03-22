#!/bin/bash
set -e

echo "=========================================="
echo "    GeoView 离线环境一键部署脚本           "
echo "=========================================="

if ! command -v docker &> /dev/null; then
    echo "错误：未安装 Docker！请先安装 Docker 和 Docker-Compose。"
    exit 1
fi

echo ">>> [1/2] 正在加载离线 Docker 镜像..."
if [ -f "./offline_images/mysql.tar" ]; then
    echo "加载 MySQL 镜像..."
    docker load -i ./offline_images/mysql.tar
else
    echo "警告：未找到 ./offline_images/mysql.tar"
fi

if [ -f "./offline_images/cugrs_app.tar" ]; then
    echo "加载 cugrs_app 应用镜像..."
    docker load -i ./offline_images/cugrs_app.tar
else
    echo "警告：未找到 ./offline_images/cugrs_app.tar"
fi
echo "✓ 镜像加载完毕!"

echo ">>> [2/2] 正在拉起服务容器..."
# 由于 docker-compose 已经指向了 ./offline_cache，无需再特殊处理模型。
docker compose up -d

echo "=========================================="
echo "✓ 部署成功！项目正在后台启动..."
echo "请等待十秒左右，您可以通过以下命令查看应用日志："
echo "   docker logs -f cugrs-app"
echo "=========================================="
