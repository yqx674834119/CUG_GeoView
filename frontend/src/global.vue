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

function normalizeBaseUrl(url) {
  const value = String(url || "").trim();
  if (!value) {
    return "";
  }
  if (/^\/\//.test(value)) {
    const protocol = typeof window !== "undefined" ? window.location.protocol : "http:";
    return withTrailingSlash(`${protocol}${value}`);
  }
  if (/^https?:\/\//i.test(value) || value.startsWith("/")) {
    return withTrailingSlash(value);
  }
  return withTrailingSlash(`http://${value}`);
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
const storedBaseUrl = typeof window !== "undefined" ? window.localStorage.getItem("GEOVIEW_BACKEND_BASEURL") : "";
const storedChunkSize = typeof window !== "undefined" ? window.localStorage.getItem("GEOVIEW_RESULT_CHUNK_SIZE") : "";
const BASEURL = normalizeBaseUrl(storedBaseUrl) || resolveBackendBaseUrl(runtimeConfig);
const initialChunkSize = Number(storedChunkSize || runtimeConfig.resultChunkSize || 65536);
const RESULT_CHUNK_SIZE = Math.max(1024, Math.min(Number.isFinite(initialChunkSize) ? initialChunkSize : 65536, 262144));
const BACKEND_ASSET_MODE = resolveBackendAssetMode(runtimeConfig);
const FRONTEND_ASSET_DEBUG = resolveFrontendAssetDebug(runtimeConfig);
const MINER_ENABLED = resolveMinerEnabled(runtimeConfig);
const MINER_URL = resolveMinerUrl(runtimeConfig);
const BAIDU_MAP_ACCESS_KEY = resolveBaiduMapAccessKey(runtimeConfig);

const globalConfig = {
  BASEURL,
  RESULT_CHUNK_SIZE,
  BACKEND_ASSET_MODE,
  FRONTEND_ASSET_DEBUG,
  MINER_ENABLED,
  MINER_URL,
  BAIDU_MAP_ACCESS_KEY,
  setBackendBaseUrl(url) {
    const nextUrl = normalizeBaseUrl(url);
    if (!nextUrl) {
      return this.BASEURL;
    }
    this.BASEURL = nextUrl;
    if (typeof window !== "undefined") {
      window.localStorage.setItem("GEOVIEW_BACKEND_BASEURL", nextUrl);
      window.dispatchEvent(new CustomEvent("geoview-backend-baseurl-change", { detail: { baseUrl: nextUrl } }));
    }
    return nextUrl;
  },
  setResultChunkSize(size) {
    const nextSize = Math.max(1024, Math.min(Number(size) || this.RESULT_CHUNK_SIZE || 65536, 262144));
    this.RESULT_CHUNK_SIZE = nextSize;
    if (typeof window !== "undefined") {
      window.localStorage.setItem("GEOVIEW_RESULT_CHUNK_SIZE", String(nextSize));
      window.dispatchEvent(new CustomEvent("geoview-result-chunk-size-change", { detail: { chunkSize: nextSize } }));
    }
    return nextSize;
  },
};

export default globalConfig;
</script>
