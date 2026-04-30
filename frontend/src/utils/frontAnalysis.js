import axios from "axios";

import { getBackendAssetPreviewDataUrl } from "@/utils/assetPreview";
import { toBackendAssetUrl } from "@/utils/backendAssetUrl";

const CLASSIFICATION_TOP_N = 5;
const SEGMENTATION_PREVIEW_SIZE = 320;
const IMAGE_PREVIEW_SIZE = 360;

const PADDLE_SEGMENTATION_CLASSES = [
  { key: "cloud", name: "云", rgb: [0, 0, 0] },
  { key: "shadow", name: "阴影", rgb: [128, 0, 0] },
  { key: "snow", name: "雪", rgb: [0, 128, 0] },
  { key: "water", name: "水体", rgb: [128, 128, 0] },
  { key: "land", name: "陆地", rgb: [0, 0, 128] },
];

const MMSEG_SEGMENTATION_CLASSES = [
  { key: "grassland", name: "草地", rgb: [0, 255, 0] },
  { key: "forest", name: "林地", rgb: [0, 128, 0] },
  { key: "building", name: "建筑", rgb: [255, 0, 0] },
  { key: "road", name: "道路", rgb: [255, 255, 0] },
  { key: "bareground", name: "裸地", rgb: [255, 0, 255] },
  { key: "water", name: "水体", rgb: [0, 191, 255] },
];

function round(value, digits = 2) {
  if (!Number.isFinite(Number(value))) {
    return 0;
  }
  const factor = 10 ** digits;
  return Math.round(Number(value) * factor) / factor;
}

function createCanvas(width, height) {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  return canvas;
}

function luminance(r, g, b) {
  return 0.299 * r + 0.587 * g + 0.114 * b;
}

function normalizedPercent(numerator, denominator) {
  if (!denominator) {
    return 0;
  }
  return round((numerator / denominator) * 100, 2);
}

async function resolveImageSource(source, maxSize) {
  if (!source) {
    return "";
  }
  const value = String(source);
  if (value.startsWith("data:") || value.startsWith("blob:")) {
    return value;
  }
  try {
    return await getBackendAssetPreviewDataUrl(value, maxSize);
  } catch (error) {
    return toBackendAssetUrl(value);
  }
}

function loadImageElement(source) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = source;
  });
}

async function loadImagePixels(source, maxSize = IMAGE_PREVIEW_SIZE) {
  const resolvedSource = await resolveImageSource(source, maxSize);
  if (!resolvedSource) {
    throw new Error("无法加载图像");
  }

  const img = await loadImageElement(resolvedSource);
  const scale = Math.min(1, maxSize / Math.max(img.naturalWidth || 1, img.naturalHeight || 1));
  const width = Math.max(1, Math.round((img.naturalWidth || 1) * scale));
  const height = Math.max(1, Math.round((img.naturalHeight || 1) * scale));
  const canvas = createCanvas(width, height);
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  ctx.drawImage(img, 0, 0, width, height);
  const imageData = ctx.getImageData(0, 0, width, height);

  return {
    source: resolvedSource,
    originalWidth: img.naturalWidth || width,
    originalHeight: img.naturalHeight || height,
    width,
    height,
    data: imageData.data,
  };
}

function computeEntropy(histogram, total) {
  if (!total) {
    return 0;
  }
  let entropy = 0;
  for (const count of histogram) {
    if (!count) {
      continue;
    }
    const probability = count / total;
    entropy -= probability * Math.log2(probability);
  }
  return round(entropy, 3);
}

function computeLaplacianVariance(gray, width, height) {
  if (width < 3 || height < 3) {
    return 0;
  }
  let sum = 0;
  let sumSquares = 0;
  let count = 0;

  for (let y = 1; y < height - 1; y += 1) {
    for (let x = 1; x < width - 1; x += 1) {
      const idx = y * width + x;
      const value = (4 * gray[idx]) - gray[idx - 1] - gray[idx + 1] - gray[idx - width] - gray[idx + width];
      sum += value;
      sumSquares += value * value;
      count += 1;
    }
  }

  if (!count) {
    return 0;
  }

  const mean = sum / count;
  return round((sumSquares / count) - (mean * mean), 2);
}

