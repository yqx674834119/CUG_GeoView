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
# 设置 Conda 环境变量
ENV PATH=/opt/conda/bin:${PATH}

# 写入 .condarc，彻底覆盖默认 channels（不再隐式引用 repo.anaconda.com）
RUN echo "channels:" > /opt/conda/.condarc && \
    echo "  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/Paddle" >> /opt/conda/.condarc && \
    echo "  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge" >> /opt/conda/.condarc && \
    echo "  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main" >> /opt/conda/.condarc && \
    echo "  - https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/r" >> /opt/conda/.condarc && \
    echo "show_channel_urls: true" >> /opt/conda/.condarc && \
    echo "channel_priority: strict" >> /opt/conda/.condarc && \
    \
    conda update -n base -y conda && \
    conda clean -afy
# 创建 Conda 环境并安装依赖（自动走清华源）
RUN conda create -y -n PaddleRS37 \
        python=3.7 \
        paddlepaddle-gpu=2.4.2 \
        cudatoolkit=11.7 \
        cudnn=8.4 \
        gdal && \
    conda clean -afy

RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g npm@9 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend ./backend
COPY frontend ./frontend
COPY PaddleRS ./PaddleRS
COPY config.yaml .

# 1️⃣ 升级 pip / setuptools
RUN conda run -n PaddleRS37 python -m pip install --upgrade pip && \
    conda run -n PaddleRS37 pip install "setuptools<=65.5.0"

# 2️⃣ 安装后端依赖
RUN conda run -n PaddleRS37 pip install -r backend/requirements.txt

# 3️⃣ 安装 PaddleRS 自身依赖（提前准备）
RUN conda run -n PaddleRS37 pip install -r PaddleRS/requirements.txt

# 4️⃣ 解决 setup.py 导入问题（提前安装 colorama）
# RUN conda run -n PaddleRS37 pip install colorama

# 5️⃣ 安装 PaddleRS 源码包
RUN conda run -n PaddleRS37 pip install -e PaddleRS

# 6️⃣ 安装运行时依赖
RUN conda run -n PaddleRS37 pip install cryptography gunicorn

# 7️⃣ 检查环境一致性
RUN conda run -n PaddleRS37 pip check


WORKDIR /app/frontend

RUN npm ci --no-audit --prefer-offline \
    && npm cache clean --force

WORKDIR /app

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENV PATH=/opt/conda/envs/PaddleRS37/bin:/opt/conda/bin:${PATH} \
    CONDA_DEFAULT_ENV=PaddleRS37 \
    PYTHONUNBUFFERED=1 \
    LD_LIBRARY_PATH=/opt/conda/envs/PaddleRS37/lib:${LD_LIBRARY_PATH} \
    PIP_DISABLE_PIP_VERSION_CHECK=1

EXPOSE 5008 3000

CMD ["entrypoint.sh"]
