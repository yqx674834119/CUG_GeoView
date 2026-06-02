<template>
  <div class="tracking-page">
    <Tabinfor>
      <template #left>
        <div id="sub-title">
          全域静态目标跟踪与预警模块<i class="icon-click" />
        </div>
      </template>
    </Tabinfor>
    <el-divider />
    <p class="intro-text">
      上传按时间顺序命名的时序图像序列，或单个视频文件，系统会自动完成多目标发现、关联与轨迹输出，并生成预览图、结果视频与轨迹 JSON。
    </p>

    <el-card class="upload-panel upload-panel--single">
      <div v-if="fileList.length" class="clear-queue">
        <el-button
          type="primary"
          class="btn-animate2 btn-animate__surround"
          @click="clearQueue"
        >
          清空
        </el-button>
      </div>

      <div class="upload-center">
        <el-upload
          ref="upload"
          v-model:file-list="fileList"
          class="upload-card"
          drag
          action="#"
          multiple
          :accept="acceptString"
          :auto-upload="false"
          @change="checkFile"
        >
          <i class="iconfont icon-yunduanshangchuan" />
          <div class="el-upload__text">
            拖拽图像序列或单个视频到此处
          </div>
          <div class="el-upload__tip">
            可上传图像序列，或 1 个常见视频文件
          </div>
        </el-upload>
        <div class="upload-action-row">
          <input
            id="upload-folder"
            ref="refFolder"
            type="file"
            webkitdirectory
            directory
            multiple
            style="display:none"
            @change="uploadFolder"
          >
          <i
            class="iconfont icon-wenjianshangchuan upload-folder-action"
            @click="folderClick"
          >上传图像文件夹</i>
        </div>
      </div>

      <div v-if="sortedNames.length && !isVideoInput" class="sequence-summary">
        <div class="summary-head">
          <div>
            <div class="summary-title">序列概览</div>
            <div class="summary-meta">
              共 {{ sortedNames.length }} 帧，首帧 {{ sortedNames[0] }}
            </div>
          </div>
          <el-tag type="success" effect="dark">
            已排序
          </el-tag>
        </div>
        <div class="summary-list">
          <span
            v-for="(name, index) in sortedNames.slice(0, 6)"
            :key="`${name}_${index}`"
            class="summary-chip"
          >
            {{ index + 1 }}. {{ name }}
          </span>
          <span v-if="sortedNames.length > 6" class="summary-chip summary-chip--muted">
            还有 {{ sortedNames.length - 6 }} 帧
          </span>
        </div>
      </div>
      <div v-else-if="sortedNames.length && isVideoInput" class="sequence-summary">
        <div class="summary-head">
          <div>
            <div class="summary-title">视频概览</div>
            <div class="summary-meta">
              已选择视频 {{ sortedNames[0] }}
            </div>
          </div>
          <el-tag type="warning" effect="dark">
            单视频输入
          </el-tag>
        </div>
      </div>

      <el-row justify="center" class="model-row">
        <div class="custom-model">
          可选跟踪模型：
          <el-radio
            v-for="(item, index) in modelPathArr"
            :key="index"
            v-model="uploadSrc.model_path"
            class="choose-item"
            :label="item.model_path"
            :disabled="item.disabled"
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
      <el-row
        v-if="isSam3Model"
        justify="center"
        class="sam3-prompt-row"
      >
        <div class="sam3-prompt-panel">
          <span class="sam3-prompt-label">开放词汇目标：</span>
          <el-select
            v-model="sam3PromptPreset"
            class="sam3-prompt-select"
            placeholder="选择目标"
            clearable
          >
            <el-option
              v-for="item in sam3PromptOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
          <el-input
            v-if="sam3PromptPreset === 'custom'"
            v-model="sam3CustomPrompt"
            class="sam3-prompt-input"
            placeholder="输入一个目标描述"
            clearable
          />
          <span class="sam3-prompt-hint">按文本目标对全序列进行分割跟踪。</span>
        </div>
      </el-row>

      <div v-if="firstFrame && requiresInitialRect && !isVideoInput" class="frame-selector">
        <p class="frame-selector__hint">请在首帧图像中框选初始目标：</p>
        <div class="frame-selector__canvas">
          <img
            ref="firstFrameImg"
            :src="firstFrame"
            class="frame-selector__image"
            @mousedown="startDraw"
            @mousemove="drawing"
            @mouseup="endDraw"
            @mouseleave="endDraw"
          >
          <div
            v-if="rect.w > 0"
            :style="{
              left: `${rect.x}px`,
              top: `${rect.y}px`,
              width: `${rect.w}px`,
              height: `${rect.h}px`,
            }"
            class="frame-selector__rect"
          />
        </div>
        <div v-if="rect.w > 0" class="rect-info">
          初始框：x={{ Math.round(rect.x) }}，y={{ Math.round(rect.y) }}，
          w={{ Math.round(rect.w) }}，h={{ Math.round(rect.h) }}
        </div>
      </div>
      <div v-else-if="firstFrame && isVideoInput" class="frame-selector frame-selector--hintonly">
        <p class="frame-selector__hint">
          当前输入为单个视频文件，系统会自动解帧并执行全图多目标跟踪，无需手工框选。
        </p>
        <div v-if="videoPreviewLoading" class="video-preview-fallback">
          正在生成标准化视频预览，请稍候。
        </div>
        <video
          v-if="inputPreviewUrl && !videoPreviewErrors.input"
          controls
          preload="metadata"
          class="input-video"
          :key="`input_${inputPreviewUrl}`"
          playsinline
          @loadeddata="clearVideoPreviewError('input')"
          @error="handleVideoPreviewError('input')"
          :src="inputPreviewUrl"
        />
        <div v-else class="video-preview-fallback">
          当前视频预览加载失败。任务仍可继续执行，处理完成后结果区仍会提供标准化 MP4 结果视频。
        </div>
      </div>
      <div v-else-if="firstFrame" class="frame-selector frame-selector--hintonly">
        <p class="frame-selector__hint">
          当前模型为全图多目标跟踪，无需手工框选初始目标，系统会自动完成目标发现与轨迹关联。
        </p>
      </div>

      <div class="handle-button">
        <el-button
          type="primary"
          class="btn-animate btn-animate__shiny"
          :loading="running"
          :disabled="!canStart"
          @click="startTracking"
        >
          开始跟踪
        </el-button>
      </div>
      <div v-if="running || trackingJobId" class="tracking-job-panel">
        <div class="tracking-job-panel__head">
          <el-tag :type="trackingJobTagType" effect="dark">
            {{ trackingJobStatusText }}
          </el-tag>
          <span class="tracking-job-panel__meta">
            {{ trackingJobMessage || "等待后端返回状态" }}
          </span>
        </div>
        <div
          class="tracking-job-panel__bar"
          :class="{ 'tracking-job-panel__bar--active': running && !isTrackingJobTerminal }"
        >
          <span :style="{ width: `${trackingProgressPercent}%` }" />
        </div>
        <div class="tracking-job-panel__foot">
          <span v-if="trackingElapsedSec">已运行 {{ trackingElapsedSec }} 秒</span>
          <span>已查询 {{ trackingPollCount }} 次</span>
          <span v-if="running && !isTrackingJobTerminal">每 3 秒自动刷新</span>
        </div>
      </div>
    </el-card>

    <Tabinfor>
      <template #left>
        <div id="sub-title">
          结果预览<i class="iconfont icon-dianji" />
        </div>
      </template>
      <template #right>
        <div v-if="resultSummary" class="result-summary">
          跟踪成功率 {{ formatRatio(resultSummary.tracking_ratio) }}
        </div>
      </template>
    </Tabinfor>
    <el-divider />

    <div v-if="result" class="result-box">
      <el-row :gutter="20">
        <el-col :xs="24" :sm="24" :md="12" :lg="12">
          <el-card class="result-card">
            <template #header>
              <div class="result-card__head">
                <span>输入预览</span>
                <el-tag effect="dark" :type="result.input_mode === 'video' ? 'warning' : 'info'">
                  {{ result.input_mode === "video" ? "视频输入" : "图像序列" }}
                </el-tag>
              </div>
            </template>
            <video
              v-if="result.input_mode === 'video' && result.source_input_full_url"
              v-show="!videoPreviewErrors.source"
              controls
              preload="metadata"
              class="result-video"
              :key="`source_${result.source_input_full_url}`"
              playsinline
              @loadeddata="clearVideoPreviewError('source')"
              @error="handleVideoPreviewError('source')"
              :src="result.source_input_full_url"
            />
            <div
              v-if="result.input_mode === 'video' && result.source_input_full_url && videoPreviewErrors.source"
              class="video-preview-fallback"
            >
              输入视频预览失败，请使用“查看输入”直接打开视频文件。
            </div>
            <el-image
              v-else
              :src="resultInputPreviewSrc"
              :preview-src-list="[resultInputPreviewSrc]"
              :preview-teleported="true"
              fit="cover"
              class="result-preview"
            />
            <div class="metric-grid">
              <span>运行时：{{ result.runtime_variant || "默认" }}</span>
              <span>模型：{{ result.method_used }}</span>
              <span v-if="result.source_input_name">输入名：{{ result.source_input_name }}</span>
            </div>
          </el-card>
        </el-col>

        <el-col :xs="24" :sm="24" :md="12" :lg="12">
          <el-card class="result-card">
            <template #header>
              <div class="result-card__head">
                <span>跟踪预览图</span>
                <el-tag type="success" effect="dark">
                  {{ result.method_used }}
                </el-tag>
              </div>
            </template>
            <el-image
              :src="resultPreviewImageSrc"
              :preview-src-list="[resultPreviewImageSrc]"
              :preview-teleported="true"
              fit="cover"
              class="result-preview"
            />
            <div class="metric-grid">
              <span>总帧数：{{ resultSummary.total_frames }}</span>
              <span>成功帧：{{ resultSummary.tracked_frames }}</span>
              <span>丢失帧：{{ resultSummary.lost_frames }}</span>
              <span>平均置信度：{{ formatRatio(resultSummary.mean_confidence) }}</span>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="20">
        <el-col :xs="24" :sm="24" :md="24" :lg="24">
          <el-card class="result-card">
            <template #header>
              <div class="result-card__head">
                <span>结果视频</span>
                <span class="result-card__meta">
                  位移 {{ formatNumber(resultSummary.center_displacement) }} px
                </span>
              </div>
            </template>
            <video
              v-show="!videoPreviewErrors.output"
              controls
              preload="metadata"
              class="result-video"
              :key="`output_${result.output_video_full_url}`"
              playsinline
              @loadeddata="clearVideoPreviewError('output')"
              @error="handleVideoPreviewError('output')"
              :src="result.output_video_full_url"
            />
            <div
              v-if="result.output_video_full_url && videoPreviewErrors.output"
              class="video-preview-fallback"
            >
              结果视频预览失败，请点击“下载结果视频”获取文件。
            </div>
            <div class="result-actions">
              <el-button
                type="primary"
                link
                @click="downloadFile(result.output_video_full_url, 'tracking_result.mp4')"
              >
                下载结果视频
              </el-button>
              <el-button
                type="primary"
                link
                @click="downloadFile(result.trajectory_full_url, 'tracking_trajectory.json')"
              >
                下载轨迹 JSON
              </el-button>
              <el-button
                v-if="result.source_input_full_url"
                type="primary"
                link
                @click="openAsset(result.input_mode === 'video' ? result.source_input_full_url : result.first_frame_full_url)"
              >
                查看输入
              </el-button>
              <el-button
                type="primary"
                link
                @click="downloadFile(result.preview_full_url, 'tracking_preview.png')"
              >
                下载预览图
              </el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-row
        v-if="trackingWarningInsight"
        :gutter="20"
      >
        <el-col :xs="24" :sm="24" :md="24" :lg="24">
          <el-card class="warning-panel">
            <div class="warning-panel__head">
              <div>
                <div class="warning-panel__title">趋势预警</div>
                <div class="warning-panel__meta">
                  基于跟踪汇总与轨迹信息生成当前序列的风险等级与目标活跃趋势
                </div>
              </div>
              <el-tag :type="trackingWarningInsight.tagType" effect="dark">
                {{ trackingWarningInsight.levelLabel }}
              </el-tag>
            </div>

            <div class="warning-panel__headline">
              {{ trackingWarningInsight.headline }}
            </div>
            <div class="warning-panel__summary">
              {{ trackingWarningInsight.summary }}
            </div>

            <div class="warning-chip-row">
              <div class="warning-chip">
                <span>跟踪成功率</span>
                <strong>{{ trackingWarningInsight.trackingRatio }}%</strong>
              </div>
              <div class="warning-chip">
                <span>活跃度趋势</span>
                <strong>{{ trackingWarningInsight.activityTrendText }}</strong>
              </div>
              <div class="warning-chip">
                <span>主导类别</span>
                <strong>{{ trackingWarningInsight.dominantLabel }}</strong>
              </div>
              <div class="warning-chip">
                <span>最长轨迹覆盖</span>
                <strong>{{ trackingWarningInsight.topTrackCoverage }}%</strong>
              </div>
            </div>

            <div class="warning-reason-row">
              <span
                v-for="reason in trackingWarningInsight.reasons"
                :key="reason"
                class="warning-reason"
              >
                {{ reason }}
              </span>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-row
        v-if="resultSummary"
        :gutter="20"
      >
        <el-col :xs="24" :sm="24" :md="24" :lg="24">
          <div class="tracking-metric-row">
            <div class="tracking-metric-card">
              <div class="tracking-metric-card__label">唯一轨迹数</div>
              <div class="tracking-metric-card__value">{{ resultSummary.unique_track_count || 0 }}</div>
              <div class="tracking-metric-card__desc">跨全序列持续存在的 track id 数量</div>
            </div>
            <div class="tracking-metric-card">
              <div class="tracking-metric-card__label">累计检测数</div>
              <div class="tracking-metric-card__value">{{ resultSummary.total_detections || 0 }}</div>
              <div class="tracking-metric-card__desc">所有帧内检测到的目标总量</div>
            </div>
            <div class="tracking-metric-card">
              <div class="tracking-metric-card__label">最大并发轨迹</div>
              <div class="tracking-metric-card__value">{{ resultSummary.max_concurrent_tracks || 0 }}</div>
              <div class="tracking-metric-card__desc">单帧同时存在的最多目标数</div>
            </div>
            <div class="tracking-metric-card">
              <div class="tracking-metric-card__label">标签种类数</div>
              <div class="tracking-metric-card__value">{{ Object.keys(resultSummary.label_histogram || {}).length }}</div>
              <div class="tracking-metric-card__desc">目标类别复杂度的一个侧面指标</div>
            </div>
          </div>
        </el-col>
      </el-row>

      <el-row
        v-if="resultSummary"
        :gutter="20"
      >
        <el-col :xs="24" :sm="24" :md="12" :lg="12">
          <el-card class="result-card">
            <template #header>
              <div class="result-card__head">
                <span>帧级状态结构</span>
                <span class="result-card__meta">成功 / 丢失</span>
              </div>
            </template>
            <v-chart
              class="analytics-chart"
              :option="trackingStatusChartOption"
              autoresize
            />
          </el-card>
        </el-col>
        <el-col :xs="24" :sm="24" :md="12" :lg="12">
          <el-card class="result-card">
            <template #header>
              <div class="result-card__head">
                <span>目标类别统计</span>
                <span class="result-card__meta">label histogram</span>
              </div>
            </template>
            <v-chart
              class="analytics-chart"
              :option="trackingLabelChartOption"
              autoresize
            />
          </el-card>
        </el-col>
      </el-row>

      <el-row
        v-if="trajectoryAnalysis"
        :gutter="20"
      >
        <el-col :xs="24" :sm="24" :md="12" :lg="12">
          <el-card class="result-card">
            <template #header>
              <div class="result-card__head">
                <span>逐帧目标数量</span>
                <span class="result-card__meta">轨迹 JSON 统计</span>
              </div>
            </template>
            <v-chart
              class="analytics-chart"
              :option="trackingFrameChartOption"
              autoresize
            />
          </el-card>
        </el-col>
        <el-col :xs="24" :sm="24" :md="12" :lg="12">
          <el-card class="result-card">
            <template #header>
              <div class="result-card__head">
                <span>Top 轨迹存活时长</span>
                <span class="result-card__meta">按出现帧数排序</span>
              </div>
            </template>
            <v-chart
              class="analytics-chart"
              :option="trackingTopTracksChartOption"
              autoresize
            />
          </el-card>
        </el-col>
      </el-row>

      <div
        v-if="trajectoryError"
        class="trajectory-error"
      >
        {{ trajectoryError }}
      </div>
    </div>
    <el-empty v-else description="暂无结果" />
  </div>
