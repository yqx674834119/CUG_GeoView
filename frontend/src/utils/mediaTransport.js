import { toBackendAssetUrl } from "@/utils/backendAssetUrl";

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
  return toBackendAssetUrl(transport?.asset_path || transport?.original_url || "");
}

export function resolveRecordSource(record, field) {
  return toBackendAssetUrl(record?.[field] || "");
}

export function resolveDataSource(record, field) {
  const segments = String(field || "").split(".").filter(Boolean);
  let current = record?.data;
  for (const segment of segments) {
    current = current?.[segment];
  }
  return toBackendAssetUrl(current || "");
}
