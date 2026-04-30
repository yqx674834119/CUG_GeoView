#!/usr/bin/env bash
set -euo pipefail

CONFIG_PATH="${CONFIG_PATH:-/app/config.yaml}"
REQUIRE_GPU="${REQUIRE_GPU:-true}"
RUNTIME_LOG_DIR="${RUNTIME_LOG_DIR:-/tmp/geoview-logs}"
FLASK_CONFIG="${FLASK_CONFIG:-embedded}"
GEOVIEW_STARTUP_DIAGNOSTICS="${GEOVIEW_STARTUP_DIAGNOSTICS:-true}"
GEOVIEW_STRICT_STARTUP_DIAGNOSTICS="${GEOVIEW_STRICT_STARTUP_DIAGNOSTICS:-true}"
GEOVIEW_REQUIRE_BINARY_ASSET_DIAGNOSTICS="${GEOVIEW_REQUIRE_BINARY_ASSET_DIAGNOSTICS:-false}"
GEOVIEW_DIAGNOSTICS_WAIT_TIMEOUT="${GEOVIEW_DIAGNOSTICS_WAIT_TIMEOUT:-60}"
GEOVIEW_BACKEND_DIAGNOSTICS_PATH="${GEOVIEW_BACKEND_DIAGNOSTICS_PATH:-${RUNTIME_LOG_DIR}/backend-startup-diagnostics.json}"
GEOVIEW_EXTERNAL_STATIC_ROOT="${GEOVIEW_EXTERNAL_STATIC_ROOT:-/data/geoview/static}"
GEOVIEW_INTERNAL_STATIC_ROOT="${GEOVIEW_INTERNAL_STATIC_ROOT:-/app/backend/static}"
GEOVIEW_ASSET_READ_ORDER="${GEOVIEW_ASSET_READ_ORDER:-external,internal}"
GEOVIEW_ASSET_DEBUG="${GEOVIEW_ASSET_DEBUG:-1}"
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
backend_enabled = "true" if services_cfg.get("backend", True) else "false"
frontend_enabled = "true" if services_cfg.get("frontend", False) else "false"
miner_service_enabled = "true" if services_cfg.get("miner", False) else "false"
asset_serve_mode = str(assets_cfg.get("serve_mode", "sendfile")).lower()
asset_chunk_size = int(assets_cfg.get("chunk_size", 1048576))

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
PY
)

eval "${CONFIG_EXPORTS}"
export FLASK_CONFIG DATABASE_BACKEND SQLITE_DATABASE_PATH
export GEOVIEW_PHOTO_ASSET_SERVE_MODE GEOVIEW_PHOTO_ASSET_CHUNK_SIZE
export GEOVIEW_STARTUP_DIAGNOSTICS GEOVIEW_STRICT_STARTUP_DIAGNOSTICS
export GEOVIEW_REQUIRE_BINARY_ASSET_DIAGNOSTICS
export GEOVIEW_DIAGNOSTICS_WAIT_TIMEOUT GEOVIEW_BACKEND_DIAGNOSTICS_PATH
export GEOVIEW_EXTERNAL_STATIC_ROOT GEOVIEW_INTERNAL_STATIC_ROOT
export GEOVIEW_ASSET_READ_ORDER GEOVIEW_ASSET_DEBUG UPLOADED_PHOTOS_DEST

mkdir -p "${RUNTIME_LOG_DIR}"
mkdir -p \
  "${GEOVIEW_EXTERNAL_STATIC_ROOT}/upload/res" \
  "${GEOVIEW_INTERNAL_STATIC_ROOT}/upload/res" \
  "$(dirname "${SQLITE_DATABASE_PATH}")"
echo "[entrypoint] asset external static root=${GEOVIEW_EXTERNAL_STATIC_ROOT}"
echo "[entrypoint] asset internal static root=${GEOVIEW_INTERNAL_STATIC_ROOT}"
echo "[entrypoint] asset upload dest=${UPLOADED_PHOTOS_DEST}"
echo "[entrypoint] asset read order=${GEOVIEW_ASSET_READ_ORDER}"
echo "[entrypoint] require binary asset diagnostics=${GEOVIEW_REQUIRE_BINARY_ASSET_DIAGNOSTICS}"
if ! touch "${GEOVIEW_EXTERNAL_STATIC_ROOT}/.geoview-write-test" 2>/dev/null; then
  echo "[entrypoint] WARNING: external static root is not writable: ${GEOVIEW_EXTERNAL_STATIC_ROOT}" >&2
else
  rm -f "${GEOVIEW_EXTERNAL_STATIC_ROOT}/.geoview-write-test" 2>/dev/null || true
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
  echo "[entrypoint] Detected ${GPU_COUNT} GPU(s)."
fi

if [ "${BACKEND_ENABLED}" = "true" ]; then
  python /app/sync_model_assets.py --quiet
fi

if [ "${BACKEND_ENABLED}" = "true" ] && { [ "${DATABASE_BACKEND}" = "sqlite" ] || [ "${FLASK_CONFIG}" = "embedded" ]; }; then
  export FLASK_CONFIG=embedded
  echo "[entrypoint] Using embedded SQLite database at ${SQLITE_DATABASE_PATH}; skipping MySQL wait."
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
  python app.py &
  BACKEND_PID=$!

  if [ "${GEOVIEW_STARTUP_DIAGNOSTICS}" = "true" ]; then
    echo "[entrypoint] Running backend startup asset diagnostics..."
    if ! python /usr/local/bin/backend_startup_diagnostics.py; then
      echo "[entrypoint] Backend startup diagnostics failed." >&2
      kill -TERM "${BACKEND_PID}" 2>/dev/null || true
      wait "${BACKEND_PID}" 2>/dev/null || true
      exit 1
    fi
  else
    echo "[entrypoint] Backend startup diagnostics are disabled."
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
