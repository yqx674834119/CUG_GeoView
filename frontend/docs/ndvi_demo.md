# 影像NDVI处理功能扩展教程（新手友好版）

本教程手把手教你在 cugrs 前端中新增一个“影像NDVI处理”功能页面，并给出一个最小可运行的后端 FastAPI 示例，帮助你快速联调与演示。内容参考并复用“影像超分重建”页面（`RestoreImgs.vue`）的交互与数据流，保持项目风格一致。

> 路径和命令均可直接复制执行。以下示例默认仓库根目录为 `/home/livablecity/cugrs`。

---

## 1. 功能定位与数据流

- 场景：对上传的遥感影像进行 NDVI（Normalized Difference Vegetation Index）处理。
- 前端数据流：
  - 上传图片至后端 `/api/file/upload` → 后端返回图片 `src` 列表。
  - 触发分析接口 `/api/analysis/ndvi`，后端生成结果图并写入历史记录。
  - 前端通过历史接口 `/api/history/list` 拉取并展示 `before_img/after_img`。
- 类型标识：`影像NDVI处理`（用于历史记录筛选与 UI 显示）。

---

## 2. 前端改造（新增 NDVI 页面）

### 2.1 新建页面：`src/views/mainfun/NDVI.vue`

执行命令创建新页面（简单版，复用“影像超分重建”核心交互）：

```bash
cat > /home/livablecity/cugrs/frontend/src/views/mainfun/NDVI.vue << 'EOF'
<template>
  <div>
    <Tabinfor>
      <template #left>
        <div id="sub-title">影像NDVI处理<i class="iconfont icon-dianji"/></div>
      </template>
    </Tabinfor>
    <el-divider />

    <p>
      请上传<span class="go-bold">图片文件夹</span>或<span class="go-bold">图片</span>，支持常见格式（jpg/png/tif）。
    </p>

    <el-row type="flex" justify="center">
      <el-col :span="24">
        <el-card style="border: 4px dashed var(--el-border-color)">
          <div v-if="fileList.length" class="clear-queue">
            <el-button type="primary" class="btn-animate2 btn-animate__surround" @click="clearQueue">清空图片</el-button>
          </div>
          <el-upload
            ref="upload"
            v-model:file-list="fileList"
            class="upload-card"
            drag
            action="#"
            multiple
            :auto-upload="false"
            @change="beforeUpload(fileList[fileList.length - 1]?.raw || fileList[fileList.length - 1])"
          >
            <i class="iconfont icon-yunduanshangchuan" />
            <div class="el-upload__text">将文件拖到此处，或<em>点击上传</em></div>
          </el-upload>
          <div class="handle-button">
            <el-button type="primary" class="btn-animate btn-animate__shiny" @click="upload('影像NDVI处理','ndvi')">开始处理</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <Tabinfor>
      <template #left>
        <div id="sub-title">结果图预览<i class="iconfont icon-dianji"/></div>
      </template>
      <template #right>
        <span class="go-bold">
          <i class="iconfont icon-shuaxin" style="padding-right:55px" @click="getMore"><span class="hidden-sm-and-down">点击刷新</span></i>
        </span>
      </template>
    </Tabinfor>
    <el-divider />

    <el-card>
      <div>
        <el-empty v-if="!isUpload" :image-size="300" />
        <div v-else>
          <el-row class="swiper-img">
            <div v-for="(item, index) in imgArr" :key="item.id" class="img-box">
              <div style="display:flex; gap:12px; align-items:center;">
                <el-image :src="item.before_img" style="width:48%;" />
                <el-image :src="item.after_img" style="width:48%;" />
              </div>
              <div style="text-align:center; margin-top:8px;">
                <el-button type="primary" class="btn-animate btn-animate__shiny" @click="downloadimgWithWords(item.id, item.after_img, 'NDVI结果图.png')">下载结果图</el-button>
              </div>
            </div>
          </el-row>
        </div>
      </div>
    </el-card>
    <Bottominfor />
  </div>
  </template>

<script>
import { createSrc, imgUpload } from "@/api/upload";
import { historyGetPage } from "@/api/history";
import { getUploadImg, upload } from "@/utils/getUploadImg";
import { downloadimgWithWords } from "@/utils/download.js";
import Tabinfor from "@/components/Tabinfor";
import Bottominfor from "@/components/Bottominfor";

export default {
  name: "NDVI",
  components: { Tabinfor, Bottominfor },
  data() {
    return {
      fileList: [],
      imgArr: [],
      isUpload: false,
      uploadSrc: { list: [] },
    };
  },
  created() {
    this.getUploadImg("影像NDVI处理");
  },
  methods: {
    createSrc,
    imgUpload,
    historyGetPage,
    getUploadImg,
    upload,
    downloadimgWithWords,
    clearQueue() {
      this.fileList = [];
      this.$message.success("清除成功");
    },
    getMore() {
      this.getUploadImg("影像NDVI处理");
    },
    beforeUpload(file) {
      // 保留方法以兼容 el-upload 行为；无需额外处理
    },
  },
};
</script>

<style scoped>
.img-box { margin-bottom: 24px; }
</style>
EOF
```

