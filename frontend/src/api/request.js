import axios from "axios";
import global from "@/global";
import { hideFullScreenLoading, showFullScreenLoading } from "@/utils/loading";
import { ElMessage } from "element-plus";

export function request(config) {
  const instance = axios.create({ baseURL: global.BASEURL });
  instance.interceptors.request.use((requestConfig) => {
    requestConfig.baseURL = global.BASEURL;
    showFullScreenLoading();
    return requestConfig;
  });
  instance.interceptors.response.use(
    (response) => {
      hideFullScreenLoading();
      if (response.data?.code !== 0 && response.data?.success !== true) {
        ElMessage.error(response.data?.msg || "请求失败");
        return Promise.reject(response);
      }
      return response;
    },
    (error) => {
      hideFullScreenLoading();
      ElMessage.error(error?.response?.data?.msg || error?.message || "网络异常");
      return Promise.reject(error);
    },
  );
  return instance(config);
}
