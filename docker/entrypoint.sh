#!/usr/bin/env bash
set -euo pipefail

CONFIG_PATH="${CONFIG_PATH:-/app/config.yaml}"
REQUIRE_GPU="${REQUIRE_GPU:-true}"
RUNTIME_LOG_DIR="${RUNTIME_LOG_DIR:-/tmp/geoview-logs}"
GEOVIEW_CONFIG="${GEOVIEW_CONFIG:-embedded}"
GEOVIEW_STARTUP_DIAGNOSTICS="${GEOVIEW_STARTUP_DIAGNOSTICS:-true}"
GEOVIEW_STRICT_STARTUP_DIAGNOSTICS="${GEOVIEW_STRICT_STARTUP_DIAGNOSTICS:-true}"
GEOVIEW_REQUIRE_BINARY_ASSET_DIAGNOSTICS="${GEOVIEW_REQUIRE_BINARY_ASSET_DIAGNOSTICS:-false}"
GEOVIEW_DIAGNOSTICS_WAIT_TIMEOUT="${GEOVIEW_DIAGNOSTICS_WAIT_TIMEOUT:-60}"
GEOVIEW_BACKEND_DIAGNOSTICS_PATH="${GEOVIEW_BACKEND_DIAGNOSTICS_PATH:-${RUNTIME_LOG_DIR}/backend-startup-diagnostics.json}"
GEOVIEW_EXTERNAL_STATIC_ROOT="${GEOVIEW_EXTERNAL_STATIC_ROOT:-/data/geoview/static}"
GEOVIEW_INTERNAL_STATIC_ROOT="${GEOVIEW_INTERNAL_STATIC_ROOT:-/app/backend/static}"
GEOVIEW_ASSET_READ_ORDER="${GEOVIEW_ASSET_READ_ORDER:-external,internal}"
GEOVIEW_ASSET_DEBUG="${GEOVIEW_ASSET_DEBUG:-1}"
GEOVIEW_DEBUG_LOG="${GEOVIEW_DEBUG_LOG:-true}"
UPLOADED_PHOTOS_DEST="${UPLOADED_PHOTOS_DEST:-${GEOVIEW_EXTERNAL_STATIC_ROOT}/upload}"

source /opt/conda/etc/profile.d/conda.sh

# Predefine GDAL-specific variables to avoid set -u errors during activation
: "${GDAL_DATA:=}"
: "${GDAL_DRIVER_PATH:=}"
: "${GEOTIFF_CSV:=}"
: "${PROJ_LIB:=}"
: "${LIBXML2_DIR:=}"

conda activate PaddleRS37