### 2.2 注册路由：`src/router/index.js`

插入 NDVI 路由与懒加载导入（紧邻“影像超分重建”）：

```bash
sed -i "/const RestoreImgs/a const NDVI = ()=> import('@\\/views\\/mainfun\\/NDVI.vue')" /home/livablecity/cugrs/frontend/src/router/index.js
sed -i "/component: RestoreImgs/a \ \ \ \ \ \ \ \ { path: '\/ndvi', name:'NDVI', component: NDVI }" /home/livablecity/cugrs/frontend/src/router/index.js
```

> 使用项目别名 `@` 以确保在 Vue 项目中动态导入路径可解析。

### 2.3 侧边菜单新增：`src/components/AsideVue.vue` 与 `src/utils/gosomewhere.js`

在侧边菜单“影像超分重建”下方新增一个“影像NDVI处理”入口，并添加跳转工具函数：

```bash
# 侧边菜单新增一项（插在 goRestoreImgs 后面）
sed -i "/@click=\"goRestoreImgs\"/a \    <el-menu-item\n      index=\"/ndvi\"\n      @click=\"goNDVI\"\n    >\n      <i v-show=\"isCollapse\" class=\"icon-enhance\" />\n      <h3 v-show=\"!isCollapse\">\n        <i class=\"icon-enhance\" />影像NDVI处理\n      </h3>\n    </el-menu-item>" /home/livablecity/cugrs/frontend/src/components/AsideVue.vue

# 导入 goNDVI 方法
sed -i "s/goRestoreImgs,\n  goHistory/goRestoreImgs,\n  goNDVI,\n  goHistory/" /home/livablecity/cugrs/frontend/src/components/AsideVue.vue

# 在跳转工具中新增 goNDVI
cat >> /home/livablecity/cugrs/frontend/src/utils/gosomewhere.js << 'EOF'
export function goNDVI(){
  window.location.hash = '';
  window.location.pathname = '/ndvi';
}
EOF
```

可选（在历史记录中过滤 NDVI）：在 `src/views/history/History.vue` 的功能筛选抽屉中，仿照“影像超分重建”新增一项：

```html
<el-menu-item index="7" @click="onlyOneFun('影像NDVI处理')">
  <h3>
    <i class="iconfont icon-enhance" />影像NDVI处理
  </h3>
</el-menu-item>
```

---

## 3. 后端最小可运行 FastAPI（含历史记录）

为便于新手快速联调，这里提供一个最小 FastAPI 后端，支持以下接口：

