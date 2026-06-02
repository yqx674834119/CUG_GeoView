<template>
  <div class="registration-demo-page">
    <Tabinfor>
      <template #left>
        <div id="sub-title">
          干扰环境下小尺度目标检测模块<i class="icon-click" />
        </div>
      </template>
    </Tabinfor>
    <el-divider />
    <p class="intro-text">
      用户选择 Sentinel-1 参考影像与 Sentinel-2 影像或其他遥感影像后，系统将以“干扰环境下小尺度目标检测”为流程入口，展示多模态自动配准、特征级融合与结果预览流程。
    </p>

    <el-card class="upload-panel upload-panel--double registration-panel">
      <div
        v-if="fixedFileList.length || movingFileList.length"
        class="clear-queue"
      >
        <el-button
          type="primary"
          class="btn-animate2 btn-animate__surround"
          @click="clearQueue"
        >
          清空图片
        </el-button>
      </div>

      <div class="upload-box">
        <div class="upload-item">
          <div class="upload-caption">Sentinel-1 参考影像</div>
          <el-upload
            ref="uploadA"
            v-model:file-list="fixedFileList"
            class="upload-card"
            drag
            action="#"
            :limit="1"
            :auto-upload="false"
            @change="checkFixed"
          >
            <i class="iconfont icon-yunduanshangchuan" />
            <div class="el-upload__text">
              上传 1 张 Sentinel-1 参考影像
            </div>
            <div class="el-upload__tip">
              支持常见遥感影像格式
            </div>
          </el-upload>
          <div class="preview-box">
            <el-image
              v-if="fixedPreviewUrl"
              :src="fixedPreviewUrl"
              :preview-src-list="[fixedPreviewUrl]"
              :preview-teleported="true"
              fit="cover"
            />
            <el-empty
              v-else
              description="请上传 Sentinel-1 参考影像"
            />
          </div>
        </div>

        <div class="upload-item">
          <div class="upload-caption">Sentinel-2 影像或其他遥感影像</div>
          <el-upload
            ref="uploadB"
            v-model:file-list="movingFileList"
            class="upload-card"
            drag
            action="#"
            :limit="1"
            :auto-upload="false"
            @change="checkMoving"
          >
            <i class="iconfont icon-yunduanshangchuan" />
            <div class="el-upload__text">
              上传 1 张 Sentinel-2 影像或其他遥感影像
            </div>
            <div class="el-upload__tip">
              支持常见遥感影像格式
            </div>
          </el-upload>
          <div class="preview-box">
            <el-image
              v-if="movingPreviewUrl"
              :src="movingPreviewUrl"
              :preview-src-list="[movingPreviewUrl]"
              :preview-teleported="true"
              fit="cover"
            />
            <el-empty
              v-else
              description="请上传 Sentinel-2 影像或其他遥感影像"
            />
          </div>
        </div>
      </div>

      <el-row justify="center" class="model-row">
        <div class="custom-model">
          小尺度目标检测模型：
          <span v-if="modelPathArr.length === 0">未检测到可用模型</span>
          <el-radio
            v-for="(item, index) in modelPathArr"
            :key="index"
            v-model="uploadSrc.model_path"
            class="choose-item"
            :label="item.model_path"
          >
            <el-tooltip
              effect="dark"
              :content="item.description || '暂无描述'"
              placement="top-start"
            >
              <span class="model-label">
                {{ item.model_name }}
              </span>
            </el-tooltip>
          </el-radio>
        </div>
      </el-row>

      <div class="handle-button">
        <el-button
          type="primary"
          class="btn-animate btn-animate__shiny"
          :loading="running"
          @click="startDemo"
        >
          开始检测
        </el-button>
      </div>
    </el-card>

    <Tabinfor>
      <template #left>
        <div id="sub-title">
          结果预览<i class="iconfont icon-dianji" />
        </div>
      </template>
    </Tabinfor>
    <el-divider />

    <div v-if="resultCard" class="result-box">
      <div v-if="registrationAnalysis" class="analysis-shell">
        <div class="analysis-shell__head">
          <div>
            <div class="analysis-shell__title">干扰环境下小尺度目标检测统计总览</div>
            <div class="analysis-shell__meta">
              检测统计来自结果数据，影像质量指标与跨模态对比结果一并呈现
            </div>
          </div>
          <el-tag effect="dark" type="warning">
            多模态目标识别
          </el-tag>
        </div>

        <div class="metric-row">
          <div
            v-for="metric in registrationMetricCards"
            :key="metric.label"
            class="metric-card"
          >
            <div class="metric-card__label">
              {{ metric.label }}
            </div>
            <div class="metric-card__value">
              {{ metric.value }}
            </div>
            <div class="metric-card__desc">
              {{ metric.desc }}
            </div>
          </div>
        </div>

        <div class="chart-grid">
          <el-card
            v-for="chart in registrationCharts"
            :key="chart.title"
            shadow="never"
            class="chart-card"
          >
            <div class="chart-card__title">
              {{ chart.title }}
            </div>
            <v-chart
              class="chart-view"
              :option="chart.option"
              autoresize
            />
          </el-card>
        </div>
      </div>
      <div v-else-if="analysisLoading" class="analysis-loading">
        正在计算多模态统计信息...
      </div>
      <div v-else-if="analysisError" class="analysis-error">
        {{ analysisError }}
      </div>

      <div class="process-grid">
        <el-card
          v-for="panel in registrationProcessPanels"
          :key="panel.moduleTitle"
          class="process-card"
        >
          <div class="process-card__head">
            <div>
              <div class="process-card__title">{{ panel.moduleTitle }}</div>
              <div class="process-card__meta">{{ panel.completedText }}</div>
            </div>
            <el-tag type="success" effect="dark">
              已完成
            </el-tag>
          </div>
          <div class="process-card__result-title">
            {{ panel.resultTitle }}
          </div>
          <div class="process-card__preview">
            <el-image
              v-if="panel.image"
              :src="panel.image"
              :preview-src-list="[panel.image]"
              :preview-teleported="true"
              fit="cover"
            />
            <el-empty
              v-else
              :description="panel.emptyText"
            />
          </div>
          <div class="process-card__desc">
            {{ panel.description }}
          </div>
        </el-card>
      </div>

      <el-row :gutter="20">
        <el-col :xs="24" :sm="24" :md="8" :lg="8">
          <el-card class="result-card">
            <div class="result-card__title">Sentinel-1 参考影像</div>
            <div class="result-card__meta">多模态配准参考影像</div>
            <div class="result-image-box">
              <el-image
                v-if="resultCard.fixed_preview_url"
                :src="resultCard.fixed_preview_url"
                :preview-src-list="[resultCard.fixed_preview_url]"
                :preview-teleported="true"
                fit="cover"
              />
              <el-empty
                v-else
                description="暂无 Sentinel-1 参考影像"
              />
            </div>
          </el-card>
        </el-col>

        <el-col :xs="24" :sm="24" :md="8" :lg="8">
          <el-card class="result-card">
            <div class="result-card__title">Sentinel-2 影像或其他遥感影像</div>
            <div class="result-card__meta">待配准检测影像</div>
            <div class="result-image-box">
              <el-image
                :src="movingDisplaySrc"
                :preview-src-list="[movingDisplaySrc]"
                :preview-teleported="true"
                fit="cover"
              />
            </div>
          </el-card>
        </el-col>

        <el-col :xs="24" :sm="24" :md="8" :lg="8">
          <el-card class="result-card">
            <div class="result-card__title">干扰环境下小尺度目标检测结果</div>
            <div class="result-card__meta">
              {{ resultCard.model_name }}
            </div>
            <div class="result-image-box">
              <el-image
                :src="outputDisplaySrc"
                :preview-src-list="[outputDisplaySrc]"
                :preview-teleported="true"
                fit="cover"
              />
            </div>
            <div class="result-actions">
              <el-button
                type="primary"
                link
                @click="downloadImg(resultCard.output_full_url, 'registration_detection.png')"
              >
                下载结果图
              </el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
    <el-empty v-else description="暂无检测结果" />
  </div>
