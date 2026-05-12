ARG BASE_IMAGE=geoview-base:latest
FROM ${BASE_IMAGE}

# ----------- APP CODE START -----------
RUN sed -i 's|mirrors.aliyun.com|archive.ubuntu.com|g' /etc/apt/sources.list && \
    sed -i 's|archive.ubuntu.com/ubuntu focal-security|security.ubuntu.com/ubuntu focal-security|g' /etc/apt/sources.list && \
    apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY sync_model_assets.py /app/sync_model_assets.py
COPY config.yaml /app/config.yaml
COPY backend /app/backend
COPY docker/patches/mmseg_cugrs_ms_deform_attn.py /app/backend/model/semantic_segmentation/mmseg_cugrs/support/dinov3/dinov3/eval/segmentation/models/utils/ms_deform_attn.py
COPY PaddleRS /app/PaddleRS

RUN conda run -n PaddleRS37 pip install -e /app/PaddleRS && \
    conda run -n PaddleRS37 pip install -r /app/backend/requirements.txt && \
    conda run -n PaddleRS37 pip install cryptography && \
    conda run -n PaddleRS37 pip check

# ----------- FRONTEND -----------
WORKDIR /app/frontend
COPY frontend/package*.json /app/frontend/
RUN npm ci --no-audit
COPY frontend /app/frontend
RUN npm run build

# ----------- MINER (矿山监测系统) -----------
WORKDIR /app/miner
COPY miner /app/miner

# ----------- ENTRYPOINT -----------
WORKDIR /app
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh && \
    chmod +x /app/sync_model_assets.py

ENV GEOVIEW_EXTERNAL_STATIC_ROOT=/data/geoview/static \
    GEOVIEW_INTERNAL_STATIC_ROOT=/app/backend/static \
    UPLOADED_PHOTOS_DEST=/data/geoview/static/upload \
    GEOVIEW_ASSET_READ_ORDER=external,internal \
    GEOVIEW_ASSET_DEBUG=0 \
    GEOVIEW_DEBUG_LOG=false \
    GEOVIEW_FRONTEND_ENABLED=true \
    FLASK_CONFIG=

EXPOSE 5008 3000

CMD ["entrypoint.sh"]
