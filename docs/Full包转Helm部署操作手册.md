# GeoView Full 包转 Helm 部署操作手册

这份文档是给内网 Helm 部署使用的。

你的起点不是源码，也不是 Thin 包，而是已经由中转同事生成好的：

```text
GeoView_Offline_Full_YYYYMMDD.tar.gz
```

你的目标是：

1. 把 Full 包带进内网允许目录
2. 用 Full 包里的离线镜像推到 Harbor
3. 生成或确认 Helm 交付物
4. 在服务运维平台 `172.20.20.241` 完成应用部署

## 1. 先记住这次真正要做的事情

你不是要再跑一次 `docker compose`。

你要做的是这 4 件事：

1. 把 Full 包上传到指定服务器目录
2. 解压 Full 包
3. 用 `deploy_helm_offline.sh` 把 Full 包里的镜像推到 Harbor
4. 把 Helm 包上传到服务运维平台

简单理解：

1. `Full 包` 负责把离线镜像和项目资产带进内网
2. `deploy_helm_offline.sh` 负责把离线镜像转成 Harbor 镜像，并生成推荐 values
3. 服务运维平台负责最终 Helm 应用部署

## 2. 你手里的 Full 包里应该有什么

解压后，项目目录里通常会包含：

1. `offline_images/geoview_images.tar`
2. `deploy/helm/geoview/`
3. `deploy_helm_offline.sh`
4. `backend/model/`
5. `offline_cache/`

重点是：

```text
offline_images/geoview_images.tar
```

这就是离线镜像合集。

## 3. 只能放到哪些服务器目录

按你们规范，只能放到这两个地方之一：

优先：

```text
172.20.20.184:/var/lib/kubelet/<你的专属目录>/
```

备用：

```text
172.20.20.107:/nfs/data/<你的专属目录>/
```

或者：

```text
172.20.20.107:/other/document/<你的专属目录>/
```

注意：

1. 严禁放到服务器根目录
2. 严禁放到其他路径
3. 如果文件很大，尽量直接在机房服务器侧上传，不要拆包

## 4. 第一步：把 Full 包上传到服务器

假设你的 Full 包叫：

```text
GeoView_Offline_Full_20260416.tar.gz
```

把它上传到例如：

```text
/var/lib/kubelet/yourname-geoview/
```

或者：

```text
/nfs/data/yourname-geoview/
```

或者：

```text
/other/document/yourname-geoview/
```

## 5. 第二步：解压 Full 包

进入上传目录后执行：

```bash
tar -xzf GeoView_Offline_Full_20260416.tar.gz
cd GeoView
```

然后先检查几个关键文件：

```bash
ls -lh offline_images/geoview_images.tar
ls deploy/helm/geoview
ls deploy_helm_offline.sh
```

正常情况下，你至少应该看到：

```text
offline_images/geoview_images.tar
deploy/helm/geoview/Chart.yaml
deploy_helm_offline.sh
```

## 6. 第三步：确认服务器环境

这条 Helm 交付流程要求当前服务器至少满足：

1. 有 `bash`
2. 有 `tar`
3. 有 `nerdctl`
4. 能访问 Harbor：`172.20.20.107:8443`
5. 能访问服务运维平台：`172.20.20.241`

你可以先执行：

```bash
which nerdctl
tar --version
pwd
```

注意：

1. 不需要安装新软件
2. 不允许改服务器系统配置
3. 如果没有 `nerdctl`，这条流程就不能在这台机器上正式执行

## 7. 第四步：先在 Harbor 创建项目

Harbor 地址：

```text
172.20.20.107:8443
```

账号：

```text
admin
```

密码：

```text
Harbor12345
```

先在 Harbor 里创建你自己的项目，例如：

```text
tenant-1-geoview
```

后面所有镜像都要推到这个项目下面。

## 8. 第五步：执行 deploy_helm_offline.sh

进入解压后的 `GeoView` 根目录后执行：

```bash
PROJECT=tenant-1-geoview APP_VERSION=20260416 ./deploy_helm_offline.sh
```

这里两个参数的含义：

1. `PROJECT`
Harbor 项目名

2. `APP_VERSION`
这次 GeoView 应用的版本号

建议不要省略 `APP_VERSION`，而是明确写一个日期或版本号。

这条命令会自动做这些事情：

