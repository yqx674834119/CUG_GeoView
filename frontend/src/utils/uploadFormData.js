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
    console.warn(`[GeoView] ${scope}: invalid upload item skipped`);
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
  return formData;
}

export function buildUploadFormData(fileList, type, options = {}) {
  return appendUploadFields(new FormData(), fileList, type, options);
}
