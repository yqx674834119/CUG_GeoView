#!/usr/bin/env bash
set -euo pipefail

TAG="${1:-20260508-transferdiag1}"

images=(
  "geoview-lite-fastapi-chunked:${TAG}:5101:5101"
  "geoview-lite-flask-wsgi:${TAG}:5102:5102"
  "geoview-lite-quart-async:${TAG}:5103:5103"
  "geoview-lite-sanic-stream:${TAG}:5104:5104"
  "geoview-lite-aiohttp-raw:${TAG}:5105:5105"
)

for item in "${images[@]}"; do
  IFS=":" read -r repo tag host_port container_port <<< "${item}"
  name="${repo}-test"
  image="${repo}:${tag}"
  echo "[GeoView轻量后端测试] 启动 ${image} -> ${host_port}:${container_port}"
  docker rm -f "${name}" >/dev/null 2>&1 || true
  docker run -d --name "${name}" \
    -p "${host_port}:${container_port}" \
    -e PORT="${container_port}" \
    -e GEOVIEW_DEBUG_LOG=true \
    -e GEOVIEW_TRANSFER_MODE=chunked \
    -e GEOVIEW_OMIT_CONTENT_LENGTH=true \
    "${image}" >/dev/null
  for _ in $(seq 1 40); do
    if curl -fsS "http://127.0.0.1:${host_port}/api/system/ping" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
  python lite_backends/test_lite_backend.py --base-url "http://127.0.0.1:${host_port}"
done

echo "[GeoView轻量后端测试] 全部变体测试完成"