function computeEdgeDensity(gray, width, height) {
  if (width < 3 || height < 3) {
    return 0;
  }

  let edgeCount = 0;
  let total = 0;
  for (let y = 1; y < height - 1; y += 1) {
    for (let x = 1; x < width - 1; x += 1) {
      const idx = y * width + x;
      const gx = gray[idx + 1] - gray[idx - 1];
      const gy = gray[idx + width] - gray[idx - width];
      const magnitude = Math.sqrt((gx * gx) + (gy * gy));
      if (magnitude > 24) {
        edgeCount += 1;
      }
      total += 1;
    }
  }

  return normalizedPercent(edgeCount, total);
}

export function computeImageMetrics(pixelSource) {
  const { data, width, height, originalWidth, originalHeight } = pixelSource;
  const totalPixels = width * height;
  if (!totalPixels) {
    return null;
  }

  const gray = new Float32Array(totalPixels);
  const histogram = new Array(32).fill(0);
  let sum = 0;
  let sumSquares = 0;
  let min = 255;
  let max = 0;

  for (let i = 0; i < totalPixels; i += 1) {
    const offset = i * 4;
    const value = luminance(data[offset], data[offset + 1], data[offset + 2]);
    gray[i] = value;
    sum += value;
    sumSquares += value * value;
    min = Math.min(min, value);
    max = Math.max(max, value);
    histogram[Math.min(31, Math.floor((value / 256) * 32))] += 1;
  }

  const mean = sum / totalPixels;
  const variance = Math.max(0, (sumSquares / totalPixels) - (mean * mean));

  return {
    width: originalWidth || width,
    height: originalHeight || height,
    megapixels: round(((originalWidth || width) * (originalHeight || height)) / 1000000, 3),
    brightness: round(mean, 2),
    contrast: round(Math.sqrt(variance), 2),
    dynamicRange: round(max - min, 2),
    entropy: computeEntropy(histogram, totalPixels),
    edgeDensity: computeEdgeDensity(gray, width, height),
    sharpness: computeLaplacianVariance(gray, width, height),
  };
}

function sortedEntries(dataObject) {
  return Object.entries(dataObject || {})
    .map(([name, score]) => ({
      name,
      score: Number(score) || 0,
    }))
    .sort((a, b) => b.score - a.score);
}

function scoreEntropy(entries) {
  const total = entries.reduce((sum, entry) => sum + entry.score, 0);
  if (!total) {
    return 0;
  }
  let entropy = 0;
  entries.forEach((entry) => {
    if (!entry.score) {
      return;
    }
    const probability = entry.score / total;
    entropy -= probability * Math.log2(probability);
  });
  return round(entropy, 3);
}

export function analyzeClassificationRecord(item) {
  const entries = sortedEntries(item?.data || {});
  const topEntries = entries.slice(0, CLASSIFICATION_TOP_N).map((entry) => ({
    ...entry,
    percent: round(entry.score * 100, 2),
  }));
  const top1 = entries[0] || { name: "未知", score: 0 };
  const top2 = entries[1] || { name: "未知", score: 0 };
  const highConfidenceCount = entries.filter((entry) => entry.score >= 0.7).length;
  const mediumConfidenceCount = entries.filter((entry) => entry.score >= 0.4 && entry.score < 0.7).length;
  const lowConfidenceCount = entries.filter((entry) => entry.score < 0.4).length;

  return {
    kind: "classification",
    topLabel: top1.name,
    topScore: round(top1.score * 100, 2),
    confidenceMargin: round((top1.score - top2.score) * 100, 2),
    entropy: scoreEntropy(entries),
    topEntries,
    confidenceBands: [
      { name: "高置信", value: highConfidenceCount },
      { name: "中置信", value: mediumConfidenceCount },
      { name: "低置信", value: lowConfidenceCount },
    ],
  };
}

