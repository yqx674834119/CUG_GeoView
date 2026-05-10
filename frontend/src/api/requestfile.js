import axios from "axios"

import global from '@/global'
import {ElMessage} from "element-plus";
import {hideFullScreenLoading} from "@/utils/loading";
import { logFrontendDebug, summarizePayload } from "@/utils/debugLog";

function sanitizeMultipartData(data) {
  if (typeof FormData === "undefined" || !(data instanceof FormData)) {
    return data;
  }

  const files = data.getAll("files");
  if (files.length) {
    const validFiles = files.filter((item) => typeof Blob !== "undefined" && item instanceof Blob);
    const droppedCount = files.length - validFiles.length;
    data.delete("files");
    validFiles.forEach((file) => data.append("files", file));
    if (droppedCount > 0) {
      logFrontendDebug("文件上传", "已移除非法 files 字段，防止后端 422", {
        originalCount: files.length,
        validCount: validFiles.length,
        droppedCount,
      }, { warn: true, always: true });
    }
  }

  const typeValues = data.getAll("type").filter((value) => String(value || "").trim() !== "");
  if (typeValues.length > 1) {
    const latestType = typeValues[typeValues.length - 1];
    data.delete("type");
    data.append("type", latestType);
    logFrontendDebug("文件上传", "已合并重复 type 字段", {
      originalCount: typeValues.length,
      type: latestType,
    }, { warn: true, always: true });
  }

  const sliceValues = data.getAll("isSlice");
  if (sliceValues.length > 1) {
    const latestSlice = sliceValues[sliceValues.length - 1];
    data.delete("isSlice");
    data.append("isSlice", latestSlice);
    logFrontendDebug("文件上传", "已合并重复 isSlice 字段", {
      originalCount: sliceValues.length,
      isSlice: latestSlice,
    }, { warn: true, always: true });
  }

  return data;
}

export function requestfile(config) {
  const instance = axios.create({
    // timeout: 5000,
    baseURL: global.BASEURL,
  })
  instance.interceptors.request.use(
    (config) => {
        config.metadata = { startTime: Date.now() }
        config.data = sanitizeMultipartData(config.data)
        config.headers.Accept = 'application/json'
        delete config.headers['Content-Type']
        logFrontendDebug("文件上传", "准备发送 multipart 请求", {
          method: (config.method || "post").toUpperCase(),
          baseURL: config.baseURL,
          url: config.url,
          payload: summarizePayload(config.data),
        }, { always: true })
        return config
    },
    (error) => {
        logFrontendDebug("文件上传", "请求发送前失败", {
          message: error?.message || String(error),
        }, { error: true, always: true })
        return Promise.reject(error)
    },
  )

  instance.interceptors.response.use(
    (response) => {
        const elapsedMs = Date.now() - (response.config?.metadata?.startTime || Date.now())
        logFrontendDebug("文件上传", "收到上传响应", {
          url: response.config?.url,
          status: response.status,
          code: response.data?.code,
          msg: response.data?.msg,
          elapsedMs,
          responseHeaders: {
            contentLength: response.headers?.["content-length"],
            requestId: response.headers?.["x-geoview-request-id"],
          },
          payload: summarizePayload(response.data),
        }, { always: true })

        if(response.data.code!==0){
            hideFullScreenLoading('#load')
            ElMessage.error(response.data.msg)
            return Promise.reject()
        }
      return response
    },
    (error) => {
      logFrontendDebug("文件上传", "上传请求失败或网络断开", {
        message: error?.message || String(error),
        url: error?.config?.url,
        baseURL: error?.config?.baseURL,
        status: error?.response?.status,
        detail: error?.response?.data?.detail || null,
        response: summarizePayload(error?.response?.data),
      }, { error: true, always: true })
      return Promise.reject(error)
    },
  )
  return instance(config)
}
