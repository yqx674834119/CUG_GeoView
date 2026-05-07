import axios from "axios";

import global from "@/global";
import { toBackendAssetPreviewUrl } from "@/utils/backendAssetUrl";
import {
  availableDisplayModes,
  getDataTransport,
  getRecordTransport,
  getJsonRenderer,
  modeLabel,
  resolveDataSource,
  resolveJsonBaseSource,
  resolveRecordSource,
  supportsJsonMode,
} from "@/utils/mediaTransport";

const RUN_FLAG = "__GEOVIEW_STARTUP_DIAGNOSTICS_RAN__";
const HISTORY_PAGE_SIZE = 10;
const RECORD_FIELDS = ["before_img", "before_img1", "after_img"];
const CANDIDATE_DATA_FIELDS = ["mask", "mask_hole", "hole", "preview_path", "output_video_path"];

function logPrefix(scope) {
  return `[前端启动诊断][${scope}]`;
}

function summarizeDataUrl(value) {
  const text = String(value || "");
  if (!text.startsWith("data:")) {
    return text;
  }
  return {
    type: "data-url",
    length: text.length,
    prefix: text.slice(0, 48),
  };
}

function summarizeTransport(transport) {
  if (!transport) {
    return null;
  }
  return {
    kind: transport.kind || "",
    mimetype: transport.mimetype || "",
    relative_path: transport.relative_path || "",
    asset_path: transport.asset_path || "",
    original_url: transport.original_url || "",
    buffered_url: transport.buffered_url || "",
    preview_url: transport.preview_url || "",
    has_preview_data_url: Boolean(transport.preview_data_url),
    preview_data_url_length: String(transport.preview_data_url || "").length,
    supports_base64: Boolean(transport.supports_base64),
    modes: Array.isArray(transport.modes) ? transport.modes : [],
  };
}

function collectDataFields(record) {
  const data = record?.data;
  if (!data || typeof data !== "object") {
    return [];
  }

  const keys = new Set(CANDIDATE_DATA_FIELDS.filter((field) => data[field]));
  Object.keys(data).forEach((key) => {
    const value = data[key];
    if (typeof value === "string" && value) {
      keys.add(key);
    }
  });
  return Array.from(keys).slice(0, 8);
}

function buildFieldSnapshot(record, mode) {
  const snapshot = {};

  RECORD_FIELDS.forEach((field) => {
    const source = resolveRecordSource(record, field, mode);
    if (!source && !record?.[field]) {
      return;
    }
    snapshot[field] = {
      raw: record?.[field] || "",
      resolved: mode === "base64" ? summarizeDataUrl(source) : source,
      transport: summarizeTransport(getRecordTransport(record, field)),
      preview_api: toBackendAssetPreviewUrl(record?.[field] || ""),
    };
  });

  const dataFields = collectDataFields(record);
  if (dataFields.length) {
    snapshot.data = {};
    dataFields.forEach((field) => {
      const source = resolveDataSource(record, field, mode);
      snapshot.data[field] = {
        raw: record?.data?.[field],
        resolved: mode === "base64" ? summarizeDataUrl(source) : source,
        transport: summarizeTransport(getDataTransport(record, field)),
      };
    });
  }

  return snapshot;
}

function logModeSnapshot(record, mode) {
  const supportedModes = availableDisplayModes(record, RECORD_FIELDS);
  const enabled = supportedModes.includes(mode);
  const title = `${logPrefix("模式")} ${modeLabel(mode)} (${mode})`;

  console.groupCollapsed(title);
  console.log("模式可用:", enabled);
  console.log("后端声明的可视化模式:", Array.isArray(record?.visualization_modes) ? record.visualization_modes : []);
  if (mode === "json") {
    console.log("JSON 渲染器:", getJsonRenderer(record) || "未提供");
    console.log("JSON 模式是否受支持:", supportsJsonMode(record));
    console.log("JSON 基础底图:", resolveJsonBaseSource(record, "original") || "无");
    console.log("visual_payload 摘要:", {
      schema: record?.visual_payload?.schema || "",
      renderer: record?.visual_payload?.renderer || "",
      transport_modes: record?.visual_payload?.transport_modes || [],
      has_source: Boolean(record?.visual_payload?.source),
      has_result: Boolean(record?.visual_payload?.result),
    });
  } else {
    console.log("字段解析结果:", buildFieldSnapshot(record, mode));
  }
  console.groupEnd();
}

async function fetchRuntimeDiagnostics() {
  const runtimeDiagnosticsUrl = new URL("./runtime-diagnostics.json", window.location.href).toString();
  const response = await axios.get(runtimeDiagnosticsUrl, { timeout: 5000 });
  console.log(logPrefix("运行时"), {
    runtimeDiagnosticsUrl,
    payload: response.data,
  });
}

async function fetchHistorySample() {
  const url = `${String(global.BASEURL || "").replace(/\/+$/, "")}/api/history/list`;
  const response = await axios.get(url, {
    params: {
      page: 1,
      limit: HISTORY_PAGE_SIZE,
      type: "",
    },
    timeout: 10000,
  });

  const payload = response.data || {};
  const items = Array.isArray(payload.data) ? payload.data : [];

  console.log(logPrefix("历史记录"), {
    requestUrl: url,
    code: payload.code,
    count: payload.count,
    pageSize: items.length,
  });

  if (!items.length) {
    console.warn(logPrefix("历史记录"), "未找到历史记录，无法输出样例渲染模式。");
    return;
  }

  const record = items[0];
  console.groupCollapsed(`${logPrefix("样例记录")} 已选择最新一条历史记录`);
  console.log("记录摘要:", {
    id: record?.id,
    type: record?.type,
    create_time: record?.create_time,
    before_img: record?.before_img || "",
    before_img1: record?.before_img1 || "",
    after_img: record?.after_img || "",
    available_modes: availableDisplayModes(record, RECORD_FIELDS),
    backend_visualization_modes: record?.visualization_modes || [],
    json_renderer: getJsonRenderer(record) || "",
  });
  console.log("media_transports 摘要:", {
    before_img: summarizeTransport(getRecordTransport(record, "before_img")),
    before_img1: summarizeTransport(getRecordTransport(record, "before_img1")),
    after_img: summarizeTransport(getRecordTransport(record, "after_img")),
  });
  console.groupEnd();

  logModeSnapshot(record, "original");
  logModeSnapshot(record, "base64");
  logModeSnapshot(record, "json");
}

export async function runStartupDiagnostics() {
  if (typeof window === "undefined" || window[RUN_FLAG]) {
    return;
  }
  window[RUN_FLAG] = true;

  console.groupCollapsed(logPrefix("总览"));
  console.log("当前页面:", window.location.href);
  console.log("后端基础地址:", global.BASEURL);
  console.log("资源输出模式:", global.BACKEND_ASSET_MODE);
  console.log("前端资源调试开关:", global.FRONTEND_ASSET_DEBUG);
  console.log("运行时配置:", window.__GEOVIEW_RUNTIME_CONFIG__ || {});
  console.groupEnd();

  try {
    await fetchRuntimeDiagnostics();
  } catch (error) {
    console.warn(logPrefix("运行时"), "读取 runtime-diagnostics.json 失败:", error?.message || error);
  }

  try {
    await fetchHistorySample();
  } catch (error) {
    console.error(logPrefix("历史记录"), "请求历史记录失败:", {
      message: error?.message || String(error),
      response: error?.response?.data || null,
      status: error?.response?.status || null,
    });
  }
}