export function summarizeClassification(items) {
  const analyzed = items.map((item) => analyzeClassificationRecord(item));
  const labelCounter = new Map();
  const scoreAccumulator = new Map();
  let avgTopScore = 0;
  let avgMargin = 0;
  let avgEntropy = 0;

  analyzed.forEach((analysis) => {
    avgTopScore += analysis.topScore;
    avgMargin += analysis.confidenceMargin;
    avgEntropy += analysis.entropy;
    labelCounter.set(analysis.topLabel, (labelCounter.get(analysis.topLabel) || 0) + 1);
    analysis.topEntries.forEach((entry) => {
      scoreAccumulator.set(entry.name, (scoreAccumulator.get(entry.name) || 0) + entry.percent);
    });
  });

  const count = analyzed.length || 1;
  return {
    kind: "classification",
    sampleCount: analyzed.length,
    avgTopScore: round(avgTopScore / count, 2),
    avgMargin: round(avgMargin / count, 2),
    avgEntropy: round(avgEntropy / count, 3),
    dominantLabels: Array.from(labelCounter.entries())
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value),
    averageScores: Array.from(scoreAccumulator.entries())
      .map(([name, value]) => ({ name, value: round(value / count, 2) }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 8),
  };
}

function getDetectionPayload(item) {
  return item?.visual_payload || item?.data?.__visual_payload || {};
}

function getDetections(item) {
  const payload = getDetectionPayload(item);
  return Array.isArray(payload?.result?.detections) ? payload.result.detections : [];
}

function getDetectionImageSize(item) {
  const payload = getDetectionPayload(item);
  return payload?.result?.image_size || {};
}

function polygonArea(points) {
  if (!Array.isArray(points) || points.length < 3) {
    return 0;
  }
  let sum = 0;
  for (let i = 0; i < points.length; i += 1) {
    const current = points[i] || [0, 0];
    const next = points[(i + 1) % points.length] || [0, 0];
    sum += (Number(current[0]) * Number(next[1])) - (Number(next[0]) * Number(current[1]));
  }
  return Math.abs(sum) / 2;
}

function detectionQuadrant(xRatio, yRatio) {
  if (xRatio < 0.5 && yRatio < 0.5) {
    return "左上";
  }
  if (xRatio >= 0.5 && yRatio < 0.5) {
    return "右上";
  }
  if (xRatio < 0.5 && yRatio >= 0.5) {
    return "左下";
  }
  return "右下";
}

function confidenceBand(score) {
  if (score >= 0.8) {
    return "高置信";
  }
  if (score >= 0.5) {
    return "中置信";
  }
  return "低置信";
}

function sizeBand(areaRatioPercent) {
  if (areaRatioPercent < 0.5) {
    return "微小目标";
  }
  if (areaRatioPercent < 2) {
    return "小目标";
  }
  if (areaRatioPercent < 8) {
    return "中目标";
  }
  return "大目标";
}

function accumulateCounter(target, key) {
  target.set(key, (target.get(key) || 0) + 1);
}

function mapToSortedArray(counter) {
  return Array.from(counter.entries())
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);
}

