const DEFAULT_PUBLIC_PREFIX = "/CUGGeoView";
const DEFAULT_ORIGIN_BASE = "https://livablecitylab.hkust-gz.edu.cn/GeoView";

export default {
  async fetch(request, env) {
    const publicPrefix = normalizePrefix(env.PUBLIC_PREFIX || DEFAULT_PUBLIC_PREFIX);
    const originBase = normalizeBase(env.ORIGIN_BASE || DEFAULT_ORIGIN_BASE);
    const url = new URL(request.url);

    if (!matchesPrefix(url.pathname, publicPrefix)) {
      return new Response("GeoView redirect is available at " + publicPrefix, {
        status: 404,
        headers: {
          "content-type": "text/plain; charset=utf-8",
          "cache-control": "no-store"
        }
      });
    }

    const target = new URL(originBase);
    const suffix = getSuffix(url.pathname, publicPrefix);
    if (suffix) {
      target.pathname = joinPath(target.pathname, suffix);
    }
    target.search = url.search;
    target.hash = url.hash;

    return Response.redirect(target.toString(), 302);
  }
};

function matchesPrefix(pathname, publicPrefix) {
  const cleanPrefix = publicPrefix.slice(0, -1);
  return pathname === cleanPrefix || pathname.startsWith(publicPrefix);
}

function getSuffix(pathname, publicPrefix) {
  const cleanPrefix = publicPrefix.slice(0, -1);
  if (pathname === cleanPrefix || pathname === publicPrefix) {
    return "";
  }
  return pathname.slice(publicPrefix.length);
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