CONFIG_EXPORTS=$(python - <<'PY'
import os
import yaml


def env_flag(name):
    value = os.environ.get(name)
    if value is None or str(value).strip() == "":
        return None
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


config_path = os.environ.get("CONFIG_PATH", "/app/config.yaml")
default_cfg = {
    "host": {"backend": "0.0.0.0", "frontend": "0.0.0.0"},
    "port": {"backend": 5008, "frontend": 3000},
    "miner": {"enabled": False, "frontend_port": 4000, "backend_port": 8000},
    "database": {"backend": "sqlite", "sqlite_path": "/app/backend/static/geoview.sqlite3"},
    "services": {"backend": True, "frontend": False, "miner": False},
    "assets": {"serve_mode": "buffered", "chunk_size": 1048576},
}

try:
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
except FileNotFoundError:
    print(f"[entrypoint] WARNING: {config_path} was not found; using built-in defaults.", flush=True)
    cfg = {}

host_cfg = {**default_cfg["host"], **(cfg.get("host") or {})}
port_cfg = {**default_cfg["port"], **(cfg.get("port") or {})}

backend_host = host_cfg["backend"]
backend_port = port_cfg["backend"]
frontend_host = host_cfg["frontend"]
frontend_port = port_cfg["frontend"]

client_host = "127.0.0.1" if backend_host == "0.0.0.0" else backend_host

# Miner config
miner_cfg = {**default_cfg["miner"], **(cfg.get("miner") or {})}
miner_enabled = "true" if miner_cfg.get("enabled", False) else "false"
miner_frontend_port = miner_cfg.get("frontend_port", 4000)
miner_backend_port = miner_cfg.get("backend_port", 8000)
database_cfg = {**default_cfg["database"], **(cfg.get("database") or {})}
database_backend = str(database_cfg.get("backend", "sqlite")).lower()
sqlite_path = database_cfg.get("sqlite_path", "/app/backend/static/geoview.sqlite3")
services_cfg = {**default_cfg["services"], **(cfg.get("services") or {})}
assets_cfg = {**default_cfg["assets"], **(cfg.get("assets") or {})}
backend_override = env_flag("GEOVIEW_BACKEND_ENABLED")
frontend_override = env_flag("GEOVIEW_FRONTEND_ENABLED")
miner_override = env_flag("GEOVIEW_MINER_SERVICE_ENABLED")
backend_enabled = "true" if (services_cfg.get("backend", True) if backend_override is None else backend_override) else "false"
frontend_enabled = "true" if (services_cfg.get("frontend", False) if frontend_override is None else frontend_override) else "false"
miner_service_enabled = "true" if (services_cfg.get("miner", False) if miner_override is None else miner_override) else "false"
asset_serve_mode = str(os.environ.get("GEOVIEW_PHOTO_ASSET_SERVE_MODE") or assets_cfg.get("serve_mode", "sendfile")).lower()
asset_chunk_size = int(os.environ.get("GEOVIEW_PHOTO_ASSET_CHUNK_SIZE") or assets_cfg.get("chunk_size", 1048576))
omit_asset_content_length = os.environ.get("GEOVIEW_OMIT_ASSET_CONTENT_LENGTH", "true")

print(f"BACKEND_HOST={backend_host}")
print(f"BACKEND_PORT={backend_port}")
print(f"FRONTEND_HOST={frontend_host}")
print(f"FRONTEND_PORT={frontend_port}")
print(f"BACKEND_CLIENT_HOST={client_host}")
print(f"MINER_ENABLED={miner_enabled}")
print(f"MINER_FRONTEND_PORT={miner_frontend_port}")
print(f"MINER_BACKEND_PORT={miner_backend_port}")
print(f"DATABASE_BACKEND={database_backend}")
print(f"SQLITE_DATABASE_PATH={sqlite_path}")
print(f"BACKEND_ENABLED={backend_enabled}")
print(f"FRONTEND_ENABLED={frontend_enabled}")
print(f"MINER_SERVICE_ENABLED={miner_service_enabled}")
print(f"GEOVIEW_PHOTO_ASSET_SERVE_MODE={asset_serve_mode}")
print(f"GEOVIEW_PHOTO_ASSET_CHUNK_SIZE={asset_chunk_size}")
print(f"GEOVIEW_OMIT_ASSET_CONTENT_LENGTH={omit_asset_content_length}")
PY
)

eval "${CONFIG_EXPORTS}"
export GEOVIEW_CONFIG DATABASE_BACKEND SQLITE_DATABASE_PATH
export GEOVIEW_PHOTO_ASSET_SERVE_MODE GEOVIEW_PHOTO_ASSET_CHUNK_SIZE GEOVIEW_OMIT_ASSET_CONTENT_LENGTH
export GEOVIEW_STARTUP_DIAGNOSTICS GEOVIEW_STRICT_STARTUP_DIAGNOSTICS
export GEOVIEW_REQUIRE_BINARY_ASSET_DIAGNOSTICS
export GEOVIEW_DIAGNOSTICS_WAIT_TIMEOUT GEOVIEW_BACKEND_DIAGNOSTICS_PATH
export GEOVIEW_EXTERNAL_STATIC_ROOT GEOVIEW_INTERNAL_STATIC_ROOT
export GEOVIEW_ASSET_READ_ORDER GEOVIEW_ASSET_DEBUG GEOVIEW_DEBUG_LOG UPLOADED_PHOTOS_DEST

mkdir -p "${RUNTIME_LOG_DIR}"
mkdir -p \
  "${GEOVIEW_EXTERNAL_STATIC_ROOT}/upload/res" \
  "${GEOVIEW_INTERNAL_STATIC_ROOT}/upload/res" \
  "$(dirname "${SQLITE_DATABASE_PATH}")"
echo "[GeoView后端容器调试] 后端容器启动参数已解析"
echo "[GeoView后端容器调试] asset external static root=${GEOVIEW_EXTERNAL_STATIC_ROOT}"
echo "[GeoView后端容器调试] asset internal static root=${GEOVIEW_INTERNAL_STATIC_ROOT}"
echo "[GeoView后端容器调试] asset upload dest=${UPLOADED_PHOTOS_DEST}"
echo "[GeoView后端容器调试] asset read order=${GEOVIEW_ASSET_READ_ORDER}"
echo "[GeoView后端容器调试] photo asset serve mode=${GEOVIEW_PHOTO_ASSET_SERVE_MODE}"
echo "[GeoView后端容器调试] photo asset chunk size=${GEOVIEW_PHOTO_ASSET_CHUNK_SIZE}"
echo "[GeoView后端容器调试] omit non-range asset content-length=${GEOVIEW_OMIT_ASSET_CONTENT_LENGTH}"
echo "[GeoView后端容器调试] debug log enabled=${GEOVIEW_DEBUG_LOG}"
echo "[GeoView后端容器调试] require binary asset diagnostics=${GEOVIEW_REQUIRE_BINARY_ASSET_DIAGNOSTICS}"
if ! touch "${GEOVIEW_EXTERNAL_STATIC_ROOT}/.geoview-write-test" 2>/dev/null; then
  echo "[GeoView后端容器调试] 警告：外部静态目录不可写，上传/历史图片可能失败：${GEOVIEW_EXTERNAL_STATIC_ROOT}" >&2