function normalizeDetection(item, detection, index, imageArea, imageWidth, imageHeight) {
  const polygon = Array.isArray(detection?.polygon) ? detection.polygon : [];
  const box = Array.isArray(detection?.box) ? detection.box : [];
  const fallbackWidth = Math.max(1, Number(imageWidth) || 1);
  const fallbackHeight = Math.max(1, Number(imageHeight) || 1);
  let x1 = 0;
  let y1 = 0;
  let x2 = 0;
  let y2 = 0;

  if (box.length >= 4) {
    [x1, y1, x2, y2] = box.map((value) => Number(value) || 0);
  } else if (polygon.length >= 3) {
    const xs = polygon.map((point) => Number(point?.[0]) || 0);
    const ys = polygon.map((point) => Number(point?.[1]) || 0);
    x1 = Math.min(...xs);
    y1 = Math.min(...ys);
    x2 = Math.max(...xs);
    y2 = Math.max(...ys);
  }

  const width = Math.max(0, x2 - x1);
  const height = Math.max(0, y2 - y1);
  const rawArea = polygon.length >= 3 ? polygonArea(polygon) : width * height;
  const areaRatioPercent = normalizedPercent(rawArea, imageArea);
  const centerX = x1 + (width / 2);
  const centerY = y1 + (height / 2);
  const centerXRatio = centerX / fallbackWidth;
  const centerYRatio = centerY / fallbackHeight;
  const score = Number(detection?.score) || 0;
  const label = detection?.label || "未命名目标";

  return {
    id: `${item?.id ?? "result"}-${index + 1}`,
    label,
    score,
    scorePercent: round(score * 100, 2),
    area: round(rawArea, 2),
    areaRatioPercent,
    width: round(width, 2),
    height: round(height, 2),
    aspectRatio: height ? round(width / height, 2) : 0,
    centerXRatio,
    centerYRatio,
    quadrant: detectionQuadrant(centerXRatio, centerYRatio),
    confidenceBand: confidenceBand(score),
    sizeBand: sizeBand(areaRatioPercent),
  };
}

function createBandRows(counter, order) {
  return order.map((name) => ({
    name,
    value: counter.get(name) || 0,
  }));
}

export function analyzeDetectionRecord(item) {
  const detections = getDetections(item);
  const imageSize = getDetectionImageSize(item);
  const imageWidth = Number(imageSize?.width) || 0;
  const imageHeight = Number(imageSize?.height) || 0;
  const imageArea = Math.max(1, imageWidth * imageHeight);
  const normalized = detections.map((detection, index) => normalizeDetection(
    item,
    detection,
    index,
    imageArea,
    imageWidth,
    imageHeight,
  ));

  const labelCounter = new Map();
  const confidenceCounter = new Map();
  const sizeCounter = new Map();
  const quadrantCounter = new Map();
  let totalScore = 0;
  let totalAreaRatio = 0;

  normalized.forEach((detection) => {
    accumulateCounter(labelCounter, detection.label);
    accumulateCounter(confidenceCounter, detection.confidenceBand);
    accumulateCounter(sizeCounter, detection.sizeBand);
    accumulateCounter(quadrantCounter, detection.quadrant);
    totalScore += detection.scorePercent;
    totalAreaRatio += detection.areaRatioPercent;
  });

  const count = normalized.length || 1;
  const labelStats = mapToSortedArray(labelCounter);
  const topDetection = [...normalized].sort((a, b) => b.score - a.score)[0] || null;

  return {
    kind: "detection",
    detectionCount: normalized.length,
    imageWidth,
    imageHeight,
    imageMegapixels: round((imageWidth * imageHeight) / 1000000, 3),
    avgConfidence: round(totalScore / count, 2),
    avgAreaRatio: round(totalAreaRatio / count, 2),
    dominantLabel: labelStats[0]?.name || "暂无",
    dominantLabelCount: labelStats[0]?.value || 0,
    labelStats,
    confidenceBands: createBandRows(confidenceCounter, ["高置信", "中置信", "低置信"]),
    sizeBands: createBandRows(sizeCounter, ["微小目标", "小目标", "中目标", "大目标"]),
    quadrantStats: createBandRows(quadrantCounter, ["左上", "右上", "左下", "右下"]),
    topDetections: [...normalized]
      .sort((a, b) => b.score - a.score)
      .slice(0, 8)
      .map((detection) => ({
        name: `${detection.label} ${detection.id.split("-").pop()}`,
        value: detection.scorePercent,
      })),
    detections: normalized,
    topDetection,
    detectionDensity: round(normalized.length / Math.max(1, (imageWidth * imageHeight) / 1000000), 2),
  };
}