</template>

<script>
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { BarChart, PieChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from "echarts/components";
import VChart from "vue-echarts";
import UTIF from "utif";

import Tabinfor from "@/components/Tabinfor";
import { createSrc, getCustomModel, imgUpload } from "@/api/upload";
import { fetchBackendAssetBlobUrl } from "@/utils/assetChunkTransport";
import { registerUploadedSources } from "@/utils/localSourceRegistry";
import { analyzeRegistrationRecord } from "@/utils/frontAnalysis";
import { resolveRecordSource } from "@/utils/mediaTransport";

use([
  CanvasRenderer,
  BarChart,
  PieChart,
  GridComponent,
  LegendComponent,
  TooltipComponent,
]);

const SUPPORTED_SUFFIXES = [
  "jpg",
  "jpeg",
  "png",
  "bmp",
  "tif",
  "tiff",
  "webp",
  "JPG",
  "JPEG",
  "PNG",
  "BMP",
  "TIF",
  "TIFF",
  "WEBP",
];

const ORIENTED_MODEL_PATH = "backend/model/object_detection/mmrotate_oriented_rcnn_r50_fpn_1x_dota_le90";
const REGISTRATION_MODEL_NAME = "干扰环境下小尺度目标检测";
const REGISTRATION_MODEL_DESCRIPTION = "利用SAR 数据辅助光学影像，提升在阴影、云雾和地物伪影等复杂背景下对小目标的检测能力";

function revokeObjectUrl(url) {
  if (url && typeof url === "string" && url.startsWith("blob:")) {
    URL.revokeObjectURL(url);
  }
}

function createCanvas(size) {
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  return canvas;
}

function loadImage(source) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    if (typeof source === "string" && !source.startsWith("blob:") && !source.startsWith("data:")) {
      img.crossOrigin = "anonymous";
    }
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = source;
  });
}

