#!/usr/bin/env bash
set -euo pipefail

TAG="${1:-20260508-transferdiag1}"
REGISTRY_PREFIX="${REGISTRY_PREFIX:-}"

build_one() {
  local name="$1"
  local dockerfile="$2"
  local image="${REGISTRY_PREFIX}${name}:${TAG}"
  local base_arg="${3:-}"
  echo "[GeoView轻量后端构建] 开始构建 ${image}"
  if [[ -n "${base_arg}" ]]; then
    docker build --build-arg "BASE_IMAGE=${base_arg}" -f "lite_backends/${dockerfile}" -t "${image}" .
  else
    docker build -f "lite_backends/${dockerfile}" -t "${image}" .
  fi
  echo "[GeoView轻量后端构建] 构建完成 ${image}"
}

build_one "geoview-lite-fastapi-chunked" "Dockerfile.fastapi"
build_one "geoview-lite-flask-wsgi" "Dockerfile.flask" "${REGISTRY_PREFIX}geoview-lite-fastapi-chunked:${TAG}"
build_one "geoview-lite-quart-async" "Dockerfile.quart" "${REGISTRY_PREFIX}geoview-lite-fastapi-chunked:${TAG}"
build_one "geoview-lite-sanic-stream" "Dockerfile.sanic" "${REGISTRY_PREFIX}geoview-lite-fastapi-chunked:${TAG}"
build_one "geoview-lite-aiohttp-raw" "Dockerfile.aiohttp" "${REGISTRY_PREFIX}geoview-lite-fastapi-chunked:${TAG}"

echo "[GeoView轻量后端构建] 镜像大小："
docker images --format '{{.Repository}}:{{.Tag}} {{.Size}}' | grep "${TAG}" | grep 'geoview-lite' || true
