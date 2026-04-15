# GeoView Thin 到 Full 再到 Helm 的交付总流程

这份文档是总说明，给你自己和协作同事一起看。

你现在的真实交付链路是：

1. 你的本地机器磁盘不够，只导出 `Thin 包`
2. 同事拿着 `Thin 包` 到一台有网络、磁盘空间足够的机器
3. 同事在这台联网中转机上把环境跑起来，再导出 `Full 包`
4. 同事把 `Full 包` 拷到移动硬盘
5. 内网环境的部署同事拿着 `Full 包`，按 Helm 流程把镜像推到 Harbor，再上传 Helm 包到服务运维平台

这就是本次的标准流程。

## 1. 三段流程分别做什么

### A. 你的本地机器

只做一件事：

1. 导出 `Thin 包`

命令：

```bash
./export_offline.sh 2
```

生成结果通常在项目上一级目录，例如：

```text
GeoView_Offline_Thin_YYYYMMDD.tar.gz
```

你要交给中转同事的内容只有这些：

1. `GeoView_Offline_Thin_YYYYMMDD.tar.gz`
2. GeoView 应用镜像地址
3. 如果需要，再给阿里云镜像仓库账号密码

### B. 联网中转机器

只做两件事：

1. 用 `Thin 包` 把环境补齐
2. 再导出 `Full 包`

命令核心是：

```bash
./deploy_offline.sh
./export_offline.sh 1
```

最终会生成：

```text
GeoView_Offline_Full_YYYYMMDD.tar.gz
```

### C. 内网 Helm 部署环境

只做部署，不再负责生成 Full 包。

这一步的目标不是 `docker compose` 启动，而是：

1. 解压 `Full 包`
2. 用 `deploy_helm_offline.sh` 或 `nerdctl` 把镜像推到 Harbor
3. 上传 Helm 包到 `172.20.20.241`
4. 在平台页面里修改 `values.yaml`
5. 完成应用部署

## 2. Thin 包和 Full 包分别包含什么

### Thin 包

`Thin 包` 包含：

1. 项目代码
2. `backend/model/`
3. `offline_cache/`
4. `docker-compose.yml`
5. `deploy_offline.sh`
6. `export_offline.sh`

但是：

1. 不包含离线镜像 tar

### Full 包

`Full 包` 包含：

1. 项目代码
2. `backend/model/`
3. `offline_cache/`
4. `docker-compose.yml`
5. `deploy_offline.sh`
6. `export_offline.sh`
7. 离线镜像合集：`offline_images/geoview_images.tar`
8. Helm 相关目录和脚本，例如 `deploy/helm/`、`deploy_helm_offline.sh`

注意：

1. 现在 Full 包里的镜像是一个合集文件：

```text
offline_images/geoview_images.tar
```

2. 内网 Helm 部署时，可以直接让 `deploy_helm_offline.sh` 使用这个合集文件

## 3. 你转发给中转同事时怎么说

你可以直接把下面这段发给中转同事：

你会收到：

1. 一个文件：`GeoView_Offline_Thin_YYYYMMDD.tar.gz`
2. GeoView 应用镜像地址
3. 如有需要，还会收到阿里云镜像仓库账号密码

你的任务不是最终部署到平台，而是：

1. 在一台有网络、磁盘空间足够的机器上解压 Thin 包
2. 把 GeoView 跑起来
3. 再导出一个 Full 包
4. 把 Full 包拷到移动硬盘交回来

## 4. 对应操作手册

更详细的中转机器操作手册见：

- [中转机器操作手册](/home/livablecity/GeoView/docs/中转机器操作手册.md)

更详细的内网 Helm 部署手册见：

- [Full包转Helm部署操作手册](/home/livablecity/GeoView/docs/Full包转Helm部署操作手册.md)

## 5. 这次流程和以前最大的不同

以前的最终步骤常常是：

1. Full 包解压后执行 `./deploy_offline.sh`

但你这次最终目标是 Helm 平台部署，所以最终步骤已经改成：

1. `Full 包` 进入内网允许目录
2. 执行 `deploy_helm_offline.sh`
3. 推送 Harbor
4. 上传 Helm 包到服务运维平台

也就是说：

1. `Thin 包` 负责从你本地把代码和模型资产交给中转同事
2. `Full 包` 负责把离线镜像和 Helm 交付物带进内网
3. 最终上线方式是 Helm，不是 `docker compose`
4. 应用部署平台必须是 `172.20.20.241`，不是 `172.20.20.240:32666`
