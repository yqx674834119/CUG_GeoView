import axios from "axios";

import { toBackendAssetPreviewUrl } from "@/utils/backendAssetUrl";
import { logFrontendDebug } from "@/utils/debugLog";

const previewCache = new Map();
export const ASSET_PREVIEW_PLACEHOLDER = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==";

function debugLog(event, payload = {}) {
  logFrontendDebug("图片预览", event, payload);
}

export function getBackendAssetPreviewDataUrl(path, maxSize = 420) {
  if (!path) {
    return Promise.resolve("");
  }

  const value = String(path);
  if (value.startsWith("data:") || value.startsWith("blob:")) {
    return Promise.resolve(value);
  }

  const previewUrl = toBackendAssetPreviewUrl(value, maxSize);
  if (!previewUrl) {
    debugLog("跳过预览请求：不是后端图片资源", { path: value, maxSize, reason: "not-backend-asset" });
    return Promise.reject(new Error("无法生成预览地址"));
  }

  const cacheKey = `${maxSize}:${previewUrl}`;
  if (previewCache.has(cacheKey)) {
    debugLog("命中预览缓存", { path: value, previewUrl, maxSize });
    return Promise.resolve(previewCache.get(cacheKey));
  }

  const startedAt = Date.now();
  debugLog("请求后端预览接口", { path: value, previewUrl, maxSize });
  return axios.get(previewUrl).then((response) => {
    const payload = response.data || {};
    if (payload.code !== 0 || !payload.data || !payload.data.data_url) {
      debugLog("预览接口返回失败", { path: value, previewUrl, maxSize, payload });
      throw new Error(payload.msg || "图片预览生成失败");
    }
    debugLog("预览接口返回成功", {
      path: value,
      previewUrl,
      maxSize,
      sourceStore: payload.data.source_store,
      originalSize: payload.data.original_size,
      previewSize: payload.data.preview_size,
      dataUrlLength: String(payload.data.data_url || "").length,
      durationMs: payload.data.duration_ms,
      frontendElapsedMs: Date.now() - startedAt,
      fallbackMisses: payload.data.fallback_misses,
    });
    previewCache.set(cacheKey, payload.data.data_url);
    return payload.data.data_url;
  }).catch((error) => {
    logFrontendDebug("图片预览", "预览接口请求异常", {
      path: value,
      previewUrl,
      maxSize,
      message: error?.message || String(error),
      status: error?.response?.status,
      response: error?.response?.data || null,
      frontendElapsedMs: Date.now() - startedAt,
    }, { error: true, always: true });
    throw error;
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
      debugLog("预览失败，使用透明占位图", {
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
