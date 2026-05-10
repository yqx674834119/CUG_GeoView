#!/usr/bin/env bash
set -euo pipefail

TAG="${1:-20260509-transferdiag-ports}"
OUT_DIR="${OUT_DIR:-/tmp}"
FRONTEND_IMAGE="${FRONTEND_IMAGE:-crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/geoview-frontend:20260508-frontendfix3-4837450}"
OUT_FILE="${OUT_DIR}/geoview-transferdiag-${TAG}.tar"

images=(
  "geoview-lite-fastapi-chunked:${TAG}"
  "geoview-lite-flask-wsgi:${TAG}"
  "geoview-lite-quart-async:${TAG}"
  "geoview-lite-sanic-stream:${TAG}"
  "geoview-lite-aiohttp-raw:${TAG}"
  "${FRONTEND_IMAGE}"
)

mkdir -p "${OUT_DIR}"
rm -f "${OUT_FILE}" "${OUT_FILE}.sha256"

echo "[GeoView轻量镜像打包] 输出 ${OUT_FILE}"
docker save -o "${OUT_FILE}" "${images[@]}"
sha256sum "${OUT_FILE}" > "${OUT_FILE}.sha256"
ls -lh "${OUT_FILE}" "${OUT_FILE}.sha256"
echo "[GeoView轻量镜像打包] 完成"
