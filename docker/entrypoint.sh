#!/usr/bin/env bash
set -euo pipefail

CONFIG_PATH="${CONFIG_PATH:-/app/config.yaml}"
REQUIRE_GPU="${REQUIRE_GPU:-true}"
RUNTIME_LOG_DIR="${RUNTIME_LOG_DIR:-/tmp/geoview-logs}"

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
with open(config_path, "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

backend_host = cfg["host"]["backend"]
backend_port = cfg["port"]["backend"]
frontend_host = cfg["host"]["frontend"]
frontend_port = cfg["port"]["frontend"]

client_host = "127.0.0.1" if backend_host == "0.0.0.0" else backend_host

# Miner config
miner_cfg = cfg.get("miner", {})
miner_enabled = "true" if miner_cfg.get("enabled", False) else "false"
miner_frontend_port = miner_cfg.get("frontend_port", 4000)
miner_backend_port = miner_cfg.get("backend_port", 8000)

print(f"BACKEND_HOST={backend_host}")
print(f"BACKEND_PORT={backend_port}")
print(f"FRONTEND_HOST={frontend_host}")
print(f"FRONTEND_PORT={frontend_port}")
print(f"BACKEND_CLIENT_HOST={client_host}")
print(f"MINER_ENABLED={miner_enabled}")
print(f"MINER_FRONTEND_PORT={miner_frontend_port}")
print(f"MINER_BACKEND_PORT={miner_backend_port}")
PY
)

eval "${CONFIG_EXPORTS}"

mkdir -p "${RUNTIME_LOG_DIR}"

# Write GeoView frontend .env (include Miner toggle)
cat > /app/frontend/.env <<EOF
VUE_APP_BACKEND_PORT = ${BACKEND_PORT}
VUE_APP_BACKEND_IP = ${BACKEND_CLIENT_HOST}
VUE_APP_MINER_ENABLED = ${MINER_ENABLED}
VUE_APP_MINER_URL = http://localhost:${MINER_FRONTEND_PORT}
EOF

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

if [ "${GPU_COUNT:-0}" = "0" ]; then
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

python /app/sync_model_assets.py --quiet || true

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

cd /app/backend
python app.py &
BACKEND_PID=$!

cd /app/frontend
npm install --no-audit --prefer-offline >"${RUNTIME_LOG_DIR}/frontend-npm.log" 2>&1
npm run serve -- --host "${FRONTEND_HOST}" --port "${FRONTEND_PORT}" >"${RUNTIME_LOG_DIR}/frontend.log" 2>&1 &
FRONTEND_PID=$!

# --- Miner (矿山监测系统) conditional startup ---
MINER_BACKEND_PID=""
MINER_FRONTEND_PID=""

if [ "${MINER_ENABLED}" = "true" ]; then
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
  PATH=/opt/node20/bin:$PATH npm install --no-audit --prefer-offline >"${RUNTIME_LOG_DIR}/miner-npm.log" 2>&1
  PATH=/opt/node20/bin:$PATH npx vite --host 0.0.0.0 --port "${MINER_FRONTEND_PORT}" >"${RUNTIME_LOG_DIR}/miner-frontend.log" 2>&1 &
  MINER_FRONTEND_PID=$!

  echo "[entrypoint] Miner backend PID=${MINER_BACKEND_PID}, frontend PID=${MINER_FRONTEND_PID}"
else
  echo "[entrypoint] Miner is DISABLED. Skipping Miner services."
fi

cd /app

terminate() {
  trap - SIGTERM SIGINT
  kill -TERM "${BACKEND_PID}" "${FRONTEND_PID}" 2>/dev/null || true
  if [ -n "${MINER_BACKEND_PID}" ]; then
    kill -TERM "${MINER_BACKEND_PID}" 2>/dev/null || true
  fi
  if [ -n "${MINER_FRONTEND_PID}" ]; then
    kill -TERM "${MINER_FRONTEND_PID}" 2>/dev/null || true
  fi
  wait "${BACKEND_PID}" "${FRONTEND_PID}" 2>/dev/null || true
  if [ -n "${MINER_BACKEND_PID}" ]; then
    wait "${MINER_BACKEND_PID}" 2>/dev/null || true
  fi
  if [ -n "${MINER_FRONTEND_PID}" ]; then
    wait "${MINER_FRONTEND_PID}" 2>/dev/null || true
  fi
}

trap terminate SIGTERM SIGINT

wait -n "${BACKEND_PID}" "${FRONTEND_PID}"
terminate
