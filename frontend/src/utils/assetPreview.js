import { fetchBackendAssetBlobUrl, getCachedBackendAssetBlobUrl } from "@/utils/assetChunkTransport";
import { isBackendPhotoAssetPath, toBackendAssetUrl } from "@/utils/backendAssetUrl";

export const ASSET_PREVIEW_PLACEHOLDER = "";

export function getBackendAssetPreviewDataUrl(path) {
  return fetchBackendAssetBlobUrl(path);
}

export async function setPreviewField(target, sourceField, previewField) {
  if (!target || !target[sourceField]) {
    return Promise.resolve("");
  }
  const source = target[sourceField];
  const url = isBackendPhotoAssetPath(source)
    ? (getCachedBackendAssetBlobUrl(source) || await awaitPreview(source, target, previewField || `${sourceField}_preview`))
    : toBackendAssetUrl(source);
  target[previewField || `${sourceField}_preview`] = url;
  return url;
}

function awaitPreview(source, target, field) {
  return fetchBackendAssetBlobUrl(source).then((url) => {
    target[field] = url;
    return url;
  });
}

export function hydrateAssetPreviews(target, fields) {
  if (!target || !fields) {
    return Promise.resolve(target);
  }
  if (Array.isArray(target)) {
    return Promise.all(target.map((item) => hydrateAssetPreviews(item, fields))).then(() => target);
  }
  const jobs = fields.map((field) => {
    if (typeof field === "string") {
      const source = target[field];
      const url = isBackendPhotoAssetPath(source)
        ? getCachedBackendAssetBlobUrl(source)
        : toBackendAssetUrl(source);
      target[`_${field}_preview`] = url;
      return isBackendPhotoAssetPath(source)
        ? awaitPreview(source, target, `_${field}_preview`)
        : Promise.resolve(url);
    }
    const object = field.object || target;
    const source = object[field.source];
    const url = isBackendPhotoAssetPath(source)
      ? getCachedBackendAssetBlobUrl(source)
      : toBackendAssetUrl(source);
    object[field.preview] = url;
    return isBackendPhotoAssetPath(source)
      ? awaitPreview(source, object, field.preview)
      : Promise.resolve(url);
  });
  return Promise.all(jobs).then(() => target);
}
