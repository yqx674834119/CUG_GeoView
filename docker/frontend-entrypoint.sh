#!/bin/sh
set -eu

WEB_ROOT="${GEOVIEW_WEB_ROOT:-/usr/share/nginx/html}"

js_escape() {
    printf '%s' "${1:-}" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

BACKEND_URL="${GEOVIEW_BACKEND_URL:-}"
BACKEND_PROTOCOL="${GEOVIEW_BACKEND_PROTOCOL:-http}"
BACKEND_HOST="${GEOVIEW_BACKEND_HOST:-}"
BACKEND_PORT="${GEOVIEW_BACKEND_PORT:-5008}"
MINER_ENABLED="${GEOVIEW_MINER_ENABLED:-false}"
MINER_URL="${GEOVIEW_MINER_URL:-}"
BAIDU_MAP_ACCESS_KEY="${GEOVIEW_BAIDU_MAP_ACCESS_KEY:-}"

mkdir -p "${WEB_ROOT}"

cat > "${WEB_ROOT}/runtime-config.js" <<EOF
window.__GEOVIEW_RUNTIME_CONFIG__ = {
  backendUrl: "$(js_escape "${BACKEND_URL}")",
  backendProtocol: "$(js_escape "${BACKEND_PROTOCOL}")",
  backendHost: "$(js_escape "${BACKEND_HOST}")",
  backendPort: "$(js_escape "${BACKEND_PORT}")",
  minerEnabled: "$(js_escape "${MINER_ENABLED}")",
  minerUrl: "$(js_escape "${MINER_URL}")",
  baiduMapAccessKey: "$(js_escape "${BAIDU_MAP_ACCESS_KEY}")"
};
EOF

if [ "${GEOVIEW_START_HTTPD:-false}" = "true" ]; then
    exec /bin/busybox httpd -f -p "${GEOVIEW_HTTP_PORT:-80}" -h "${WEB_ROOT}"
fi
