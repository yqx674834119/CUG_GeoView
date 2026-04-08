# GeoView Helm / K8s 部署入门与迁移说明

这份文档是给“第一次接触 Kubernetes / Helm”的同学看的。

目标不是立刻把 Helm 包做完，而是先让你搞清楚：

1. 现在项目里已经有什么
2. Helm / K8s 里的这些东西分别是什么
3. 还需要新增什么
4. 你的部署流程要怎么改

---

## 1. 先说结论

你现在的项目还不是一个“可以直接打 Helm 包”的状态。

原因很简单：

当前项目的运行方式本质上还是：

1. 用一个大镜像启动 `app`
2. 再通过 `docker-compose.yml` 把宿主机里的 `backend/`、`frontend/`、`miner/`、`config.yaml`、`offline_cache/` 挂进去
3. 容器启动后再跑 Flask、Vue dev server、Miner dev server

而 Kubernetes / Helm 更推荐的方式是：

1. 镜像本身就是最终产物
2. 容器启动时尽量不依赖宿主机源码目录
3. 配置走 `ConfigMap / Secret`
4. 数据走 `PVC`
5. 服务通过 `Service / Ingress` 暴露

所以如果别人说“请打成 Helm 包”，你不能只理解成“把 docker-compose.yml 翻译成 YAML”。

真正需要做的是：

1. 先把运行方式从“本地开发式挂载”改成“镜像即交付物”
2. 再给它补一套 Helm Chart

---

## 2. 你现在手里分别有什么

### 2.1 现在的主要部署文件

当前项目最关键的部署相关文件是：

- [docker-compose.yml](/home/livablecity/GeoView/docker-compose.yml)
- [Dockerfile](/home/livablecity/GeoView/Dockerfile)
- [deploy_offline.sh](/home/livablecity/GeoView/deploy_offline.sh)
- [export_offline.sh](/home/livablecity/GeoView/export_offline.sh)
- [config.yaml](/home/livablecity/GeoView/config.yaml)

### 2.2 当前 docker-compose 在做什么

你现在的 Compose 里有两个服务：

1. `app`
2. `mysql`

其中：

- `app` 是 GeoView 主应用
- `mysql` 是数据库

`app` 里面又同时承担了很多职责：

1. Flask 后端
2. Vue 前端
3. Miner 前端
4. Miner 后端
5. 模型缓存初始化

也就是说，现在的 `app` 不是一个“单职责容器”，而是一个“大一统容器”。

这在 Docker Compose 里能跑，但在 K8s 里会让 Helm 设计变复杂。

---

## 3. Helm、K8s 这些词分别是什么

下面尽量用“新手能理解的话”解释。

### 3.1 Kubernetes 是什么

Kubernetes，简称 K8s，是“容器编排平台”。

你可以把它理解成：

- Docker 是“把一个程序装进容器里”
- Kubernetes 是“批量管理很多容器，让它们稳定运行”

它负责：

1. 启动容器
2. 重启挂掉的容器
3. 分配网络访问
4. 绑定存储
5. 管理副本数
6. 滚动升级

### 3.2 Helm 是什么

Helm 可以理解成“Kubernetes 的安装包管理器”。

你可以把它类比成：

- `apt install xxx`
- `pip install xxx`
- `npm install xxx`

只不过 Helm 安装的不是 Python 包，而是一组 K8s 资源。

Helm 的产物叫：

- `Chart`

所以“打成 Helm 包”基本就是：

1. 写一个 Chart
2. 让别人可以用 `helm install` / `helm upgrade` 部署你的应用

### 3.3 Chart 是什么

Chart 就是一套模板化的 K8s 部署文件。

它通常包含：

1. `Chart.yaml`
2. `values.yaml`
3. `templates/*.yaml`

其中：

- `Chart.yaml` 记录这个 Helm 包是谁、版本是多少
- `values.yaml` 提供默认配置
- `templates/` 里面是真正渲染成 K8s YAML 的模板

### 3.4 values.yaml 是什么

`values.yaml` 可以理解成“这个 Helm 包的总配置入口”。

你以后很多部署参数都会写在这里，比如：

- 镜像地址
- 镜像标签
- 服务端口
- 是否启用 Ingress
- PVC 大小
- 数据库地址
- GPU 请求数量

### 3.5 Deployment 是什么

Deployment 是 K8s 里最常见的“应用部署对象”。

它负责：

1. 启动 Pod
2. 保证 Pod 挂了会自动拉起
3. 管理副本数
4. 做滚动升级

通常无状态服务会用 Deployment。

### 3.6 Pod 是什么

