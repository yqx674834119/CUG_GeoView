# GeoView 整项目双文件 Helm 交付说明

本流程适用于整项目 GeoView 的应用部署，目标平台为：

- Harbor：`172.20.20.243:8443`
- 服务运维平台：`172.20.20.241`

目标是只交付两个文件：

1. `geoview_images.tar`
2. `geoview-0.1.0.tgz`

## 1. 在中转机器上生成两个文件

进入项目根目录执行：

```bash
./export_offline.sh 3
```

执行成功后会生成：

```bash
deploy/helm/dist/geoview_images.tar
deploy/helm/dist/geoview-0.1.0.tgz
```

说明：

- `geoview_images.tar`：包含 GeoView 应用镜像和 MySQL 镜像
- `geoview-0.1.0.tgz`：上传到服务运维平台的 Helm 包

## 2. 这两个文件分别怎么用

### 文件 1：镜像包

将 `geoview_images.tar` 上传到以下任一规范路径：

- `172.20.20.184:/var/lib/kubelet/<你的专属目录>`
- `172.20.20.107:/nfs/data/<你的专属目录>`

然后在服务器上：

```bash
nerdctl load -i geoview_images.tar
```

登录 Harbor：

```bash
nerdctl login 172.20.20.243:8443 -u admin -p 'Hc@Cloud01'
```

推送镜像：

```bash
nerdctl tag crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/cugrs:latest 172.20.20.243:8443/<你的项目名>/geoview-app:20260416
nerdctl tag registry.openanolis.cn/openanolis/mysql:8.0.30-8.6 172.20.20.243:8443/<你的项目名>/mysql:8.0.30-8.6
nerdctl push 172.20.20.243:8443/<你的项目名>/geoview-app:20260416
nerdctl push 172.20.20.243:8443/<你的项目名>/mysql:8.0.30-8.6
```

### 文件 2：Helm 包

将 `geoview-0.1.0.tgz` 上传到服务运维平台：

- 地址：`172.20.20.241`
- 账号：`admin`
- 密码：`xieyun@2026`

路径：

1. `项目中心` -> 创建命名空间
2. `容器中心` -> `应用中心` -> `创建应用`
3. 上传 `geoview-0.1.0.tgz`

## 3. 平台 values.yaml 至少要改什么

最少改这几项：

```yaml
app:
  image:
    repository: 172.20.20.243:8443/<你的项目名>/geoview-app
    tag: "20260416"
  persistence:
    storageClass: csi-sc

mysql:
  image:
    repository: 172.20.20.243:8443/<你的项目名>/mysql
    tag: "8.0.30-8.6"
  persistence:
    storageClass: csi-sc
```

如果要启用 GPU，保持：

```yaml
app:
  gpu:
    enabled: true
    count: 1
```

## 4. 什么时候还需要 Full 包

如果你最终目标是应用 Helm 部署，通常不再需要：

```bash
GeoView_Offline_Full_YYYYMMDD.tar.gz
```

`Full 包` 仍然可以保留给旧的离线 Docker/全量项目交付流程使用。

但对于当前这套应用平台流程，优先使用：

1. `geoview_images.tar`
2. `geoview-0.1.0.tgz`