export function summarizeDetection(items, analyses) {
  const labelCounter = new Map();
  const confidenceCounter = new Map();
  const sizeCounter = new Map();
  let totalDetections = 0;
  let totalConfidence = 0;
  let totalAreaRatio = 0;

  analyses.forEach((analysis, index) => {
    totalDetections += analysis.detectionCount;
    totalConfidence += analysis.avgConfidence * analysis.detectionCount;
    totalAreaRatio += analysis.avgAreaRatio * analysis.detectionCount;
    analysis.labelStats.forEach((entry) => {
      labelCounter.set(entry.name, (labelCounter.get(entry.name) || 0) + entry.value);
    });
    analysis.confidenceBands.forEach((entry) => {
      confidenceCounter.set(entry.name, (confidenceCounter.get(entry.name) || 0) + entry.value);
    });
    analysis.sizeBands.forEach((entry) => {
      sizeCounter.set(entry.name, (sizeCounter.get(entry.name) || 0) + entry.value);
    });
  });

  const sampleCount = analyses.length;
  const safeDetectionCount = totalDetections || 1;
  const labelStats = mapToSortedArray(labelCounter);

  return {
    kind: "detection",
    sampleCount,
    totalDetections,
    averageDetections: round(totalDetections / Math.max(1, sampleCount), 2),
    averageConfidence: round(totalConfidence / safeDetectionCount, 2),
    averageAreaRatio: round(totalAreaRatio / safeDetectionCount, 2),
    classCount: labelStats.length,
    dominantLabels: labelStats,
    confidenceBands: createBandRows(confidenceCounter, ["高置信", "中置信", "低置信"]),
    sizeBands: createBandRows(sizeCounter, ["微小目标", "小目标", "中目标", "大目标"]),
    imageDetectionCounts: analyses.map((analysis, index) => ({
      name: `第${items[index]?.id ?? index + 1}组`,
      value: analysis.detectionCount,
    })),
  };
}

function isMmsegResult(item) {
  return Boolean(item?.after_img && String(item.after_img).includes("pred_"));
}

function deriveMaskPath(afterImg) {
  if (!afterImg) {
    return "";
  }
  return String(afterImg).replace(/pred_([^/]+)\.png(\?.*)?$/, "mask_$1.png");
}

function nearestPaletteIndex(r, g, b, classes) {
  let bestIndex = 0;
  let bestDistance = Number.POSITIVE_INFINITY;
  classes.forEach((item, index) => {
    const [pr, pg, pb] = item.rgb;
    const distance = ((r - pr) ** 2) + ((g - pg) ** 2) + ((b - pb) ** 2);
    if (distance < bestDistance) {
      bestDistance = distance;
      bestIndex = index;
    }
  });
  return bestIndex;
}

function buildSegmentationClassStats(counts, classes, total) {
  return classes.map((item, index) => ({
    ...item,
    count: counts[index] || 0,
    ratio: normalizedPercent(counts[index] || 0, total),
    color: `rgb(${item.rgb.join(",")})`,
  })).sort((a, b) => b.count - a.count);
}

async function analyzeMmsegSegmentation(item) {
  const classes = MMSEG_SEGMENTATION_CLASSES;
  const maskPath = deriveMaskPath(item.after_img);
  const pixels = await loadImagePixels(maskPath, SEGMENTATION_PREVIEW_SIZE);
  const counts = new Array(classes.length).fill(0);
  const total = pixels.width * pixels.height;

  for (let i = 0; i < pixels.data.length; i += 4) {
    const classIndex = Math.max(0, Math.min(classes.length - 1, Math.round(pixels.data[i])));
    counts[classIndex] += 1;
  }

  const classStats = buildSegmentationClassStats(counts, classes, total);
  return {
    kind: "segmentation",
    scheme: "mmseg",
    source: "原始 mask",
    totalPixels: total,
    dominantClass: classStats[0]?.name || "未知",
    dominantRatio: classStats[0]?.ratio || 0,
    classStats,
  };
}