else
  rm -f "${GEOVIEW_EXTERNAL_STATIC_ROOT}/.geoview-write-test" 2>/dev/null || true
  echo "[GeoView后端容器调试] 外部静态目录写入检查通过"
fi

# Write GeoView frontend .env (include Miner toggle)
cat > /app/frontend/.env <<EOF
VUE_APP_BACKEND_PORT = ${BACKEND_PORT}
VUE_APP_BACKEND_IP = ${BACKEND_CLIENT_HOST}
VUE_APP_MINER_ENABLED = ${MINER_ENABLED}
VUE_APP_MINER_URL = http://localhost:${MINER_FRONTEND_PORT}
EOF

GPU_COUNT=0
if [ "${BACKEND_ENABLED}" = "true" ]; then
GPU_COUNT=$(python - <<'PY'
import paddle

def gpu_count():
    try:
        if not paddle.device.is_compiled_with_cuda():
            return 0
        return paddle.device.cuda.device_count()
    except Exception:
        return 0

print(gpu_count())
PY
)
fi

if [ "${BACKEND_ENABLED}" = "true" ] && [ "${GPU_COUNT:-0}" = "0" ]; then
  if [ "${REQUIRE_GPU}" = "true" ]; then
    echo "[entrypoint] ERROR: GPU is required, but no usable GPU was detected inside the container." >&2
    echo "[entrypoint] Check the host NVIDIA driver, container runtime, and docker compose GPU settings." >&2
    exit 1
  fi
  unset CUDA_VISIBLE_DEVICES || true
  unset FLAGS_selected_gpus || true
  echo "[entrypoint] No GPU detected, forcing Paddle to use CPU." >&2
else
  echo "[GeoView后端容器调试] 检测到 ${GPU_COUNT} 块 GPU。"
fi

if [ "${BACKEND_ENABLED}" = "true" ]; then
  python /app/sync_model_assets.py --quiet
fi

if [ "${BACKEND_ENABLED}" = "true" ] && { [ "${DATABASE_BACKEND}" = "sqlite" ] || [ "${GEOVIEW_CONFIG}" = "embedded" ]; }; then
  export GEOVIEW_CONFIG=embedded
  echo "[GeoView后端容器调试] 使用内置 SQLite 数据库：${SQLITE_DATABASE_PATH}，跳过 MySQL 等待。"
elif [ "${BACKEND_ENABLED}" = "true" ]; then
  python - <<'PY'
import os
import sys
import time

import pymysql

host = os.getenv("MYSQL_HOST", "127.0.0.1")
port = int(os.getenv("MYSQL_PORT", "3306"))
user = os.getenv("MYSQL_USERNAME", "root")
password = os.getenv("MYSQL_PASSWORD", "")
database = os.getenv("MYSQL_DATABASE", "")

for attempt in range(30):
    try:
        conn = pymysql.connect(host=host, port=port, user=user, password=password, database=database or None)
        conn.close()
        break
    except Exception as exc:
        wait = 2
        print(f"[entrypoint] Waiting for MySQL at {host}:{port} (attempt {attempt + 1}/30): {exc}", flush=True)
        time.sleep(wait)
else:
    print("[entrypoint] MySQL did not become available in time, exiting.", flush=True)
    sys.exit(1)
PY
fi

BACKEND_PID=""
if [ "${BACKEND_ENABLED}" = "true" ]; then
  cd /app/backend
  gunicorn app:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind "${BACKEND_HOST}:${BACKEND_PORT}" \
    --workers "${GEOVIEW_BACKEND_WORKERS:-1}" \
    --timeout "${GEOVIEW_BACKEND_TIMEOUT:-3600}" \
    --graceful-timeout "${GEOVIEW_BACKEND_GRACEFUL_TIMEOUT:-60}" \
    --access-logfile - \
    --error-logfile - &
  BACKEND_PID=$!

  if [ "${GEOVIEW_STARTUP_DIAGNOSTICS}" = "true" ]; then
    echo "[GeoView后端容器调试] 开始执行后端启动资产诊断..."
    if ! python /usr/local/bin/backend_startup_diagnostics.py; then
      echo "[GeoView后端容器调试] 后端启动资产诊断失败。" >&2
      kill -TERM "${BACKEND_PID}" 2>/dev/null || true
      wait "${BACKEND_PID}" 2>/dev/null || true
      exit 1
    fi
  else
    echo "[GeoView后端容器调试] 后端启动资产诊断已关闭。"
  fi