1. 先从 `offline_images/geoview_images.tar` 加载离线镜像
2. 再确认 GeoView 应用镜像和 MySQL 镜像都已准备好
3. 登录 Harbor
4. 把镜像重新打成 Harbor 规范地址
5. 推送到 Harbor
6. 重新打包 Helm Chart
7. 生成推荐的 `values-harbor-*.yaml`

## 9. 执行成功后你会得到什么

执行成功后，通常能得到这些结果：

1. Harbor 中出现两个镜像
2. `deploy/helm/dist/geoview-0.1.0.tgz`
3. `deploy/helm/dist/values-harbor-<project>-<version>.yaml`

Harbor 镜像示例：

```text
172.20.20.107:8443/tenant-1-geoview/geoview-app:20260416
172.20.20.107:8443/tenant-1-geoview/mysql:8.0.30-8.6
```

## 10. 第六步：登录服务运维平台

地址：

```text
172.20.20.241
```

账号：

```text
admin
```

密码：

```text
xieyun@2026
```

注意：

1. GeoView 是应用部署
2. 不要部署到 `172.20.20.240:32666` 的服务部署中心

## 11. 第七步：创建命名空间

进入：

```text
项目中心 -> 创建命名空间 -> 分配资源
```

建议：

1. 给 GeoView 单独建一个命名空间
2. 资源不要给得过大
3. 如果要跑当前 GPU 版镜像，命名空间要能分到 GPU 资源

## 12. 第八步：上传 Helm 包

进入：

```text
容器服务 -> 应用中心 -> 创建应用 -> 上传 Helm 包
```

上传这个文件：

```text
deploy/helm/dist/geoview-0.1.0.tgz
```

## 13. 第九步：在平台里修改 values.yaml

平台允许在线修改 `values.yaml` 时，优先参考：

```text
deploy/helm/dist/values-harbor-<project>-<version>.yaml
```

至少要保证下面这些字段正确：

```yaml
app:
  image:
    repository: 172.20.20.107:8443/tenant-1-geoview/geoview-app
    tag: "20260416"
  init:
    image:
      repository: 172.20.20.107:8443/tenant-1-geoview/mysql
      tag: "8.0.30-8.6"
      pullPolicy: IfNotPresent
  gpu:
    enabled: true
    count: 1
  persistence:
    storageClass: csi-block-sc2
    size: 80Gi
  config:
    miner:
      enabled: false

mysql:
  image:
    repository: 172.20.20.107:8443/tenant-1-geoview/mysql
    tag: "8.0.30-8.6"
  persistence:
    storageClass: csi-block-sc2
    size: 20Gi
```

## 14. 为什么这里必须开 GPU

当前 GeoView 应用镜像基于 NVIDIA CUDA 运行时镜像。

如果平台按 CPU 应用部署，不给 Pod 分配 GPU 资源，就可能报：

```text
/bin/bash: error while loading shared libraries: /usr/lib/x86_64-linux-gnu/libcuda.so.1: file too short
```

所以这次平台部署必须保证：

1. `app.gpu.enabled: true`
2. `app.gpu.count: 1`

注意：

1. 这能解决“应用按 CPU 部署导致拿不到真实 `libcuda.so.1`”这一类问题
2. 但如果平台 GPU 节点本身的 NVIDIA runtime / device plugin 有问题，或者 Pod 没有真正调度到 GPU 节点，同样还会报这个错
3. 也就是说，这个 Helm 配置已经是正确方向，但不能代替平台侧 GPU 环境本身

## 15. 为什么 init.image 要单独用 MySQL 镜像

Helm Chart 里有一个初始化容器，用来先创建 PVC 目录。

如果它也用 GeoView 的 GPU 镜像，就可能在正式容器启动前先碰到 `libcuda` 问题。

所以这里专门让它使用 MySQL 镜像来做初始化，这样更稳。

## 16. 最容易犯的 5 个错误

1. Full 包解压后，没有先检查 `offline_images/geoview_images.tar` 是否存在

2. 误以为最终部署是 `docker compose`
说明：这次最终目标是 Helm 平台部署，不是 Docker Compose 部署

3. Harbor 镜像没带版本号
说明：应用镜像必须带版本号 tag，不能只用 `latest`

4. values 里没开 GPU
说明：当前镜像是 GPU 版，不开 GPU 容易触发 `libcuda` 错误

5. PVC 存储类没改成 `csi-block-sc2`
说明：你们平台规范要求应用部署使用这个存储类型