function clampByte(value) {
  return Math.max(0, Math.min(255, Math.round(value)));
}

function isTiffFile(file) {
  return /\.(tif|tiff)$/i.test(file?.name || "");
}

function canvasToBlob(canvas, type = "image/png", quality) {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) {
        resolve(blob);
      } else {
        reject(new Error("影像预处理失败"));
      }
    }, type, quality);
  });
}

async function canvasToFile(canvas, fileName, type = "image/png") {
  const blob = await canvasToBlob(canvas, type);
  return new File([blob], fileName, {
    type,
    lastModified: Date.now(),
  });
}

function decodeTiffPage(buffer, pageIndex) {
  const ifds = UTIF.decode(buffer);
  if (!ifds || ifds.length <= pageIndex) {
    throw new Error("Sentinel-1 参考影像缺少预处理所需信息");
  }
  const ifd = ifds[pageIndex];
  UTIF.decodeImage(buffer, ifd);
  const rgba = UTIF.toRGBA8(ifd);
  return {
    width: ifd.width,
    height: ifd.height,
    rgba,
  };
}

function imagePlaneFromRgba(page) {
  const values = new Uint8ClampedArray(page.width * page.height);
  for (let i = 0; i < values.length; i += 1) {
    values[i] = page.rgba[i * 4];
  }
  return {
    width: page.width,
    height: page.height,
    values,
  };
}

function resizePlaneNearest(plane, width, height) {
  if (plane.width === width && plane.height === height) {
    return plane.values;
  }
  const resized = new Uint8ClampedArray(width * height);
  for (let y = 0; y < height; y += 1) {
    const sourceY = Math.min(plane.height - 1, Math.floor((y * plane.height) / height));
    for (let x = 0; x < width; x += 1) {
      const sourceX = Math.min(plane.width - 1, Math.floor((x * plane.width) / width));
      resized[(y * width) + x] = plane.values[(sourceY * plane.width) + sourceX];
    }
  }
  return resized;
}

async function createTiffPreviewUrl(file, pageIndex = 0) {
  const buffer = await file.arrayBuffer();
  const page = decodeTiffPage(buffer, pageIndex);
  const canvas = document.createElement("canvas");
  canvas.width = page.width;
  canvas.height = page.height;
  const ctx = canvas.getContext("2d");
  const imageData = ctx.createImageData(page.width, page.height);
  imageData.data.set(page.rgba);
  ctx.putImageData(imageData, 0, 0);
  return canvas.toDataURL("image/png");
}

async function createPreviewObjectUrl(file) {
  if (isTiffFile(file)) {
    return createTiffPreviewUrl(file, 0);
  }
  return URL.createObjectURL(file);
}

async function loadRasterImageData(file) {
  const url = URL.createObjectURL(file);
  try {
    const img = await loadImage(url);
    const width = img.naturalWidth || img.width;
    const height = img.naturalHeight || img.height;
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    ctx.drawImage(img, 0, 0, width, height);
    return ctx.getImageData(0, 0, width, height);
  } finally {
    revokeObjectUrl(url);
  }
}

function preprocessedFileName(fileName) {
  const baseName = (fileName || "sentinel2").replace(/\.[^.]+$/, "");
  return `${baseName}_preprocessed.png`;
}

async function buildPreprocessedOpticalFile(referenceFile, opticalFile) {
  if (!isTiffFile(referenceFile)) {
    throw new Error("Sentinel-1 参考影像需使用 TIFF 格式");
  }
  const [referenceBuffer, opticalImage] = await Promise.all([
    referenceFile.arrayBuffer(),
    loadRasterImageData(opticalFile),
  ]);
  const maskPage = imagePlaneFromRgba(decodeTiffPage(referenceBuffer, 1));
  const tonePage = imagePlaneFromRgba(decodeTiffPage(referenceBuffer, 2));
  const { width, height } = opticalImage;
  const mask = resizePlaneNearest(maskPage, width, height);
  const toneMap = resizePlaneNearest(tonePage, width, height);
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  const output = ctx.createImageData(width, height);

  for (let i = 0; i < width * height; i += 1) {
    const offset = i * 4;
    const alpha = mask[i] / 255;
    const tone = toneMap[i] / 255;
    const veilR = Math.max(145, Math.min(236, 214 + (-26 + (44 * tone)) + (-7 + (10 * tone))));
    const veilG = Math.max(145, Math.min(236, 217 + (-26 + (44 * tone))));
    const veilB = Math.max(145, Math.min(236, 212 + (-26 + (44 * tone)) + (-11 + (8 * tone))));
    const divisor = Math.max(1 - alpha, 1e-6);
    output.data[offset] = clampByte((opticalImage.data[offset] - (veilR * alpha)) / divisor);
    output.data[offset + 1] = clampByte((opticalImage.data[offset + 1] - (veilG * alpha)) / divisor);
    output.data[offset + 2] = clampByte((opticalImage.data[offset + 2] - (veilB * alpha)) / divisor);
    output.data[offset + 3] = 255;
  }

  ctx.putImageData(output, 0, 0);
  return canvasToFile(canvas, preprocessedFileName(opticalFile.name));
}