async function analyzePaletteSegmentation(item) {
  const classes = PADDLE_SEGMENTATION_CLASSES;
  const pixels = await loadImagePixels(item._after_img_preview || item.after_img, SEGMENTATION_PREVIEW_SIZE);
  const counts = new Array(classes.length).fill(0);
  const total = pixels.width * pixels.height;

  for (let i = 0; i < pixels.data.length; i += 4) {
    const classIndex = nearestPaletteIndex(
      pixels.data[i],
      pixels.data[i + 1],
      pixels.data[i + 2],
      classes,
    );
    counts[classIndex] += 1;
  }

  const classStats = buildSegmentationClassStats(counts, classes, total);
  return {
    kind: "segmentation",
    scheme: "paddle",
    source: "结果图近似估计",
    totalPixels: total,
    dominantClass: classStats[0]?.name || "未知",
    dominantRatio: classStats[0]?.ratio || 0,
    classStats,
  };
}

export async function analyzeSegmentationRecord(item) {
  if (isMmsegResult(item)) {
    try {
      return await analyzeMmsegSegmentation(item);
    } catch (error) {
      return analyzePaletteSegmentation(item);
    }
  }
  return analyzePaletteSegmentation(item);
}

export function summarizeSegmentation(items, analyses) {
  const sampleCount = items.length;
  const classCounter = new Map();

  analyses.forEach((analysis) => {
    analysis.classStats.forEach((entry) => {
      classCounter.set(entry.name, (classCounter.get(entry.name) || 0) + entry.count);
    });
  });

  const totalPixels = Array.from(classCounter.values()).reduce((sum, value) => sum + value, 0);
  const classStats = Array.from(classCounter.entries())
    .map(([name, count]) => ({ name, count, ratio: normalizedPercent(count, totalPixels) }))
    .sort((a, b) => b.count - a.count);

  const dominantMap = new Map();
  analyses.forEach((analysis) => {
    dominantMap.set(analysis.dominantClass, (dominantMap.get(analysis.dominantClass) || 0) + 1);
  });

  return {
    kind: "segmentation",
    sampleCount,
    dominantClasses: Array.from(dominantMap.entries())
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value),
    aggregateClassStats: classStats,
  };
}

function toMetricRows(beforeMetrics, afterMetrics) {
  const rows = [
    { key: "sharpness", name: "清晰度", before: beforeMetrics.sharpness, after: afterMetrics.sharpness },
    { key: "contrast", name: "对比度", before: beforeMetrics.contrast, after: afterMetrics.contrast },
    { key: "entropy", name: "信息熵", before: beforeMetrics.entropy, after: afterMetrics.entropy },
    { key: "edgeDensity", name: "边缘密度", before: beforeMetrics.edgeDensity, after: afterMetrics.edgeDensity },
    { key: "dynamicRange", name: "动态范围", before: beforeMetrics.dynamicRange, after: afterMetrics.dynamicRange },
  ];

  return rows.map((row) => ({
    ...row,
    delta: round(row.after - row.before, 2),
    deltaPercent: row.before ? round(((row.after - row.before) / row.before) * 100, 2) : 0,
  }));
}

export async function analyzeRestorationRecord(item) {
  const [beforePixels, afterPixels] = await Promise.all([
    loadImagePixels(item._before_img_preview || item.before_img, IMAGE_PREVIEW_SIZE),
    loadImagePixels(item._after_img_preview || item.after_img, IMAGE_PREVIEW_SIZE),
  ]);

  const beforeMetrics = computeImageMetrics(beforePixels);
  const afterMetrics = computeImageMetrics(afterPixels);
  const comparisonRows = toMetricRows(beforeMetrics, afterMetrics);
  const pixelScale = ((afterMetrics.width * afterMetrics.height) / Math.max(1, beforeMetrics.width * beforeMetrics.height));

  return {
    kind: "restoration",
    beforeMetrics,
    afterMetrics,
    comparisonRows,
    scale: {
      widthRatio: round(afterMetrics.width / Math.max(1, beforeMetrics.width), 2),
      heightRatio: round(afterMetrics.height / Math.max(1, beforeMetrics.height), 2),
      pixelRatio: round(pixelScale, 2),
    },
  };
}

