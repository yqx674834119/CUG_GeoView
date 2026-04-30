#!/bin/sh
set -eu

WEB_ROOT="${GEOVIEW_WEB_ROOT:-/usr/share/nginx/html}"
STRICT_RUNTIME_DIAGNOSTICS="${GEOVIEW_STRICT_RUNTIME_DIAGNOSTICS:-true}"

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
BACKEND_ASSET_MODE="${GEOVIEW_BACKEND_ASSET_MODE:-buffered}"
FRONTEND_ASSET_DEBUG="${GEOVIEW_FRONTEND_ASSET_DEBUG:-false}"

if [ -z "${BACKEND_URL}" ] && [ -z "${BACKEND_PORT}" ]; then
    BACKEND_PORT="5008"
fi

mkdir -p "${WEB_ROOT}"

case "${BACKEND_ASSET_MODE}" in
    buffered|sendfile|chunked)
        ASSET_MODE_VALID="true"
        ;;
    *)
        ASSET_MODE_VALID="false"
        ;;
esac

RESOLVED_BACKEND_URL="${BACKEND_URL}"
if [ -z "${RESOLVED_BACKEND_URL}" ] && [ -n "${BACKEND_HOST}" ] && [ -n "${BACKEND_PORT}" ]; then
    RESOLVED_BACKEND_URL="${BACKEND_PROTOCOL}://${BACKEND_HOST}:${BACKEND_PORT}"
fi
if [ -z "${RESOLVED_BACKEND_URL}" ] && [ -n "${BACKEND_PORT}" ]; then
    RESOLVED_BACKEND_URL="${BACKEND_PROTOCOL}://127.0.0.1:${BACKEND_PORT}"
fi

PREFERRED_ASSET_PREFIX="/api/file/assets/photos/"
if [ "${BACKEND_ASSET_MODE}" = "buffered" ]; then
    PREFERRED_ASSET_PREFIX="/api/file/assets-buffered/photos/"
fi

cat > "${WEB_ROOT}/runtime-config.js" <<EOF
window.__GEOVIEW_RUNTIME_CONFIG__ = {
  backendUrl: "$(js_escape "${BACKEND_URL}")",
  backendProtocol: "$(js_escape "${BACKEND_PROTOCOL}")",
  backendHost: "$(js_escape "${BACKEND_HOST}")",
  backendPort: "$(js_escape "${BACKEND_PORT}")",
  backendAssetMode: "$(js_escape "${BACKEND_ASSET_MODE}")",
  frontendAssetDebug: "$(js_escape "${FRONTEND_ASSET_DEBUG}")",
  minerEnabled: "$(js_escape "${MINER_ENABLED}")",
  minerUrl: "$(js_escape "${MINER_URL}")",
  baiduMapAccessKey: "$(js_escape "${BAIDU_MAP_ACCESS_KEY}")"
};
EOF

cat > "${WEB_ROOT}/runtime-diagnostics.json" <<EOF
{
  "status": "$([ "${ASSET_MODE_VALID}" = "true" ] && printf 'ok' || printf 'invalid')",
  "resolvedBackendUrl": "$(js_escape "${RESOLVED_BACKEND_URL}")",
  "backendUrl": "$(js_escape "${BACKEND_URL}")",
  "backendProtocol": "$(js_escape "${BACKEND_PROTOCOL}")",
  "backendHost": "$(js_escape "${BACKEND_HOST}")",
  "backendPort": "$(js_escape "${BACKEND_PORT}")",
  "backendAssetMode": "$(js_escape "${BACKEND_ASSET_MODE}")",
  "frontendAssetDebug": "$(js_escape "${FRONTEND_ASSET_DEBUG}")",
  "preferredAssetPrefix": "$(js_escape "${PREFERRED_ASSET_PREFIX}")",
  "legacyAssetPrefix": "/_uploads/photos/",
  "strictRuntimeDiagnostics": "$(js_escape "${STRICT_RUNTIME_DIAGNOSTICS}")"
}
EOF

echo "[diag][frontend] runtime diagnostics summary"
echo "[diag][frontend] resolved_backend_url=${RESOLVED_BACKEND_URL}"
echo "[diag][frontend] backend_asset_mode=${BACKEND_ASSET_MODE}"
echo "[diag][frontend] frontend_asset_debug=${FRONTEND_ASSET_DEBUG}"
echo "[diag][frontend] preferred_asset_prefix=${PREFERRED_ASSET_PREFIX}"
echo "[diag][frontend] diagnostics_file=${WEB_ROOT}/runtime-diagnostics.json"

if [ "${ASSET_MODE_VALID}" != "true" ]; then
    echo "[diag][frontend] error=unsupported GEOVIEW_BACKEND_ASSET_MODE: ${BACKEND_ASSET_MODE}" >&2
    if [ "${STRICT_RUNTIME_DIAGNOSTICS}" = "true" ]; then
        exit 1
    fi
fi

if [ -z "${RESOLVED_BACKEND_URL}" ]; then
    echo "[diag][frontend] error=backend target is empty; set GEOVIEW_BACKEND_URL or HOST/PORT" >&2
    if [ "${STRICT_RUNTIME_DIAGNOSTICS}" = "true" ]; then
        exit 1
    fi
fi

if [ "${GEOVIEW_START_HTTPD:-false}" = "true" ]; then
    exec /bin/busybox httpd -f -p "${GEOVIEW_HTTP_PORT:-80}" -h "${WEB_ROOT}"
fi