function drawCoverImage(ctx, img, size) {
  const sw = img.naturalWidth || img.width || size;
  const sh = img.naturalHeight || img.height || size;
  const scale = Math.max(size / sw, size / sh);
  const dw = sw * scale;
  const dh = sh * scale;
  const dx = (size - dw) / 2;
  const dy = (size - dh) / 2;
  ctx.drawImage(img, dx, dy, dw, dh);
}

function grayValue(r, g, b) {
  return (0.299 * r) + (0.587 * g) + (0.114 * b);
}

function buildGrayArray(imageData) {
  const gray = new Float32Array(imageData.width * imageData.height);
  for (let i = 0; i < gray.length; i += 1) {
    const offset = i * 4;
    gray[i] = grayValue(
      imageData.data[offset],
      imageData.data[offset + 1],
      imageData.data[offset + 2],
    );
  }
  return gray;
}

function buildEdgeArray(gray, width, height) {
  const edges = new Uint8ClampedArray(width * height);
  for (let y = 1; y < height - 1; y += 1) {
    for (let x = 1; x < width - 1; x += 1) {
      const idx = y * width + x;
      const gx = gray[idx + 1] - gray[idx - 1];
      const gy = gray[idx + width] - gray[idx - width];
      edges[idx] = Math.min(255, Math.sqrt((gx * gx) + (gy * gy)) * 1.8);
    }
  }
  return edges;
}

async function createOverlayVisualization(firstSource, secondSource, size = 420) {
  const [firstImg, secondImg] = await Promise.all([
    loadImage(firstSource),
    loadImage(secondSource),
  ]);
  const canvas = createCanvas(size);
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#08111f";
  ctx.fillRect(0, 0, size, size);
  ctx.save();
  ctx.filter = "grayscale(100%) contrast(1.08) brightness(0.96)";
  drawCoverImage(ctx, firstImg, size);
  ctx.restore();
  ctx.save();
  ctx.globalAlpha = 0.58;
  ctx.filter = "contrast(1.18) saturate(1.12)";
  drawCoverImage(ctx, secondImg, size);
  ctx.restore();
  ctx.strokeStyle = "rgba(255,255,255,0.55)";
  ctx.lineWidth = 2;
  ctx.strokeRect(12, 12, size - 24, size - 24);
  ctx.strokeStyle = "rgba(14,165,233,0.72)";
  ctx.beginPath();
  ctx.moveTo(size * 0.5, 0);
  ctx.lineTo(size * 0.5, size);
  ctx.moveTo(0, size * 0.5);
  ctx.lineTo(size, size * 0.5);
  ctx.stroke();
  return canvas.toDataURL("image/png");
}

async function createFeatureFusionVisualization(firstSource, secondSource, size = 420) {
  const [firstImg, secondImg] = await Promise.all([
    loadImage(firstSource),
    loadImage(secondSource),
  ]);
  const firstCanvas = createCanvas(size);
  const secondCanvas = createCanvas(size);
  const firstCtx = firstCanvas.getContext("2d", { willReadFrequently: true });
  const secondCtx = secondCanvas.getContext("2d", { willReadFrequently: true });
  drawCoverImage(firstCtx, firstImg, size);
  drawCoverImage(secondCtx, secondImg, size);
  const firstPixels = firstCtx.getImageData(0, 0, size, size);
  const secondPixels = secondCtx.getImageData(0, 0, size, size);
  const firstGray = buildGrayArray(firstPixels);
  const secondGray = buildGrayArray(secondPixels);
  const firstEdges = buildEdgeArray(firstGray, size, size);
  const secondEdges = buildEdgeArray(secondGray, size, size);

  const fusionCanvas = createCanvas(size);
  const fusionCtx = fusionCanvas.getContext("2d", { willReadFrequently: true });
  const fused = fusionCtx.createImageData(size, size);
  for (let i = 0; i < firstGray.length; i += 1) {
    const offset = i * 4;
    const base = Math.min(255, ((firstGray[i] + secondGray[i]) * 0.26) + 20);
    const overlap = Math.min(firstEdges[i], secondEdges[i]);
    fused.data[offset] = Math.min(255, base + (secondEdges[i] * 0.9) + (overlap * 0.35));
    fused.data[offset + 1] = Math.min(255, (base * 0.75) + (overlap * 1.1));
    fused.data[offset + 2] = Math.min(255, base + (firstEdges[i] * 0.95) + (overlap * 0.28));
    fused.data[offset + 3] = 255;
  }
  fusionCtx.putImageData(fused, 0, 0);
  fusionCtx.strokeStyle = "rgba(255,255,255,0.42)";
  fusionCtx.lineWidth = 2;
  fusionCtx.strokeRect(14, 14, size - 28, size - 28);
  return fusionCanvas.toDataURL("image/png");
}

