<script>
function hasText(value) {
  return typeof value === "string" && value.trim() !== "";
}

function getRuntimeConfig() {
  if (typeof window === "undefined") {
    return {};
  }
  return window.__GEOVIEW_RUNTIME_CONFIG__ || {};
}

function withTrailingSlash(url) {
  return url.endsWith("/") ? url : `${url}/`;
}

function resolveBackendBaseUrl(runtimeConfig) {
  if (hasText(runtimeConfig.backendUrl)) {
    return withTrailingSlash(runtimeConfig.backendUrl.trim());
  }

  const envHost = process.env.VUE_APP_BACKEND_IP;
  const envPort = process.env.VUE_APP_BACKEND_PORT;
  const runtimeHost = hasText(runtimeConfig.backendHost)
    ? runtimeConfig.backendHost.trim()
    : (typeof window !== "undefined" ? window.location.hostname : envHost);
  const runtimePort = hasText(runtimeConfig.backendPort)
    ? runtimeConfig.backendPort.trim()
    : envPort;
  const runtimeProtocol = hasText(runtimeConfig.backendProtocol)
    ? runtimeConfig.backendProtocol.trim()
    : "http";

  if (hasText(runtimeHost) && hasText(runtimePort)) {
    return `${runtimeProtocol}://${runtimeHost}:${runtimePort}/`;
  }

  if (hasText(envHost) && hasText(envPort)) {
    return `http://${envHost}:${envPort}/`;
  }

  return "/";
}

function resolveMinerEnabled(runtimeConfig) {
  const rawValue = hasText(runtimeConfig.minerEnabled)
    ? runtimeConfig.minerEnabled
    : process.env.VUE_APP_MINER_ENABLED;
  return String(rawValue || "false").toLowerCase() === "true";
}

function resolveMinerUrl(runtimeConfig) {
  if (hasText(runtimeConfig.minerUrl)) {
    return runtimeConfig.minerUrl.trim();
  }
  return process.env.VUE_APP_MINER_URL || "http://localhost:4000";
}

function resolveBaiduMapAccessKey(runtimeConfig) {
  if (hasText(runtimeConfig.baiduMapAccessKey)) {
    return runtimeConfig.baiduMapAccessKey.trim();
  }
  return process.env.VUE_APP_BAIDU_MAP_ACCESS_KEY || "";
}

const runtimeConfig = getRuntimeConfig();
const BASEURL = resolveBackendBaseUrl(runtimeConfig);
const MINER_ENABLED = resolveMinerEnabled(runtimeConfig);
const MINER_URL = resolveMinerUrl(runtimeConfig);
const BAIDU_MAP_ACCESS_KEY = resolveBaiduMapAccessKey(runtimeConfig);

export default {
  BASEURL,
  MINER_ENABLED,
  MINER_URL,
  BAIDU_MAP_ACCESS_KEY,
};
</script>
