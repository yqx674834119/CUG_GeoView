# GeoView Offline Deployment Guide

这份文档给交付同事使用，目标是保持现有 Thin/Full 离线交付流程不变，同时说明新的模型真源已经统一到 `backend/model/<页面>/<模型名>/`。

## 先记住当前交付链路

1. 源机器导出 Thin 包  
   使用 `./export_offline.sh 2`，只打包代码和模型资产，不保存本地镜像 tar。

2. 中转机器补全并验证  
   解压 Thin 包后执行 `./deploy_offline.sh` 启动服务，再执行 `./export_offline.sh 1` 导出 Full 包。

3. 最终离线机器部署  
   解压 Full 包后执行 `./deploy_offline.sh`，直接离线启动。

这条操作顺序没有变，变化的是模型目录和缓存生成方式。

## 给中转机器到底要交付什么

如果你现在是在“源机器”准备交付给“中转机器”，默认只需要交付下面这 2 样东西：

1. `GeoView_Offline_Thin_YYYYMMDD.tar.gz`
2. 阿里云镜像地址

当前默认镜像地址是：

```text
crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/cugrs:latest
```

如果中转机器还没有登录过阿里云镜像仓库，还要额外给对方：

1. 镜像仓库登录账号
2. 镜像仓库登录密码或 Access Token

注意：

- 不需要单独再发 `backend/model/`
- 不需要单独再发 `offline_cache/`
- 不需要单独再发 `offline_images/*.tar`
- 因为这些内容都已经包含在 Thin 包里，或者会在中转机器上自动生成 / 自动拉取

一句话理解：

- 发给中转机器的是 `Thin 包`
- 中转机器生成的是 `Full 包`
- 最终离线机器使用的是 `Full 包`

## 中转机器小白操作手册

下面这段可以直接发给中转机器同事照着做。

### 0. 你会收到什么

你会收到：

1. 一个文件：`GeoView_Offline_Thin_YYYYMMDD.tar.gz`
2. 一个镜像地址：`crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/cugrs:latest`
3. 如果仓库是私有的，还会收到阿里云登录账号密码

你的目标不是直接交付最终环境，而是：

1. 用 Thin 包把系统在中转机器上跑起来
2. 让系统自动补齐镜像和缓存
3. 再导出一个更完整的 Full 包
4. 把 Full 包交给最终离线机器

### 1. 中转机器要提前准备什么

中转机器需要满足：

1. 能联网
2. 安装了 Docker
3. 安装了 Docker Compose 插件
4. 磁盘空间尽量充足，因为这一步会生成完整 Full 包

先执行：

```bash
docker --version
docker compose version
```

只要这两条命令能正常输出版本号，就可以继续。

### 2. 把 Thin 包放到中转机器

把你收到的：

```text
GeoView_Offline_Thin_YYYYMMDD.tar.gz
```

放到任意一个你方便操作的目录，比如：

```bash
~/delivery/
```

### 3. 解压 Thin 包

进入存放目录，执行：

```bash
cd ~/delivery
tar -xzf GeoView_Offline_Thin_*.tar.gz
cd GeoView
```

解压后，目录里应该能看到：

- `deploy_offline.sh`
- `export_offline.sh`
- `docker-compose.yml`
- `backend/`
- `offline_cache/`
- `backend/model/`

### 4. 如果阿里云仓库需要登录，先登录

如果你还没有登录过阿里云镜像仓库，先执行：

```bash
docker login --username=你的账号 crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com
```

然后输入密码。

如果这一步已经做过，可以跳过。

### 5. 在中转机器上启动系统

在 `GeoView` 目录下执行：

```bash
./deploy_offline.sh
```

这条命令会自动做这些事：

1. 先检查并整理 `offline_cache/`
2. 从 `backend/model/` 生成运行时缓存
3. 检查模型资产是否完整
4. 如果本地没有应用镜像，就自动从阿里云拉取
5. 自动启动 GeoView 容器和 MySQL 容器

### 6. 等待启动完成后，做 3 个检查

先看容器状态：

```bash
docker compose ps
```

如果看到 `cugrs-app` 和 `cugrs-mysql` 都是 `Up`，说明容器已经启动。

