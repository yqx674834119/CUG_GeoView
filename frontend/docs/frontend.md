# cugrs 前端说明文档

目标：帮助新开发者快速理解前端的用途、定位与核心逻辑，并可直接复制执行文档中的命令与路径。

## 1. 项目结构（整体目录树）

前端位于：`/home/livablecity/cugrs/frontend/`

```plain
/home/livablecity/cugrs/frontend
├── .env                       # 前端环境变量文件（后端首次启动会自动写入，可以手动修改）
├── package.json               # 项目依赖与脚本
├── vue.config.js              # 开发服务配置（读取根目录 config.yaml）
├── public/ 
│   ├── index.html             # 入口 HTML 文件，加载 Vue 应用
│   └── logo.svg               # 项目图标，显示在浏览器标签栏
├── src/
│   ├── main.js                # 入口，注册 Element Plus、路由、指令等
│   ├── App.vue
│   ├── global.vue             # 全局配置：根据 .env 计算后端 BaseURL
│   ├── router/
│   │   └── index.js           # 路由定义（懒加载各业务页面）
│   ├── api/                   # 与后端交互的封装
│   │   ├── request.js         # axios 实例，JSON 请求与拦截器
│   │   ├── requestfile.js     # axios 实例，文件上传（multipart/form-data）
│   │   ├── upload.js          # 上传与分析相关请求封装
│   │   └── history.js         # 历史记录相关请求封装
│   ├── components/            # 可复用 UI 组件
│   │   ├── AsideVue.vue       # 左侧导航与分组
│   │   ├── Bottominfor.vue    # 页脚信息与 GitHub 链接
│   │   ├── DraggableItem.vue  # 可拖拽组件
│   │   ├── ImgShow.vue        # 图片展示组件
│   │   ├── MyVueCropper.vue   # 裁剪组件
│   │   ├── Tabinfor.vue       # 顶部标签辅助信息
│   │   └── Tablogin.vue       # 顶部工具条（系统设置入口预留）
│   ├── assets/                # 静态资源：样式、字体、图片
│   ├── utils/                 # 工具方法（下载、加载、预处理等）
│   │   ├── download.js
│   │   ├── getUploadImg.js
│   │   ├── preHandle.js
│   │   ├── preview.js
│   │   ├── loading.js         # 全屏 Loading 管理（Element Plus）
│   │   └── gosomewhere.js     # 路由跳转工具
│   └── views/                 # 业务页面
│       ├── Home.vue           # 主布局（侧栏 + 顶栏 + 内容区）
│       ├── NotFound.vue       # 404 页面
│       ├── history/History.vue
│       └── mainfun/
│           ├── DetectChanges.vue     # 时序变化分析
│           ├── DetectObjects.vue     # 目标检测
│           ├── Segmentation.vue      # 语义分割
│           └── Classification.vue    # 场景分类
└── README.md
```

## 2. 环境配置与运行

前端依赖：Node.js（建议 LTS 版本），npm。后端为 Flask（Python 3）。

- 根目录配置文件：`/home/livablecity/cugrs/config.yaml`
- 前端开发服务器的 `host/port` 会从该文件读取：

```yaml
port:
  backend: 5008
  frontend: 3000
host:
  backend: 0.0.0.0
  frontend: 0.0.0.0
```

前后端启动顺序建议：先启动后端，再启动前端。后端启动时会自动生成前端的 `.env` 文件。

### 2.1 启动后端（写入前端 .env）

```bash
cd /home/livablecity/cugrs/backend
python app.py
```

启动后会在 `frontend/.env` 写入如下环境变量（由 `config.yaml` 推导）：

```ini
# /home/livablecity/cugrs/frontend/.env
VUE_APP_BACKEND_PORT = 5008
VUE_APP_BACKEND_IP = 127.0.0.1
VUE_APP_BAIDU_MAP_ACCESS_KEY = <ACCESS_KEY>
```

如未启动后端但需要调试前端，可手动创建 `.env` 并填写上述变量。

### 2.2 安装前端依赖并启动开发服务器

```bash
cd /home/livablecity/cugrs/frontend
npm install
npm run serve
```

默认开发地址由 `config.yaml` 决定，通常为：`http://127.0.0.1:3000/`

### 2.3 生产构建

```bash
cd /home/livablecity/cugrs/frontend
npm run build
```

构建产物输出到 `frontend/dist/` 目录，可按需接入生产环境。

### 2.4 代码检查（可选）

```bash
cd /home/livablecity/cugrs/frontend
npx eslint --ext .js,.vue --fix src
```

或在根目录执行完整检查脚本：

```bash
cd /home/livablecity/cugrs/tests
bash lint.sh
```

## 3. 接口与数据交互

### 3.1 BaseURL 与环境变量

`src/global.vue` 中根据 `.env` 的值拼接后端地址：

```js
// /home/livablecity/cugrs/frontend/src/global.vue
const BASEURL = "http://" + process.env.VUE_APP_BACKEND_IP + ":" + process.env.VUE_APP_BACKEND_PORT + "/";
export default { BASEURL };
```

建议后端保持与前端 `.env` 一致的 IP 与端口；如替换后端或数据源，优先通过修改 `.env` 完成切换。

### 3.2 请求封装与拦截器

- `src/api/request.js`：JSON 请求 axios 实例，统一 `baseURL`＝`global.BASEURL`。
  - 请求拦截：显示全屏 Loading。
  - 响应拦截：`response.data.code !== 0` 视为失败，提示 `response.data.msg`。
  - 网络错误：提示“网络异常，请检查后端服务是否启动”。

- `src/api/requestfile.js`：文件上传专用 axios 实例，`Content-Type: multipart/form-data`，与上同样的成功失败约定。

以上约定意味着：后端需返回统一结构的响应。例如：

