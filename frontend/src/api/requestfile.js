import axios from "axios";
import global from "@/global";
import { ElMessage } from "element-plus";
import { hideFullScreenLoading } from "@/utils/loading";

export function requestfile(config) {
  const instance = axios.create({ baseURL: global.BASEURL });
  instance.interceptors.request.use((requestConfig) => {
    requestConfig.baseURL = global.BASEURL;
    requestConfig.headers.Accept = "application/json";
    delete requestConfig.headers["Content-Type"];
    return requestConfig;
  });
  instance.interceptors.response.use(
    (response) => {
      if (response.data?.code !== 0 && response.data?.success !== true) {
        hideFullScreenLoading("#load");
        ElMessage.error(response.data?.msg || "上传失败");
        return Promise.reject(response);
      }
      return response;
    },
    (error) => {
      hideFullScreenLoading("#load");
      ElMessage.error(error?.response?.data?.msg || error?.message || "上传失败");
      return Promise.reject(error);
    },
  );
  return instance(config);
}