Pod 是 K8s 里真正运行容器的最小单位。

你可以简单理解成：

- Docker 里你最常接触的是“容器”
- K8s 里你最常接触的是“Pod”

Pod 里可以有一个或多个容器。

### 3.7 Service 是什么

Service 负责给 Pod 提供稳定访问入口。

因为 Pod IP 会变，所以不能直接写死 Pod 地址。

Service 提供一个稳定名字，例如：

- `mysql`
- `geoview-backend`

### 3.8 Ingress 是什么

Ingress 是 HTTP/HTTPS 的入口规则。

你可以把它理解成：

- 外部访问入口
- 域名转发规则

比如：

- `geoview.example.com -> 前端服务`
- `api.geoview.example.com -> 后端服务`

### 3.9 ConfigMap 是什么

ConfigMap 用来放“普通配置”。

例如：

- `config.yaml`
- 端口配置
- 功能开关

### 3.10 Secret 是什么

Secret 用来放“敏感配置”。

例如：

- MySQL 密码
- 镜像仓库密码
- API Key

### 3.11 PVC 是什么

PVC 是 PersistentVolumeClaim，中文可以理解成“持久化存储申请”。

它用来解决：

- 容器重启后数据不要丢
- 模型缓存不要每次重下
- MySQL 数据库文件要长期保存

你项目里未来最可能需要 PVC 的地方有：

1. MySQL 数据目录
2. `backend/static`
3. `offline_cache`
4. 可能还有 `backend/model`，如果你不打算把模型烘焙进镜像

### 3.12 StatefulSet 是什么

StatefulSet 是给“有状态服务”用的。

最典型的例子就是：

- MySQL
- Redis

因为数据库比普通服务更需要固定身份和持久存储。

### 3.13 Namespace 是什么

Namespace 就是 K8s 里的“项目隔离空间”。

比如你可以专门建一个：

- `geoview`

以后所有 GeoView 相关资源都放在这个命名空间里。

### 3.14 imagePullSecret 是什么

如果你的镜像仓库是私有的，K8s 集群拉镜像就需要凭证。

这个凭证通常通过：

- `imagePullSecrets`

传给 Pod。

这对你当前使用阿里云私有镜像仓库很重要。

---

## 4. 当前项目离 Helm 还差什么

下面说“缺口”。

### 4.1 仓库里目前没有任何 Helm / K8s 文件

我检查过当前仓库，暂时没有：

- `charts/`
- `helm/`
- `k8s/`
- `templates/`

也就是说，现在 Helm 包还没有起步。

### 4.2 当前运行方式依赖宿主机 bind mount

这件事非常关键。

当前 [docker-compose.yml](/home/livablecity/GeoView/docker-compose.yml) 里有这些挂载：

- `./config.yaml:/app/config.yaml`
- `./backend:/app/backend`
- `./frontend:/app/frontend`
- `./miner:/app/miner`
- `./backend/static:/app/backend/static`
- `./offline_cache/*:/root/.cache/...`

这意味着：

当前容器运行时强依赖宿主机目录。

但 K8s 里一般不会这样干。

因为：

1. K8s 节点不是你的开发机
2. Pod 可能漂移到不同节点
3. 宿主机路径不稳定
4. Helm 包不应该依赖“某台机器上刚好有这个目录”

所以迁移到 K8s 时，最大的变化不是 YAML，而是“运行方式变了”。

### 4.3 当前前端 / Miner 仍然是开发模式启动

从当前镜像和入口脚本看，你还在跑：

- Vue dev server
- Vite dev server

这在本地开发很方便，但在 K8s 生产部署里不理想。

K8s 更推荐：

1. 前端先构建成静态文件
2. 用 Nginx 或后端静态服务直接提供

否则：

1. 容器启动慢
2. 日志噪音大
3. 资源占用更高
4. 生产行为不稳定

### 4.4 当前数据库是 Compose 里自带 MySQL

这在本地部署没问题。

但在 K8s 里你需要明确选一种：

1. 继续在集群里部署 MySQL
2. 直接改成连接外部托管 MySQL

通常建议：

- 测试环境：可以自己在 K8s 里起 MySQL
- 生产环境：优先使用外部托管数据库

### 4.5 模型和缓存如何放，是 Helm 迁移里的大问题

你现在的模型真源统一在：

- `backend/model/...`

运行缓存放在：

- `offline_cache/...`

迁移到 K8s 时，你必须明确这几个问题：

1. 模型是打进镜像，还是挂 PVC？
2. `offline_cache` 是容器启动时生成，还是提前准备？
3. 多个 Pod 是否共享同一份缓存？
4. GPU 节点是否都有这些模型文件？