```json
{
  "code": 0,
  "msg": "ok",
  "data": { /* 具体数据 */ }
}
```

如需适配不同后端，请同步修改上述拦截器中的成功判断与错误处理。

### 3.3 关键接口（端点与示例）

- 上传原图（表单）：

```bash
curl -X POST \
  "http://127.0.0.1:5008/api/file/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/absolute/path/to/image.png"
```

- 发起分析（统一入口）：`/api/analysis/{funUrl}`

示例：时序变化分析（`funUrl=detectchanges`，请求体为 JSON）：

```bash
curl -X POST \
  "http://127.0.0.1:5008/api/analysis/detectchanges" \
  -H "Content-Type: application/json" \
  -d '{
        "window_size": 256,
        "stride": 128,
        "list": [ {"first": "static/upload/a.png", "second": "static/upload/b.png"} ],
        "prehandle": 0,
        "denoise": 0,
        "model_path": "model/your_model_dir"
      }'
```

- 直方图匹配：

```bash
curl -X POST \
  "http://127.0.0.1:5008/api/analysis/histogram_match" \
  -H "Content-Type: application/json" \
  -d '{
        "list": [ {"first": "static/upload/a.png", "second": "static/upload/b.png"} ],
        "prehandle": 0
      }'
```

- 预处理：

```bash
curl -X POST \
  "http://127.0.0.1:5008/api/analysis/image_pre" \
  -H "Content-Type: application/json" \
  -d '{
        "list": [ {"first": "static/upload/a.png", "second": "static/upload/b.png"} ]
      }'
```

- 获取自定义模型列表：

```bash
curl -X GET "http://127.0.0.1:5008/api/model/list/change_detection"
curl -X GET "http://127.0.0.1:5008/api/model/list/object_detection"
```

- 历史记录分页：

```bash
curl -X GET "http://127.0.0.1:5008/api/history/list?page=1&limit=10&type=变化检测"
```

- 批量删除历史记录：

```bash
curl -X DELETE \
  "http://127.0.0.1:5008/api/history/batchRemove" \
  -H "Content-Type: application/json" \
  -d '{"ids": [1,2,3] }'
```

### 3.4 前后端对接要点（便于替换后端/数据源）

- 通过 `.env` 与 `global.vue` 控制 `BASEURL`，替换后端时无需改动业务代码。
- 保持响应结构（`code/msg/data`），否则需调整 `request.js/requestfile.js` 的拦截器。
- 文件路径（如 `static/upload/...`）由后端返回，前端拼接为 `global.BASEURL + path`。

## 4. 组件与 UI 体系

### 4.1 框架与库

- Vue 3 + Vue Router
- Element Plus（中文本地化已启用）
- animate.css、JSZip、file-saver 等辅助库

### 4.2 布局与导航

- 顶层布局：`views/Home.vue`，包含：
  - 左侧导航 `components/AsideVue.vue`（分组与路由跳转）
  - 顶部工具条 `components/Tablogin.vue`
  - 内容区 `router-view`（过渡动画 `fade`）
  - 页脚信息 `components/Bottominfor.vue`
- 返回顶部：`<el-backtop target=".main-ctx" />`

### 4.3 路由规范

`/home` 为容器路由，业务子路由如下（见 `src/router/index.js`）：

```text
/detectchanges   # 时序变化分析
/detectobjects   # 目标检测
/segmentation    # 语义分割
/classification  # 场景分类
/restoreimgs     # 影像重建
/history         # 历史记录
```

新增页面流程：

1. 在 `src/views/` 下创建业务页面（建议与现有分组保持一致）。
2. 在 `src/router/index.js` 使用懒加载 `const Page = () => import('...')` 注册路由。
3. 在 `AsideVue.vue` 添加对应菜单项，保持文案与图标风格一致。

### 4.4 样式与一致性

- 基础样式位于 `src/assets/css`，部分页面使用 Less（例如 `app.less`）。
- 统一使用 Element Plus 组件，遵循已有交互与配色（如 `var(--theme--color)`）。
- Loading 与消息通知统一使用 `utils/loading.js` 与 Element Plus 的 `ElMessage`。

## 5. 可复用部分说明（跨项目迁移）

以下模块在其他项目中也易于复用：

- `src/api/request.js`、`src/api/requestfile.js`：统一的 axios 封装与拦截器。
- `src/global.vue`：通过环境变量拼接后端 `BASEURL` 的模式。
- `src/utils/loading.js`：请求 Loading 计数管理。
- `src/utils/download.js`：打包下载、图片保存工具。
- `src/utils/getUploadImg.js`、`src/utils/preHandle.js`、`src/utils/preview.js`：图像上传、预处理与预览工具集合。
- `src/components/DraggableItem.vue`、`src/components/MyVueCropper.vue`、`src/components/ImgShow.vue`：交互组件。

迁移指引：

1. 在新项目中创建 `.env` 并配置 `VUE_APP_BACKEND_IP/VUE_APP_BACKEND_PORT`。
2. 复制上述模块到对应目录（`api/`、`utils/`、`components/`）。
3. 安装依赖：`axios`、`element-plus`、`file-saver`、`jszip` 等。
4. 验证响应结构与拦截器约定（`code===0` 为成功），必要时调整。
5. 保持路由与菜单结构一致，避免破坏 UI 一致性。

## 6. 常用命令速查

```bash
# 查看根配置
cat /home/livablecity/cugrs/config.yaml

# 启动后端（写入前端 .env）
cd /home/livablecity/cugrs/backend
python app.py

# 安装并启动前端
cd /home/livablecity/cugrs/frontend
npm install
npm run serve

# 生产构建
npm run build

# 代码检查（前端）
npx eslint --ext .js,.vue --fix src
```

—— 完 ——