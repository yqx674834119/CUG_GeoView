#!/usr/bin/env bash
set -euo pipefail

TAG="${1:-20260509-transferdiag-ports}"
FRONTEND_IMAGE="${FRONTEND_IMAGE:-crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/geoview-frontend:20260508-frontendfix3-4837450}"

backend_rows=(
  "fastapi:geoview-lite-fastapi-chunked:${TAG}:5101"
  "flask:geoview-lite-flask-wsgi:${TAG}:5102"
  "quart:geoview-lite-quart-async:${TAG}:5103"
  "sanic:geoview-lite-sanic-stream:${TAG}:5104"
  "aiohttp:geoview-lite-aiohttp-raw:${TAG}:5105"
)

for row in "${backend_rows[@]}"; do
  IFS=":" read -r key repo image_tag port <<< "${row}"
  image="${repo}:${image_tag}"
  name="geoview-lite-${key}-offline-check"
  docker rm -f "${name}" >/dev/null 2>&1 || true
  echo "[GeoView离线自检] 后端无网络启动 ${image}"
  docker run -d --network none --name "${name}" \
    -e PORT="${port}" \
    -e GEOVIEW_DEBUG_LOG=true \
    -e GEOVIEW_TRANSFER_MODE=chunked \
    -e GEOVIEW_OMIT_CONTENT_LENGTH=true \
    "${image}" >/dev/null
  sleep 4
  docker exec "${name}" python - "${port}" <<'PY'
import json
import sys
import time
import urllib.request

port = sys.argv[1]
base = f"http://127.0.0.1:{port}"
last_error = None
for _ in range(40):
    try:
        with urllib.request.urlopen(base + "/api/system/ping", timeout=3) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        assert payload.get("code") == 0, payload
        break
    except Exception as exc:
        last_error = exc
        time.sleep(1)
else:
    raise SystemExit(f"ping failed: {last_error}")

with urllib.request.urlopen(base + "/api/history/list?page=1&limit=10", timeout=10) as resp:
    history = json.loads(resp.read().decode("utf-8"))
assert history.get("code") == 0 and len(history.get("data") or []) >= 7, history

with urllib.request.urlopen(base + "/api/file/assets/photos/cd_val1_2_3mb.png", timeout=20) as resp:
    body = resp.read()
assert len(body) > 2_000_000, len(body)
print("[GeoView离线自检] 后端容器无网络自检通过", flush=True)
PY
  docker rm -f "${name}" >/dev/null
done

frontend_name="geoview-lite-frontend-offline-check"
docker rm -f "${frontend_name}" >/dev/null 2>&1 || true
echo "[GeoView离线自检] 前端无网络启动 ${FRONTEND_IMAGE}"
docker run -d --network none --name "${frontend_name}" \
  -e GEOVIEW_BACKEND_URL="http://127.0.0.1:5101/" \
  -e GEOVIEW_BACKEND_ASSET_MODE=buffered \
  -e GEOVIEW_FRONTEND_ASSET_DEBUG=true \
  -e GEOVIEW_FRONTEND_DEBUG=true \
  "${FRONTEND_IMAGE}" >/dev/null
sleep 3
docker exec "${frontend_name}" sh -c 'test -s /usr/share/nginx/html/index.html && test -s /usr/share/nginx/html/runtime-config.js && test -s /usr/share/nginx/html/runtime-diagnostics.json'
docker rm -f "${frontend_name}" >/dev/null

echo "[GeoView离线自检] 所有镜像无外网依赖自检通过"