这部分如果不提前设计，Helm 包很难真正可用。

---

## 5. 你至少需要新增什么

如果要做 Helm 化，最少建议新增下面这些目录和文件。

## 5.1 Helm Chart 目录

建议新增：

```text
deploy/
  helm/
    geoview/
      Chart.yaml
      values.yaml
      templates/
        app-deployment.yaml
        app-service.yaml
        mysql-statefulset.yaml
        mysql-service.yaml
        configmap.yaml
        secret.yaml
        pvc.yaml
        ingress.yaml
        image-pull-secret.yaml
        NOTES.txt
```

### 5.2 至少要写的模板

最小可用版一般需要：

1. `app-deployment.yaml`
2. `app-service.yaml`
3. `configmap.yaml`
4. `secret.yaml`
5. `pvc.yaml`

如果数据库也内置到 Chart 中，还需要：

1. `mysql-statefulset.yaml`
2. `mysql-service.yaml`

如果要通过域名访问，还需要：

1. `ingress.yaml`

如果镜像仓库是私有的，还需要：

1. `image-pull-secret.yaml`

### 5.3 values.yaml 至少要有的配置项

最少建议包含这些配置：

1. `image.repository`
2. `image.tag`
3. `image.pullPolicy`
4. `imagePullSecrets`
5. `service.type`
6. `service.ports`
7. `ingress.enabled`
8. `resources`
9. `nodeSelector`
10. `tolerations`
11. `affinity`
12. `persistence.enabled`
13. `persistence.size`
14. `mysql.enabled`
15. `mysql.host`
16. `mysql.port`
17. `mysql.username`
18. `mysql.password`
19. `env`
20. `gpu.enabled`
21. `gpu.count`

---

## 6. 对 GeoView 来说，推荐的 Helm 化方案是什么

不是所有项目都适合同一条路。

对你现在这个项目，我建议分成两种方案看。

## 6.1 方案 A：最小改造版

适合：

- 你想先尽快“能用”
- 接受结构暂时不够优雅
- 先满足别人“Helm 部署”要求

做法：

1. 保留当前大一统 `app` 镜像
2. K8s 里仍然只部署一个 `app` 服务
3. MySQL 可以先放进同一套 Chart，或者接外部 MySQL
4. `config.yaml` 改成 ConfigMap
5. `backend/static`、`offline_cache` 改成 PVC
6. `backend/model` 优先打进镜像，或者挂单独 PVC

优点：

- 改造最少
- 上线最快

缺点：

- 前端 / 后端 / Miner 还混在一起
- 镜像很大
- 生产形态不够优雅
- 扩缩容和资源控制比较笨重

## 6.2 方案 B：推荐生产版

适合：

- 真正准备长期上 K8s
- 后续要交给别人维护
- 想让 Helm Chart 更清晰

做法：

1. 拆分成多个服务
2. 前端改为静态构建产物
3. 后端单独一个 Deployment
4. Miner 前端 / 后端按需要拆开
5. MySQL 尽量外置
6. 模型缓存走 PVC 或预制镜像层

优点：

- 更标准
- 更容易扩缩容
- 更容易做生产治理

缺点：

- 改造工作量更大

如果你现在是新手，我建议：

1. 第一步先做“方案 A”
2. 等 Helm 跑通后，再考虑拆成“方案 B”

---

## 7. 你的部署流程要怎么改

这一部分最重要。

### 7.1 你现在的部署流程

你现在是：

1. 构建 / 拉取 Docker 镜像
2. `docker compose up -d`
3. 如果要离线交付，就走 `Thin -> 中转 -> Full`

### 7.2 以后做 Helm 后的基础流程

最基础会变成：

1. 构建并推送镜像
2. 准备 Helm Chart
3. 配置 `values.yaml`
4. 执行 `helm upgrade --install`

### 7.3 如果是在线 K8s 集群

建议流程：

1. 在源机器构建 GeoView 镜像
2. 推送到阿里云镜像仓库
3. 准备 Helm Chart
4. 在 K8s 集群配置好 `imagePullSecret`
5. 用 Helm 安装到集群

大概会变成：

```bash
helm upgrade --install geoview ./deploy/helm/geoview \
  -n geoview \
  --create-namespace
```

### 7.4 如果是离线 K8s 集群

这件事会比现在的 Docker 离线流程复杂不少。

因为离线 K8s 通常不仅要交付：

1. Helm Chart
2. 镜像
3. 配置
4. 模型 / 缓存

还可能要解决：

