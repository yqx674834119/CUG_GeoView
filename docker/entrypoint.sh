#!/usr/bin/env bash
set -euo pipefail

CONFIG_PATH="${CONFIG_PATH:-/app/config.yaml}"

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

print(f"BACKEND_HOST={backend_host}")
print(f"BACKEND_PORT={backend_port}")
print(f"FRONTEND_HOST={frontend_host}")
print(f"FRONTEND_PORT={frontend_port}")
print(f"BACKEND_CLIENT_HOST={client_host}")
PY
)

eval "${CONFIG_EXPORTS}"

cat > /app/frontend/.env <<EOF
VUE_APP_BACKEND_PORT = ${BACKEND_PORT}
VUE_APP_BACKEND_IP = ${BACKEND_CLIENT_HOST}
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
  export CUDA_VISIBLE_DEVICES=""
  export FLAGS_selected_gpus=""
  echo "[entrypoint] No GPU detected, forcing Paddle to use CPU." >&2
else
  echo "[entrypoint] Detected ${GPU_COUNT} GPU(s)."
fi

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
npm install --no-audit --prefer-offline
npm run serve -- --host "${FRONTEND_HOST}" --port "${FRONTEND_PORT}" &
FRONTEND_PID=$!

cd /app

terminate() {
  trap - SIGTERM SIGINT
  kill -TERM "${BACKEND_PID}" "${FRONTEND_PID}" 2>/dev/null || true
  wait "${BACKEND_PID}" "${FRONTEND_PID}" 2>/dev/null || true
}

trap terminate SIGTERM SIGINT

wait -n "${BACKEND_PID}" "${FRONTEND_PID}"
terminate