fi

FRONTEND_PID=""
if [ "${FRONTEND_ENABLED}" = "true" ]; then
  cd /app/frontend
  if [ ! -d node_modules ]; then
    npm install --no-audit --prefer-offline >"${RUNTIME_LOG_DIR}/frontend-npm.log" 2>&1
  else
    echo "[entrypoint] frontend node_modules exists; skipping npm install."
  fi
  npm run serve -- --host "${FRONTEND_HOST}" --port "${FRONTEND_PORT}" >"${RUNTIME_LOG_DIR}/frontend.log" 2>&1 &
  FRONTEND_PID=$!
fi

# --- Miner (矿山监测系统) conditional startup ---
MINER_BACKEND_PID=""
MINER_FRONTEND_PID=""

if [ "${MINER_ENABLED}" = "true" ] && [ "${MINER_SERVICE_ENABLED}" = "true" ]; then
  echo "[entrypoint] Miner is ENABLED. Starting Miner services..."

  # Write Miner .env for GeoView URL
  cat > /app/miner/.env <<MENV
VITE_GEOVIEW_URL=http://localhost:${FRONTEND_PORT}/#/detectchanges
MENV

  # Start Miner Express backend (using Node.js 20)
  cd /app/miner
  PATH=/opt/node20/bin:$PATH PORT=${MINER_BACKEND_PORT} node server.js >"${RUNTIME_LOG_DIR}/miner-backend.log" 2>&1 &
  MINER_BACKEND_PID=$!

  # Start Miner Vite dev server (using Node.js 20)
  cd /app/miner
  if [ ! -d node_modules ]; then
    PATH=/opt/node20/bin:$PATH npm install --no-audit --prefer-offline >"${RUNTIME_LOG_DIR}/miner-npm.log" 2>&1
  else
    echo "[entrypoint] miner node_modules exists; skipping npm install."
  fi
  PATH=/opt/node20/bin:$PATH npx vite --host 0.0.0.0 --port "${MINER_FRONTEND_PORT}" >"${RUNTIME_LOG_DIR}/miner-frontend.log" 2>&1 &
  MINER_FRONTEND_PID=$!

  echo "[entrypoint] Miner backend PID=${MINER_BACKEND_PID}, frontend PID=${MINER_FRONTEND_PID}"
else
  echo "[entrypoint] Miner is DISABLED. Skipping Miner services."
fi

cd /app

terminate() {
  trap - SIGTERM SIGINT
  if [ -n "${BACKEND_PID}" ]; then
    kill -TERM "${BACKEND_PID}" 2>/dev/null || true
  fi
  if [ -n "${FRONTEND_PID}" ]; then
    kill -TERM "${FRONTEND_PID}" 2>/dev/null || true
  fi
  if [ -n "${MINER_BACKEND_PID}" ]; then
    kill -TERM "${MINER_BACKEND_PID}" 2>/dev/null || true
  fi
  if [ -n "${MINER_FRONTEND_PID}" ]; then
    kill -TERM "${MINER_FRONTEND_PID}" 2>/dev/null || true
  fi
  if [ -n "${BACKEND_PID}" ]; then
    wait "${BACKEND_PID}" 2>/dev/null || true
  fi
  if [ -n "${FRONTEND_PID}" ]; then
    wait "${FRONTEND_PID}" 2>/dev/null || true
  fi
  if [ -n "${MINER_BACKEND_PID}" ]; then
    wait "${MINER_BACKEND_PID}" 2>/dev/null || true
  fi
  if [ -n "${MINER_FRONTEND_PID}" ]; then
    wait "${MINER_FRONTEND_PID}" 2>/dev/null || true
  fi
}

trap terminate SIGTERM SIGINT

if [ -n "${BACKEND_PID}" ] && [ -n "${FRONTEND_PID}" ]; then
  wait -n "${BACKEND_PID}" "${FRONTEND_PID}"
elif [ -n "${BACKEND_PID}" ]; then
  wait "${BACKEND_PID}"
elif [ -n "${FRONTEND_PID}" ]; then
  wait "${FRONTEND_PID}"
else
  echo "[entrypoint] ERROR: neither backend nor frontend service is enabled." >&2
  exit 1
fi
terminate