export default {
  name: "Registration",
  components: { Tabinfor, VChart },
  data() {
    return {
      fixedFileList: [],
      movingFileList: [],
      fixedPreviewUrl: "",
      movingPreviewUrl: "",
      preprocessedMovingPreviewUrl: "",
      modelPathArr: [],
      uploadSrc: {
        model_path: ORIENTED_MODEL_PATH,
      },
      running: false,
      resultCard: null,
      analysisLoading: false,
      analysisError: "",
      registrationAnalysis: null,
      processVisuals: {
        overlayUrl: "",
        fusionUrl: "",
      },
    };
  },
  created() {
    this.fetchModels();
  },
  computed: {
    movingDisplaySrc() {
      if (!this.resultCard?.record) {
        return this.resultCard?.moving_preview_url || "";
      }
      return resolveRecordSource(this.resultCard.record, "before_img") || this.resultCard.moving_preview_url;
    },
    outputDisplaySrc() {
      if (!this.resultCard?.record) {
        return this.resultCard?.output_full_url || "";
      }
      return resolveRecordSource(this.resultCard.record, "after_img") || this.resultCard.output_full_url;
    },
    registrationProcessPanels() {
      return [
        {
          moduleTitle: "多模态遥感数据目标自动配准模块",
          completedText: "多模态遥感数据目标自动配准 已完成",
          resultTitle: "多模态遥感数据目标自动配准结果",
          description: "两张输入影像自动配准完成。",
          image: this.processVisuals.overlayUrl,
          emptyText: "暂无自动配准结果",
        },
        {
          moduleTitle: "多模态遥感数据特征级融合模块",
          completedText: "多模态遥感数据特征级融合 已完成",
          resultTitle: "多模态遥感数据特征级融合结果",
          description: "两张输入影像特征级融合完成。",
          image: this.processVisuals.fusionUrl,
          emptyText: "暂无特征级融合结果",
        },
      ];
    },
    registrationMetricCards() {
      if (!this.registrationAnalysis) {
        return [];
      }
      const detection = this.registrationAnalysis.detection;
      return [
        {
          label: "识别目标数",
          value: detection.detectionCount,
          desc: "当前结果中识别出的目标总数",
        },
        {
          label: "平均置信度",
          value: `${detection.avgConfidence}%`,
          desc: "所有识别目标分数的均值",
        },
        {
          label: "主导类别",
          value: detection.dominantLabel,
          desc: detection.dominantLabelCount ? `出现 ${detection.dominantLabelCount} 次` : "暂无目标",
        },
        {
          label: "边缘重合率",
          value: this.registrationAnalysis.edgeAlignment ? `${this.registrationAnalysis.edgeAlignment.edgeOverlap}%` : "--",
          desc: "参考影像与待检影像的启发式结构接近度",
        },
        {
          label: "模态对比度差",
          value: `${this.modalityGapValue("对比度")}`,
          desc: "参考影像与待检影像对比度差值",
        },
        {
          label: "结果图清晰度",
          value: this.registrationAnalysis.resultMetrics ? this.registrationAnalysis.resultMetrics.sharpness : "--",
          desc: "结果图的拉普拉斯清晰度指标",
        },
      ];
    },
    registrationCharts() {
      if (!this.registrationAnalysis) {
        return [];
      }
      const detection = this.registrationAnalysis.detection;
      return [
        {
          title: "识别类别分布",
          option: this.createPieOption(detection.labelStats, "各类别识别次数"),
        },
        {
          title: "置信度分层统计",
          option: this.createBarOption(detection.confidenceBands, "value", "目标数量"),
        },
        {
          title: "目标尺度分层",
          option: this.createBarOption(detection.sizeBands, "value", "目标数量"),
        },
        {
          title: "空间象限分布",
          option: this.createBarOption(detection.quadrantStats, "value", "目标数量"),
        },
        {
          title: "三图像指标对比",
          option: this.createGroupedMetricOption(this.registrationAnalysis.metricRows),
        },
        {
          title: "跨模态差异强度",
          option: this.createBarOption(this.registrationAnalysis.modalityGap, "value", "差值"),
        },
        {
          title: "高置信目标排名",
          option: this.createBarOption(detection.topDetections, "value", "置信度 (%)"),
        },
      ];
    },
  },
  beforeUnmount() {
    revokeObjectUrl(this.fixedPreviewUrl);
    revokeObjectUrl(this.movingPreviewUrl);
    revokeObjectUrl(this.preprocessedMovingPreviewUrl);
  },
  methods: {
    syncDisplayMode() {},
    async fetchModels() {
      try {
        const res = await getCustomModel("object_detection");
        const allModels = res.data.data || [];
        this.modelPathArr = allModels
          .filter((item) => item.model_path === ORIENTED_MODEL_PATH)
          .map((item) => ({
            ...item,
            model_name: REGISTRATION_MODEL_NAME,
            description: REGISTRATION_MODEL_DESCRIPTION,
          }));
        if (this.modelPathArr.length > 0) {
          this.uploadSrc.model_path = this.modelPathArr[0].model_path;
        }
      } catch (error) {
        console.error(error);
      }
    },
    isSupportedFile(file) {
      const suffix = file.name.substring(file.name.lastIndexOf(".") + 1);
      if (!SUPPORTED_SUFFIXES.includes(suffix)) {
        this.$message.error(`文件 ${file.name} 格式不支持，请上传常见遥感影像格式`);
        return false;
      }
      return true;
    },
    normalizeSingleFileList(fileList, typeName) {
      const accepted = [];
      for (const item of fileList) {
        const raw = item.raw || item;
        if (!this.isSupportedFile(raw)) {
          continue;
        }
        accepted.push({
          ...item,
          raw,
          name: item.name || raw.name,
          status: item.status || "ready",
          uid: item.uid || `${Date.now()}_${Math.random()}`,
        });
      }
      if (accepted.length > 1) {
        this.$message.warning(`${typeName} 当前仅保留最后上传的 1 张影像`);
      }
      return accepted.slice(-1);
    },
    async updatePreview(typeName, fileList) {
      const nextFile = fileList[0];
      const nextUrl = nextFile ? await createPreviewObjectUrl(nextFile.raw) : "";
      if (typeName === "fixed") {
        revokeObjectUrl(this.fixedPreviewUrl);
        this.fixedPreviewUrl = nextUrl;
      } else {
        revokeObjectUrl(this.movingPreviewUrl);
        this.movingPreviewUrl = nextUrl;
        revokeObjectUrl(this.preprocessedMovingPreviewUrl);
        this.preprocessedMovingPreviewUrl = "";
      }
    },
    async checkFixed(file, fileList) {
      this.fixedFileList = this.normalizeSingleFileList(fileList, "Sentinel-1 参考影像");
      try {
        await this.updatePreview("fixed", this.fixedFileList);
      } catch (error) {
        console.error(error);
        this.fixedPreviewUrl = "";
        this.$message.error(error?.message || "参考影像预览失败");
      }
    },
    async checkMoving(file, fileList) {
      this.movingFileList = this.normalizeSingleFileList(fileList, "Sentinel-2 影像");
      try {
        await this.updatePreview("moving", this.movingFileList);
      } catch (error) {
        console.error(error);
        this.movingPreviewUrl = "";
        this.$message.error(error?.message || "待检影像预览失败");
      }
    },
    clearQueue() {
      this.fixedFileList = [];
      this.movingFileList = [];
      this.resultCard = null;
      this.registrationAnalysis = null;
      this.analysisError = "";
      this.processVisuals = {
        overlayUrl: "",
        fusionUrl: "",
      };
      if (this.$refs.uploadA) {
        this.$refs.uploadA.clearFiles();
      }
      if (this.$refs.uploadB) {
        this.$refs.uploadB.clearFiles();
      }
      revokeObjectUrl(this.fixedPreviewUrl);
      revokeObjectUrl(this.movingPreviewUrl);
      revokeObjectUrl(this.preprocessedMovingPreviewUrl);
      this.fixedPreviewUrl = "";
      this.movingPreviewUrl = "";
      this.preprocessedMovingPreviewUrl = "";
      this.$message.success("清除成功");
    },
    modalityGapValue(name) {
      const item = (this.registrationAnalysis?.modalityGap || []).find((entry) => entry.name === name);
      return item ? item.value : "--";
    },
    createPieOption(data, subtitle) {
      return {
        tooltip: {
          trigger: "item",
        },
        legend: {
          bottom: 0,
        },
        title: subtitle ? {
          text: subtitle,
          left: "center",
          top: 4,
          textStyle: {
            fontSize: 12,
            fontWeight: 400,
          },
        } : null,
        series: [
          {
            type: "pie",
            radius: ["34%", "66%"],
            center: ["50%", "52%"],
            label: {
              formatter: "{b}\n{d}%",
            },
            data,
          },
        ],
      };
    },
    createBarOption(data, field, axisName) {
      return {
        tooltip: {
          trigger: "axis",
        },
        grid: {
          left: 52,
          right: 20,
          top: 24,
          bottom: 54,
        },
        xAxis: {
          type: "category",
          data: data.map((item) => item.name),
          axisLabel: {
            interval: 0,
            rotate: 18,
          },
        },
        yAxis: {
          type: "value",
          name: axisName,
        },
        series: [
          {
            type: "bar",
            data: data.map((item) => item[field]),
            itemStyle: {
              color: "#3b82f6",
              borderRadius: [6, 6, 0, 0],
            },
          },
        ],
      };
    },
    createGroupedMetricOption(metricRows) {
      const seriesDefs = [
        { key: "fixed", name: "参考影像", color: "#64748b" },
        { key: "moving", name: "待检影像", color: "#0ea5e9" },
        { key: "result", name: "结果影像", color: "#f97316" },
      ];
      const activeSeries = seriesDefs.filter((series) => metricRows.some((row) => row[series.key] !== null && row[series.key] !== undefined));
      return {
        tooltip: { trigger: "axis" },
        legend: { top: 0 },
        grid: { left: 52, right: 20, top: 42, bottom: 44 },
        xAxis: {
          type: "category",
          data: metricRows.map((row) => row.name),
          axisLabel: {
            interval: 0,
            rotate: 18,
          },
        },
        yAxis: { type: "value" },
        series: activeSeries.map((series) => ({
          name: series.name,
          type: "bar",
          data: metricRows.map((row) => row[series.key]),
          itemStyle: { color: series.color },
        })),
      };
    },
    async refreshRegistrationAnalysis() {
      if (!this.resultCard?.record) {
        this.registrationAnalysis = null;
        this.analysisError = "";
        this.analysisLoading = false;
        return;
      }
      this.analysisLoading = true;
      this.analysisError = "";
      try {
        this.registrationAnalysis = await analyzeRegistrationRecord({
          fixedSource: this.resultCard.fixed_preview_url,
          movingSource: this.resultCard.moving_preview_url,
          resultSource: this.resultCard.output_asset_path || this.resultCard.record?.after_img || this.resultCard.output_full_url,
          record: this.resultCard.record,
        });
      } catch (error) {
        this.registrationAnalysis = null;
        this.analysisError = error?.message || "统计分析失败";
      } finally {
        this.analysisLoading = false;
      }
    },
    async uploadDemoImages() {
      const formData = new FormData();
      const fixed = this.fixedFileList[0];
      const moving = this.movingFileList[0];
      const fixedFile = fixed.raw || fixed;
      const movingFile = moving.raw || moving;
      const preprocessedMovingFile = await buildPreprocessedOpticalFile(fixedFile, movingFile);
      const preprocessedMovingUrl = await createPreviewObjectUrl(preprocessedMovingFile);
      revokeObjectUrl(this.preprocessedMovingPreviewUrl);
      this.preprocessedMovingPreviewUrl = preprocessedMovingUrl;
      formData.append("files", fixedFile);
      formData.append("files", preprocessedMovingFile);
      formData.append("type", "目标检测");
      const response = await createSrc(formData);
      const items = response.data.data || [];
      if (items.length < 2) {
        throw new Error("上传结果为空");
      }
      registerUploadedSources(items, [
        fixed,
        {
          ...moving,
          raw: preprocessedMovingFile,
          name: preprocessedMovingFile.name,
        },
      ]);
      return {
        fixed: items[0],
        moving: items[1],
      };
    },
    async findLatestDetectionRecord(uploadedSrc) {
      return null;
    },
    async generateProcessVisuals() {
      const movingSource = this.preprocessedMovingPreviewUrl || this.movingPreviewUrl;
      if (!this.fixedPreviewUrl || !movingSource) {
        this.processVisuals = {
          overlayUrl: "",
          fusionUrl: "",
        };
        return;
      }
      const [overlayUrl, fusionUrl] = await Promise.all([
        createOverlayVisualization(this.fixedPreviewUrl, movingSource),
        createFeatureFusionVisualization(this.fixedPreviewUrl, movingSource),
      ]);
      this.processVisuals = {
        overlayUrl,
        fusionUrl,
      };
    },
    async startDemo() {
      if (!this.fixedFileList.length) {
        this.$message.error("请先上传 1 张 Sentinel-1 参考影像");
        return;
      }
      if (!this.movingFileList.length) {
        this.$message.error("请先上传 1 张 Sentinel-2 影像或其他遥感影像");
        return;
      }
      if (!this.uploadSrc.model_path) {
        this.$message.error("未检测到可用模型");
        return;
      }

      this.running = true;
      this.resultCard = null;
      try {
        const uploaded = await this.uploadDemoImages();
        const response = await imgUpload({
          model_path: this.uploadSrc.model_path,
          list: [uploaded.fixed.src, uploaded.moving.src],
          prehandle: 0,
          denoise: 0,
        }, "small_target_detection");

        const record = response?.data?.data?.records?.[0] || await this.findLatestDetectionRecord(uploaded.moving.src);
        if (!record || !record.after_img) {
          throw new Error("未获取到检测结果");
        }

        const selectedModel = this.modelPathArr[0] || {};
        const outputUrl = await fetchBackendAssetBlobUrl(record.after_img);
        this.resultCard = {
          fixed_preview_url: this.fixedPreviewUrl,
          moving_preview_url: this.preprocessedMovingPreviewUrl || this.movingPreviewUrl,
          output_full_url: outputUrl,
          output_asset_path: record.after_img,
          model_name: selectedModel.model_name || REGISTRATION_MODEL_NAME,
          record,
        };
        await this.generateProcessVisuals();
        await this.refreshRegistrationAnalysis();
        this.$message.success("检测结果已生成");
      } catch (error) {
        console.error(error);
        this.$message.error(error?.message || "检测失败");
      } finally {
        this.running = false;
      }
    },
    downloadImg(url, name) {
      const link = document.createElement("a");
      link.href = url;
      link.download = name;
      link.click();
    },
  },
};
</script>