再看后端日志：

```bash
docker logs -f cugrs-app
```

如果日志没有持续报错，可以按 `Ctrl+C` 退出日志。

最后可以在浏览器访问：

```text
http://127.0.0.1:3000
```

如果页面能打开，说明中转机器这一步成功了。

### 7. 在中转机器导出 Full 包

确认服务正常后，在 `GeoView` 目录执行：

```bash
./export_offline.sh 1
```

这个命令会把完整内容打进去，包括：

1. 项目代码
2. `backend/model/` 下的统一模型资产
3. `offline_cache/` 下生成好的缓存
4. 应用镜像 `offline_images/cugrs_app.tar`
5. MySQL 镜像 `offline_images/mysql.tar`

### 8. Full 包生成后在哪里找

生成完成后，完整包不在当前目录，而是在 `GeoView` 的上一级目录。

也就是说，如果你当前在：

```bash
~/delivery/GeoView
```

那么 Full 包通常会出现在：

```bash
~/delivery/GeoView_Offline_Full_YYYYMMDD.tar.gz
```

### 9. 中转机器最后要交付给最终离线机器什么

中转机器最后只需要交付：

1. `GeoView_Offline_Full_YYYYMMDD.tar.gz`

最终离线机器拿到这个包后，就不再需要联网。

### 10. 中转机器最容易犯的 3 个错误

1. 不要在中转机器再次执行 `./export_offline.sh 2`
说明：中转机器的目标是生成 Full 包，所以这里必须执行 `./export_offline.sh 1`

2. 不要删 `offline_images/`
说明：Full 包导出时会把镜像 tar 一起打进去，删掉就不完整了

3. 如果 `deploy_offline.sh` 拉镜像失败，先检查是否登录阿里云
说明：大部分“镜像找不到/无权限”问题，本质上都是没有先 `docker login`

## 新的模型真源目录

所有页面可选模型现在都显式落在：

- `backend/model/change_detection/<model_name>/`
- `backend/model/object_detection/<model_name>/`
- `backend/model/semantic_segmentation/<model_name>/`
- `backend/model/classification/<model_name>/`
- `backend/model/image_restoration/<model_name>/`
- `backend/model/registration/<model_name>/`
- `backend/model/tracking/<model_name>/`

当前关键模型对应关系如下：

- `backend/model/change_detection/bit_256x256`
- `backend/model/classification/resnet50`
- `backend/model/object_detection/paddle_yolo`
- `backend/model/object_detection/hf_detr_resnet50`
- `backend/model/object_detection/hf_conditional_detr_resnet50`
- `backend/model/object_detection/hf_waldo30`
- `backend/model/object_detection/mmrotate_oriented_rcnn_r50_fpn_1x_dota_le90`
- `backend/model/semantic_segmentation/paddle_deeplabv3p`
- `backend/model/semantic_segmentation/mmseg_cugrs`
- `backend/model/image_restoration/hf_swin2sr_x2`
- `backend/model/image_restoration/hf_swin2sr_x4`
- `backend/model/registration/auto`
- `backend/model/registration/opencv`
- `backend/model/registration/loftr_outdoor`
- `backend/model/tracking/auto`
- `backend/model/tracking/csrt`
- `backend/model/tracking/kcf`

说明：

- Paddle 模型直接存放在各自目录中
- HuggingFace 模型目录内带 `hf_config.json` 和本地 Hub 快照
- MMSeg/MMRotate 目录内带 `config.py` 和 `checkpoint.pth`
- 注册/跟踪中的工程基线目录使用 `model_manifest.json` 描述运行方式

## `offline_cache/` 现在是什么

`offline_cache/` 仍然保留，但它不再是模型真源，而是运行期兼容缓存。

- `offline_cache/huggingface/`
- `offline_cache/torch/`
- `offline_cache/paddle/`

脚本会在打包和部署时自动执行：

```bash
python3 ./sync_model_assets.py
```

把 `backend/model/` 中的 HF / LoFTR 资产同步到 `offline_cache/`，然后继续沿用原有 Docker 挂载关系：

