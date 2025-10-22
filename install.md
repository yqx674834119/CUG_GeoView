## paddlepaddle 和 paddleRS 安装 
```bash
conda create -n PaddleRS37 python==3.7
# conda remove -n PaddleRS37 --all
# 安装 paddlepaddle
conda install paddlepaddle-gpu==2.4.2 cudatoolkit=11.7 -c https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/Paddle/ -c conda-forge
# 安装 paddlers
git clone -b release/1.0 https://github.com/PaddlePaddle/PaddleRS.git

cd PaddleRS
pip install "setuptools<=65.5.0"
pip install -r requirements.txt
pip install -e .
conda install gdal
pip install cryptography
```

## 基础配置
MySQL >= 5.7
```bash
# 更新包索引
sudo apt update
# 安装 MySQL 服务端和客户端
sudo apt install mysql-server mysql-client -y
# 查看版本
mysql --version

sudo service mysql start

sudo mysql
CREATE USER 'paddle_rs'@'localhost' IDENTIFIED BY 'Yqx090315.';
GRANT ALL PRIVILEGES ON paddle_rs.* TO 'paddle_rs'@'localhost';
FLUSH PRIVILEGES;
```

Node.js >= 16.0
```bash
# 安装依赖
sudo apt update
sudo apt install -y curl gnupg

# 下载并安装 NodeSource 脚本（Node.js 18）
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -

# 安装 Node.js
sudo apt install -y nodejs

node -v
npm -v

```

## 项目配置
接着，运行如下命令以安装Web后端的所有依赖：
```bash
pip install -r backend/requirements.txt
```

## 启动 Web 后端
在项目根目录执行如下指令以启动 Web 后端：
```bash
conda activate PaddleRS37
cd backend
python app.py
```
启动后，数据库将自动得到初始化。

## Docker 一键部署（推荐）
为了解决本地 Conda 环境较难复现的问题，项目提供了基于 Docker 的前后端整合镜像以及配套的 MySQL 服务。

### 0. 前置准备
1. 在目标机器上安装 [Docker Engine](https://docs.docker.com/engine/install/) 与 [Docker Compose 插件](https://docs.docker.com/compose/install/)。安装完成后，确保以下命令能够执行：
   ```bash
   docker --version
   docker compose version
   ```
2. 克隆或下载本项目的代码，并保持目录结构完整（至少包含 `Dockerfile`、`docker-compose.yml`、`config.yaml`、`backend/`、`frontend/`）。
3. 若需要修改服务端口或数据库密码，可先编辑仓库根目录的 `config.yaml` 和 `docker-compose.yml`。

### 1. 构建镜像
在项目根目录执行：
```bash
docker compose build
```

> 如需使用 GPU，请确保宿主机已安装正确版本的 NVIDIA 驱动，并按照 [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) 的指引完成配置。
> 部署时默认会暴露全部 GPU（`NVIDIA_VISIBLE_DEVICES=all`），如需限定可在执行 `docker compose up -d` 前手动设置 `export NVIDIA_VISIBLE_DEVICES=<GPU 索引列表>`。

### 2. 启动所有服务
```bash
docker compose up -d
```

该命令会启动三个端口：
- `3000`：Vue 前端（默认地址 http://localhost:3000）
- `5008`：Flask 后端 API（默认地址 http://localhost:5008）
- `3306`：MySQL 数据库

执行完成后，前端、后端与 MySQL 会自动在后台同时运行，无需手动进入容器启动任何程序。容器首次启动时会自动安装 PaddleRS、初始化数据库结构，并根据 `config.yaml` 写入前端环境变量。
如需查看运行状态，可访问：
- http://localhost:3000 验证前端页面是否加载成功；
- http://localhost:5008/api/health（若实现该路由）或其他后端接口确认服务是否可用；
- 使用 `docker compose ps` 查看容器状态。

### 3. 查看日志与停止
```bash
docker compose logs -f
docker compose down
```

如需修改端口或数据库凭据，可直接调整 `config.yaml` 或 `docker-compose.yml` 中对应字段，再重新执行 `docker compose up -d`。
### 直接进入docker容器

```bash
docker compose exec app bash
```

### 4. 分享镜像给他人
构建完成后有两种推荐方式分享：

1. 上传到镜像仓库  
   ```bash
   docker tag geoview/app:latest <你的仓库地址>/geoview:latest
   docker push <你的仓库地址>/geoview:latest
   ```
   接收方只需执行 `docker pull <你的仓库地址>/geoview:latest`，再进入项目目录运行 `docker compose up -d` 即可使用。

2. 导出为离线包  
   ```bash
   docker save geoview/app:latest -o geoview.tar
   ```
   将 `geoview.tar` 与项目代码（包含 `docker-compose.yml`、`config.yaml` 等文件）一起分享，接收方执行：
   ```bash
   docker load -i geoview.tar
   docker compose up -d
   ```