export function summarizeRestoration(items, analyses) {
  const count = analyses.length || 1;
  const totals = {
    widthRatio: 0,
    pixelRatio: 0,
    sharpness: 0,
    contrast: 0,
    entropy: 0,
    edgeDensity: 0,
  };

  analyses.forEach((analysis) => {
    totals.widthRatio += analysis.scale.widthRatio;
    totals.pixelRatio += analysis.scale.pixelRatio;
    analysis.comparisonRows.forEach((row) => {
      if (Object.prototype.hasOwnProperty.call(totals, row.key)) {
        totals[row.key] += row.deltaPercent;
      }
    });
  });

  return {
    kind: "restoration",
    sampleCount: items.length,
    averageScales: {
      widthRatio: round(totals.widthRatio / count, 2),
      pixelRatio: round(totals.pixelRatio / count, 2),
    },
    averageChanges: [
      { name: "清晰度", value: round(totals.sharpness / count, 2) },
      { name: "对比度", value: round(totals.contrast / count, 2) },
      { name: "信息熵", value: round(totals.entropy / count, 2) },
      { name: "边缘密度", value: round(totals.edgeDensity / count, 2) },
    ],
  };
}

export async function analyzeRegistrationRecord({
  fixedSource,
  movingSource,
  resultSource,
  record,
} = {}) {
  const detection = analyzeDetectionRecord(record || {});
  const [fixedPixels, movingPixels, resultPixels] = await Promise.all([
    fixedSource ? loadImagePixels(fixedSource, IMAGE_PREVIEW_SIZE).catch(() => null) : Promise.resolve(null),
    movingSource ? loadImagePixels(movingSource, IMAGE_PREVIEW_SIZE).catch(() => null) : Promise.resolve(null),
    resultSource ? loadImagePixels(resultSource, IMAGE_PREVIEW_SIZE).catch(() => null) : Promise.resolve(null),
  ]);

  const fixedMetrics = fixedPixels ? computeImageMetrics(fixedPixels) : null;
  const movingMetrics = movingPixels ? computeImageMetrics(movingPixels) : null;
  const resultMetrics = resultPixels ? computeImageMetrics(resultPixels) : null;
  const edgeAlignment = fixedSource && movingSource
    ? await computeEdgeAlignmentComparison(fixedSource, movingSource, 256).catch(() => null)
    : null;

  const metricRows = [
    {
      name: "亮度",
      fixed: fixedMetrics?.brightness ?? null,
      moving: movingMetrics?.brightness ?? null,
      result: resultMetrics?.brightness ?? null,
    },
    {
      name: "对比度",
      fixed: fixedMetrics?.contrast ?? null,
      moving: movingMetrics?.contrast ?? null,
      result: resultMetrics?.contrast ?? null,
    },
    {
      name: "信息熵",
      fixed: fixedMetrics?.entropy ?? null,
      moving: movingMetrics?.entropy ?? null,
      result: resultMetrics?.entropy ?? null,
    },
    {
      name: "边缘密度",
      fixed: fixedMetrics?.edgeDensity ?? null,
      moving: movingMetrics?.edgeDensity ?? null,
      result: resultMetrics?.edgeDensity ?? null,
    },
    {
      name: "清晰度",
      fixed: fixedMetrics?.sharpness ?? null,
      moving: movingMetrics?.sharpness ?? null,
      result: resultMetrics?.sharpness ?? null,
    },
  ];

  const modalityGap = metricRows
    .filter((row) => row.fixed !== null && row.moving !== null)
    .map((row) => ({
      name: row.name,
      value: round(Math.abs(row.fixed - row.moving), 2),
    }));

  return {
    kind: "registration_detection",
    detection,
    fixedMetrics,
    movingMetrics,
    resultMetrics,
    edgeAlignment,
    metricRows,
    modalityGap,
  };
}

