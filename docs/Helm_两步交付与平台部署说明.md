# GeoView Helm 两步交付与平台部署说明

这份文档是基于你给出的内网规范写的，目标是让 GeoView 按“应用部署”的方式交付成 Helm 包，同时兼顾你本地磁盘空间不足的问题。

核心思路只有一句话：

1. 你的电脑只负责生成轻量 Helm 交付物
2. 大镜像相关操作放到服务器 / 机房侧完成

补充说明：

1. 这次 GeoView 是“应用部署”，最终发布平台必须是 `172.20.20.241` 的服务运维平台。
2. 你提供的 `172.20.20.240:32666` 服务部署中心，不作为这次应用 Helm 发布平台。
3. 但镜像文件存储规范、Harbor 仓库规范、版本号规范，仍然全部适用。

---

## 1. 为什么要改成两步法

你现在最大的限制不是 Helm 本身，而是：

1. GeoView 应用镜像很大
2. 本地磁盘空间不够
3. 平台最终要的是 `Helm 包 + Harbor 镜像`

所以最合理的交付方式不是：

- 你在本地生成超大的镜像 tar 再上传

而是：

- 你在本地生成一个很小的 Helm 交付包
- 到 184 / 107 节点或机房环境，直接拉镜像并推 Harbor

这样更适合你的机器条件。

---

## 2. 这次交付里各个东西分别是什么

### 2.1 Helm 包是什么

Helm 包就是最终上传到“服务运维平台”的压缩包。

它本质上是一个 `.tgz` 文件，里面包含：

1. `Chart.yaml`
2. `values.yaml`
3. `templates/*.yaml`

平台上传后，会校验这个包是不是一个有效的 Helm Chart。

### 2.2 values.yaml 是什么

`values.yaml` 是 Helm 部署配置入口。

平台上传 Helm 包后，你最常要改的就是这里面的内容，比如：

1. 应用镜像地址
2. MySQL 镜像地址
3. 资源配额
4. 存储类型
5. 端口

### 2.3 镜像 tar 是什么

镜像 tar 是容器镜像的离线文件。

如果你已经在服务器侧能直接拉镜像，其实可以不在本地先生成这个大 tar。

对于你现在的情况，更推荐：

1. 服务器侧直接 `nerdctl pull`
2. 再 `nerdctl tag`
3. 再 `nerdctl push` 到 Harbor

### 2.4 Harbor 是什么

Harbor 是内网镜像仓库。

K8s 集群最终会从 Harbor 拉镜像，而不是直接从你的阿里云镜像仓库拉。

所以这次交付里，Harbor 是“真正给集群使用的镜像来源”。

### 2.5 命名空间是什么

命名空间就是这个应用在平台里的隔离空间。

按照你的最终规范，应用部署要在：

- 服务运维平台
- 先创建自己的命名空间

### 2.6 PVC 是什么

PVC 就是持久化存储申请。

对于 GeoView，这次 Helm Chart 里主要用在：

1. MySQL 数据目录
2. 应用运行缓存目录

平台里优先使用：

```text
csi-sc
```

### 2.7 模型文件要不要单独上传

对于 GeoView 第一版 Helm 方案，我默认：

- 模型直接打在应用镜像里

原因是：

1. 当前模型真源已经统一到 `backend/model/...`
2. 这样最容易先跑通 Helm 版本
3. 能少引入一层“模型单独挂载”的复杂度

所以第一版 Helm 交付默认：

- 不走“服务模型”单独上传

如果以后模型过大、更新频繁，再改成独立 PVC 挂载。

---

## 3. 这次我已经帮你新增了什么

仓库里现在已经新增了第一版 Helm 相关内容：

- [Chart.yaml](/home/livablecity/GeoView/deploy/helm/geoview/Chart.yaml)
- [values.yaml](/home/livablecity/GeoView/deploy/helm/geoview/values.yaml)
- [values-harbor-example.yaml](/home/livablecity/GeoView/deploy/helm/geoview/values-harbor-example.yaml)
- [build_helm_delivery.sh](/home/livablecity/GeoView/build_helm_delivery.sh)
- [push_harbor_with_nerdctl_example.sh](/home/livablecity/GeoView/deploy/helm/push_harbor_with_nerdctl_example.sh)
- [image-manifest.txt](/home/livablecity/GeoView/deploy/helm/image-manifest.txt)

