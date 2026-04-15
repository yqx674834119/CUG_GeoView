# GeoView 独立前端 Docker 部署说明

本方案不会改动现有前后端合并镜像，只额外提供一个独立前端镜像。

## 1. 构建独立前端压缩包

在项目根目录执行：

```bash
chmod +x export_frontend_offline.sh deploy_frontend_offline.sh
./export_frontend_offline.sh
```

说明：

- 脚本会优先尝试使用 `Dockerfile.frontend` 构建标准 `nginx` 版本镜像
- 如果当前机器无法拉取公共基础镜像，脚本会自动回退到“本地前端产物 + 本机 `busybox` + scratch 镜像”的纯本地构建方案
- 如果希望直接跳过公共镜像拉取，可以执行 `GEOVIEW_FRONTEND_BUILD_MODE=local ./export_frontend_offline.sh`

输出文件位置：

```bash
deploy/frontend/dist/GeoView_Frontend_Offline_YYYYMMDD.tar.gz
```

## 2. 部署独立前端容器

解压压缩包后，进入解压目录：

```bash
tar -xzf GeoView_Frontend_Offline_YYYYMMDD.tar.gz
cd GeoView_Frontend_Offline
```

如需固定后端地址，先准备配置文件：

```bash
cp frontend.env.example frontend.env
```

推荐直接设置完整后端地址：

```bash
GEOVIEW_BACKEND_URL=http://<后端IP>:5008
```

然后执行：

```bash
chmod +x deploy_frontend_offline.sh
./deploy_frontend_offline.sh
```

## 3. 后端地址配置规则

- 优先使用 `GEOVIEW_BACKEND_URL`
- 如果 `GEOVIEW_BACKEND_URL` 为空，则使用 `GEOVIEW_BACKEND_HOST + GEOVIEW_BACKEND_PORT`
- 如果 `GEOVIEW_BACKEND_HOST` 也为空，则前端自动使用浏览器当前访问主机名，再拼接 `GEOVIEW_BACKEND_PORT`

这意味着：

- 前后端部署在同一台服务器时，通常只需要设置 `GEOVIEW_BACKEND_PORT=5008`
- 后端部署后拿到新的 IP 时，只需要修改 `frontend.env` 里的 `GEOVIEW_BACKEND_URL` 并重新执行 `./deploy_frontend_offline.sh`

## 4. 直接在线构建与运行

如果不需要离线压缩包，也可以直接在项目根目录执行：

```bash
docker build -f Dockerfile.frontend -t geoview-frontend:latest .
docker compose -f docker-compose.frontend.yml up -d
```
