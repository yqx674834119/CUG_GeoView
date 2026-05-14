import global from "@/global";
import {
  backendAssetRelativePath,
  isBackendPhotoAssetPath,
  toBackendAssetUrl,
} from "@/utils/backendAssetUrl";

const blobUrlCache = new Map();
const blobPromiseCache = new Map();

function baseUrl() {
  return String(global.BASEURL || "").replace(/\/+$/, "");
}

function chunkSize() {
  return Number(global.RESULT_CHUNK_SIZE || 65536);
}

function decodeBase64(value) {
  const binary = window.atob(value || "");
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

function assetKey(path) {
  const relative = backendAssetRelativePath(path);
  return relative ? `${relative}|${chunkSize()}` : "";
}

function query(path, params = {}) {
  const search = new URLSearchParams();
  search.set("path", path);
  Object.keys(params).forEach((key) => search.set(key, params[key]));
  return search.toString();
}

export function getCachedBackendAssetBlobUrl(path) {
  const key = assetKey(path);
  return key ? (blobUrlCache.get(key) || "") : "";
}

export async function fetchBackendAssetBlob(path) {
  const relative = backendAssetRelativePath(path);
  if (!relative) {
    const response = await fetch(toBackendAssetUrl(path));
    if (!response.ok) {
      throw new Error(`asset fetch failed: ${response.status}`);
    }
    return response.blob();
  }

  const requestedLimit = chunkSize();
  const manifestUrl = `${baseUrl()}/api/transport/asset/manifest?${query(relative)}`;
  const manifestResponse = await fetch(manifestUrl, { headers: { Accept: "application/json" } });
  const manifestPayload = await manifestResponse.json();
  if (!manifestResponse.ok || manifestPayload?.success !== true) {
    throw new Error(manifestPayload?.msg || `asset manifest failed: ${manifestResponse.status}`);
  }

  const manifest = manifestPayload.data || {};
  const chunks = [];
  let offset = 0;
  let index = 0;
  console.groupCollapsed(`[GeoView][asset] receive ${relative}`);
  console.info("[GeoView][asset] manifest", manifest);

  while (offset < Number(manifest.size || 0)) {
    const url = `${baseUrl()}/api/transport/asset/chunk?${query(relative, {
      offset,
      limit: requestedLimit,
    })}`;
    const startedAt = performance.now();
    const response = await fetch(url, { headers: { Accept: "application/json" } });
    const text = await response.text();
    const payload = JSON.parse(text);
    if (!response.ok || payload?.success !== true) {
      console.groupEnd();
      throw new Error(payload?.msg || `asset chunk failed: ${response.status}`);
    }

    const data = payload.data || {};
    index += 1;
    chunks.push(decodeBase64(data.chunk || ""));
    console.info("[GeoView][asset] chunk", {
      index,
      offset,
      next_offset: data.next_offset,
      response_bytes: new Blob([text]).size,
      chunk_chars: String(data.chunk || "").length,
      limit: requestedLimit,
      duration_ms: Math.round(performance.now() - startedAt),
    });
    offset = Number(data.next_offset || offset);
    if (data.done || offset >= Number(manifest.size || 0)) {
      break;
    }
  }

  console.info("[GeoView][asset] completed", {
    chunks: index,
    size: manifest.size,
    mime: manifest.mime,
  });
  console.groupEnd();
  return new Blob(chunks, { type: manifest.mime || "application/octet-stream" });
}

export async function fetchBackendAssetBlobUrl(path) {
  if (!path) {
    return "";
  }
  if (!isBackendPhotoAssetPath(path)) {
    return toBackendAssetUrl(path);
  }

  const key = assetKey(path);
  if (blobUrlCache.has(key)) {
    return blobUrlCache.get(key);
  }
  if (blobPromiseCache.has(key)) {
    return blobPromiseCache.get(key);
  }

  const promise = fetchBackendAssetBlob(path)
    .then((blob) => {
      const url = window.URL.createObjectURL(blob);
      blobUrlCache.set(key, url);
      blobPromiseCache.delete(key);
      return url;
    })
    .catch((error) => {
      blobPromiseCache.delete(key);
      throw error;
    });
  blobPromiseCache.set(key, promise);
  return promise;
}
