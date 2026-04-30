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
  const fallbackPort = "5008";

  if (hasText(runtimeHost) && hasText(runtimePort)) {
    return `${runtimeProtocol}://${runtimeHost}:${runtimePort}/`;
  }

  if (hasText(runtimeHost)) {
    return `${runtimeProtocol}://${runtimeHost}:${fallbackPort}/`;
  }

  if (hasText(envHost) && hasText(envPort)) {
    return `http://${envHost}:${envPort}/`;
  }

  return `http://127.0.0.1:${fallbackPort}/`;
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

function resolveBackendAssetMode(runtimeConfig) {
  if (hasText(runtimeConfig.backendAssetMode)) {
    return runtimeConfig.backendAssetMode.trim();
  }
  return "buffered";
}

function resolveFrontendAssetDebug(runtimeConfig) {
  const rawValue = hasText(runtimeConfig.frontendAssetDebug)
    ? runtimeConfig.frontendAssetDebug
    : process.env.VUE_APP_FRONTEND_ASSET_DEBUG;
  return String(rawValue || "false").toLowerCase() === "true";
}

function resolveBaiduMapAccessKey(runtimeConfig) {
  if (hasText(runtimeConfig.baiduMapAccessKey)) {
    return runtimeConfig.baiduMapAccessKey.trim();
  }
  return process.env.VUE_APP_BAIDU_MAP_ACCESS_KEY || "";
}

const runtimeConfig = getRuntimeConfig();
const BASEURL = resolveBackendBaseUrl(runtimeConfig);
const BACKEND_ASSET_MODE = resolveBackendAssetMode(runtimeConfig);
const FRONTEND_ASSET_DEBUG = resolveFrontendAssetDebug(runtimeConfig);
const MINER_ENABLED = resolveMinerEnabled(runtimeConfig);
const MINER_URL = resolveMinerUrl(runtimeConfig);
const BAIDU_MAP_ACCESS_KEY = resolveBaiduMapAccessKey(runtimeConfig);

export default {
  BASEURL,
  BACKEND_ASSET_MODE,
  FRONTEND_ASSET_DEBUG,
  MINER_ENABLED,
  MINER_URL,
  BAIDU_MAP_ACCESS_KEY,
};
</script>
