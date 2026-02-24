# mine

## 快速启动（前端、后端、MySQL）

### 环境准备
- Node `^20.19.0` 或 `>=22.12.0`（已在 `package.json` 的 `engines` 指定）
- MySQL 8（本地服务或 Docker 均可）
- 推荐安装 Docker 以快速运行 MySQL（可选）

### 数据库配置
在项目根目录创建/编辑 `.env`：

```
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=mine_user
DB_PASSWORD=
DB_NAME=mine_db
```


```
mysql -uroot -p你的密码 -e "CREATE DATABASE IF NOT EXISTS mine_db CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;"
```

也可以用 Docker 启动一个 MySQL 8（可选）：

```
docker run -d --name mysql8 \
  -e MYSQL_ROOT_PASSWORD=你的密码 \
  -e MYSQL_DATABASE=mine_db \
  -p 3306:3306 mysql:8
```

### 安装依赖

```
npm install
```

### 启动后端（Express + mysql2）
- 后端入口：`server.js`，默认端口 `8000`
- 读取 `.env` 连接 MySQL，启动时会：
  - 创建表 `mines_geojson`（如不存在）
  - 若表为空并存在 `dali.geojson`，自动导入为要素集合

启动命令：

```
node server.js
# 输出示例：服务器运行在 http://localhost:8000
```

### 启动前端（Vite + Vue 3）

```
npm run dev -- --host
# 本地开发地址：http://localhost:5173/
```

前端会从后端读取数据：
- `GET http://localhost:8000/api/geojson` 返回矿山 GeoJSON 集合
- `GET http://localhost:8000/api/mines/ndvi?fid={FID_1}` 返回该矿山历年 NDVI 统计
- `GET http://localhost:8000/api/mines/search?q={FID_1 或 名称片段}` 按编号/名称搜索

### 可选：导入 NDVI 数据（Excel）
项目根目录已有 `NDVI_2year.xlsx`，可按需导入到 MySQL：

```
npm run import:ndvi  # 默认读取 NDVI_2year.xlsx
# 或指定文件
npm run import:ndvi -- your.xlsx
```

脚本会自动：
- 创建表 `ndvi_data(fid INT, year INT, ndvi_value DECIMAL(6,3), PRIMARY KEY(fid,year))`
- 解析 Excel 并写入/更新 (fid,year) 的 NDVI 值

> 提示：若需要指定 GeoJSON 文件，设置环境变量 `GEOJSON_PATH`（默认 `dali.geojson`）。

---

## NDVI 数据导入（从 NDVI_2year.xlsx 到 MySQL）

1. 配置数据库连接，在项目根目录 `.env` 中设置：

```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=你的密码
DB_NAME=mine_db
```

2. 将 `NDVI_2year.xlsx` 放在项目根目录（已存在）。支持两种表头结构：
   - 宽表：`FID_1` 列 + 多个年份列（如 `2023`, `2024`）
   - 纵表：`FID_1`, `year`, `ndvi`（或 `ndvi_value`）

3. 执行导入：

```
npm run import:ndvi  # 默认读取 NDVI_2year.xlsx
# 或指定文件
npm run import:ndvi -- your.xlsx
```

脚本会自动：
- 创建表 `ndvi_data(fid INT, year INT, ndvi_value DECIMAL(6,3), PRIMARY KEY(fid,year))`
- 解析 Excel 并写入/更新 (fid,year) 的 NDVI 值

4. 后端接口 `/api/mines/ndvi?fid=xxx` 会从 `ndvi_data` 读取该 FID 的所有年份 NDVI，后端以 JS 计算：
- `ndvi_mean`：均值
- `ndvi_trend`：线性回归斜率（year vs NDVI）
- `mk_trend`：根据斜率阈值判定（上升/下降/无趋势）

如需改为数据库视图/存储过程计算，可根据需要扩展。


This template should help get you started developing with Vue 3 in Vite.

## Recommended IDE Setup

[VS Code](https://code.visualstudio.com/) + [Vue (Official)](https://marketplace.visualstudio.com/items?itemName=Vue.volar) (and disable Vetur).

## Recommended Browser Setup

- Chromium-based browsers (Chrome, Edge, Brave, etc.):
  - [Vue.js devtools](https://chromewebstore.google.com/detail/vuejs-devtools/nhdogjmejiglipccpnnnanhbledajbpd) 
  - [Turn on Custom Object Formatter in Chrome DevTools](http://bit.ly/object-formatters)
- Firefox:
  - [Vue.js devtools](https://addons.mozilla.org/en-US/firefox/addon/vue-js-devtools/)
  - [Turn on Custom Object Formatter in Firefox DevTools](https://fxdx.dev/firefox-devtools-custom-object-formatters/)

## Customize configuration

See [Vite Configuration Reference](https://vite.dev/config/).

## Project Setup

```sh
npm install
```

### Compile and Hot-Reload for Development

```sh
npm run dev
```

### Compile and Minify for Production

```sh
npm run build
```
