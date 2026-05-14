import { fetchBackendAssetBlobUrl, getCachedBackendAssetBlobUrl } from "@/utils/assetChunkTransport";
import { isBackendPhotoAssetPath, toBackendAssetUrl } from "@/utils/backendAssetUrl";

export const DISPLAY_MODES = ["original"];

export function getTransportNode() {
  return null;
}

export function getRecordTransport() {
  return null;
}

export function getDataTransport() {
  return null;
}

export function resolveTransportSource(transport) {
  const value = transport?.asset_path || transport?.original_url || "";
  return isBackendPhotoAssetPath(value) ? getCachedBackendAssetBlobUrl(value) : toBackendAssetUrl(value);
}

export function resolveRecordSource(record, field) {
  const value = record?.[field] || "";
  return isBackendPhotoAssetPath(value) ? getCachedBackendAssetBlobUrl(value) : toBackendAssetUrl(value);
}

export function resolveDataSource(record, field) {
  const segments = String(field || "").split(".").filter(Boolean);
  let current = record?.data;
  for (const segment of segments) {
    current = current?.[segment];
  }
  const value = current || "";
  return isBackendPhotoAssetPath(value) ? getCachedBackendAssetBlobUrl(value) : toBackendAssetUrl(value);
}

export async function hydrateRecordSource(record, field) {
  const value = record?.[field] || "";
  if (!isBackendPhotoAssetPath(value)) {
    return toBackendAssetUrl(value);
  }
  return fetchBackendAssetBlobUrl(value);
}

export async function hydrateDataSource(record, field) {
  const segments = String(field || "").split(".").filter(Boolean);
  let current = record?.data;
  for (const segment of segments) {
    current = current?.[segment];
  }
  const value = current || "";
  if (!isBackendPhotoAssetPath(value)) {
    return toBackendAssetUrl(value);
  }
  return fetchBackendAssetBlobUrl(value);
}
