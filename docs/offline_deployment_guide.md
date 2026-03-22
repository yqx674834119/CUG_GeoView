# GeoView 完全离线部署操作指南 (面向小白版)

这份指南将指导您如何把 `GeoView_Offline_Thin_*.tar.gz` 轻量代码缓存包，通过一台“有网且空间大”的中转电脑，最终生成一个能在完全无网环境下运行的全量离线包。

---

## 阶段一：在“有网络且存储空间大”的电脑上的操作

**目的：把别人给的微弱代码包，跟云端的巨大运行环境系统（Docker 镜像）合并成一个完整的“超级终点离线包”。**

### 1. 准备材料
将第一台电脑发给您的压缩包（名字类似：`GeoView_Offline_Thin_20260311.tar.gz`）拷贝到这台电脑任意文件夹（例如您的用户目录 `~` 或桌面下）。

### 2. 解压项目包
打开终端 (Terminal)，进入压缩包所在的目录（比如您把它放到了桌面：`cd ~/Desktop`）。
输入以下解压命令：
```bash
tar -xzf GeoView_Offline_Thin_*.tar.gz
```
解压完成后，您当前目录下会多出一个名为 `GeoView` 的文件夹。请进入它：
```bash
cd GeoView
```

### 3. 拉取最新的系统镜像
我们需要连网，把打包好的庞大环境系统拉下来：
*请在终端中逐条复制并运行以下命令（如果在拉取过程中需要密码，密码是之前告知您的 `Yqx123123123`）：*
```bash
docker login --username=13997543646yqx crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com
docker pull crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/cugrs:latest
docker pull crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/mysql:8.0.30-8.6
```
*(注意：拉取这两项比较大，需要几分钟的时间，请耐心等待直到两个都显示 Pull complete。)*

为了让刚才拖下来的系统兼容咱们的代码脚本，执行一下改名：
```bash
docker tag crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/cugrs:latest cugrs:local-build
docker tag crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/mysql:8.0.30-8.6 registry.openanolis.cn/openanolis/mysql:8.0.30-8.6
```

### 4. 生成“超级终极包”
此时您还在 `GeoView` 文件夹中。请直接运行里面的自动打包脚本：
```bash
./export_offline.sh
```
屏幕上会弹出以下选项：
```text
[1] 完整离线打包：镜像(.tar) + 模型缓存 + 代码一起打包 (适合磁盘空间宽裕的机器)
[2] 轻量空间中转打包：跳过镜像保存，仅提取模型及代码，并将镜像推送到阿里云 (适合当前机器磁盘不足)
```
因为这台机器空间够，所以此处**敲击键盘输入 1 并回车**。

这时候电脑可能需要响十分钟在努力将镜像导出封进压缩包里。直到看见屏幕显示`✓ 全部完成！`，恭喜您，在上级目录中已经诞生了一个名字带有 `GeoView_Offline_Full...tar.gz` 的巨大压缩包（通常得十几二十个G）！

这就是需要交付给最终离线电脑的神奇大包！请把它拷进超大容量的 U 盘或者移动硬盘里带走。

---
<br>

## 阶段二：在完全没网络的“离线电脑”部署

**目的：在这个绝对的孤岛上，不用一滴网络，直接拉起咱们的系统！**前提是：这台机器也同样需要事先安装好了 `Docker` 并且配置带有 NVIDIA 显卡驱动。

### 1. 解压终极安装包
将 U 盘里那个硕大的 `GeoView_Offline_Full...tar.gz` 拖到离线电脑的合适目录里。（比如 `~/`）。打开终端并解压它（可能要十分钟以上）
```bash
tar -xzf GeoView_Offline_Full_*.tar.gz
```
解压后，进入解压出的目录：
```bash
cd GeoView
```

### 2. 一键魔法开机！
由于我们之前配置了超完美的完全断网设定，您此时不用做任何关于网络的操作。
在当前目录中直接使用这行终极魔法脚本（**千万记得要以最高管理员或者加入 docker 用户组的高权限人员执行**）：

```bash
./deploy_offline.sh
```

**此时背后会自动发生的事：**
1. 脚本会把 `GeoView` 内部自带的环境系统 `cugrs_app.tar` 以及 `mysql.tar` 直接加载 (`docker load`) 唤醒。
2. 脚本会自动启动 (`docker compose up -d`) 这个服务。

只要终端里没有报满屏的红字或 Error，而是显示部署成功并且 `Started`，那么就代表服务大功告成被召唤出来了！

### 3. 一切结束 🎉
只需静等二三十秒即可用浏览器访问本机相应的系统入口进行使用了！
您可以随时在这台机器的任意终端中敲击 `docker logs -f cugrs-app` 观察它在后台努力干活输出的字幕以排查隐患。

如果在途中报错什么缺失功能，很大可能是当初在第一台机器抽出来环境（也就是 Thin 包里所谓的缓存）的时候不全面，需要重新从上游补齐再往下传。