第一版 Chart 里包含：

1. GeoView `app` Deployment
2. GeoView `app` Service
3. `config.yaml` 的 ConfigMap
4. MySQL StatefulSet
5. MySQL Service
6. Secret
7. PVC
8. 可选 Ingress

---

## 4. 你的部署流程要怎么改

你原来是：

1. 构建 / 拉取 Docker 镜像
2. `docker compose up -d`
3. 离线时走 Thin / Full 包

现在改成 Helm 后，建议流程变成：

### 第一步：本地生成轻量 Helm 交付物

你本地执行：

```bash
./build_helm_delivery.sh
```

这个命令会生成两个文件：

1. `deploy/helm/dist/geoview-0.1.0.tgz`
2. `deploy/helm/dist/GeoView_Helm_Thin_YYYYMMDD.tar.gz`

其中：

- `geoview-0.1.0.tgz` 是最终要上传到平台的 Helm 包
- `GeoView_Helm_Thin_YYYYMMDD.tar.gz` 是轻量交付包，方便你发给服务器侧操作同事

### 第二步：服务器 / 机房侧处理大镜像

这一步不要在你本地做。

应放到：

- 184 节点：`/var/lib/kubelet/<你的目录>`
- 或 107 节点：`/nfs/data/<你的目录>`

推荐优先使用：

- 184 节点 `172.20.20.184`

### 第三步：服务器侧推镜像到 Harbor

按你给的内网规范，用 `nerdctl` 完成：

1. 登录 Harbor
2. 拉取源镜像
3. 打上 Harbor tag
4. 推送到 Harbor

### 第四步：在服务运维平台上传 Helm 包

最后去：

- `172.20.20.241`

按应用部署流程：

1. 创建命名空间
2. 上传 Helm 包
3. 修改 values
4. 选择命名空间
5. 完成部署

---

## 5. 推荐的两步交付法

这就是最适合你现在电脑空间不足的方案。

### 阶段 A：你本地做的事情

你本地只做这些：

```bash
./build_helm_delivery.sh
```

生成后，你只需要交付这些小文件：

1. `deploy/helm/dist/geoview-0.1.0.tgz`
2. `deploy/helm/dist/GeoView_Helm_Thin_YYYYMMDD.tar.gz`

不需要在本地先导出巨大镜像 tar。

### 阶段 B：服务器侧做的事情

服务器侧同事拿到轻量交付包后：

1. 解压轻量包
2. 根据里面的说明，使用 `nerdctl` 处理大镜像
3. 推送 Harbor
4. 上传 Helm 包到服务运维平台

这就是“两步法”。

如果你手里拿到的是已经通过 `export_offline.sh 1` 导出的 Full 包，也可以直接在服务器上执行：

```bash
PROJECT=tenant-1-geoview APP_VERSION=20260401 ./deploy_helm_offline.sh
```

注意：

1. 解压和执行目录必须在 `/var/lib/kubelet/<你的专属目录>` 或 `/nfs/data/<你的专属目录>` 下。
2. `deploy_helm_offline.sh` 现在会强制使用 `nerdctl`，不再回退到 `docker`。
3. 镜像 tag 会严格带版本号，不会推送无版本号镜像。

这个脚本会直接复用 Full 包里的：

1. `offline_images/cugrs_app.tar`
2. `offline_images/mysql.tar`

然后自动完成：

1. 加载镜像
2. 登录 Harbor
3. 打 tag
4. 推送镜像
5. 打 Helm 包
6. 生成平台推荐 values 文件

也就是说，如果你已经有 Full 包，就不一定非要先手工执行一遍 `docker load` 和 `docker push`。

---

## 6. 按你的最终规范，服务器侧应该怎么做

下面这部分是给服务器侧操作同事的。

### 6.1 把轻量交付包上传到服务器

把：

```text
GeoView_Helm_Thin_YYYYMMDD.tar.gz
```

上传到允许的目录，例如：