function buildBinaryEdgeMap(gray, width, height) {
  const edgeMap = new Uint8Array(width * height);
  for (let y = 1; y < height - 1; y += 1) {
    for (let x = 1; x < width - 1; x += 1) {
      const idx = y * width + x;
      const gx = gray[idx + 1] - gray[idx - 1];
      const gy = gray[idx + width] - gray[idx - width];
      const magnitude = Math.sqrt((gx * gx) + (gy * gy));
      if (magnitude > 28) {
        edgeMap[idx] = 1;
      }
    }
  }
  return edgeMap;
}

function grayArray(pixelSource, width, height) {
  const arr = new Float32Array(width * height);
  for (let i = 0; i < width * height; i += 1) {
    const offset = i * 4;
    arr[i] = luminance(
      pixelSource.data[offset],
      pixelSource.data[offset + 1],
      pixelSource.data[offset + 2],
    );
  }
  return arr;
}

async function loadComparablePixels(source, size = 256) {
  const resolvedSource = await resolveImageSource(source, size);
  const img = await loadImageElement(resolvedSource);
  const canvas = createCanvas(size, size);
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  ctx.drawImage(img, 0, 0, size, size);
  return ctx.getImageData(0, 0, size, size);
}

export async function computeEdgeAlignmentComparison(firstSource, secondSource, size = 256) {
  const [firstImage, secondImage] = await Promise.all([
    loadComparablePixels(firstSource, size),
    loadComparablePixels(secondSource, size),
  ]);
  const firstGray = grayArray(firstImage, size, size);
  const secondGray = grayArray(secondImage, size, size);
  const firstEdges = buildBinaryEdgeMap(firstGray, size, size);
  const secondEdges = buildBinaryEdgeMap(secondGray, size, size);

  let firstCount = 0;
  let secondCount = 0;
  let overlapCount = 0;

  for (let i = 0; i < firstEdges.length; i += 1) {
    if (firstEdges[i]) {
      firstCount += 1;
    }
    if (secondEdges[i]) {
      secondCount += 1;
    }
    if (firstEdges[i] && secondEdges[i]) {
      overlapCount += 1;
    }
  }

  const denominator = Math.max(1, Math.min(firstCount, secondCount));
  return {
    edgeOverlap: normalizedPercent(overlapCount, denominator),
    firstEdgeCount: firstCount,
    secondEdgeCount: secondCount,
  };
}

export function summarizeTrajectoryPayload(payload) {
  const frames = payload?.frames || [];
  const tracks = new Map();
  const frameCounts = [];

  frames.forEach((frame, index) => {
    const objects = frame.objects || [];
    frameCounts.push({
      frame: index + 1,
      value: objects.length,
    });
    objects.forEach((object) => {
      const id = object.track_id;
      if (id === null || id === undefined) {
        return;
      }
      if (!tracks.has(id)) {
        tracks.set(id, {
          id,
          label: object.label || "object",
          count: 0,
          scores: [],
        });
      }
      const current = tracks.get(id);
      current.count += 1;
      current.scores.push(Number(object.score) || 0);
    });
  });

  const topTracks = Array.from(tracks.values())
    .map((track) => ({
      id: track.id,
      label: track.label,
      count: track.count,
      meanScore: round(track.scores.reduce((sum, value) => sum + value, 0) / Math.max(1, track.scores.length), 3),
    }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 8);

  return {
    frameCounts,
    topTracks,
  };
}

export async function fetchJsonAsset(url) {
  if (!url) {
    return null;
  }
  const response = await axios.get(url);
  return response.data;
}
