# GeoView Helm 最终交付手册

这份文档是给“平台部署同事”直接使用的。

目标只有一件事：

把 GeoView 作为一个 Helm 应用，按你们现有规范部署到服务运维平台。

这次采用两步法，原因是本地电脑空间不足，不适合在本地先导出超大镜像文件。

## 1. 你会收到什么

通常你只需要把下面这个轻量包交给部署同事：

```text
GeoView_Helm_Thin_YYYYMMDD.tar.gz
```

这个包里包含：

1. `geoview-0.1.0.tgz`
2. `values-harbor-example.yaml`
3. `image-manifest.txt`
4. `push_harbor_with_nerdctl_example.sh`
5. `Helm_K8s_部署入门与迁移说明.md`
6. `Helm_两步交付与平台部署说明.md`
7. `GeoView_Helm_最终交付手册.md`

其中最重要的是：

1. `geoview-0.1.0.tgz`
2. `values-harbor-example.yaml`

## 2. 这次交付的核心规则

请严格遵守你提供的内网规范：

1. 严禁在服务器根目录和其他非指定路径存储文件。
2. 镜像文件优先存到 `172.20.20.184:/var/lib/kubelet/<你的专属目录>`。
3. 如果使用 `172.20.20.107`，则只能放到 `/nfs/data/<你的专属目录>`。
4. Harbor 镜像必须带版本号 tag，严禁上传无版本号镜像。
5. 如果 Harbor 多次返回 500，立即停止上传，大概率是磁盘不足。
6. 应用必须在“服务运维平台”部署，不要在“服务部署中心”部署应用。

补充说明：

1. 你提供的 `172.20.20.240:32666` 这套“服务部署中心”流程，GeoView 这次不用于应用部署。
2. GeoView 这次是 Helm 应用交付，最终部署平台必须是 `172.20.20.241` 的“服务运维平台”。
3. 前面的镜像存储、Harbor 登录、Harbor 推送规范仍然要遵守。

## 3. 两步交付法

### 第一步：准备镜像

这一步建议在机房服务器侧完成，不建议在本地电脑完成。

原因：

1. GeoView 应用镜像较大。
2. 本地磁盘空间有限。
3. 服务器侧到 Harbor 的网络通常更稳定。

### 第二步：上传 Helm 包到平台

镜像进入 Harbor 后，再去服务运维平台上传 Helm 包并修改 `values.yaml`。

## 4. 平台部署同事的完整操作步骤

### 4.1 上传轻量交付包到指定目录

推荐上传到：

```text
172.20.20.184:/var/lib/kubelet/<你的专属目录>
```

如果 184 不方便，再用：

```text
172.20.20.107:/nfs/data/<你的专属目录>
```

解压：

```bash
tar -xzf GeoView_Helm_Thin_YYYYMMDD.tar.gz
cd GeoView_Helm_Thin
```

### 4.2 登录 Harbor

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

先在 Harbor 上创建你自己的项目，例如：

```text
tenant-1-geoview
```

### 4.3 把镜像推到 Harbor

参考包内脚本：

```bash
chmod +x push_harbor_with_nerdctl_example.sh
./push_harbor_with_nerdctl_example.sh
```

如果你拿到的是 Full 包并且已经解压到服务器允许目录，也可以直接执行：

```bash
PROJECT=tenant-1-geoview APP_VERSION=20260401 ./deploy_helm_offline.sh
```

默认脚本会做这些事情：

1. 登录 Harbor
2. 使用 `nerdctl` 准备镜像
3. 重新打 Harbor tag
4. 推送到 Harbor
5. 生成 Helm 包和推荐 values

你需要至少确认两个变量：

```bash
export PROJECT=tenant-1-geoview
export APP_VERSION=20260401
./push_harbor_with_nerdctl_example.sh
```

推送完成后，Harbor 中通常会出现类似镜像：

```text
172.20.20.243:8443/tenant-1-geoview/geoview-app:20260401
172.20.20.243:8443/tenant-1-geoview/mysql:8.0.30-8.6
```