- `offline_cache/huggingface -> /root/.cache/huggingface`
- `offline_cache/torch -> /root/.cache/torch`
- `offline_cache/paddle -> /root/.paddle`
- `offline_cache/paddle -> /root/.cache/paddle`

## 阶段一：源机器导出 Thin 包

### 1. 先确认镜像已存在

```bash
docker image inspect crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/cugrs:latest >/dev/null
```

如果失败，先在联网环境执行：

```bash
docker pull crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/cugrs:latest
```

### 2. 执行轻量导出

```bash
./export_offline.sh 2
```

这一步会做 4 件事：

1. 不保存本地 Docker 镜像 tar。
2. 先把 `backend/model/` 同步到 `offline_cache/`。
3. 再从运行中容器或历史卷补充可能存在的旧缓存。
4. 执行 `python3 ./audit_offline_assets.py --strict` 做严格校验。

完成后会在上一级目录生成类似：

```bash
GeoView_Offline_Thin_20260331.tar.gz
```

### 3. 推送应用镜像到镜像仓库

`export_offline.sh 2` 结束后，按脚本提示执行：

- `docker login`
- `docker tag`
- `docker push`

Thin 包本身仍然不包含 `offline_images/*.tar`。

## 阶段二：中转机器补全并导出 Full 包

### 1. 解压 Thin 包

```bash
tar -xzf GeoView_Offline_Thin_*.tar.gz
cd GeoView
```

### 2. 执行部署脚本

```bash
./deploy_offline.sh
```

现在的部署脚本会先做以下预处理，再启动容器：

1. 修正 `offline_cache/` 目录权限
2. 从 `backend/model/` 生成运行期缓存
3. 执行 `audit_offline_assets.py --strict`
4. 加载本地镜像 tar 或按原逻辑拉取镜像
5. 执行 `docker compose up -d --no-build`

### 3. 验证服务是否正常

```bash
docker compose ps
docker logs -f cugrs-app
```

### 4. 导出 Full 包

确认服务可用后执行：

```bash
./export_offline.sh 1
```

这一步会把以下内容一起打包：

- 项目代码
- `backend/model/` 下的统一模型资产
- `offline_cache/` 下生成好的运行期缓存
- `offline_images/cugrs_app.tar`
- `offline_images/mysql.tar`

生成结果类似：

```bash
GeoView_Offline_Full_20260331.tar.gz
```

## 阶段三：最终离线机器部署

### 1. 解压 Full 包

```bash
tar -xzf GeoView_Offline_Full_*.tar.gz
cd GeoView
```

### 2. 直接部署

```bash
./deploy_offline.sh
```

离线机器不需要联网。脚本会自动：

1. 从 `backend/model/` 生成运行期缓存
2. 从 `offline_images/` 加载镜像
3. 使用 `docker compose up -d --no-build` 启动服务

### 3. 查看状态

```bash
docker compose ps
docker logs -f cugrs-app
```

### 4. 访问系统

- GeoView 前端：`3000`
- GeoView 后端：`5008`
- Miner 前端：`4000`
- Miner 后端：`8000`
- MySQL：`3307`

本机通常直接访问：

```text
http://127.0.0.1:3000
```

## 最常见的排查方法

### 1. 校验模型资产

```bash
python3 ./audit_offline_assets.py --strict
```

### 2. 确认真源目录完整

```bash
du -sh backend/model/change_detection
du -sh backend/model/object_detection
du -sh backend/model/semantic_segmentation
du -sh backend/model/image_restoration
du -sh backend/model/registration
du -sh backend/model/tracking
```

### 3. 确认兼容缓存已经生成

```bash
du -sh offline_cache/huggingface
du -sh offline_cache/torch
du -sh offline_cache/paddle
```

### 4. 重新生成缓存

如果怀疑 `offline_cache/` 过旧，可以手动执行：

```bash
python3 ./sync_model_assets.py
```

## 推荐的完整交付顺序

```bash
# 源机器
./export_offline.sh 2

# 中转机器
tar -xzf GeoView_Offline_Thin_*.tar.gz
cd GeoView
./deploy_offline.sh
./export_offline.sh 1

# 最终离线机器
tar -xzf GeoView_Offline_Full_*.tar.gz
cd GeoView
./deploy_offline.sh
```