1. 集群节点如何导入镜像
2. 私有仓库如何离线同步
3. PVC 初始化怎么做
4. GPU 节点调度怎么做

所以我建议你把 K8s 迁移分成两阶段：

### 阶段一：先实现“在线 Helm 部署”

先做到：

1. 集群能联网
2. Pod 能从阿里云拉镜像
3. Helm 能部署成功

这一步先不追求离线。

### 阶段二：再实现“离线 K8s 交付”

这一步再去设计：

1. 如何导出 Helm 包
2. 如何导出镜像 tar
3. 如何导入到目标集群节点或私有仓库
4. 如何初始化 PVC

---

## 8. 对你来说，真正需要修改的东西有哪些

下面是最现实的待办清单。

### 8.1 镜像层面

你需要把“镜像即运行产物”这件事做实。

也就是说：

1. 不要依赖 `./backend:/app/backend`
2. 不要依赖 `./frontend:/app/frontend`
3. 不要依赖 `./miner:/app/miner`

这些代码都应该在镜像构建时放进去，并且容器启动时直接可运行。

### 8.2 配置层面

你需要把：

- `config.yaml`
- 数据库配置
- 端口配置

从“宿主机挂载文件”迁移到：

- `ConfigMap`
- `Secret`

### 8.3 数据层面

你需要明确这些目录谁负责持久化：

1. MySQL 数据目录
2. `backend/static`
3. `offline_cache/huggingface`
4. `offline_cache/torch`
5. `offline_cache/paddle`

### 8.4 数据库层面

你要选定一种方式：

1. Helm 里带 MySQL
2. Helm 不带 MySQL，只连接外部数据库

对新手来说，测试环境可以先“Helm 带 MySQL”。

但正式环境更建议：

- MySQL 外置

### 8.5 GPU 层面

你当前应用明显依赖 GPU。

所以 Helm/K8s 里还要考虑：

1. 集群是否装了 NVIDIA device plugin
2. Pod 是否声明 GPU 资源
3. 是否需要调度到 GPU 节点

否则应用即使启动了，也未必能正常跑推理。

---

## 9. 建议你新增的第一版交付物

如果你接下来真的要开始做 Helm，我建议第一批新增这些东西：

1. 一份 Helm 入门文档
2. 一份 GeoView Helm 设计文档
3. 一套最小 Helm Chart 骨架
4. 一份在线 K8s 部署说明

也就是说，建议先落地：

```text
docs/Helm_K8s_部署入门与迁移说明.md
deploy/helm/geoview/Chart.yaml
deploy/helm/geoview/values.yaml
deploy/helm/geoview/templates/app-deployment.yaml
deploy/helm/geoview/templates/app-service.yaml
deploy/helm/geoview/templates/configmap.yaml
deploy/helm/geoview/templates/secret.yaml
deploy/helm/geoview/templates/pvc.yaml
```

这是一版“最小能讨论、最小能评审”的起点。

---

## 10. 你现在最应该怎么推进

如果你是新手，我建议按下面顺序，不要跳步骤。

### 第一步：先把概念看懂

你先看完这份文档，知道：

1. Helm 是什么
2. K8s 资源分别是什么
3. 现在项目缺什么

### 第二步：先做“在线 Helm 部署”，不要一上来做离线 K8s

因为：

- 现在 Docker 离线流程已经很复杂
- K8s 离线交付会比它更复杂

所以应先完成：

1. Helm Chart 骨架
2. 在线 K8s 部署

### 第三步：再考虑离线 K8s

当在线 K8s 跑通后，再去讨论：

1. Helm Chart 怎么打包
2. 镜像怎么离线导入
3. PVC 怎么预填充

---

## 11. 用一句话概括这次迁移

从 Docker Compose 迁移到 Helm，不是“换个配置文件格式”。

而是把当前项目从：

- 本地开发式部署

逐步改造成：

- 镜像化
- 配置外置
- 存储独立
- 集群可调度

最后才能自然地打成 Helm 包。

---

## 12. 下一步最合理的产出

在这份文档之后，最合理的下一步不是“直接上 Helm 正式部署”，而是：

1. 先确定采用“最小改造版”还是“推荐生产版”
2. 再补一版 `deploy/helm/geoview/` 初始骨架
3. 然后写一份“在线 K8s 部署说明”

如果你愿意，我下一步可以继续直接帮你做下面其中一项：

1. 帮你生成第一版 Helm Chart 骨架
2. 帮你写第二份文档：《GeoView Helm 实施计划》
3. 帮你把当前 Docker Compose 映射成 K8s 资源清单
