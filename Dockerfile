FROM nvidia/cuda:11.7.1-cudnn8-runtime-ubuntu20.04

ARG USER_HOME=/root
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Shanghai \
    MAMBA_DOCKERFILE_ACTIVATE=1

RUN sed -i 's|archive.ubuntu.com|mirrors.aliyun.com|g' /etc/apt/sources.list \
    && sed -i 's|security.ubuntu.com|mirrors.aliyun.com|g' /etc/apt/sources.list

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

# Install Node.js 18
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g npm@9 \
    && rm -rf /var/lib/apt/lists/*

# ----------- APP CODE START -----------
WORKDIR /app

# Copy backend
COPY backend /app/backend

# Copy PaddleRS code
COPY PaddleRS /app/PaddleRS

# pip config
RUN mkdir -p /root/.pip && \
    echo "[global]" > /root/.pip/pip.conf && \
    echo "index-url = https://pypi.tuna.tsinghua.edu.cn/simple" >> /root/.pip/pip.conf && \
    echo "trusted-host = pypi.tuna.tsinghua.edu.cn" >> /root/.pip/pip.conf

# Install backend deps
RUN conda run -n PaddleRS37 python -m pip install --upgrade pip && \
    conda run -n PaddleRS37 pip install "setuptools<=65.5.0"

RUN conda run -n PaddleRS37 pip install -r backend/requirements.txt

# Install PaddleRS
RUN conda run -n PaddleRS37 pip install -r PaddleRS/requirements.txt && \
    conda run -n PaddleRS37 pip install -e PaddleRS

RUN conda run -n PaddleRS37 pip install cryptography gunicorn
RUN conda run -n PaddleRS37 pip check

# ----------- FRONTEND -----------
WORKDIR /app/frontend
COPY frontend /app/frontend
RUN npm install --no-audit --prefer-offline
RUN npm run build || true   # 不失败（开发模式可 serve）

# ----------- ENTRYPOINT -----------
WORKDIR /app
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENV PATH=/opt/conda/envs/PaddleRS37/bin:/opt/conda/bin:${PATH} \
    CONDA_DEFAULT_ENV=PaddleRS37 \
    PYTHONUNBUFFERED=1 \
    LD_LIBRARY_PATH=/opt/conda/envs/PaddleRS37/lib:${LD_LIBRARY_PATH}

EXPOSE 5008 3000

CMD ["entrypoint.sh"]
