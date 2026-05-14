import global from "@/global";

function baseUrl() {
  return String(global.BASEURL || "").replace(/\/+$/, "");
}

function chunkSize() {
  return Number(global.RESULT_CHUNK_SIZE || 65536);
}

function decodeBase64(value) {
  const binary = window.atob(value || "");
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

async function gunzip(bytes) {
  if (typeof DecompressionStream === "undefined") {
    throw new Error("当前浏览器不支持 gzip 解压，请使用新版 Chrome/Edge 测试");
  }
  const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"));
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

export async function fetchTransportResult(manifest) {
  if (!manifest?.result_id) {
    return null;
  }

  const requestedLimit = chunkSize();
  let offset = 0;
  let encoded = "";
  let chunkIndex = 0;
  console.groupCollapsed(
    `[GeoView][transport] receive ${manifest.route || "analysis"} result_id=${manifest.result_id}`,
  );
  console.info("[GeoView][transport] manifest", manifest);

  while (offset < Number(manifest.encoded_size || 0)) {
    const url = `${baseUrl()}/api/transport/result/${manifest.result_id}/chunk?offset=${offset}&limit=${requestedLimit}`;
    const startedAt = performance.now();
    const response = await fetch(url, { headers: { Accept: "application/json" } });
    const payload = await response.json();
    if (!response.ok || payload?.success !== true) {
      console.groupEnd();
      throw new Error(payload?.msg || `分片请求失败 HTTP ${response.status}`);
    }

    const data = payload.data || {};
    const part = data.chunk || "";
    chunkIndex += 1;
    encoded += part;
    console.info("[GeoView][transport] chunk", {
      index: chunkIndex,
      offset,
      next_offset: data.next_offset,
      chars: part.length,
      limit: requestedLimit,
      duration_ms: Math.round(performance.now() - startedAt),
    });
    offset = Number(data.next_offset || offset + part.length);
    if (data.done) {
      break;
    }
  }

  const compressedBytes = decodeBase64(encoded);
  const jsonBytes = await gunzip(compressedBytes);
  const text = new TextDecoder("utf-8").decode(jsonBytes);
  const result = JSON.parse(text);
  console.info("[GeoView][transport] completed", {
    chunks: chunkIndex,
    encoded_size: encoded.length,
    decoded_bytes: jsonBytes.length,
  });
  console.groupEnd();
  return result;
}

export async function hydrateTransportResponse(response) {
  const manifest = response?.data?.data?.transport_manifest;
  if (!manifest) {
    return response;
  }
  const result = await fetchTransportResult(manifest);
  response.data.transport_manifest = manifest;
  response.data.data = result;
  return response;
}
