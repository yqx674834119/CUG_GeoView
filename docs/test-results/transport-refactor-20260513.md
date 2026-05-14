# 传输架构重构测试报告

日期：2026-05-13

## 结论

- `/health` 已支持探测包大小，并可在前端右上角手动调节传输包大小。
- 分析接口首包已改为 `transport_manifest`，完整结果由 `/api/transport/result/<id>/chunk` 分片拉取。
- 前端浏览器页加载未再出现空图片报错。
- 镜像已构建并推送到阿里云。

## 交付物

- 后端镜像：`crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/cugrs:20260513-transport-v2`
- 前端镜像：`crpi-4r2gidb79yjyny4o.cn-hangzhou.personal.cr.aliyuncs.com/shawnyao/geoview-frontend:20260513-transport-v2`
- 前端 Helm 包：`deliverables/geoview-frontend-20260513-transport-v2.tgz`

## 已验证项

### 1. `/health` 探测

- 浏览器侧循环请求 `/health?payload_size=...`
- 探测范围：`1k -> 200k`
- 步长：`10k`
- 结果：稳定通过，最大稳定值写回右上角分片大小

截图：
- [health probe](/tmp/geoview_health_probe.png)

### 2. 前端页面空态与报错

已检查页面：
- `#/detectobjects`
- `#/registration`
- `#/tracking`

结果：
- 控制台无 `error` / `pageerror`
- 无额外图片请求
- 无 `image load failed`

截图：
- [detectobjects](/tmp/geoview___detectobjects.png)
- [registration](/tmp/geoview___registration.png)
- [tracking](/tmp/geoview___tracking.png)

### 3. 后端分片接口闭环

使用 Flask 测试客户端对 `change_detection` 进行 monkeypatch 验证：
- 首包返回 `transport_manifest`
- 分片接口 `/api/transport/result/<id>/chunk` 可继续拉取
- 重组后能恢复原始 JSON

结果：
- `analysis_status 200`
- `transport=chunked_result_v2`
- `chunk_route_status 200`

### 4. 受限项

本地直接跑真实模型时，当前 Python 环境的 Paddle/模型依赖与运行时不完全一致，真实 `TestData` 推理未在本机解释器里完整跑通；浏览器与传输闭环已验证，真实 GPU 容器建议在部署镜像里复测。
