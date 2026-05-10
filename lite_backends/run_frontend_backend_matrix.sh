#!/usr/bin/env bash
set -euo pipefail

TAG="${1:-20260509-transferdiag-ports}"
FRONTEND_IMAGE="${FRONTEND_IMAGE:-crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/geoview-frontend:20260508-frontendfix3-4837450}"

rows=(
  "fastapi:geoview-lite-fastapi-chunked:${TAG}:5101:3101"
  "flask:geoview-lite-flask-wsgi:${TAG}:5102:3102"
  "quart:geoview-lite-quart-async:${TAG}:5103:3103"
  "sanic:geoview-lite-sanic-stream:${TAG}:5104:3104"
  "aiohttp:geoview-lite-aiohttp-raw:${TAG}:5105:3105"
)

for row in "${rows[@]}"; do
  IFS=":" read -r key backend_repo backend_tag backend_port frontend_port <<< "${row}"
  backend_name="geoview-lite-${key}-backend"
  frontend_name="geoview-lite-${key}-frontend"
  backend_image="${backend_repo}:${backend_tag}"
  backend_url="http://127.0.0.1:${backend_port}/"

  docker rm -f "${backend_name}" "${frontend_name}" "${backend_repo}-test" >/dev/null 2>&1 || true

  echo "[GeoView轻量矩阵启动] 启动后端 ${backend_name}: ${backend_image} -> ${backend_port}:${backend_port}"
  docker run -d --name "${backend_name}" \
    -p "${backend_port}:${backend_port}" \
    -e PORT="${backend_port}" \
    -e GEOVIEW_DEBUG_LOG=true \
    -e GEOVIEW_TRANSFER_MODE=chunked \
    -e GEOVIEW_OMIT_CONTENT_LENGTH=true \
    "${backend_image}" >/dev/null

  for _ in $(seq 1 40); do
    if curl -fsS "http://127.0.0.1:${backend_port}/api/system/ping" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done

  echo "[GeoView轻量矩阵启动] 启动前端 ${frontend_name}: ${FRONTEND_IMAGE} -> ${frontend_port}:80，后端=${backend_url}"
  docker run -d --name "${frontend_name}" \
    -p "${frontend_port}:80" \
    -e GEOVIEW_BACKEND_URL="${backend_url}" \
    -e GEOVIEW_BACKEND_ASSET_MODE=buffered \
    -e GEOVIEW_FRONTEND_ASSET_DEBUG=true \
    -e GEOVIEW_FRONTEND_DEBUG=true \
    "${FRONTEND_IMAGE}" >/dev/null

  for _ in $(seq 1 30); do
    if curl -fsS "http://127.0.0.1:${frontend_port}/runtime-diagnostics.json" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
done

echo "[GeoView轻量矩阵启动] 5 组前后端已启动："
echo "FastAPI  前端 http://127.0.0.1:3101  后端 http://127.0.0.1:5101"
echo "Flask    前端 http://127.0.0.1:3102  后端 http://127.0.0.1:5102"
echo "Quart    前端 http://127.0.0.1:3103  后端 http://127.0.0.1:5103"
echo "Sanic    前端 http://127.0.0.1:3104  后端 http://127.0.0.1:5104"
echo "aiohttp  前端 http://127.0.0.1:3105  后端 http://127.0.0.1:5105"
