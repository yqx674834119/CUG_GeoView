#!/bin/sh
set -eu

WEB_ROOT="${GEOVIEW_WEB_ROOT:-/usr/share/nginx/html}"

js_escape() {
    printf '%s' "${1:-}" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

BACKEND_URL="${GEOVIEW_BACKEND_URL:-}"
BACKEND_PROTOCOL="${GEOVIEW_BACKEND_PROTOCOL:-http}"
BACKEND_HOST="${GEOVIEW_BACKEND_HOST:-}"
BACKEND_PORT="${GEOVIEW_BACKEND_PORT:-}"
MINER_ENABLED="${GEOVIEW_MINER_ENABLED:-false}"
MINER_URL="${GEOVIEW_MINER_URL:-}"
BAIDU_MAP_ACCESS_KEY="${GEOVIEW_BAIDU_MAP_ACCESS_KEY:-}"
BACKEND_ASSET_MODE="${GEOVIEW_BACKEND_ASSET_MODE:-sendfile}"
FRONTEND_ASSET_DEBUG="${GEOVIEW_FRONTEND_ASSET_DEBUG:-false}"
FRONTEND_DEBUG="${GEOVIEW_FRONTEND_DEBUG:-false}"
FRONTEND_VERSION_TAG="${GEOVIEW_FRONTEND_VERSION_TAG:-}"

if [ -z "${BACKEND_URL}" ] && [ -z "${BACKEND_PORT}" ]; then
    BACKEND_PORT="5008"
fi

mkdir -p "${WEB_ROOT}"

RESOLVED_BACKEND_URL="${BACKEND_URL}"
if [ -z "${RESOLVED_BACKEND_URL}" ] && [ -n "${BACKEND_HOST}" ] && [ -n "${BACKEND_PORT}" ]; then
    RESOLVED_BACKEND_URL="${BACKEND_PROTOCOL}://${BACKEND_HOST}:${BACKEND_PORT}"
fi
if [ -z "${RESOLVED_BACKEND_URL}" ] && [ -n "${BACKEND_PORT}" ]; then
    RESOLVED_BACKEND_URL="${BACKEND_PROTOCOL}://127.0.0.1:${BACKEND_PORT}"
fi

cat > "${WEB_ROOT}/runtime-config.js" <<EOF
window.__GEOVIEW_RUNTIME_CONFIG__ = {
  backendUrl: "$(js_escape "${BACKEND_URL}")",
  backendProtocol: "$(js_escape "${BACKEND_PROTOCOL}")",
  backendHost: "$(js_escape "${BACKEND_HOST}")",
  backendPort: "$(js_escape "${BACKEND_PORT}")",
  backendAssetMode: "$(js_escape "${BACKEND_ASSET_MODE}")",
  frontendAssetDebug: "$(js_escape "${FRONTEND_ASSET_DEBUG}")",
  frontendDebug: "$(js_escape "${FRONTEND_DEBUG}")",
  frontendVersionTag: "$(js_escape "${FRONTEND_VERSION_TAG}")",
  minerEnabled: "$(js_escape "${MINER_ENABLED}")",
  minerUrl: "$(js_escape "${MINER_URL}")",
  baiduMapAccessKey: "$(js_escape "${BAIDU_MAP_ACCESS_KEY}")"
};
EOF
echo "[GeoView] runtime-config.js generated backend_url=${RESOLVED_BACKEND_URL}"

if [ "${GEOVIEW_START_HTTPD:-false}" = "true" ]; then
    exec /bin/busybox httpd -f -p "${GEOVIEW_HTTP_PORT:-80}" -h "${WEB_ROOT}"
fi
