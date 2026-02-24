FROM nvidia/cuda:11.7.1-cudnn8-runtime-ubuntu20.04

ARG USER_HOME=/root
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Shanghai \
    MAMBA_DOCKERFILE_ACTIVATE=1

# 替换 Ubuntu 源 + 删除自带的 NVIDIA CUDA 源
RUN sed -i 's|archive.ubuntu.com|mirrors.aliyun.com|g' /etc/apt/sources.list \
    && sed -i 's|security.ubuntu.com|mirrors.aliyun.com|g' /etc/apt/sources.list \
    && rm -f /etc/apt/sources.list.d/cuda.list /etc/apt/sources.list.d/nvidia-ml.list || true

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    curl \
    git \
    build-essential \
    wget \
    bzip2 \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Miniconda
RUN wget -O /tmp/miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    && bash /tmp/miniconda.sh -b -p /opt/conda \
    && rm /tmp/miniconda.sh

ENV PATH=/opt/conda/bin:${PATH}

# Conda config
RUN echo "channels:" > /opt/conda/.condarc && \
    echo "  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/Paddle" >> /opt/conda/.condarc && \
    echo "  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge" >> /opt/conda/.condarc && \
    echo "  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main" >> /opt/conda/.condarc && \
    echo "  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/r" >> /opt/conda/.condarc && \
    echo "show_channel_urls: true" >> /opt/conda/.condarc && \
    echo "channel_priority: strict" >> /opt/conda/.condarc && \
    conda update -n base -y conda && \
    conda clean -afy

# Create conda env
RUN conda create -y -n PaddleRS37 \
    python=3.7 \
    paddlepaddle-gpu=2.4.2 \
    cudatoolkit=11.7 \
    cudnn=8.4 \
    gdal && \
    conda clean -afy

# Create HuggingFace/PyTorch conda env (Python 3.10)
# This environment is used for HuggingFace transformers models (e.g., Swin2SR)
RUN conda create -y -n HFPyTorch310 python=3.10 && \
    conda clean -afy

# Install PyTorch 2.1+ with CUDA 11.8 support in HFPyTorch310
# Using cu118 for better compatibility with transformers
RUN conda run -n HFPyTorch310 pip install \
    torch==2.1.2 torchvision==0.16.2 --index-url https://download.pytorch.org/whl/cu118 && \
    conda run -n HFPyTorch310 pip install \
    numpy==1.26.4 pillow>=9.0.0 && \
    conda run -n HFPyTorch310 pip install \
    transformers==4.36.2 huggingface_hub \
    timm scipy "numpy<2" ultralytics && \
    conda run -n HFPyTorch310 pip cache purge

# Set HuggingFace mirror for China (optional, helps with network issues)
ENV HF_ENDPOINT=https://hf-mirror.com

# Create MMSegmentation conda env (Python 3.10)
# This environment is used for MMSegmentation models (e.g., CUGRS DinoV3+Swin)
RUN conda create -y -n MMSeg310 python=3.10 gdal && \
    conda clean -afy

# Install PyTorch 2.4 with CUDA 11.8 support in MMSeg310
RUN conda run -n MMSeg310 pip install \
    torch==2.4.0 torchvision==0.19.0 --index-url https://download.pytorch.org/whl/cu118

# Install OpenMMLab dependencies in MMSeg310
RUN conda run -n MMSeg310 pip install \
    openmim==0.3.9 && \
    conda run -n MMSeg310 mim install mmengine==0.10.4 && \
    conda run -n MMSeg310 mim install "mmcv==2.2.0"

# Install MMSegmentation 1.2.2 and patch version check for MMCV 2.2.0 compatibility
RUN conda run -n MMSeg310 pip install \
    mmsegmentation==1.2.2 \
    transformers==4.36.2 \
    huggingface_hub \
    numpy==1.26.4 \
    "opencv-python-headless<4.11" \
    pillow>=9.0.0 \
    ftfy \
    regex \
    "scipy<1.14" && \
    # Patch mmseg to accept mmcv 2.2.0 (change < 2.2.0 to <= 2.2.0)
    conda run -n MMSeg310 sed -i "s/MMCV_MAX = '2.2.0'/MMCV_MAX = '2.3.0'/" /opt/conda/envs/MMSeg310/lib/python3.10/site-packages/mmseg/__init__.py && \
    # Install MMRotate for Oriented Object Detection (DOTA, FAIR1M)
    conda run -n MMSeg310 mim install "mmrotate==1.0.0rc1" && \
    conda run -n MMSeg310 pip cache purge