</template>

<script>
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { BarChart, LineChart, PieChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from "echarts/components";
import VChart from "vue-echarts";

import Tabinfor from "@/components/Tabinfor";
import { createSrc, createVideoPreview, getCustomModel } from "@/api/upload";
import global from "@/global.vue";
import { fetchBackendAssetBlobUrl } from "@/utils/assetChunkTransport";
import { fetchJsonAsset, summarizeTrajectoryPayload } from "@/utils/frontAnalysis";
import { getLocalSourceUrl, registerLocalSource, registerUploadedSources } from "@/utils/localSourceRegistry";
import { fetchTransportResult } from "@/utils/resultTransport";

use([
  CanvasRenderer,
  BarChart,
  LineChart,
  PieChart,
  GridComponent,
  LegendComponent,
  TooltipComponent,
]);

const IMAGE_SUFFIXES = [
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
const VIDEO_SUFFIXES = [
  "mp4",
  "avi",
  "mov",
  "mkv",
  "m4v",
  "webm",
  "MP4",
  "AVI",
  "MOV",
  "MKV",
  "M4V",
  "WEBM",
];
const ACCEPT_SUFFIXES = [
  ...IMAGE_SUFFIXES.map((suffix) => `.${suffix.toLowerCase()}`),
  ...VIDEO_SUFFIXES.map((suffix) => `.${suffix.toLowerCase()}`),
];
const LOCAL_PREVIEW_SAFE_VIDEO_SUFFIXES = ["mp4", "webm", "m4v"];

function roundMetric(value, digits = 2) {
  if (!Number.isFinite(Number(value))) {
    return 0;
  }
  const factor = 10 ** digits;
  return Math.round(Number(value) * factor) / factor;
}

function safeAverage(values) {
  const list = Array.isArray(values) ? values.filter((value) => Number.isFinite(Number(value))) : [];
  if (!list.length) {
    return 0;
  }
  return list.reduce((sum, value) => sum + Number(value), 0) / list.length;
}

function buildTrackingWarningInsight(summary, trajectoryAnalysis) {
  if (!summary) {
    return null;
  }

  const totalFrames = Number(summary.total_frames) || 0;
  const trackedFrames = Number(summary.tracked_frames) || 0;
  const lostFrames = Number(summary.lost_frames) || 0;
  const meanConfidence = roundMetric(Number(summary.mean_confidence) || 0, 3);
  const trackingRatio = roundMetric(
    Number.isFinite(Number(summary.tracking_ratio))
      ? (Number(summary.tracking_ratio) * 100)
      : ((trackedFrames / Math.max(1, totalFrames)) * 100),
    2,
  );
  const lostRatio = roundMetric((lostFrames / Math.max(1, totalFrames)) * 100, 2);

  const frameCounts = trajectoryAnalysis?.frameCounts || [];
  const startWindow = frameCounts.slice(0, Math.min(5, frameCounts.length)).map((item) => item.value);
  const endWindow = frameCounts.slice(Math.max(0, frameCounts.length - 5)).map((item) => item.value);
  const startAvg = safeAverage(startWindow);
  const endAvg = safeAverage(endWindow);
  const activityChange = startAvg
    ? roundMetric(((endAvg - startAvg) / startAvg) * 100, 2)
    : 0;

  const labelEntries = Object.entries(summary.label_histogram || {}).sort((a, b) => Number(b[1]) - Number(a[1]));
  const dominantLabel = labelEntries[0]?.[0] || "暂无";
  const dominantCount = Number(labelEntries[0]?.[1]) || 0;
  const topTrackCoverage = roundMetric(
    ((trajectoryAnalysis?.topTracks?.[0]?.count || 0) / Math.max(1, totalFrames)) * 100,
    2,
  );

  let riskScore = 0;
  if (trackingRatio < 75) {
    riskScore += 2;
  } else if (trackingRatio < 88) {
    riskScore += 1;
  }
  if (lostRatio > 20) {
    riskScore += 2;
  } else if (lostRatio > 10) {
    riskScore += 1;
  }
  if (activityChange <= -25) {
    riskScore += 2;
  } else if (activityChange <= -10) {
    riskScore += 1;
  }
  if (meanConfidence < 0.55) {
    riskScore += 1;
  }
  if (topTrackCoverage < 35 && totalFrames >= 10) {
    riskScore += 1;
  }

  let levelLabel = "低风险";
  let tagType = "success";
  let headline = "当前序列整体跟踪稳定，未见明显异常趋势。";
  if (riskScore >= 5) {
    levelLabel = "高风险预警";
    tagType = "danger";
    headline = "当前序列存在明显失跟或目标活跃度衰减，建议优先复核。";
  } else if (riskScore >= 3) {
    levelLabel = "中风险预警";
    tagType = "warning";
    headline = "当前序列出现一定程度波动，建议结合结果视频重点查看后段帧。";
  }

  let activityTrendText = "平稳";
  if (activityChange >= 10) {
    activityTrendText = `上升 ${activityChange}%`;
  } else if (activityChange <= -10) {
    activityTrendText = `下降 ${Math.abs(activityChange)}%`;
  }

  return {
    levelLabel,
    tagType,
    headline,
    summary: `共 ${totalFrames} 帧，成功跟踪 ${trackedFrames} 帧，丢失 ${lostFrames} 帧；当前主导类别为 ${dominantLabel}，出现 ${dominantCount} 次。`,
    trackingRatio,
    dominantLabel,
    topTrackCoverage,
    activityTrendText,
    reasons: [
      `丢失帧占比 ${lostRatio}%`,
      `平均置信度 ${roundMetric(meanConfidence * 100, 2)}%`,
      `前后段平均目标数 ${roundMetric(startAvg, 2)} -> ${roundMetric(endAvg, 2)}`,
      `最长轨迹覆盖 ${topTrackCoverage}% 帧序列`,
    ],
  };
}

export default {
  name: "Tracking",
  components: { Tabinfor, VChart },
  data() {
    return {
      fileList: [],
      sortedNames: [],
      modelPathArr: [],
      uploadSrc: {
        model_path: "",
      },
      sam3PromptPreset: "vehicle",
      sam3CustomPrompt: "",
      sam3PromptOptions: [
        { label: "车辆", value: "vehicle" },
        { label: "船只", value: "ship" },
        { label: "飞机", value: "airplane" },
        { label: "建筑物", value: "building" },
        { label: "储气罐", value: "storage tank" },
        { label: "自定义", value: "custom" },
      ],
      firstFrame: null,
      rect: { x: 0, y: 0, w: 0, h: 0 },
      isDrawing: false,
      startX: 0,
      startY: 0,
      running: false,
      result: null,
      global: {
        BASEURL: global.BASEURL,
      },
      inputMode: "image_sequence",
      videoPreviewLoading: false,
      videoPreviewPromise: null,
      videoPreviewTicket: 0,
      preparedVideoUpload: null,
      remoteInputVideoUrl: "",
      videoPreviewErrors: {
        input: false,
        source: false,
        output: false,
      },
      trajectoryPayload: null,
      trajectoryAnalysis: null,
      trajectoryError: "",
      trackingJobId: "",
      trackingJobStatus: "",
      trackingJobMessage: "",
      trackingElapsedSec: 0,
      trackingPollCount: 0,
      trackingPollTimer: null,
    };
  },
  computed: {
    acceptString() {
      return ACCEPT_SUFFIXES.join(",");
    },
    isVideoInput() {
      return this.inputMode === "video";
    },
    inputPreviewUrl() {
      return this.remoteInputVideoUrl || this.firstFrame || "";
    },
    canStart() {
      const hasValidInput = this.isVideoInput ? this.fileList.length === 1 : this.fileList.length >= 2;
      return hasValidInput
        && (!this.isSam3Model || Boolean(this.sam3PromptText))
        && (!this.requiresInitialRect || (this.rect.w > 0 && this.rect.h > 0));
    },
    resultSummary() {
      return (this.result && this.result.summary) || null;
    },
    resultInputPreviewSrc() {
      if (!this.result) {
        return "";
      }
      return this.result.first_frame_full_url;
    },
    resultPreviewImageSrc() {
      if (!this.result) {
        return "";
      }
      return this.result.preview_full_url;
    },
    selectedModel() {
      return this.modelPathArr.find((item) => item.model_path === this.uploadSrc.model_path) || null;
    },
    isSam3Model() {
      return (this.selectedModel?.model_path || "").includes("/tracking/sam3_prompt");
    },
    sam3PromptText() {
      return this.sam3PromptPreset === "custom"
        ? String(this.sam3CustomPrompt || "").trim()
        : this.sam3PromptPreset;
    },
    trackingStatusChartOption() {
      const summary = this.resultSummary || {};
      return {
        tooltip: { trigger: "item" },
        legend: { bottom: 0 },
        series: [
          {
            type: "pie",
            radius: ["38%", "68%"],
            data: [
              { name: "成功帧", value: summary.tracked_frames || 0, itemStyle: { color: "#16a34a" } },
              { name: "丢失帧", value: summary.lost_frames || 0, itemStyle: { color: "#dc2626" } },
            ],
            label: { formatter: "{b}\n{d}%" },
          },
        ],
      };
    },
    trackingLabelChartOption() {
      const entries = Object.entries(this.resultSummary?.label_histogram || {});
      return {
        tooltip: { trigger: "axis" },
        grid: { left: 50, right: 20, top: 20, bottom: 50 },
        xAxis: {
          type: "category",
          data: entries.map(([name]) => name),
          axisLabel: {
            interval: 0,
            rotate: 18,
          },
        },
        yAxis: { type: "value", name: "目标数" },
        series: [
          {
            type: "bar",
            data: entries.map(([, value]) => value),
            itemStyle: { color: "#2563eb", borderRadius: [6, 6, 0, 0] },
          },
        ],
      };
    },
    trackingFrameChartOption() {
      const frameCounts = this.trajectoryAnalysis?.frameCounts || [];
      return {
        tooltip: { trigger: "axis" },
        grid: { left: 52, right: 24, top: 20, bottom: 42 },
        xAxis: { type: "category", data: frameCounts.map((item) => item.frame) },
        yAxis: { type: "value", name: "目标数" },
        series: [
          {
            type: "line",
            smooth: true,
            data: frameCounts.map((item) => item.value),
            itemStyle: { color: "#0f766e" },
            areaStyle: { color: "rgba(15, 118, 110, 0.18)" },
          },
        ],
      };
    },
    trackingTopTracksChartOption() {
      const topTracks = this.trajectoryAnalysis?.topTracks || [];
      return {
        tooltip: { trigger: "axis" },
        grid: { left: 52, right: 20, top: 20, bottom: 50 },
        xAxis: {
          type: "category",
          data: topTracks.map((item) => `#${item.id}`),
          axisLabel: {
            interval: 0,
          },
        },
        yAxis: { type: "value", name: "出现帧数" },
        series: [
          {
            type: "bar",
            data: topTracks.map((item) => item.count),
            itemStyle: { color: "#7c3aed", borderRadius: [6, 6, 0, 0] },
          },
        ],
      };
    },
    trackingWarningInsight() {
      return buildTrackingWarningInsight(this.resultSummary, this.trajectoryAnalysis);
    },
    trackingJobStatusText() {
      const map = {
        queued: "排队中",
        running: "运行中",
        succeeded: "已完成",
        failed: "失败",
      };
      return map[this.trackingJobStatus] || (this.running ? "提交中" : "待提交");
    },
    trackingJobTagType() {
      if (this.trackingJobStatus === "failed") {
        return "danger";
      }
      if (this.trackingJobStatus === "succeeded") {
        return "success";
      }
      if (this.trackingJobStatus === "queued") {
        return "warning";
      }
      return "info";
    },
    isTrackingJobTerminal() {
      return this.trackingJobStatus === "succeeded" || this.trackingJobStatus === "failed";
    },
    trackingProgressPercent() {
      if (this.trackingJobStatus === "succeeded") {
        return 100;
      }
      if (this.trackingJobStatus === "failed") {
        return 100;
      }
      if (this.trackingJobStatus === "running") {
        return Math.min(92, 24 + this.trackingPollCount * 7);
      }
      if (this.trackingJobStatus === "queued") {
        return Math.min(24, 8 + this.trackingPollCount * 4);
      }
      return this.running ? 8 : 0;
    },
    requiresInitialRect() {
      const modelPath = (this.selectedModel && this.selectedModel.model_path) || "";
      return !(
        modelPath.includes("/tracking/botsort")
        || modelPath.includes("/tracking/botsort_official")
        || modelPath.includes("/tracking/sam3_prompt")
        || modelPath.endsWith(":botsort")
        || modelPath.endsWith(":botsort_official")
        || modelPath.endsWith(":botsort_engineering")
      );
    },
  },
  created() {
    this.fetchModels();
  },
  beforeUnmount() {
    this.stopTrackingPolling();
    this.revokeFirstFrameUrl();
  },
  methods: {
    fetchModels() {
      getCustomModel("tracking").then((res) => {
        const currentModels = res.data.data || [];
        this.modelPathArr = currentModels.filter((item) => {
          const path = item.model_path || "";
          return path.includes("/tracking/botsort_official") || path.includes("/tracking/sam3_prompt");
        }).sort((a, b) => {
          const aOfficial = (a.model_path || "").includes("/tracking/botsort_official");
          const bOfficial = (b.model_path || "").includes("/tracking/botsort_official");
          if (aOfficial !== bOfficial) {
            return Number(bOfficial) - Number(aOfficial);
          }
          const aSam3 = (a.model_path || "").includes("/tracking/sam3_prompt");
          const bSam3 = (b.model_path || "").includes("/tracking/sam3_prompt");
          if (aSam3 !== bSam3) {
            return Number(aSam3) - Number(bSam3);
          }
          return Number(bOfficial) - Number(aOfficial);
        });
        if (this.modelPathArr.length > 0) {
          this.uploadSrc.model_path = this.modelPathArr[0].model_path;
        }
      }).catch(() => {});
    },
    clearQueue() {
      this.running = false;
      this.revokeFirstFrameUrl();
      this.fileList = [];
      this.sortedNames = [];
      this.firstFrame = null;
      this.inputMode = "image_sequence";
      this.rect = { x: 0, y: 0, w: 0, h: 0 };
      this.result = null;
      this.preparedVideoUpload = null;
      this.remoteInputVideoUrl = "";
      this.videoPreviewLoading = false;
      this.videoPreviewPromise = null;
      this.videoPreviewTicket += 1;
      this.videoPreviewErrors = {
        input: false,
        source: false,
        output: false,
      };
      this.trajectoryPayload = null;
      this.trajectoryAnalysis = null;
      this.trajectoryError = "";
      this.stopTrackingPolling();
      this.trackingJobId = "";
      this.trackingJobStatus = "";
      this.trackingJobMessage = "";
      this.trackingElapsedSec = 0;
      this.trackingPollCount = 0;
      if (this.$refs.upload) {
        this.$refs.upload.clearFiles();
      }
      if (this.$refs.refFolder) {
        this.$refs.refFolder.value = "";
      }
      this.$message.success("清除成功");
    },
    folderClick() {
      this.$refs.refFolder.click();
    },
    checkFile(file, fileList) {
      const normalized = this.normalizeInputItems(fileList);
      this.fileList = normalized.items;
      this.inputMode = normalized.mode;
      this.refreshInputPreview();
    },
    uploadFolder() {
      const normalized = this.mergeFileList(
        this.fileList,
        Array.from(this.$refs.refFolder.files || []),
      );
      this.fileList = normalized.items;
      this.inputMode = normalized.mode;
      this.refreshInputPreview();
    },
    normalizeInputItems(fileList) {
      const accepted = [];
      let mode = "";
      for (const item of fileList) {
        const raw = item.raw || item;
        const fileKind = this.getSupportedKind(raw);
        if (!fileKind) {
          continue;
        }
        if (!mode) {
          mode = fileKind;
        }
        if (fileKind !== mode) {
          this.$message.warning("目标跟踪仅支持上传图像序列或单个视频文件，请勿混合上传");
          continue;
        }
        if (mode === "video" && accepted.length >= 1) {
          this.$message.warning("目标跟踪当前仅支持上传 1 个视频文件");
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
      return {
        items: accepted,
        mode: mode === "video" ? "video" : "image_sequence",
      };
    },
    mergeFileList(existingList, incomingFiles) {
      const merged = [...existingList];
      for (const file of incomingFiles) {
        if (!this.getSupportedKind(file)) {
          continue;
        }
        merged.push({
          name: file.name,
          raw: file,
          status: "ready",
          uid: `${Date.now()}_${Math.random()}`,
        });
      }
      return this.normalizeInputItems(merged);
    },
    getSupportedKind(file) {
      const suffix = file.name.substring(file.name.lastIndexOf(".") + 1);
      if (IMAGE_SUFFIXES.includes(suffix)) {
        return "image";
      }
      if (VIDEO_SUFFIXES.includes(suffix)) {
        if (!LOCAL_PREVIEW_SAFE_VIDEO_SUFFIXES.includes(suffix.toLowerCase())) {
          this.$message.warning("当前浏览器对该视频格式的预览兼容性有限，处理完成后将优先提供标准化 MP4 预览");
        }
        return "video";
      }
      this.$message.error(`文件 ${file.name} 格式不支持，请上传常见影像或视频格式`);
      return "";
    },
    refreshInputPreview() {
      const ordered = [...this.fileList].sort((a, b) => (
        (a.name || "").localeCompare(b.name || "", undefined, { numeric: true, sensitivity: "base" })
      ));
      this.revokeFirstFrameUrl();
      this.fileList = ordered;
      this.sortedNames = ordered.map((item) => item.name);
      this.rect = { x: 0, y: 0, w: 0, h: 0 };
      this.result = null;
      this.preparedVideoUpload = null;
      this.remoteInputVideoUrl = "";
      this.videoPreviewLoading = false;
      this.videoPreviewPromise = null;
      this.videoPreviewTicket += 1;
      this.videoPreviewErrors = {
        input: false,
        source: false,
        output: false,
      };
      this.trajectoryPayload = null;
      this.trajectoryAnalysis = null;
      this.trajectoryError = "";
      this.stopTrackingPolling();
      this.trackingJobId = "";
      this.trackingJobStatus = "";
      this.trackingJobMessage = "";
      this.trackingElapsedSec = 0;
      this.trackingPollCount = 0;
      this.firstFrame = ordered.length ? URL.createObjectURL(ordered[0].raw) : null;
      if (this.inputMode === "video" && ordered.length === 1) {
        this.prepareVideoPreview(ordered[0]);
      }
    },
    revokeFirstFrameUrl() {
      if (this.firstFrame && this.firstFrame.startsWith("blob:")) {
        URL.revokeObjectURL(this.firstFrame);
      }
    },
    prepareVideoPreview(fileItem) {
      if (!fileItem || !fileItem.raw || this.inputMode !== "video") {
        return null;
      }
      const ticket = ++this.videoPreviewTicket;
      this.videoPreviewLoading = true;
      this.remoteInputVideoUrl = "";
      this.preparedVideoUpload = null;
      this.videoPreviewErrors.input = false;
      this.videoPreviewPromise = (async () => {
        const formData = new FormData();
        formData.append("files", fileItem.raw);
        formData.append("type", "目标跟踪");
        const response = await createVideoPreview(formData);
        if (ticket !== this.videoPreviewTicket) {
          return null;
        }
        const responseData = response?.data?.data || null;
        const data = Array.isArray(responseData) ? responseData[0] : responseData;
        if (!data?.src) {
          throw new Error(response?.data?.msg || "视频上传失败");
        }
        registerLocalSource(data.src, fileItem.raw, {
          filename: data.filename,
        });
        this.preparedVideoUpload = [{
          src: data.src,
          filename: data.filename,
          photo_id: data.photo_id,
        }];
        try {
          this.remoteInputVideoUrl = await this.prefixUrl(data.preview_video_path || data.src);
        } catch (error) {
          this.remoteInputVideoUrl = this.firstFrame || "";
        }
        this.videoPreviewErrors.input = false;
        return data;
      })().catch((error) => {
        if (ticket !== this.videoPreviewTicket) {
          return null;
        }
        this.remoteInputVideoUrl = "";
        this.preparedVideoUpload = null;
        console.error(error);
        return null;
      }).finally(() => {
        if (ticket === this.videoPreviewTicket) {
          this.videoPreviewLoading = false;
        }
      });
      return this.videoPreviewPromise;
    },
    startDraw(event) {
      if (!this.firstFrame) {
        return;
      }
      this.isDrawing = true;
      const img = this.$refs.firstFrameImg;
      const bounds = img.getBoundingClientRect();
      this.startX = event.clientX - bounds.left;
      this.startY = event.clientY - bounds.top;
      this.rect = { x: this.startX, y: this.startY, w: 0, h: 0 };
    },
    drawing(event) {
      if (!this.isDrawing) {
        return;
      }
      const img = this.$refs.firstFrameImg;
      const bounds = img.getBoundingClientRect();
      const currentX = event.clientX - bounds.left;
      const currentY = event.clientY - bounds.top;
      this.rect.w = currentX - this.startX;
      this.rect.h = currentY - this.startY;
    },
    endDraw() {
      if (!this.isDrawing) {
        return;
      }
      this.isDrawing = false;
      if (this.rect.w < 0) {
        this.rect.x += this.rect.w;
        this.rect.w = Math.abs(this.rect.w);
      }
      if (this.rect.h < 0) {
        this.rect.y += this.rect.h;
        this.rect.h = Math.abs(this.rect.h);
      }
    },
    async uploadSequence(fileList) {
      const formData = new FormData();
      for (const item of fileList) {
        formData.append("files", item.raw || item);
      }
      formData.append("type", "目标跟踪");
      const response = await createSrc(formData);
      const uploaded = response.data.data || [];
      registerUploadedSources(uploaded, fileList);
      return uploaded;
    },
    async startTracking() {
      if (!this.canStart) {
        this.$message.error(this.requiresInitialRect
          ? "请先上传有效输入并框选目标"
          : "请先上传至少 2 帧图像，或 1 个视频文件");
        return;
      }
      if (!this.uploadSrc.model_path) {
        this.$message.error("请选择跟踪模型");
        return;
      }
      if (this.isSam3Model && !this.sam3PromptText) {
        this.$message.error("请输入开放词汇目标");
        return;
      }

      this.running = true;
      this.videoPreviewErrors.source = false;
      this.videoPreviewErrors.output = false;
      try {
        if (this.isVideoInput && this.videoPreviewPromise) {
          await this.videoPreviewPromise;
        }
        const uploaded = (this.isVideoInput && this.preparedVideoUpload?.length)
          ? this.preparedVideoUpload
          : await this.uploadSequence(this.fileList);
        if ((!this.isVideoInput && uploaded.length < 2) || (this.isVideoInput && uploaded.length < 1)) {
          throw new Error(this.isVideoInput
            ? "上传结果缺少有效视频文件，无法执行目标跟踪"
            : "上传结果不足 2 帧，无法执行目标跟踪");
        }
        const ordered = this.isVideoInput ? [...uploaded] : [...uploaded].sort((a, b) => (
          (a.filename || "").localeCompare(b.filename || "", undefined, { numeric: true, sensitivity: "base" })
        ));
        const payload = {
          model_path: this.uploadSrc.model_path,
          list: ordered.map((item) => ({
            src: item.src,
            filename: item.filename,
          })),
        };
        if (this.isSam3Model) {
          payload.prompt_text = this.sam3PromptText;
        }
        if (this.requiresInitialRect) {
          const img = this.$refs.firstFrameImg;
          const scaleX = img.naturalWidth / img.clientWidth;
          const scaleY = img.naturalHeight / img.clientHeight;
          payload.rect = [
            Math.round(this.rect.x * scaleX),
            Math.round(this.rect.y * scaleY),
            Math.round(this.rect.w * scaleX),
            Math.round(this.rect.h * scaleY),
          ];
        }
        const submitted = await this.submitTrackingJob(payload);
        this.trackingJobId = submitted.job_id || "";
        this.trackingJobStatus = submitted.status || "queued";
        this.trackingJobMessage = submitted.message || "目标跟踪任务已提交";
        this.trackingElapsedSec = 0;
        this.trackingPollCount = 0;
        if (!this.trackingJobId) {
          throw new Error("后端未返回目标跟踪任务 ID");
        }
        await this.pollTrackingJob(this.trackingJobId);
      } catch (error) {
        console.error(error);
        const message = error?.response?.data?.msg || error?.message || "目标跟踪失败";
        this.$message.error(message);
      } finally {
        this.running = false;
      }
    },
    backendUrl(path) {
      return `${String(this.global.BASEURL || "").replace(/\/+$/, "")}${path}`;
    },
    async requestTrackingJson(path, options = {}) {
      const headers = {
        Accept: "application/json",
        ...(options.headers || {}),
      };
      if (options.body && !headers["Content-Type"]) {
        headers["Content-Type"] = "application/json";
      }
      const response = await fetch(this.backendUrl(path), {
        ...options,
        headers,
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || payload?.success !== true) {
        throw new Error(payload?.msg || `请求失败 HTTP ${response.status}`);
      }
      return payload.data || {};
    },
    async submitTrackingJob(payload) {
      this.stopTrackingPolling();
      this.trackingJobStatus = "queued";
      this.trackingJobMessage = "正在提交目标跟踪任务";
      this.trackingPollCount = 0;
      const chunkSize = encodeURIComponent(String(global.RESULT_CHUNK_SIZE || 65536));
      return this.requestTrackingJson(`/api/analysis/tracking/async?chunk_size=${chunkSize}`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    waitTrackingPoll(ms) {
      return new Promise((resolve) => {
        this.trackingPollTimer = window.setTimeout(resolve, ms);
      });
    },
    stopTrackingPolling() {
      if (this.trackingPollTimer) {
        window.clearTimeout(this.trackingPollTimer);
        this.trackingPollTimer = null;
      }
    },
    async pollTrackingJob(jobId) {
      while (this.running && jobId === this.trackingJobId) {
        const job = await this.requestTrackingJson(`/api/analysis/tracking/jobs/${jobId}`, {
          method: "GET",
        });
        this.trackingPollCount += 1;
        this.trackingJobStatus = job.status || "";
        this.trackingJobMessage = job.message || "";
        this.trackingElapsedSec = Number(job.elapsed_sec || 0);
        if (job.status === "failed") {
          throw new Error(job.message || job.error || "目标跟踪失败");
        }
        if (job.status === "succeeded") {
          const data = await fetchTransportResult(job.transport_manifest);
          await this.applyTrackingResult(data || {});
          this.$message.success(job.message || "目标跟踪完成");
          return;
        }
        await this.waitTrackingPoll(3000);
      }
    },
    async applyTrackingResult(data) {
      if (!data.preview_path || !data.output_video_path) {
        throw new Error("跟踪结果不完整");
      }
      this.result = {
        ...data,
        record: data.record || null,
        first_frame_full_url: await this.prefixUrl(data.first_frame_input),
        source_input_full_url: await this.prefixUrl(data.source_input_path),
        preview_full_url: await this.prefixUrl(data.preview_path),
        output_video_full_url: await this.prefixUrl(data.output_video_path),
        trajectory_full_url: await this.prefixUrl(data.trajectory_path),
      };
      await this.loadTrajectoryAnalysis(this.result.trajectory_full_url);
    },
    async prefixUrl(path) {
      if (!path) {
        return "";
      }
      return fetchBackendAssetBlobUrl(path);
    },
    downloadFile(url, filename) {
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.click();
    },
    openAsset(url) {
      if (!url) {
        return;
      }
      window.open(url, "_blank", "noopener");
    },
    async loadTrajectoryAnalysis(url) {
      this.trajectoryPayload = null;
      this.trajectoryAnalysis = null;
      this.trajectoryError = "";
      if (!url) {
        return;
      }
      try {
        const payload = await fetchJsonAsset(url);
        this.trajectoryPayload = payload;
        this.trajectoryAnalysis = summarizeTrajectoryPayload(payload);
      } catch (error) {
        console.error(error);
        this.trajectoryError = "轨迹 JSON 已生成，但详细统计暂时无法读取。";
      }
    },
    handleVideoPreviewError(type) {
      this.videoPreviewErrors[type] = true;
    },
    clearVideoPreviewError(type) {
      this.videoPreviewErrors[type] = false;
    },
    formatRatio(value) {
      if (value === null || value === undefined || Number.isNaN(Number(value))) {
        return "暂无";
      }
      return `${(Number(value) * 100).toFixed(1)}%`;
    },
    formatNumber(value) {
      if (value === null || value === undefined || Number.isNaN(Number(value))) {
        return "暂无";
      }
      return Number(value).toFixed(2);
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

.tracking-page {
  position: relative;
}

.clear-queue {
  position: absolute;
  left: 20px;
  top: 24px;
  z-index: 100;
}

.upload-center {
  text-align: center;
}

.sequence-summary {
  margin-top: 20px;
  padding: 16px 18px;
  border-radius: 14px;
  background: var(--theme-surface-secondary);
  border: 1px solid var(--theme-border-color);
}

.summary-head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 12px;
}

.summary-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

.summary-meta {
  margin-top: 4px;
  font-size: 14px;
  color: var(--text-secondary);
}

.summary-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
}

.summary-chip {
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(19, 126, 255, 0.08);
  color: var(--theme-active-color);
  font-size: 13px;
}

.summary-chip--muted {
  background: rgba(0, 0, 0, 0.04);
  color: var(--text-secondary);
}

.model-row {
  margin-top: 18px;
}

.sam3-prompt-row {
  margin-top: 12px;
}

.sam3-prompt-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 10px;
}

.sam3-prompt-label {
  font-size: 14px;
  color: var(--theme-heading-color);
}

.sam3-prompt-select {
  width: 260px;
}

.sam3-prompt-input {
  width: 280px;
}

.sam3-prompt-hint {
  font-size: 12px;
  color: var(--theme-color);
}

.custom-model {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.model-plan-tip {
  width: 100%;
  margin-top: 8px;
  color: var(--text-secondary);
  font-size: 13px;
}

.frame-selector {
  margin-top: 24px;
}

.frame-selector--hintonly {
  padding: 16px 18px;
  border-radius: 14px;
  background: var(--theme-surface-secondary);
  border: 1px solid var(--theme-border-color);
}

.frame-selector__hint {
  color: var(--text-secondary);
}

.input-video {
  width: min(100%, 960px);
  margin-top: 12px;
  border-radius: 16px;
  background: #000;
}

.frame-selector__canvas {
  position: relative;
  display: inline-block;
  max-width: 100%;
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid var(--theme-border-color);
}

.frame-selector__image {
  display: block;
  max-width: min(100%, 960px);
  max-height: 560px;
  object-fit: contain;
  user-select: none;
}

.frame-selector__rect {
  position: absolute;
  border: 2px solid #19be6b;
  background: rgba(25, 190, 107, 0.12);
  pointer-events: none;
}

.rect-info {
  margin-top: 12px;
  color: var(--text-secondary);
}

.handle-button {
  margin-top: 24px;
  text-align: center;
}

.tracking-job-panel {
  margin: 18px auto 0;
  max-width: 760px;
  padding: 14px 16px;
  border-radius: 8px;
  border: 1px solid var(--theme-border-color);
  background: var(--theme-surface-secondary);
}

.tracking-job-panel__head,
.tracking-job-panel__foot {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
}

.tracking-job-panel__meta,
.tracking-job-panel__foot {
  color: var(--text-secondary);
  font-size: 14px;
}

.tracking-job-panel__bar {
  position: relative;
  height: 8px;
  margin-top: 12px;
  overflow: hidden;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.22);
}

.tracking-job-panel__bar span {
  position: absolute;
  inset: 0 auto 0 0;
  min-width: 8px;
  border-radius: inherit;
  background: linear-gradient(90deg, #2563eb, #16a34a);
  transition: width 0.35s ease;
}

.tracking-job-panel__bar--active span {
  background:
    linear-gradient(90deg, #2563eb, #16a34a),
    repeating-linear-gradient(
      45deg,
      rgba(255, 255, 255, 0.2) 0,
      rgba(255, 255, 255, 0.2) 8px,
      rgba(255, 255, 255, 0) 8px,
      rgba(255, 255, 255, 0) 16px
    );
}

.tracking-job-panel__foot {
  margin-top: 10px;
  font-size: 13px;
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

.result-summary {
  padding-right: 40px;
  font-weight: 600;
  color: var(--theme-active-color);
}

.result-card {
  margin-bottom: 20px;
}

.result-card__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.result-card__meta {
  color: var(--text-secondary);
  font-size: 13px;
}

.result-preview {
  width: 100%;
  border-radius: 14px;
  overflow: hidden;
}

.result-video {
  width: 100%;
  border-radius: 14px;
  background: #000;
}

.video-preview-fallback {
  margin-top: 12px;
  padding: 14px 16px;
  border-radius: 12px;
  border: 1px solid rgba(255, 160, 0, 0.25);
  background: rgba(255, 248, 230, 0.9);
  color: #8a5a00;
  line-height: 1.6;
}

.metric-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 18px;
  margin-top: 14px;
  color: var(--text-secondary);
}

.result-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 20px;
  margin-top: 12px;
}

.tracking-metric-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px;
  margin-bottom: 20px;
}

.tracking-metric-card {
  padding: 16px;
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(244, 247, 255, 0.98));
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.tracking-metric-card__label {
  color: var(--text-secondary);
  font-size: 13px;
}

.tracking-metric-card__value {
  margin-top: 8px;
  font-size: 30px;
  line-height: 1.1;
  color: var(--theme-heading-color);
  font-family: var(--theme-display-fontfamily);
}

.tracking-metric-card__desc {
  margin-top: 8px;
  color: var(--text-secondary);
  font-size: 12px;
}

.analytics-chart {
  width: 100%;
  height: 320px;
}

.trajectory-error {
  margin-top: 4px;
  color: #b91c1c;
  font-size: 13px;
}

.warning-panel {
  margin-top: 0;
  margin-bottom: 20px;
  border-radius: 18px;
  border: 1px solid rgba(245, 158, 11, 0.22);
  background:
    radial-gradient(circle at top right, rgba(245, 158, 11, 0.12), transparent 32%),
    linear-gradient(180deg, rgba(255, 251, 235, 0.98), rgba(255, 255, 255, 0.98));
}

.warning-panel__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 14px;
}

.warning-panel__title {
  font-size: 18px;
  font-weight: 700;
  color: var(--theme-heading-color);
}

.warning-panel__meta {
  margin-top: 6px;
  color: var(--text-secondary);
  font-size: 13px;
}

.warning-panel__headline {
  margin-top: 16px;
  font-size: 18px;
  font-weight: 700;
  color: #9a3412;
}

.warning-panel__summary {
  margin-top: 10px;
  color: var(--text-primary);
  line-height: 1.8;
}

.warning-chip-row {
  margin-top: 18px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.warning-chip {
  padding: 14px 16px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(148, 163, 184, 0.18);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.warning-chip span {
  font-size: 13px;
  color: var(--text-secondary);
}

.warning-chip strong {
  font-size: 22px;
  color: var(--theme-heading-color);
  font-family: var(--theme-display-fontfamily);
}

.warning-reason-row {
  margin-top: 14px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.warning-reason {
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid rgba(245, 158, 11, 0.18);
  color: #92400e;
  font-size: 13px;
}

@media (max-width: 768px) {
  .clear-queue {
    position: static;
    margin-bottom: 16px;
  }

  .result-summary {
    padding-right: 0;
  }

  .analytics-chart {
    height: 260px;
  }
}
</style>