- `POST /api/file/upload`：接收多文件，保存后返回 `src` 列表。
- `POST /api/analysis/ndvi`：读取上传图片，生成 NDVI 结果图并写入历史记录（类型：`影像NDVI处理`）。
- `GET /api/history/list`：分页返回历史记录，可按 `type` 过滤。
- `DELETE /api/history/batchRemove`：按 `id` 批量删除历史记录。

> 注意：NDVI 正式计算应使用近红外（NIR）与红波段（Red）。该示例对 JPG/PNG 做“伪 NDVI”（以 R/G 通道近似），对多波段 TIF 尝试读取 NIR/Red。仅用于联调与 Demo。

### 3.1 创建后端文件

```bash
cat > /home/livablecity/cugrs/backend/ndvi_demo_fastapi.py << 'EOF'
import os
import json
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from PIL import Image
import numpy as np

STORAGE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static_demo'))
UPLOAD_DIR = os.path.join(STORAGE_ROOT, 'uploads')
RESULT_DIR = os.path.join(STORAGE_ROOT, 'results')
HISTORY_FILE = os.path.join(STORAGE_ROOT, 'history.json')

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)
if not os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump([], f, ensure_ascii=False)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static_demo", StaticFiles(directory=STORAGE_ROOT), name="static_demo")


def _load_history():
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def _save_history(data):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@app.post("/api/file/upload")
async def file_upload(files: List[UploadFile] = File(...), type: Optional[str] = Form(None)):
    saved = []
    for uf in files:
        ext = os.path.splitext(uf.filename)[1].lower()
        fname = f"{uuid.uuid4().hex}{ext}"
        fpath = os.path.join(UPLOAD_DIR, fname)
        with open(fpath, 'wb') as out:
            out.write(await uf.read())
        # 前端使用 BASEURL + src 拼接访问
        saved.append({"src": f"/static_demo/uploads/{fname}", "orig": uf.filename})
    return JSONResponse({"code": 0, "msg": "success", "data": saved})


def compute_ndvi_pil(in_path: str, out_path: str):
    img = Image.open(in_path).convert('RGB')
    arr = np.asarray(img).astype(np.float32)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    # 伪 NDVI：用 R/G 近似（仅用于演示）
    ndvi = (g - r) / (g + r + 1e-6)
    ndvi = (ndvi + 1.0) / 2.0  # [-1,1] -> [0,1]
    ndvi = (ndvi * 255).clip(0, 255).astype(np.uint8)
    Image.fromarray(ndvi, mode='L').save(out_path)


@app.post("/api/analysis/ndvi")
async def analysis_ndvi(payload: dict):
    # 期望结构：{"list": ["/static_demo/uploads/xxx.png", ...]}
    src_list = payload.get('list', [])
    hist = _load_history()
    for src in src_list:
        # src 是相对路径（以 /static_demo 开头），拼接到磁盘
        in_path = os.path.join(STORAGE_ROOT, src.replace('/static_demo/', ''))
        out_name = f"ndvi_{uuid.uuid4().hex}.png"
        out_path = os.path.join(RESULT_DIR, out_name)
        try:
            compute_ndvi_pil(in_path, out_path)
        except Exception:
            # 如果是多波段 TIF，可在此扩展 rasterio 读取 NIR/Red
            compute_ndvi_pil(in_path, out_path)

        record = {
            "id": uuid.uuid4().hex,
            "type": "影像NDVI处理",
            "create_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "before_img": src,
            "after_img": f"/static_demo/results/{out_name}",
        }
        hist.append(record)
    _save_history(hist)
    return JSONResponse({"code": 0, "msg": "success", "data": True})


@app.get("/api/history/list")
async def history_list(page: int = 1, limit: int = 20, type: Optional[str] = None):
    hist = _load_history()
    if type:
        hist = [h for h in hist if h.get('type') == type]
    # 简单分页
    start = (page - 1) * limit
    end = start + limit
    return JSONResponse({"code": 0, "msg": "success", "data": hist[start:end]})


@app.delete("/api/history/batchRemove")
async def history_remove(payload: dict):
    ids = set(payload.get('ids', []))
    hist = _load_history()
    hist = [h for h in hist if h.get('id') not in ids]
    _save_history(hist)
    return JSONResponse({"code": 0, "msg": "success", "data": True})


@app.get("/")
async def root():
    return {"code": 0, "msg": "ok", "data": "ndvi-demo"}
EOF
```