# Install Kornia and dependencies for Registration/Tracking in HFPyTorch310
RUN conda run -n HFPyTorch310 pip install \
    kornia==0.7.1 \
    kornia_moons \
    opencv-python-headless \
    matplotlib


# Install Node.js 18 (system default, used by GeoView frontend)
RUN set -eux; \
    ARCH="linux-x64"; \
    NODE_VERSION="v18.20.3"; \
    curl -fsSL https://mirrors.tuna.tsinghua.edu.cn/nodejs-release/${NODE_VERSION}/node-${NODE_VERSION}-${ARCH}.tar.xz -o node.tar.xz; \
    tar -xJf node.tar.xz -C /usr/local --strip-components=1; \
    rm node.tar.xz; \
    ln -sf /usr/local/bin/node /usr/bin/node; \
    ln -sf /usr/local/bin/npm /usr/bin/npm; \
    ln -sf /usr/local/bin/npx /usr/bin/npx



# ----------- APP CODE START -----------
WORKDIR /app

# Copy backend
# Copy backend requirements first for caching
COPY backend/requirements.txt /app/backend/requirements.txt

# pip config (Restore missing config)
RUN mkdir -p /root/.pip && \
    echo "[global]" > /root/.pip/pip.conf && \
    echo "index-url = https://pypi.tuna.tsinghua.edu.cn/simple" >> /root/.pip/pip.conf && \
    echo "trusted-host = pypi.tuna.tsinghua.edu.cn" >> /root/.pip/pip.conf

# Install backend deps
RUN conda run -n PaddleRS37 python -m pip install --upgrade pip && \
    conda run -n PaddleRS37 pip install "setuptools<=65.5.0"

RUN conda run -n PaddleRS37 pip install -r backend/requirements.txt

# Copy backend source code (frequently changing)
COPY backend /app/backend

# Copy PaddleRS requirements first
COPY PaddleRS/requirements.txt /app/PaddleRS/requirements.txt

# Install PaddleRS deps
RUN conda run -n PaddleRS37 pip install -r PaddleRS/requirements.txt

# Copy PaddleRS source
COPY PaddleRS /app/PaddleRS

# Install PaddleRS package
RUN conda run -n PaddleRS37 pip install -e PaddleRS
RUN conda run -n PaddleRS37 pip install cryptography gunicorn
RUN conda run -n PaddleRS37 pip check

# ----------- FRONTEND -----------
WORKDIR /app/frontend
COPY frontend /app/frontend
RUN npm install --no-audit --prefer-offline
RUN npm run build || true   # 不失败（开发模式可 serve）

# ----------- MINER (矿山监测系统) -----------
# Miner uses Vite 7.x which requires Node.js >=20.19.0
# Install Node.js 20 to /opt/node20 (separate from system Node.js 18)
RUN set -eux; \
    ARCH="linux-x64"; \
    NODE_VERSION="v20.19.0"; \
    mkdir -p /opt/node20; \
    (curl -fsSL --retry 3 https://nodejs.org/dist/${NODE_VERSION}/node-${NODE_VERSION}-${ARCH}.tar.xz -o /tmp/node20.tar.xz || \
    curl -fsSL --retry 3 https://mirrors.tuna.tsinghua.edu.cn/nodejs-release/${NODE_VERSION}/node-${NODE_VERSION}-${ARCH}.tar.xz -o /tmp/node20.tar.xz); \
    tar -xJf /tmp/node20.tar.xz -C /opt/node20 --strip-components=1; \
    rm /tmp/node20.tar.xz

WORKDIR /app/miner
COPY miner/package.json miner/package-lock.json /app/miner/
RUN PATH=/opt/node20/bin:$PATH npm install --no-audit --prefer-offline
COPY miner /app/miner

# ----------- ENTRYPOINT -----------
WORKDIR /app
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENV PATH=/opt/conda/envs/PaddleRS37/bin:/opt/conda/bin:${PATH} \
    CONDA_DEFAULT_ENV=PaddleRS37 \
    PYTHONUNBUFFERED=1 \
    LD_LIBRARY_PATH=/opt/conda/envs/PaddleRS37/lib:${LD_LIBRARY_PATH}

EXPOSE 5008 3000 4000 8000

CMD ["entrypoint.sh"]
