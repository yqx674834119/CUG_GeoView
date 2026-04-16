# GeoView 前端 Helm 部署说明

本说明仅适用于 GeoView 前端单独交付，部署目标为服务运维平台 `172.20.20.241`。

## 1. 交付物说明

本地执行前端交付打包后，会得到两个文件：

```bash
deploy/frontend/helm/dist/geoview-frontend-0.1.0.tgz
deploy/frontend/helm/dist/GeoView_Frontend_Helm_Thin_YYYYMMDD.tar.gz
```

说明：

- `geoview-frontend-0.1.0.tgz`：最终上传到服务运维平台的 Helm 包
- `GeoView_Frontend_Helm_Thin_YYYYMMDD.tar.gz`：交给内网部署同事的前端交付包，里面包含 Helm 包、前端镜像 tar、示例 values、镜像清单

## 2. 本地生成前端 Helm 交付包

如果本地已经生成前端离线镜像包，可直接执行：

```bash
./build_frontend_helm_delivery.sh
```

如果脚本提示缺少本地前端镜像，请先生成前端离线包：

```bash
GEOVIEW_FRONTEND_BUILD_MODE=local ./export_frontend_offline.sh
./build_frontend_helm_delivery.sh
```

## 3. 内网服务器准备镜像

将 `GeoView_Frontend_Helm_Thin_YYYYMMDD.tar.gz` 上传到以下规范路径之一：

- `172.20.20.184:/var/lib/kubelet/<你的专属目录>`
- `172.20.20.107:/nfs/data/<你的专属目录>`

严禁放在根目录或其他路径。

服务器上解压：

```bash
cd /var/lib/kubelet/<你的专属目录>
tar -xzf GeoView_Frontend_Helm_Thin_YYYYMMDD.tar.gz
cd GeoView_Frontend_Helm_Thin
```

登录 Harbor：

- 地址：`172.20.20.243:8443`
- 账号：`admin`
- 密码：`Hc@Cloud01`

先在 Harbor 创建自己的项目，例如 `tenant-1-geoview`。

然后使用 `nerdctl` 导入并推送前端镜像：

```bash
nerdctl load -i offline_images/geoview_frontend.tar
nerdctl login 172.20.20.243:8443 -u admin -p 'Hc@Cloud01'
nerdctl tag geoview-frontend:latest 172.20.20.243:8443/<你的项目名>/geoview-frontend:20260416
nerdctl push 172.20.20.243:8443/<你的项目名>/geoview-frontend:20260416
```

注意：

- 必须带版本号，例如 `:20260416`
- 不要推送无版本号镜像

## 4. 服务运维平台部署前端应用

前端属于应用部署流程，只使用服务运维平台：

- 地址：`172.20.20.241`
- 账号：`admin`
- 密码：`xieyun@2026`

操作步骤：

1. 进入“项目中心”，创建命名空间并分配资源
2. 进入“容器中心 -> 应用中心 -> 创建应用”
3. 上传 Helm 包：`geoview-frontend-0.1.0.tgz`
4. 修改 `values.yaml`
5. 选择刚创建的命名空间并完成部署

## 5. values.yaml 该怎么改

上传 Helm 包后，至少修改以下内容：

```yaml
frontend:
  image:
    repository: 172.20.20.243:8443/<你的项目名>/geoview-frontend
    tag: "20260416"
```

如果后端地址固定，推荐直接写完整后端地址：

```yaml
frontend:
  runtimeConfig:
    backendUrl: "http://<后端IP>:5008"
    backendProtocol: http
    backendHost: ""
    backendPort: "5008"
    minerEnabled: false
    minerUrl: ""
    baiduMapAccessKey: ""
```

资源建议按前端最小需求配置：

```yaml
frontend:
  resources:
    requests:
      cpu: "100m"
      memory: "128Mi"
    limits:
      cpu: "1"
      memory: "512Mi"
```

服务端口默认如下：

```yaml
frontend:
  service:
    type: ClusterIP
    port: 3000
    targetPort: 80
```

## 6. 存储说明

前端单独部署不需要模型、不需要 PVC，一般不需要配置 `csi-sc`。

如果你后续自行扩展了 PVC，再按平台规范优先使用 `csi-sc`。

## 7. 最小交付清单

如果只交前端 Helm 部署，最小只需要这一个交付包：

```bash
GeoView_Frontend_Helm_Thin_YYYYMMDD.tar.gz
```

它里面已经包含：

- `geoview-frontend-0.1.0.tgz`
- `offline_images/geoview_frontend.tar`
- `values-harbor-example.yaml`
- `image-manifest.txt`
- 本说明文档
