import axios from "axios";
import global from "@/global";
import { hideFullScreenLoading, showFullScreenLoading } from "@/utils/loading";
import { ElMessage } from "element-plus";
import { hydrateTransportResponse } from "@/utils/resultTransport";

export function request(config) {
  const instance = axios.create({ baseURL: global.BASEURL });
  instance.interceptors.request.use((requestConfig) => {
    requestConfig.baseURL = global.BASEURL;
    requestConfig.headers = requestConfig.headers || {};
    requestConfig.headers["X-Geoview-Chunk-Size"] = String(global.RESULT_CHUNK_SIZE || 65536);
    showFullScreenLoading();
    return requestConfig;
  });
  instance.interceptors.response.use(
    async (response) => {
      hideFullScreenLoading();
      if (response.data?.code !== 0 && response.data?.success !== true) {
        ElMessage.error(response.data?.msg || "请求失败");
        return Promise.reject(response);
      }
      return hydrateTransportResponse(response);
    },
    (error) => {
      hideFullScreenLoading();
      ElMessage.error(error?.response?.data?.msg || error?.message || "网络异常");
      return Promise.reject(error);
    },
  );
  return instance(config);
}
