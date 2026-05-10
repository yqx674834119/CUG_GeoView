import { logFrontendDebug } from "@/utils/debugLog";

export function resolveUploadFile(item) {
  if (!item) {
    return null;
  }
  const file = item.raw || item;
  if (typeof Blob !== "undefined" && file instanceof Blob) {
    return file;
  }
  return null;
}

export function appendUploadFile(formData, item, scope = "文件上传") {
  const file = resolveUploadFile(item);
  if (!file) {
    logFrontendDebug(scope, "跳过非法上传项，避免 multipart 422", {
      itemKeys: item && typeof item === "object" ? Object.keys(item).slice(0, 20) : [],
      itemType: typeof item,
    }, { warn: true, always: true });
    return false;
  }
  formData.append("files", file);
  return true;
}

export function appendUploadFields(formData, fileList, type, options = {}) {
  let fileCount = 0;
  for (const item of fileList || []) {
    if (appendUploadFile(formData, item, options.scope)) {
      fileCount += 1;
    }
  }
  formData.append("type", type);
  if (Object.prototype.hasOwnProperty.call(options, "isSlice")) {
    formData.append("isSlice", String(Boolean(options.isSlice)));
  }
  logFrontendDebug(options.scope || "文件上传", "FormData 已标准化", {
    type,
    fileCount,
    isSlice: Object.prototype.hasOwnProperty.call(options, "isSlice") ? Boolean(options.isSlice) : undefined,
  }, { always: true });
  return formData;
}

export function buildUploadFormData(fileList, type, options = {}) {
  return appendUploadFields(new FormData(), fileList, type, options);
}
