import { toBackendAssetUrl } from "@/utils/backendAssetUrl";
import { getLocalSourceUrl } from "@/utils/localSourceRegistry";

export const DISPLAY_MODES = ["original", "base64", "json"];
export const JSON_RENDERERS = new Set([
  "object_detection",
  "semantic_segmentation",
  "registration",
  "change_detection",
  "tracking",
  "scene_classification",
  "image_restoration",
]);

function isObject(value) {
  return value && typeof value === "object" && !Array.isArray(value);
}

function normalizeResolvedValue(value) {
  return typeof value === "string" ? toBackendAssetUrl(value) : (value || "");
}

export function getTransportNode(target, path) {
  const segments = Array.isArray(path)
    ? path
    : String(path || "")
      .split(".")
      .filter(Boolean);
  let current = target;
  for (const segment of segments) {
    if (current == null) {
      return null;
    }
    current = current[segment];
  }
  return current || null;
}

export function getRecordTransport(record, field) {
  if (!record || !field) {
    return null;
  }
  return getTransportNode(record?.media_transports, field);
}

export function getDataTransport(record, field) {
  if (!record || !field) {
    return null;
  }
  return getTransportNode(record?.media_transports, ["data", ...String(field).split(".")]);
}

export function resolveTransportSource(transport, mode = "original") {
  if (!transport) {
    return "";
  }
  if (mode === "base64" && transport.preview_data_url) {
    return transport.preview_data_url;
  }
  return normalizeResolvedValue(transport.original_url || transport.buffered_url || transport.asset_path || "");
}

export function resolveRecordSource(record, field, mode = "original") {
  const transport = getRecordTransport(record, field);
  if (transport) {
    return resolveTransportSource(transport, mode);
  }
  return normalizeResolvedValue(record?.[field] || "");
}

export function resolveDataSource(record, field, mode = "original") {
  const transport = getDataTransport(record, field);
  if (transport && isObject(transport) && (transport.original_url || transport.preview_data_url || transport.asset_path)) {
    return resolveTransportSource(transport, mode);
  }
  return normalizeResolvedValue(getTransportNode(record?.data, field) || "");
}

export function getJsonRenderer(record) {
  return record?.visual_payload?.renderer || "";
}

export function supportsJsonMode(record) {
  return JSON_RENDERERS.has(getJsonRenderer(record));
}

export function availableDisplayModes(record, fields = ["before_img", "after_img"]) {
  const base = ["original"];
  const hasBase64 = fields.some((field) => {
    const transport = field.startsWith("data.")
      ? getDataTransport(record, field.slice("data.".length))
      : getRecordTransport(record, field);
    return transport?.preview_data_url;
  });
  if (hasBase64) {
    base.push("base64");
  }
  if (supportsJsonMode(record)) {
    base.push("json");
  }
  return base;
}

export function normalizeDisplayMode(currentMode, availableModes = ["original"]) {
  if (availableModes.includes(currentMode)) {
    return currentMode;
  }
  if (availableModes.includes("original")) {
    return "original";
  }
  return availableModes[0] || "original";
}

export function resolveJsonBaseSource(record, preferredMode = "base64") {
  const assetPath = record?.visual_payload?.source?.primary?.asset_path || record?.before_img || "";
  const localSource = getLocalSourceUrl(assetPath);
  if (localSource) {
    return localSource;
  }

  const sourceTransport = record?.visual_payload?.source?.primary?.transport;
  if (sourceTransport) {
    return resolveTransportSource(sourceTransport, preferredMode);
  }
  const mainTransport = getRecordTransport(record, "before_img");
  if (mainTransport) {
    return resolveTransportSource(mainTransport, preferredMode);
  }
  return normalizeResolvedValue(assetPath);
}

export function modeLabel(mode) {
  if (mode === "original") {
    return "原始图像/视频";
  }
  if (mode === "base64") {
    return "备用 Base64";
  }
  return "JSON 前端可视化";
}
