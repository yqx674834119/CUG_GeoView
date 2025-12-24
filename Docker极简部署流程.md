## Docker 一键部署（推荐）
为了解决本地 Conda 环境较难复现的问题，项目提供了基于 Docker 的前后端整合镜像以及配套的 MySQL 服务。

### 1. 安装 NVIDIA Container Toolkit（可选）
Ubuntu 环境如果需要在 Docker 容器中使用 NVIDIA GPU，需安装 NVIDIA Container Toolkit。

#### 步骤 1：添加 USTC 镜像的 GPG key（国内可访问）
```
curl -fsSL https://mirrors.ustc.edu.cn/libnvidia-container/gpgkey \
  | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
```
#### 步骤 2：添加源（使用 USTC 镜像，不访问 github.io）
```
curl -s -L https://mirrors.ustc.edu.cn/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://nvidia.github.io#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://mirrors.ustc.edu.cn#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
```
#### 步骤 3：更新 & 安装
```
sudo apt update
sudo apt install nvidia-container-toolkit
```

### 2. Docker 启动
1. `git clone https://github.com/yqx674834119/CUG_GeoView.git` (如果网络不畅，使用Gitee镜像 `git clone https://gitee.com/sakura674834119/CUG_GeoView.git`)
2. `cd CUG_GeoView`
3. 下载模型并解压到 backend 目录  
   `https://hkustgz-my.sharepoint.com/:u:/g/personal/qyao951_connect_hkust-gz_edu_cn/IQBeAzzP_XEYTojzwRH1pr2aAYkevLWWiDuh6sTVNyQzeak?e=wr9Yvc`
4. 登录阿里云 
   `docker login --username=13997543646yqx crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com`
5. Password: `Yqx123123123`
6. 拉取镜像 `docker pull crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/cugrs:latest `
7. 启动服务 `docker compose up -d`

