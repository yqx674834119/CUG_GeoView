const DEFAULT_PUBLIC_PREFIX = "/CUGGeoView";
const DEFAULT_ORIGIN_BASE = "https://livablecitylab.hkust-gz.edu.cn/Geoview";

export default {
  async fetch(request, env) {
    const publicPrefix = normalizePrefix(env.PUBLIC_PREFIX || DEFAULT_PUBLIC_PREFIX);
    const originBase = normalizeBase(env.ORIGIN_BASE || DEFAULT_ORIGIN_BASE);
    const url = new URL(request.url);

    if (url.pathname === publicPrefix.slice(0, -1)) {
      url.pathname = publicPrefix;
      return Response.redirect(url.toString(), 301);
    }

    if (!url.pathname.startsWith(publicPrefix)) {
      return new Response("GeoView proxy is available at " + publicPrefix, {
        status: 404,
        headers: {
          "content-type": "text/plain; charset=utf-8",
          "cache-control": "no-store"
        }
      });
    }

    const externalBase = `${url.protocol}//${url.host}${publicPrefix.slice(0, -1)}`;

    if (url.pathname === `${publicPrefix}runtime-config.js`) {
      return runtimeConfig(externalBase);
    }

    const originUrl = new URL(originBase);
    const suffix = url.pathname.slice(publicPrefix.length);
    originUrl.pathname = joinPath(originUrl.pathname, suffix);
    originUrl.search = url.search;

    const headers = new Headers(request.headers);
    headers.set("host", originUrl.host);
    headers.set("x-forwarded-host", url.host);
    headers.set("x-forwarded-proto", url.protocol.replace(":", ""));
    headers.set("x-forwarded-prefix", publicPrefix.slice(0, -1));

    const init = {
      method: request.method,
      headers,
      redirect: "manual"
    };

    if (request.method !== "GET" && request.method !== "HEAD") {
      init.body = request.body;
    }

    const response = await fetch(originUrl, init);
    return rewriteResponse(response, originBase, externalBase, publicPrefix);
  }
};

function runtimeConfig(externalBase) {
  const body = `window.__GEOVIEW_RUNTIME_CONFIG__ = {
  backendUrl: "${externalBase}",
  backendProtocol: "https",
  backendHost: "",
  backendPort: "",
  backendAssetMode: "sendfile",
  frontendAssetDebug: "false",
  frontendDebug: "false",
  minerEnabled: "false",
  minerUrl: "",
  baiduMapAccessKey: ""
};`;

  return new Response(body, {
    headers: {
      "content-type": "application/javascript; charset=utf-8",
      "cache-control": "no-store, no-cache, must-revalidate, proxy-revalidate"
    }
  });
}

async function rewriteResponse(response, originBase, externalBase, publicPrefix) {
  const headers = new Headers(response.headers);
  headers.delete("content-security-policy");
  headers.delete("content-security-policy-report-only");
  headers.delete("content-length");
  headers.set("access-control-allow-origin", "*");

  const location = headers.get("location");
  if (location) {
    headers.set("location", rewriteUrl(location, originBase, externalBase));
  }

  const contentType = headers.get("content-type") || "";
  if (isTextResponse(contentType)) {
    const body = rewriteBody(await response.text(), originBase, externalBase, publicPrefix);
    return new Response(body, {
      status: response.status,
      statusText: response.statusText,
      headers
    });
  }

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers
  });
}

function rewriteUrl(value, originBase, externalBase) {
  if (value.startsWith(originBase)) {
    return externalBase + value.slice(originBase.length);
  }
  const alternateOriginBase = originBase.startsWith("https://")
    ? originBase.replace("https://", "http://")
    : originBase.replace("http://", "https://");
  if (value.startsWith(alternateOriginBase)) {
    return externalBase + value.slice(alternateOriginBase.length);
  }
  return value;
}

function rewriteBody(body, originBase, externalBase, publicPrefix) {
  const alternateOriginBase = originBase.startsWith("https://")
    ? originBase.replace("https://", "http://")
    : originBase.replace("http://", "https://");

  const origin = new URL(originBase);
  const alternateOrigin = new URL(alternateOriginBase);
  const replacements = [
    [originBase, externalBase],
    [alternateOriginBase, externalBase],
    [`${origin.protocol}//${origin.host}`, externalBase],
    [`${alternateOrigin.protocol}//${alternateOrigin.host}`, externalBase],
    [origin.host, new URL(externalBase).host]
  ];

  let rewritten = body;
  for (const [from, to] of replacements) {
    rewritten = replaceAll(rewritten, from, to);
  }

  const cleanPrefix = publicPrefix.endsWith("/") ? publicPrefix.slice(0, -1) : publicPrefix;
  rewritten = rewritten.replace(/(["'=])\/(assets|api|static|favicon\.ico|runtime-config\.js)([/?#"'])/g, `$1${cleanPrefix}/$2$3`);
  return rewritten;
}

function isTextResponse(contentType) {
  return /text\/|application\/(javascript|json|x-javascript|xml)|image\/svg\+xml/.test(contentType);
}

function replaceAll(value, from, to) {
  return value.split(from).join(to);
}

function normalizePrefix(prefix) {
  const withLeadingSlash = prefix.startsWith("/") ? prefix : `/${prefix}`;
  return withLeadingSlash.endsWith("/") ? withLeadingSlash : `${withLeadingSlash}/`;
}

function normalizeBase(base) {
  return base.endsWith("/") ? base.slice(0, -1) : base;
}

function joinPath(basePath, suffix) {
  const cleanBase = basePath.endsWith("/") ? basePath.slice(0, -1) : basePath;
  const cleanSuffix = suffix.startsWith("/") ? suffix : `/${suffix}`;
  return `${cleanBase}${cleanSuffix}`;
}
