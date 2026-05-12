import { toBackendAssetUrl } from "@/utils/backendAssetUrl";

export const ASSET_PREVIEW_PLACEHOLDER = "";

export function getBackendAssetPreviewDataUrl(path) {
  return Promise.resolve(toBackendAssetUrl(path));
}

export function setPreviewField(target, sourceField, previewField) {
  if (!target || !target[sourceField]) {
    return Promise.resolve("");
  }
  const url = toBackendAssetUrl(target[sourceField]);
  target[previewField || `${sourceField}_preview`] = url;
  return Promise.resolve(url);
}

export function hydrateAssetPreviews(target, fields) {
  if (!target || !fields) {
    return Promise.resolve(target);
  }
  if (Array.isArray(target)) {
    return Promise.all(target.map((item) => hydrateAssetPreviews(item, fields))).then(() => target);
  }
  fields.forEach((field) => {
    if (typeof field === "string") {
      const url = toBackendAssetUrl(target[field]);
      target[`_${field}_preview`] = url;
      return;
    }
    const object = field.object || target;
    object[field.preview] = toBackendAssetUrl(object[field.source]);
  });
  return Promise.resolve(target);
}
