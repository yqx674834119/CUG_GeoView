影像 NDVI 处理扩展功能开发 Demo

目的
- 新增前端页面“影像NDVI处理”，并复用现有上传、排队处理、历史记录与结果预览能力。
- 直接模仿页面“影像超分重建”的交互与数据流，替换功能标识与接口路由即可。

前提
- 启动后端并写入前端环境：

```bash
cd /home/livablecity/cugrs
python backend/app.py
```

- 启动前端开发服务：

```bash
cd /home/livablecity/cugrs/frontend
npm install
npm run serve
```

- 后端需提供 `POST /api/analysis/ndvi` 接口（与其他分析接口保持一致，入参结构相同）。如后端暂未就绪，可先复用 `image_restoration` 验证前端流程。

一、复制并改造“影像超分重建”页面
- 在仓库根路径 `/home/livablecity/cugrs` 执行：

```bash
# 1) 复制页面为 NDVI 页面
cp frontend/src/views/mainfun/RestoreImgs.vue frontend/src/views/mainfun/Ndvi.vue

# 2) 修改组件名、功能标识与接口路由（命令可直接执行）
sed -i 's/name: "Restoreimgs"/name: "Ndvi"/' frontend/src/views/mainfun/Ndvi.vue
sed -i 's/影像超分重建/影像NDVI处理/g' frontend/src/views/mainfun/Ndvi.vue
sed -i 's/image_restoration/ndvi/g' frontend/src/views/mainfun/Ndvi.vue
sed -i 's/`影像超分重建结果图.png`/`影像NDVI处理结果图.png`/' frontend/src/views/mainfun/Ndvi.vue
```

说明
- 该页面依赖以下工具与 API（均已存在，无需新建）：
  - `@/api/upload.js` 的 `createSrc(formdata)` 与 `imgUpload(data, funUrl)`（本功能传 `funUrl='ndvi'`）。
  - `@/utils/getUploadImg.js` 的 `getUploadImg(type)`、`goCompress(type)`、`upload(type, funUrl)`。
  - `@/api/history.js` 的 `historyGetPage`（用于历史与结果读取）。
  - `@/global.vue` 的 `BASEURL`（拼接图片地址）。
  - 注意：上面的替换会把 `getCustomModel('image_restoration')` 改为 `getCustomModel('ndvi')`。NDVI 通常无需模型，可保留或删除该模块；若后端支持模型列表，可沿用。

二、路由注册（手动插入）
- 编辑 `frontend/src/router/index.js`，在现有 `routes` 数组中新增 NDVI 路由：

```js
{
  path: '/ndvi',
  name: 'Ndvi',
  component: () => import('@/views/mainfun/Ndvi.vue'),
  meta: { title: '影像NDVI处理' }
}
```

三、侧边菜单入口（手动插入）
- 编辑 `frontend/src/components/AsideVue.vue`，在“影像超分重建”同级位置新增菜单项：

```vue
<el-menu-item index="/ndvi" @click="goNdvi">
  <i v-show="isCollapse" class="icon-enhance" />
  <h3 v-show="!isCollapse"><i class="icon-enhance" />影像NDVI处理</h3>
</el-menu-item>
```

- 编辑 `frontend/src/utils/gosomewhere.js`，新增跳转方法（与其他方法一致）：

```js
export function goNdvi() {
  window.location.hash = '#/ndvi'
}
```

四、接口约定与联调
- 前端上传流程与其他分析页面一致：
  - 先将文件（或文件夹）上传至后端：`POST /api/file/upload` → 返回 `src` 列表。
  - 将 `uploadSrc` 结构提交分析：`POST /api/analysis/ndvi`。

- 请求体示例（与 `image_restoration` 一致）：

```json
{
  "list": ["/static/upload/xxx1.png", "/static/upload/xxx2.png"],
  "model_path": "可选模型路径（NDVI通常无需模型，可为空）",
  "prehandle": 0,
  "denoise": 0,
  "type": "影像NDVI处理"
}
```

- curl 示例：

```bash
# 1) 先上传文件，得到 src 列表
curl -X POST "http://$(grep ^VUE_APP_BACKEND_IP= frontend/.env | cut -d= -f2):$(grep ^VUE_APP_BACKEND_PORT= frontend/.env | cut -d= -f2)/api/file/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@/path/to/your/image1.png" -F "files=@/path/to/your/image2.png" -F "type=影像NDVI处理"

# 2) 将 src 列表提交到 ndvi 分析（将上一步返回的 src 替换至 list）
curl -X POST "http://$(grep ^VUE_APP_BACKEND_IP= frontend/.env | cut -d= -f2):$(grep ^VUE_APP_BACKEND_PORT= frontend/.env | cut -d= -f2)/api/analysis/ndvi" \
  -H "Content-Type: application/json" \
  -d '{"list":["/static/upload/xxx1.png","/static/upload/xxx2.png"],"type":"影像NDVI处理"}'
```

后端返回结构约定
- 与其他分析接口一致，建议返回：`{ code, msg, data }`，其中 `data` 为结果集（含 `before_img` 与 `after_img` 的 URL 或相对路径）。
- 前端会自动拼接 `global.BASEURL + 相对路径`。

五、历史与结果预览
- 历史查询：`getUploadImg('影像NDVI处理')` 会调用 `historyGetPage(1, 20, type)` 拉取前 20 条记录。
- 结果预览：复用滑块对比（若含 `before_img` 与 `after_img`），或直接列表展示。打包下载复用 `goCompress('影像NDVI处理')`。
- 单图下载：复用 `downloadimgWithWords(id, url, '影像NDVI处理结果图.png')`。

六、运行与验证
- 启动前端（首次需安装依赖）：

```bash
cd /home/livablecity/cugrs/frontend
npm install
npm run serve
```

- 浏览器访问并验证：

```bash
xdg-open http://127.0.0.1:3000/#/ndvi
```

七、常见问题排查
- 页面空白或报 404：确认 `router/index.js` 已添加 `/ndvi` 路由。
- 按钮点击无响应：确认 `@click="upload('影像NDVI处理','ndvi')"` 已替换正确。
- 图片地址无法显示：检查后端返回是否为相对路径，并确认 `global.BASEURL` 正确（由 `.env` 注入）。
- 接口 404：后端需实现 `POST /api/analysis/ndvi`；可用 `image_restoration` 先联调前端。

八、可选增强
- NDVI 通常无需模型选择：可移除页面的“可选训练模型”块，或保持占位。
- 预处理（裁剪、去噪）：可保留与复用现有 `MyVueCropper` 与预处理工具。
- 批量与压缩提示：保留现有逻辑，当上传数量≥10 自动提示是否打包。

参考文件
- 视图模板：`frontend/src/views/mainfun/RestoreImgs.vue`
- 上传与分析 API：`frontend/src/api/upload.js`
- 历史与预览工具：`frontend/src/utils/getUploadImg.js`
- 基础地址：`frontend/src/global.vue`
- 路由：`frontend/src/router/index.js`
- 侧边菜单：`frontend/src/components/AsideVue.vue`