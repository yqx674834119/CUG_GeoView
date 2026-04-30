import axios from "axios";

import { toBackendAssetPreviewUrl } from "@/utils/backendAssetUrl";
import global from "@/global";

const previewCache = new Map();
export const ASSET_PREVIEW_PLACEHOLDER = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==";

function debugLog(event, payload = {}) {
  if (global.FRONTEND_ASSET_DEBUG) {
    console.log(`[asset-preview] ${event}`, payload);
  }
}

export function getBackendAssetPreviewDataUrl(path, maxSize = 640) {
  if (!path) {
    return Promise.resolve("");
  }

  const value = String(path);
  if (value.startsWith("data:") || value.startsWith("blob:")) {
    return Promise.resolve(value);
  }

  const previewUrl = toBackendAssetPreviewUrl(value, maxSize);
  if (!previewUrl) {
    debugLog("skip", { path: value, maxSize, reason: "not-backend-asset" });
    return Promise.reject(new Error("无法生成预览地址"));
  }

  const cacheKey = `${maxSize}:${previewUrl}`;
  if (previewCache.has(cacheKey)) {
    debugLog("cache-hit", { path: value, previewUrl, maxSize });
    return Promise.resolve(previewCache.get(cacheKey));
  }

  debugLog("request", { path: value, previewUrl, maxSize });
  return axios.get(previewUrl).then((response) => {
    const payload = response.data || {};
    if (payload.code !== 0 || !payload.data || !payload.data.data_url) {
      debugLog("failure", { path: value, previewUrl, maxSize, payload });
      throw new Error(payload.msg || "图片预览生成失败");
    }
    debugLog("success", {
      path: value,
      previewUrl,
      maxSize,
      sourceStore: payload.data.source_store,
      originalSize: payload.data.original_size,
      previewSize: payload.data.preview_size,
      durationMs: payload.data.duration_ms,
      fallbackMisses: payload.data.fallback_misses,
    });
    previewCache.set(cacheKey, payload.data.data_url);
    return payload.data.data_url;
  });
}

export function setPreviewField(target, sourceField, previewField, maxSize = 420) {
  if (!target || !target[sourceField]) {
    return Promise.resolve("");
  }
  return getBackendAssetPreviewDataUrl(target[sourceField], maxSize)
    .then((dataUrl) => {
      target[previewField || `${sourceField}_preview`] = dataUrl;
      return dataUrl;
    })
    .catch((error) => {
      debugLog("fallback-placeholder", {
        path: target[sourceField],
        field: sourceField,
        maxSize,
        error: error && error.message,
      });
      target[previewField || `${sourceField}_preview`] = ASSET_PREVIEW_PLACEHOLDER;
      return ASSET_PREVIEW_PLACEHOLDER;
    });
}

export function hydrateAssetPreviews(target, fields, maxSize = 420) {
  if (!target || !fields) {
    return Promise.resolve(target);
  }

  if (Array.isArray(target)) {
    return Promise.all(target.map((item) => hydrateAssetPreviews(item, fields, maxSize)))
      .then(() => target);
  }

  const jobs = fields.map((field) => {
    if (typeof field === "string") {
      return setPreviewField(target, field, `_${field}_preview`, maxSize);
    }
    return setPreviewField(
      field.object || target,
      field.source,
      field.preview,
      field.maxSize || maxSize,
    );
  });

  return Promise.all(jobs).then(() => target);
}
