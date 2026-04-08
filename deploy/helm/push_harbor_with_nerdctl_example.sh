#!/bin/bash
set -euo pipefail

# This script is a template for the relay/server-side environment.
# Adjust PROJECT and APP_VERSION before running.

HARBOR_REGISTRY="${HARBOR_REGISTRY:-172.20.20.243:8443}"
HARBOR_USER="${HARBOR_USER:-admin}"
HARBOR_PASSWORD="${HARBOR_PASSWORD:-Hc@Cloud01}"

PROJECT="${PROJECT:-your-project}"
APP_VERSION="${APP_VERSION:-20260401}"

APP_SOURCE_IMAGE="${APP_SOURCE_IMAGE:-crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/cugrs:latest}"
MYSQL_SOURCE_IMAGE="${MYSQL_SOURCE_IMAGE:-registry.openanolis.cn/openanolis/mysql:8.0.30-8.6}"

APP_TARGET_IMAGE="${HARBOR_REGISTRY}/${PROJECT}/geoview-app:${APP_VERSION}"
MYSQL_TARGET_IMAGE="${HARBOR_REGISTRY}/${PROJECT}/mysql:8.0.30-8.6"

echo "==> Login to Harbor"
nerdctl login "${HARBOR_REGISTRY}" -u "${HARBOR_USER}" -p "${HARBOR_PASSWORD}"

echo "==> Pull source images"
nerdctl pull "${APP_SOURCE_IMAGE}"
nerdctl pull "${MYSQL_SOURCE_IMAGE}"

echo "==> Retag images for Harbor"
nerdctl tag "${APP_SOURCE_IMAGE}" "${APP_TARGET_IMAGE}"
nerdctl tag "${MYSQL_SOURCE_IMAGE}" "${MYSQL_TARGET_IMAGE}"

echo "==> Push images to Harbor"
nerdctl push "${APP_TARGET_IMAGE}"
nerdctl push "${MYSQL_TARGET_IMAGE}"

echo "==> Done"
echo "APP_TARGET_IMAGE=${APP_TARGET_IMAGE}"
echo "MYSQL_TARGET_IMAGE=${MYSQL_TARGET_IMAGE}"