### 4.4 登录服务运维平台

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

### 4.5 创建命名空间

进入：

```text
项目中心 -> 创建命名空间 -> 分配资源
```

注意：

1. 资源不要给太大。
2. 建议一个 GeoView 服务对应一个单独命名空间。

### 4.6 上传 Helm 包

进入：

```text
容器中心 -> 应用中心 -> 创建应用 -> 上传 Helm 包
```

上传这个文件：

```text
geoview-0.1.0.tgz
```

### 4.7 在平台里修改 values 配置

上传 Helm 包后，平台通常允许在线修改 `values.yaml`。

至少要改下面这些字段：

```yaml
app:
  image:
    repository: 172.20.20.243:8443/tenant-1-geoview/geoview-app
    tag: "20260401"
  gpu:
    enabled: true
    count: 1
  resources:
    requests:
      cpu: "4"
      memory: "16Gi"
    limits:
      cpu: "8"
      memory: "32Gi"
  persistence:
    storageClass: csi-sc
    size: 80Gi

mysql:
  image:
    repository: 172.20.20.243:8443/tenant-1-geoview/mysql
    tag: "8.0.30-8.6"
  persistence:
    storageClass: csi-sc
    size: 20Gi
```

如果平台需要镜像拉取密钥，再补：

```yaml
imagePullSecrets:
  - name: your-harbor-secret
```

包里已经提供了示例文件：

```text
values-harbor-example.yaml
```

可以直接照着改。

### 4.8 选择命名空间并完成部署

选择刚创建的命名空间后，提交部署。

## 5. 这个 Helm 包里实际会部署什么

当前第一版 Helm Chart 会部署：

1. 一个 GeoView 应用容器
2. 一个 MySQL StatefulSet
3. 一个 GeoView Service
4. 一个 MySQL Service
5. 一个 ConfigMap
6. 一个 Secret
7. 一个应用 PVC
8. 一个 MySQL PVC

说明：

1. GeoView 模型当前默认打在应用镜像里，不单独挂模型 PVC。
2. 运行缓存会挂在应用 PVC 上。
3. 存储类型默认使用 `csi-sc`。

## 6. 端口说明

这个应用默认会暴露这些容器内端口：

1. 前端：`3000`
2. 后端：`5008`
3. Miner 前端：`4000`
4. Miner 后端：`8000`
5. MySQL：`3306`

如果平台要求检查端口占用，请重点确认外部暴露方式和平台侧端口策略。

## 7. 你需要交付给最终平台同事的东西

最少只要交付这些：

1. `GeoView_Helm_Thin_YYYYMMDD.tar.gz`
2. Harbor 项目名
3. 应用版本号

如果希望对方更省心，也可以直接告诉对方：

1. Harbor 应用镜像地址
2. Harbor MySQL 镜像地址
3. 推荐的资源配额
4. 推荐的 PVC 大小

## 8. 失败时怎么排查

### 8.1 应用一直 Pending

一般是资源不足，重点检查：

1. 命名空间资源配额
2. CPU / 内存 / GPU 是否足够
3. PVC 是否成功绑定

### 8.2 应用启动失败

一般优先检查：

1. Harbor 镜像地址是否写对
2. tag 是否存在
3. 平台是否有权限拉取 Harbor 镜像
4. `imagePullSecrets` 是否缺失

### 8.3 上传 Harbor 失败

如果多次报 500，按你的规范应立即停止上传，通常是 Harbor 磁盘空间不足。

## 9. 当前方案的边界

这次交付的是第一版可交付 Helm 方案，特点是：

1. 先保证能按你们平台流程交付
2. 镜像内已经包含 GeoView 代码和模型
3. 暂时不把模型拆成单独 PVC

如果后面你们需要：

1. 模型独立挂载
2. 前后端拆分成多个服务
3. 更标准的生产探针和灰度升级

可以在这个 Helm Chart 基础上继续迭代。
