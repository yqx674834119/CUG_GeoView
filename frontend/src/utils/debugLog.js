import global from "@/global";

export function frontendDebugEnabled() {
  return Boolean(global.FRONTEND_ASSET_DEBUG);
}

export function summarizePayload(value) {
  if (!value) {
    return { type: typeof value };
  }
  if (typeof FormData !== "undefined" && value instanceof FormData) {
    const fields = [];
    value.forEach((fieldValue, key) => {
      if (fieldValue && typeof fieldValue === "object" && "name" in fieldValue) {
        fields.push({
          key,
          filename: fieldValue.name,
          size: fieldValue.size,
          type: fieldValue.type,
        });
      } else {
        fields.push({ key, value: String(fieldValue).slice(0, 80) });
      }
    });
    return { type: "FormData", fields };
  }
  if (typeof value === "string") {
    return value.startsWith("data:")
      ? { type: "data-url", length: value.length, prefix: value.slice(0, 64) }
      : { type: "string", length: value.length, preview: value.slice(0, 120) };
  }
  if (Array.isArray(value)) {
    return { type: "array", length: value.length };
  }
  if (typeof value === "object") {
    return { type: "object", keys: Object.keys(value).slice(0, 20) };
  }
  return { type: typeof value, value };
}

export function logFrontendDebug(scope, message, payload = {}, options = {}) {
  if (!options.always && !frontendDebugEnabled()) {
    return;
  }
  const prefix = `[GeoView前端调试][${scope}] ${message}`;
  if (options.warn) {
    console.warn(prefix, payload);
  } else if (options.error) {
    console.error(prefix, payload);
  } else {
    console.log(prefix, payload);
  }
}
