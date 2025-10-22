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

RUN wget -O /tmp/miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    && bash /tmp/miniconda.sh -b -p /opt/conda \
    && rm /tmp/miniconda.sh

ENV PATH=/opt/conda/bin:${PATH}

RUN conda config --system --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/Paddle/ \
    && conda config --system --add channels conda-forge \
    && conda config --system --set channel_priority strict \
    && conda update -n base -y conda \
    && conda clean -afy

RUN conda create -y -n PaddleRS37 \
        python=3.7 \
        paddlepaddle-gpu=2.4.2 \
        cudatoolkit=11.7 \
        gdal \
    && conda clean -afy

RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g npm@9 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend ./backend
COPY frontend ./frontend
COPY PaddleRS ./PaddleRS
COPY config.yaml .

RUN conda run -n PaddleRS37 python -m pip install --upgrade pip \
    && conda run -n PaddleRS37 pip install "setuptools<=65.5.0" \
    && conda run -n PaddleRS37 pip install -r backend/requirements.txt \
    && conda run -n PaddleRS37 pip install -e PaddleRS \
    && conda run -n PaddleRS37 pip install cryptography gunicorn \
    && conda run -n PaddleRS37 pip check

WORKDIR /app/frontend

RUN npm ci --no-audit --prefer-offline \
    && npm cache clean --force

WORKDIR /app

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENV PATH=/opt/conda/envs/PaddleRS37/bin:/opt/conda/bin:${PATH} \
    CONDA_DEFAULT_ENV=PaddleRS37 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

EXPOSE 5008 3000

CMD ["entrypoint.sh"]
