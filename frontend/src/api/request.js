import axios from "axios"

import global from '@/global'
import {hideFullScreenLoading, showFullScreenLoading} from '@/utils/loading'
import {ElMessage} from "element-plus";
import { logFrontendDebug, summarizePayload } from "@/utils/debugLog";

export function request(config) {
  const instance = axios.create({
    baseURL:global.BASEURL
  })
    instance.interceptors.request.use(
        config=>{
            config.metadata = { startTime: Date.now() }
            logFrontendDebug("JSON请求", "准备发送请求", {
              method: (config.method || "get").toUpperCase(),
              baseURL: config.baseURL,
              url: config.url,
              params: config.params || {},
              payload: summarizePayload(config.data),
            })
            showFullScreenLoading()
            return config
        }
    )
  instance.interceptors.response.use(
    (response) => {
        hideFullScreenLoading()
      const elapsedMs = Date.now() - (response.config?.metadata?.startTime || Date.now())
      logFrontendDebug("JSON请求", "收到后端响应", {
        method: (response.config?.method || "get").toUpperCase(),
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
      })
      if(response.data.code!==0){
          ElMessage.error(response.data.msg)
        return Promise.reject()
      }
      return response
    },
    (error) => {
      hideFullScreenLoading()
      logFrontendDebug("JSON请求", "请求失败或网络异常", {
        message: error?.message || String(error),
        url: error?.config?.url,
        baseURL: error?.config?.baseURL,
        status: error?.response?.status,
        response: summarizePayload(error?.response?.data),
      }, { error: true, always: true })
      return Promise.reject(error || new Error('网络异常，请检查后端服务是否启动'))
    },
  )
  return instance(config)
}