- `172.20.20.184:/var/lib/kubelet/<your-folder>/`
- `172.20.20.107:/nfs/data/<your-folder>/`

不要上传到根目录。

### 6.2 解压轻量交付包

```bash
tar -xzf GeoView_Helm_Thin_*.tar.gz
cd GeoView_Helm_Thin
```

### 6.3 登录 Harbor

地址：

```text
172.20.20.243:8443
```

账号：

```text
admin
```

密码：

```text
Hc@Cloud01
```

### 6.4 推镜像到 Harbor

建议直接用包里的示例脚本：

```bash
chmod +x push_harbor_with_nerdctl_example.sh
PROJECT=你的镜像仓库文件夹 APP_VERSION=20260401 ./push_harbor_with_nerdctl_example.sh
```

这个脚本默认会：

1. 从源仓库拉 GeoView 应用镜像
2. 从源仓库拉 MySQL 镜像
3. 打成 Harbor 路径
4. 推送到 Harbor

### 6.5 修改 Helm values

用包里的：

- `values-harbor-example.yaml`

把镜像改成 Harbor 路径，例如：

```text
172.20.20.243:8443/你的仓库/geoview-app:20260401
172.20.20.243:8443/你的仓库/mysql:8.0.30-8.6
```

并根据资源规范，修改：

1. CPU
2. 内存
3. GPU
4. PVC 大小
5. `storageClass: csi-sc`

### 6.6 在服务运维平台上传 Helm 包

平台地址：

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

然后按规范：

1. 项目中心 -> 创建命名空间 -> 分配资源
2. 容器中心 -> 应用中心 -> 创建应用
3. 上传 `geoview-0.1.0.tgz`
4. 在平台里修改 `values.yaml`
5. 选择命名空间
6. 完成部署

---

## 7. GeoView 第一版 Helm 部署的默认设计

当前第一版 Chart 默认采用下面的设计：

1. GeoView 应用是一个 `Deployment`
2. MySQL 是一个 `StatefulSet`
3. 模型默认打在应用镜像里
4. 缓存和静态目录通过 PVC 持久化
5. 默认存储类型是 `csi-sc`

这样设计的好处是：

1. 你不用先处理“模型单独上传”
2. Chart 第一版更容易跑起来
3. 更符合你当前代码结构

---

## 8. 当前这版 Helm 你还要注意什么

### 8.1 这是第一版 Helm Chart

它的目标是：

- 先形成一套可交付、可评审、可继续迭代的 K8s 方案

它不是说已经在你内网平台上完成过最终上线验证。

### 8.2 当前应用镜像依然比较大

所以这次两步法的重点就是：

- Helm 包小
- 大镜像处理放到服务器侧

### 8.3 前端和 Miner 仍然在同一个应用镜像里

这也是第一版 Chart 选择“最小改造”的原因。

后面如果要进一步生产化，可以再把：

1. 前端
2. 后端
3. Miner

继续拆分成多个服务。

---

## 9. 你现在真正应该交付什么

如果你要把这套 K8s / Helm 方案交给别人，推荐交付下面这些东西：

1. `deploy/helm/dist/geoview-0.1.0.tgz`
2. `deploy/helm/dist/GeoView_Helm_Thin_YYYYMMDD.tar.gz`
3. 这份文档
4. [Helm_K8s_部署入门与迁移说明.md](/home/livablecity/GeoView/docs/Helm_K8s_部署入门与迁移说明.md)

其中真正的平台上传物是：

1. `geoview-0.1.0.tgz`

真正的“大文件交付说明包”是：

1. `GeoView_Helm_Thin_YYYYMMDD.tar.gz`

---

## 10. 下一步最合理的动作

你现在最应该做的是：

1. 先执行 `./build_helm_delivery.sh`
2. 看看生成的 `geoview-0.1.0.tgz` 和 `GeoView_Helm_Thin_YYYYMMDD.tar.gz`
3. 再把它交给服务器侧同事去按规范推 Harbor 和平台部署

如果你愿意，我下一步可以继续帮你做两件事里的一个：

1. 再补一份“服务器侧小白操作手册”
2. 帮你把第一版 Chart 再压实成更适合平台上传的版本
