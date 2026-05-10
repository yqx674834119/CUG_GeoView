# GeoView 轻量传输诊断后端

这些后端只用于集群传输诊断，不包含数据库和模型推理。5 个镜像暴露相同的 GeoView 前端兼容 API，但使用不同框架/传输实现，便于定位 `ERR_CONTENT_LENGTH_MISMATCH` 是否来自框架、GET 请求或集群网关。

## 镜像

- `geoview-lite-fastapi-chunked`
- `geoview-lite-flask-wsgi`
- `geoview-lite-quart-async`
- `geoview-lite-sanic-stream`
- `geoview-lite-aiohttp-raw`

默认端口均为 `5008`。

## 本机构建与测试

```bash
./lite_backends/build_all.sh 20260508-transferdiag1
./lite_backends/run_local_matrix.sh 20260508-transferdiag1
```

测试脚本会启动 5 个容器：

- FastAPI: `http://127.0.0.1:5101`
- Flask/Gunicorn: `http://127.0.0.1:5102`
- Quart/Hypercorn: `http://127.0.0.1:5103`
- Sanic: `http://127.0.0.1:5104`
- aiohttp: `http://127.0.0.1:5105`

前端只需要把 `BaseUrl` 改成其中一个地址即可对比。测试完成后如果要清理容器：

```bash
docker rm -f geoview-lite-fastapi-chunked-test geoview-lite-flask-wsgi-test geoview-lite-quart-async-test geoview-lite-sanic-stream-test geoview-lite-aiohttp-raw-test
```

## 已覆盖接口

- `/api/system/ping`
- `/api/history/list`
- `/api/model/list/{model_type}`
- `/api/model/huggingface/list`
- `/api/file/upload`
- `/api/file/upload-video-preview`
- `/api/file/assets/photos/{filename}`
- `/api/file/assets-buffered/photos/{filename}`
- `/_uploads/photos/{filename}`
- `/api/file/assets-preview/photos/{filename}`
- `/api/file/assets-transport/photos/{filename}`
- `/api/probe/method-asset/{filename}`，支持 `GET/POST/HEAD`，用于验证“GET 是否被集群网关截断”
- `/api/analysis/{route_name}`、`/api/analysis/tracking`、`/api/analysis/histogram_match`、`/api/analysis/image_pre`
- `/api/analysis/show/{type_name}`

## 推送到仓库

```bash
docker login crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com
REGISTRY_PREFIX=crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/ ./lite_backends/build_all.sh 20260508-transferdiag1
REGISTRY_PREFIX=crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/ ./lite_backends/push_all.sh 20260508-transferdiag1
```

## 常用环境变量

- `PORT`: 服务端口，默认 `5008`
- `GEOVIEW_TRANSFER_MODE`: `chunked`、`buffered`、`ranged`，默认 `chunked`
- `GEOVIEW_OMIT_CONTENT_LENGTH`: 非 Range 响应是否省略 `Content-Length`，默认 `true`
- `GEOVIEW_CHUNK_SIZE`: 分块大小，默认 `65536`
- `GEOVIEW_DEBUG_LOG`: 是否输出中文 debug，默认 `true`
