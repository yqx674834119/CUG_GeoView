#!/usr/bin/env bash
set -euo pipefail

TAG="${1:-20260508-transferdiag1}"
REGISTRY_PREFIX="${REGISTRY_PREFIX:-}"

if [[ -z "${REGISTRY_PREFIX}" ]]; then
  echo "[GeoView轻量后端推送] REGISTRY_PREFIX 为空，只能推送本地仓库名；如需阿里云请先设置 REGISTRY_PREFIX=crpi-xxx.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/" >&2
fi

images=(
  "geoview-lite-fastapi-chunked"
  "geoview-lite-flask-wsgi"
  "geoview-lite-quart-async"
  "geoview-lite-sanic-stream"
  "geoview-lite-aiohttp-raw"
)

for name in "${images[@]}"; do
  image="${REGISTRY_PREFIX}${name}:${TAG}"
  echo "[GeoView轻量后端推送] 推送 ${image}"
  docker push "${image}"
done

echo "[GeoView轻量后端推送] 全部推送完成"
