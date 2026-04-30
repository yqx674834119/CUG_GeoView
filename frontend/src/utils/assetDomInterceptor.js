import { isBackendPhotoAssetPath } from "@/utils/backendAssetUrl";
import {
  ASSET_PREVIEW_PLACEHOLDER,
  getBackendAssetPreviewDataUrl,
} from "@/utils/assetPreview";
import global from "@/global";

const INSTALL_FLAG = "__GEOVIEW_ASSET_IMAGE_INTERCEPTOR_INSTALLED__";
const imageState = new WeakMap();
let tokenSeed = 0;

function debugLog(event, payload = {}) {
  if (global.FRONTEND_ASSET_DEBUG) {
    console.log(`[asset-preview-dom] ${event}`, payload);
  }
}

function isPreviewViewerImage(element) {
  if (!element || typeof element.closest !== "function") {
    return false;
  }
  return Boolean(
    element.closest(".el-image-viewer__wrapper")
      || element.closest(".el-image-viewer__canvas")
      || element.classList?.contains("el-image-viewer__img"),
  );
}

function resolveMaxSize(element) {
  const explicit = Number(element?.getAttribute?.("data-geoview-preview-size"));
  if (Number.isFinite(explicit) && explicit > 0) {
    return explicit;
  }
  return isPreviewViewerImage(element) ? 1400 : 420;
}

function isSkippableSrc(value) {
  const text = String(value || "");
  return !text || text.startsWith("data:") || text.startsWith("blob:");
}

function nextToken(element) {
  const token = `${Date.now()}:${tokenSeed += 1}`;
  imageState.set(element, token);
  return token;
}

function isCurrent(element, token) {
  return imageState.get(element) === token;
}

export function installAssetImageInterceptor() {
  if (typeof window === "undefined" || typeof HTMLImageElement === "undefined") {
    return;
  }
  if (window[INSTALL_FLAG]) {
    return;
  }

  const srcDescriptor = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, "src");
  const nativeSetAttribute = HTMLImageElement.prototype.setAttribute;
  if (!srcDescriptor || typeof srcDescriptor.set !== "function") {
    debugLog("install-skip", { reason: "src descriptor unavailable" });
    return;
  }

  const nativeSetSrc = srcDescriptor.set;
  const nativeGetSrc = srcDescriptor.get;

  function assignNative(element, value) {
    nativeSetSrc.call(element, value);
  }

  function assignPreview(element, rawValue) {
    const value = String(rawValue || "");
    const token = nextToken(element);

    if (isSkippableSrc(value) || !isBackendPhotoAssetPath(value)) {
      assignNative(element, rawValue);
      return true;
    }

    const maxSize = resolveMaxSize(element);
    debugLog("intercept", { path: value, maxSize });
    assignNative(element, ASSET_PREVIEW_PLACEHOLDER);
    getBackendAssetPreviewDataUrl(value, maxSize)
      .then((dataUrl) => {
        if (!isCurrent(element, token)) {
          debugLog("stale-success", { path: value, maxSize });
          return;
        }
        assignNative(element, dataUrl || ASSET_PREVIEW_PLACEHOLDER);
        debugLog("applied", { path: value, maxSize });
      })
      .catch((error) => {
        if (!isCurrent(element, token)) {
          return;
        }
        assignNative(element, ASSET_PREVIEW_PLACEHOLDER);
        debugLog("fallback-placeholder", {
          path: value,
          maxSize,
          error: error && error.message,
        });
      });
    return true;
  }

  Object.defineProperty(HTMLImageElement.prototype, "src", {
    configurable: true,
    enumerable: srcDescriptor.enumerable,
    get: nativeGetSrc,
    set(value) {
      assignPreview(this, value);
    },
  });

  HTMLImageElement.prototype.setAttribute = function setAttribute(name, value) {
    if (String(name).toLowerCase() === "src") {
      assignPreview(this, value);
      return;
    }
    nativeSetAttribute.call(this, name, value);
  };

  window[INSTALL_FLAG] = true;
  debugLog("installed");
}