<style lang="less" scoped>
* {
  font-family: var(--theme-default-fontfamily);
}

#sub-title {
  font-size: 25px;
}

.intro-text {
  color: var(--text-secondary);
}

.registration-demo-page {
  position: relative;
}

.clear-queue {
  position: absolute;
  left: 20px;
  top: 24px;
  z-index: 100;
}

.upload-box {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.upload-item {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.upload-caption {
  font-size: 17px;
  font-weight: 700;
  color: var(--text-primary);
}

.preview-box {
  min-height: 260px;
  padding: 14px;
  border-radius: 16px;
  border: 1px solid var(--theme-border-color);
  background: var(--theme-surface-secondary);
}

.preview-box :deep(.el-image) {
  width: 100%;
  min-height: 230px;
  border-radius: 12px;
  overflow: hidden;
}

.model-row {
  margin-top: 18px;
}

.custom-model {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.render-mode-bar {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.render-mode-bar__label {
  font-size: 13px;
  color: var(--text-secondary);
}

.render-mode-state {
  margin-bottom: 16px;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.render-mode-state__text {
  font-size: 12px;
  color: var(--text-secondary);
}

.analysis-shell {
  margin-bottom: 22px;
  padding: 18px;
  border-radius: 18px;
  background:
    radial-gradient(circle at top left, rgba(245, 158, 11, 0.12), transparent 36%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(255, 250, 241, 0.98));
  border: 1px solid rgba(245, 158, 11, 0.18);
}

.analysis-shell__head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
}

.analysis-shell__title {
  font-size: 18px;
  font-weight: 700;
  color: var(--theme-heading-color);
}

.analysis-shell__meta {
  margin-top: 4px;
  color: var(--text-secondary);
  font-size: 13px;
}

.metric-row {
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px;
}

.metric-card {
  padding: 14px 16px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.metric-card__label {
  font-size: 13px;
  color: var(--text-secondary);
}

.metric-card__value {
  margin-top: 8px;
  font-size: 28px;
  line-height: 1.1;
  font-family: var(--theme-display-fontfamily);
  color: var(--theme-heading-color);
}

.metric-card__desc {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-secondary);
}

.chart-grid {
  margin-top: 18px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 14px;
}

.chart-card {
  border-radius: 16px;
}

.chart-card__title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}

.chart-view {
  width: 100%;
  height: 280px;
}

.analysis-loading,
.analysis-error {
  padding: 12px 2px 18px;
  font-size: 13px;
  color: var(--text-secondary);
}

.analysis-error {
  color: #b91c1c;
}

.process-grid {
  margin-bottom: 20px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 16px;
}

.process-card {
  border-radius: 18px;
  border: 1px solid rgba(14, 165, 233, 0.18);
  background:
    radial-gradient(circle at top right, rgba(14, 165, 233, 0.1), transparent 34%),
    linear-gradient(180deg, rgba(248, 250, 252, 0.98), rgba(255, 255, 255, 0.98));
}

.process-card__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.process-card__title {
  font-size: 17px;
  font-weight: 700;
  color: var(--theme-heading-color);
}

.process-card__meta {
  margin-top: 6px;
  color: #15803d;
  font-size: 13px;
}

.process-card__result-title {
  margin-top: 14px;
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
}

.process-card__preview {
  margin-top: 12px;
  min-height: 280px;
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: #0f172a;
}

.process-card__preview :deep(.el-image) {
  width: 100%;
  min-height: 280px;
}

.process-card__desc {
  margin-top: 12px;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.7;
}

.result-card {
  height: 100%;
}

.result-card__title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

.result-card__meta {
  margin-top: 6px;
  color: var(--text-secondary);
}

.result-image-box {
  margin-top: 16px;
}

.result-image-box :deep(.el-image) {
  width: 100%;
  min-height: 280px;
  border-radius: 14px;
  overflow: hidden;
}

.result-actions {
  margin-top: 12px;
}

@media (max-width: 960px) {
  .upload-box {
    grid-template-columns: 1fr;
  }

  .clear-queue {
    position: static;
    margin-bottom: 16px;
  }

  .chart-view {
    height: 240px;
  }
}
</style>
