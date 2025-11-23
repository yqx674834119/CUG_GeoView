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

### 4. 推送镜像到云端镜像仓库（推荐）
构建完成后，推荐将镜像推送到云端仓库（如 Docker Hub、阿里云、华为云等），方便团队成员直接拉取。

1. 选择并创建镜像仓库  
   - Docker Hub: 新建公开或私有仓库，例如 `yourname/cugrs`。  
   - 阿里云等企业仓库：按照各自控制台提示创建命名空间与仓库，记下完整仓库地址（例如 `registry.cn-hangzhou.aliyuncs.com/yourteam/cugrs`）。

2. 登录镜像仓库  
   ```bash
   # Docker Hub
   docker login
   # 其他仓库需指定 Registry 地址，例如阿里云：
   docker login --username=13997543646yqx crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com
   ```

3. 为本地镜像重新打 Tag  
   构建完成后默认镜像名为 `cugrs/app:latest`。根据创建的仓库地址重新打标签，例如：
   ```bash
   docker tag cugrs/app:latest yourname/cugrs:latest
   # 或针对阿里云仓库
   docker tag cugrs/app:latest crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/cugrs:latest
   ```

4. 推送镜像  
   ```bash
   docker push yourname/cugrs:latest
   # 或阿里云仓库地址
   docker push crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/cugrs:latest
   ```

5. 团队成员使用  
   接收方只需执行：
   ```bash
   docker pull crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/cugrs:latest  
   docker compose up -d
   ```
   如需覆盖更新，可在推送新版本前调整标签（例如 `:v1.0.1`），或使用 `docker compose pull` 自动拉取最新镜像。

### 5. 导出为离线包（备用方案）
当目标环境无法访问云端镜像仓库时，可通过离线包分发镜像与项目代码。完整流程如下：

#### 5.1 准备项目目录
确保当前仓库包含以下最小结构（可用 `tree -L 1` 查看）：
```
cugrs/
├── Dockerfile
├── docker-compose.yml
├── config.yaml
├── backend/
├── frontend/
├── docs/            # 说明文档，可选
└── install.md
```
如果有额外的模型文件或配置（如 `models/`、`.env`），也一并保留。

#### 5.2 导出 Docker 镜像
在项目根目录执行：
```bash
docker save cugrs/app:latest -o cugrs-image.tar
```
> 如果本地镜像标签不同，请将 `cugrs/app:latest` 替换为实际名称。

#### 5.3 打包项目代码
```bash
tar czf cugrs-project.tar.gz .
```


#### 5.4 汇总离线包
将导出的镜像 `cugrs-image.tar` 与项目压缩包 `cugrs-project.tar.gz`（或直接的项目文件夹）一起分享给接收方，可配合 MD5 等校验值确保传输完整。

---

### 6. 使用离线包（接收方操作）
1. 解压代码包  
   ```bash
   tar xzf cugrs-project.tar.gz
   cd cugrs  # 进入解压后的项目目录
   ```

2. 导入 Docker 镜像  
   ```bash
   docker load -i ../cugrs-image.tar   # 路径按实际位置调整
   ```
   使用 `docker images | grep cugrs` 确认镜像已导入。

3. 准备配置  
   - 根据需要修改 `config.yaml`、`docker-compose.yml`（例如端口、数据库密码）。  
   - 如果需要 GPU，确保宿主机配置了 NVIDIA 驱动及 Container Toolkit。

4. 启动服务  
   ```bash
   docker compose up -d
   ```

5. 验证运行状态  
   - 前端：http://localhost:3000  
   - 后端：http://localhost:5008  
   - 如果需要，执行 `docker compose ps`、`docker compose logs -f app` 查看状态与日志。

如需停机或更新，执行 `docker compose down`，并重复上述步骤加载新的镜像与代码。


1. `git clone https://github.com/yqx674834119/CUG_GeoView.git`
2. `cd CUG_GeoView`
3. 下载模型并解压到 backend 目录  `https://hkustgz-my.sharepoint.com/:u:/g/personal/qyao951_connect_hkust-gz_edu_cn/IQBeAzzP_XEYTojzwRH1pr2aAYkevLWWiDuh6sTVNyQzeak?e=wr9Yvc`
4. 登录阿里云 `docker login --username=13997543646yqx crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com`
5. Password: Yqx123123123
6. 拉取镜像 `docker pull crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/cugrs:latest `
7. docker compose up -d


### 8. 安装 NVIDIA Container Toolkit（可选）
如果需要在 Docker 容器中使用 NVIDIA GPU，需安装 NVIDIA Container Toolkit。以下是在 Ubuntu 22.04 上安装的步骤（其他系统请参考官方文档）：

步骤 1：添加 USTC 镜像的 GPG key（国内可访问）
curl -fsSL https://mirrors.ustc.edu.cn/libnvidia-container/gpgkey \
  | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

步骤 2：添加源（使用 USTC 镜像，不访问 github.io）
curl -s -L https://mirrors.ustc.edu.cn/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://nvidia.github.io#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://mirrors.ustc.edu.cn#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

步骤 3：更新 & 安装
sudo apt update
sudo apt install nvidia-container-toolkit