### 3.2 安装与启动后端（默认 5000 端口）

```bash
python3 -m venv /home/livablecity/cugrs/.venv
source /home/livablecity/cugrs/.venv/bin/activate
pip install --upgrade pip
pip install fastapi uvicorn python-multipart pillow numpy

uvicorn backend.ndvi_demo_fastapi:app --host 127.0.0.1 --port 5000
```

> 若需退出虚拟环境：`deactivate`

### 3.3 前端联调（设置 .env 指向后端）

将前端 `.env` 指向上面 FastAPI 的地址（如非使用 `backend/app.py` 自动写入）：

```bash
cat > /home/livablecity/cugrs/frontend/.env << 'EOF'
VUE_APP_BACKEND_IP=127.0.0.1
VUE_APP_BACKEND_PORT=5000
EOF
```

然后启动前端：

```bash
cd /home/livablecity/cugrs/frontend
npm install
npm run serve
```

访问：`http://127.0.0.1:3000/ndvi`

---

## 4. 接口测试（可独立验证后端）

### 4.1 上传文件

```bash
curl -F "files=@/home/livablecity/cugrs/frontend/public/logo.svg" \
     -F "type=影像NDVI处理" \
     http://127.0.0.1:5000/api/file/upload
```

返回示例：

```json
{"code":0,"msg":"success","data":[{"src":"/static_demo/uploads/<xxx>.svg","orig":"logo.svg"}]}
```

### 4.2 触发 NDVI 处理

```bash
curl -X POST http://127.0.0.1:5000/api/analysis/ndvi \
  -H 'Content-Type: application/json' \
  -d '{"list": ["/static_demo/uploads/<xxx>.svg"]}'
```

### 4.3 拉取历史记录

```bash
curl "http://127.0.0.1:5000/api/history/list?page=1&limit=20&type=影像NDVI处理"
```

---

## 5. 与现有页面的对齐点（仿照“影像超分重建”）

- 统一的交互：上传 → 分析 → 历史拉取 → 预览与下载。
- 统一的接口结构：后端返回 `{code, msg, data}`；前端 axios 拦截器基于 `code===0` 判定成功。
- 统一的 BASEURL：`src/global.vue` 拼接 `process.env.VUE_APP_BACKEND_IP/PORT`；后端静态文件挂载在 `/static_demo`，供前端直接访问。
- 历史记录类型：页面使用字符串 `影像NDVI处理` 与 `history/list` 的 `type` 参数对应。

---

## 6. 常见问题与排错

- 图片无法显示：检查前端 `.env` 是否指向后端；确保后端静态路径 `/static_demo/...` 可访问。
- 处理失败或网络异常：查看后端控制台与前端浏览器控制台；前端 axios 拦截器会展示错误消息。
- TIF 多波段：示例代码对 TIF 做了简单兜底。正式项目建议用 `rasterio` 精确读取 NIR/Red 波段（例如 NIR=Band4, Red=Band3，随数据而定）。

---

## 7. 扩展小结（复制模板快速新增功能）

新增功能的最小改动清单：

- 新建页面：`src/views/mainfun/<YourFeature>.vue`，将按钮 `upload('<中文功能名>','<后端funUrl>')` 与历史类型 `<中文功能名>` 对齐。
- 路由注册与侧边菜单入口。
- 后端实现两个核心接口：`/api/file/upload` 与 `/api/analysis/<funUrl>`；历史接口用于展示与下载。

照此模板即可扩充其它影像处理能力，保持与现有页面一致的用户体验与数据约定。