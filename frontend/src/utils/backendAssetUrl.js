import global from "@/global";

function isAbsoluteUrl(value) {
  return /^(https?:)?\/\//i.test(value) || value.startsWith("data:") || value.startsWith("blob:");
}

function normalizeBackendAssetPath(value) {
  if (typeof value !== "string") {
    return value;
  }

  if (value.startsWith("/_uploads/photos/")) {
    return `/api/file/assets/photos/${value.slice("/_uploads/photos/".length)}`;
  }

  if (value.startsWith("/static/upload/")) {
    return `/api/file/assets/photos/${value.slice("/static/upload/".length)}`;
  }

  const staticUploadMarker = "/static/upload/";
  const staticUploadIndex = value.indexOf(staticUploadMarker);
  if (staticUploadIndex >= 0) {
    return `/api/file/assets/photos/${value.slice(staticUploadIndex + staticUploadMarker.length)}`;
  }

  return value;
}

function applyAssetMode(path) {
  if (global.BACKEND_ASSET_MODE !== "buffered") {
    return path;
  }

  if (path.startsWith("/api/file/assets/photos/")) {
    return `/api/file/assets-buffered/photos/${path.slice("/api/file/assets/photos/".length)}`;
  }

  return path;
}

export function toBackendAssetUrl(path) {
  if (!path) {
    return "";
  }

  const value = applyAssetMode(normalizeBackendAssetPath(String(path)));
  if (isAbsoluteUrl(value)) {
    return value;
  }

  const base = String(global.BASEURL || "").replace(/\/+$/, "");
  const suffix = value.replace(/^\/+/, "");

  if (!base) {
    return suffix ? `/${suffix}` : "";
  }

  return suffix ? `${base}/${suffix}` : base;
}
