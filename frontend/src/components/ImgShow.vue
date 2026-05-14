<template>
  <el-card style="margin-bottom: 10px">
    <el-empty
      v-if="childImgArr.length === 0"
      :image-size="200"
    />

    <div v-else>
      <div v-if="overviewStats" class="analysis-shell">
        <div class="analysis-shell__head">
          <div>
            <div class="analysis-shell__title">结果统计总览</div>
            <div class="analysis-shell__meta">
              共 {{ overviewStats.sampleCount }} 条结果，统计仅依赖前端可见数据计算
            </div>
          </div>
          <el-tag
            effect="dark"
            :type="overviewTagType"
          >
            {{ overviewTagText }}
          </el-tag>
        </div>

        <div class="metric-row">
          <div
            v-for="metric in overviewMetricCards"
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

        <div
          v-if="overviewCharts.length"
          class="chart-grid"
        >
          <el-card
            v-for="chart in overviewCharts"
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

      <div v-if="analysisLoading" class="analysis-loading">
        正在计算统计信息...
      </div>
      <div v-else-if="analysisError" class="analysis-error">
        {{ analysisError }}
      </div>

      <div class="img-display-box">
        <div
          v-for="(item,index) in childImgArr"
          :key="index"
          class="img-display-item"
        >
          <el-divider class="img-divider">
            第<span class="index-number">{{ item.id }}</span>组
          </el-divider>
          <div>
            <el-image
              ref="tableTab"
              class="img-display"
              :src="displaySrc(item, 'before_img')"
              :fit="fit"
              :lazy="false"
              :preview-src-list="[displaySrc(item, 'before_img')]"
              :preview-teleported="true"
              @error="onImageLoadError(item, 'before_img')"
            />

            <div class="img-infor">
              <span>原图</span>
            </div>
          </div>
          <div class="img-display-item__result">
            <div v-if="item.type!=='场景分类'">
              <div style="display: flex;">
                <div>
                  <el-image
                    ref="tableTab"
                    class="img-display"
                    :src="displaySrc(item, 'after_img')"
                    :fit="fit"
                    :lazy="false"
                    :preview-src-list="[displaySrc(item, 'after_img')]"
                    :preview-teleported="true"
                    @error="onImageLoadError(item, 'after_img')"
                  />
                  <div class="img-infor">
                    <span>预测结果</span>
                    <span
                      @click="
                        downloadimgWithWords(
                          item.id,
                          item.after_img,
                          `${item.type}结果图.png`
                        )
                      "
                    ><i class="iconfont icon-xiazai" /></span>
                  </div>
                </div>

                <div
                  v-if="item.type === '地物分类'"
                  style="margin-left: 20px; display: flex; flex-direction: column; justify-content: center;"
                >
                  <h4>类别图例</h4>
                  <div
                    v-if="!item.after_img.includes('pred_')"
                    style="font-size: 14px; line-height: 1.8;"
                  >
                    <div style="display: flex; align-items: center;"><span style="width: 20px; height: 20px; background-color: rgb(0, 0, 0); margin-right: 8px; border: 1px solid #ccc;" /> <span>云 (Cloud)</span></div>
                    <div style="display: flex; align-items: center;"><span style="width: 20px; height: 20px; background-color: rgb(128, 0, 0); margin-right: 8px;" /> <span>阴影 (Shadow)</span></div>
                    <div style="display: flex; align-items: center;"><span style="width: 20px; height: 20px; background-color: rgb(0, 128, 0); margin-right: 8px;" /> <span>雪 (Snow)</span></div>
                    <div style="display: flex; align-items: center;"><span style="width: 20px; height: 20px; background-color: rgb(128, 128, 0); margin-right: 8px;" /> <span>水体 (Water)</span></div>
                    <div style="display: flex; align-items: center;"><span style="width: 20px; height: 20px; background-color: rgb(0, 0, 128); margin-right: 8px;" /> <span>陆地 (Land)</span></div>
                  </div>
                  <div
                    v-else
                    style="font-size: 14px; line-height: 1.8;"
                  >
                    <div style="display: flex; align-items: center;"><span style="width: 20px; height: 20px; background-color: rgb(0, 255, 0); margin-right: 8px;" /> <span>草地 (Grassland)</span></div>
                    <div style="display: flex; align-items: center;"><span style="width: 20px; height: 20px; background-color: rgb(0, 128, 0); margin-right: 8px;" /> <span>林地 (Forest)</span></div>
                    <div style="display: flex; align-items: center;"><span style="width: 20px; height: 20px; background-color: rgb(255, 0, 0); margin-right: 8px;" /> <span>建筑 (Building)</span></div>
                    <div style="display: flex; align-items: center;"><span style="width: 20px; height: 20px; background-color: rgb(255, 255, 0); margin-right: 8px;" /> <span>道路 (Road)</span></div>
                    <div style="display: flex; align-items: center;"><span style="width: 20px; height: 20px; background-color: rgb(255, 0, 255); margin-right: 8px;" /> <span>裸地 (Bareground)</span></div>
                    <div style="display: flex; align-items: center;"><span style="width: 20px; height: 20px; background-color: rgb(0, 191, 255); margin-right: 8px;" /> <span>水体 (Water)</span></div>
                  </div>
                </div>
              </div>
            </div>
            <div
              v-else
              class="img-index"
            >
              <span class="index-number ">{{ classificationSummary(item, index) }}</span>
            </div>

            <div
              v-if="analysisFor(item, index)"
              class="record-analysis"
            >
              <div class="record-analysis__head">
                <div class="record-analysis__title">
                  单条分析
                </div>
                <el-tag size="small">
                  {{ analysisTagText(analysisFor(item, index)) }}
                </el-tag>
              </div>

              <el-descriptions
                :column="2"
                border
                size="small"
              >
                <el-descriptions-item
                  v-for="metric in itemMetricCards(analysisFor(item, index))"
                  :key="metric.label"
                  :label="metric.label"
                >
                  {{ metric.value }}
                </el-descriptions-item>
              </el-descriptions>

              <div
                v-if="itemCharts(analysisFor(item, index)).length"
                class="chart-grid chart-grid--record"
              >
                <el-card
                  v-for="chart in itemCharts(analysisFor(item, index))"
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
          </div>
        </div>
      </div>
    </div>
  </el-card>
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

import { downloadimgWithWords } from "@/utils/download.js";
import { ASSET_PREVIEW_PLACEHOLDER, hydrateAssetPreviews } from "@/utils/assetPreview";
import {
  analyzeClassificationRecord,
  analyzeDetectionRecord,
  analyzeRestorationRecord,
  analyzeSegmentationRecord,
  summarizeClassification,
  summarizeDetection,
  summarizeRestoration,
  summarizeSegmentation,
} from "@/utils/frontAnalysis";
import { resolveRecordSource } from "@/utils/mediaTransport";
import { fetchBackendAssetBlobUrl, getCachedBackendAssetBlobUrl } from "@/utils/assetChunkTransport";
import { isBackendPhotoAssetPath, toBackendAssetUrl } from "@/utils/backendAssetUrl";

use([
  CanvasRenderer,
  BarChart,
  PieChart,
  GridComponent,
  LegendComponent,
  TooltipComponent,
]);

const SUPPORTED_ANALYSIS_TYPES = ["场景分类", "目标检测", "地物分类", "影像超分重建"];

export default {
  name: "Imgshow",
  components: {
    VChart,
  },
  props: {
    imgArr: {
      type: Array,
      default() {
        return [];
      },
    },
  },
  data() {
    return {
      fit: "fill",
      childImgArr: [],
      analysisMap: {},
      overviewStats: null,
      analysisLoading: false,
      analysisError: "",
      analysisToken: 0,
    };
  },
  computed: {
    currentType() {
      return this.childImgArr[0]?.type || "";
    },
    overviewTagText() {
      return this.currentType || "统计";
    },
    overviewTagType() {
      if (this.currentType === "场景分类") {
        return "success";
      }
      if (this.currentType === "地物分类") {
        return "warning";
      }
      if (this.currentType === "目标检测") {
        return "danger";
      }
      if (this.currentType === "影像超分重建") {
        return "info";
      }
      return "";
    },
    overviewMetricCards() {
      if (!this.overviewStats) {
        return [];
      }

      if (this.overviewStats.kind === "classification") {
        const dominant = this.overviewStats.dominantLabels[0];
        return [
          {
            label: "平均 Top1 置信度",
            value: `${this.overviewStats.avgTopScore}%`,
            desc: "每张图最高类别分数均值",
          },
          {
            label: "平均领先差值",
            value: `${this.overviewStats.avgMargin}%`,
            desc: "Top1 与 Top2 的平均差距",
          },
          {
            label: "平均分布熵",
            value: this.overviewStats.avgEntropy,
            desc: "越高表示类别分布越分散",
          },
          {
            label: "最常见标签",
            value: dominant ? dominant.name : "暂无",
            desc: dominant ? `出现 ${dominant.value} 次` : "暂无样本",
          },
        ];
      }

      if (this.overviewStats.kind === "segmentation") {
        const dominant = this.overviewStats.aggregateClassStats[0];
        const dominantLabel = this.overviewStats.dominantClasses[0];
        return [
          {
            label: "主导地物",
            value: dominant ? dominant.name : "暂无",
            desc: dominant ? `总占比 ${dominant.ratio}%` : "暂无样本",
          },
          {
            label: "最常见主类",
            value: dominantLabel ? dominantLabel.name : "暂无",
            desc: dominantLabel ? `${dominantLabel.value} 张影像以其为主` : "暂无样本",
          },
          {
            label: "统计样本数",
            value: this.overviewStats.sampleCount,
            desc: "已完成前端像素统计的结果条目",
          },
          {
            label: "类别数",
            value: this.overviewStats.aggregateClassStats.length,
            desc: "聚合后出现过的地物类别",
          },
        ];
      }

      if (this.overviewStats.kind === "detection") {
        const dominant = this.overviewStats.dominantLabels[0];
        return [
          {
            label: "累计识别目标",
            value: this.overviewStats.totalDetections,
            desc: "全部结果中识别出的目标总数",
          },
          {
            label: "平均每图目标数",
            value: this.overviewStats.averageDetections,
            desc: "衡量场景拥挤程度的基础指标",
          },
          {
            label: "平均置信度",
            value: `${this.overviewStats.averageConfidence}%`,
            desc: "所有识别目标分数的整体均值",
          },
          {
            label: "主导类别",
            value: dominant ? dominant.name : "暂无",
            desc: dominant ? `累计出现 ${dominant.value} 次` : "暂无样本",
          },
        ];
      }

      if (this.overviewStats.kind === "restoration") {
        return [
          {
            label: "平均宽度倍率",
            value: `${this.overviewStats.averageScales.widthRatio}x`,
            desc: "结果图宽度相对输入图的放大倍数",
          },
          {
            label: "平均像素倍率",
            value: `${this.overviewStats.averageScales.pixelRatio}x`,
            desc: "结果图总像素量相对输入图的变化",
          },
          {
            label: "平均清晰度变化",
            value: `${this.metricValueByName("清晰度")}%`,
            desc: "基于拉普拉斯方差的启发式变化",
          },
          {
            label: "平均边缘密度变化",
            value: `${this.metricValueByName("边缘密度")}%`,
            desc: "边缘像素比例变化",
          },
        ];
      }

      return [];
    },
    overviewCharts() {
      if (!this.overviewStats) {
        return [];
      }

      if (this.overviewStats.kind === "classification") {
        return [
          {
            title: "预测标签分布",
            option: this.createPieOption(
              this.overviewStats.dominantLabels,
              "各标签成为 Top1 的次数",
            ),
          },
          {
            title: "平均类别得分 Top 8",
            option: this.createBarOption(
              this.overviewStats.averageScores,
              "value",
              "平均得分 (%)",
            ),
          },
        ];
      }

      if (this.overviewStats.kind === "segmentation") {
        return [
          {
            title: "聚合地物面积占比",
            option: this.createPieOption(
              this.overviewStats.aggregateClassStats.map((item) => ({
                name: item.name,
                value: item.count,
              })),
              "按像素累计的地物占比",
            ),
          },
          {
            title: "主导地物频次",
            option: this.createBarOption(
              this.overviewStats.dominantClasses,
              "value",
              "成为主导类别的影像数",
            ),
          },
        ];
      }

      if (this.overviewStats.kind === "detection") {
        return [
          {
            title: "识别类别分布",
            option: this.createPieOption(
              this.overviewStats.dominantLabels,
              "各类别累计识别次数",
            ),
          },
          {
            title: "置信度分层统计",
            option: this.createBarOption(
              this.overviewStats.confidenceBands,
              "value",
              "目标数量",
            ),
          },
          {
            title: "目标尺度分层",
            option: this.createBarOption(
              this.overviewStats.sizeBands,
              "value",
              "目标数量",
            ),
          },
          {
            title: "各结果目标数量",
            option: this.createBarOption(
              this.overviewStats.imageDetectionCounts,
              "value",
              "目标数",
            ),
          },
        ];
      }

      if (this.overviewStats.kind === "restoration") {
        return [
          {
            title: "平均质量变化",
            option: this.createBarOption(
              this.overviewStats.averageChanges,
              "value",
              "平均变化率 (%)",
            ),
          },
        ];
      }

      return [];
    },
  },
  mounted() {
    this.syncAndAnalyze(this.imgArr);
  },
  watch: {
    imgArr: {
      deep: true,
      handler(value) {
        this.syncAndAnalyze(value);
      },
    },
  },
  methods: {
    downloadimgWithWords,
    metricValueByName(name) {
      const item = (this.overviewStats?.averageChanges || []).find((entry) => entry.name === name);
      return item ? item.value : 0;
    },
    analysisKey(item, index) {
      return `${item.id ?? index}`;
    },
    displaySrc(item, field) {
      const preview = item && item[`_${field}_preview`];
      if (preview) {
        return preview;
      }
      const source = resolveRecordSource(item, field);
      if (source) {
        return source;
      }
      const fallback = this.visualPayloadAsset(item, field);
      if (fallback) {
        return fallback;
      }
      return (item && item[`_${field}_preview`]) || ASSET_PREVIEW_PLACEHOLDER;
    },
    visualPayloadAsset(item, field) {
      const legacyAssets = item?.visual_payload?.legacy_assets || {};
      const source = item?.visual_payload?.source || {};
      const result = item?.visual_payload?.result || {};
      if (field === "before_img") {
        return this.cachedOrQueueAsset(item, field, legacyAssets.source_primary || source.primary?.asset_path || "");
      }
      if (field === "after_img") {
        return this.cachedOrQueueAsset(item, field, legacyAssets.primary_result || result.mask_path || "");
      }
      return "";
    },
    cachedOrQueueAsset(item, field, path) {
      if (!path) {
        return "";
      }
      if (!isBackendPhotoAssetPath(path)) {
        return toBackendAssetUrl(path);
      }
      const cached = getCachedBackendAssetBlobUrl(path);
      if (cached) {
        return cached;
      }
      fetchBackendAssetBlobUrl(path)
        .then((url) => {
          this.$set(item, `_${field}_preview`, url);
        })
        .catch(() => {});
      return ASSET_PREVIEW_PLACEHOLDER;
    },
    onImageLoadError(item, field) {
      const url = this.displaySrc(item, field);
      if (!url) {
        return;
      }
      console.error("[GeoView] image load failed", {
        field,
        url,
        recordId: item?.id,
        type: item?.type,
      });
    },
    async syncAndAnalyze(value) {
      this.childImgArr = Array.isArray(value) ? value : [];
      await this.refreshPreviews();
      this.refreshAnalysis();
    },
    refreshPreviews() {
      return hydrateAssetPreviews(this.childImgArr, ["before_img", "after_img"], 420);
    },
    async refreshAnalysis() {
      const currentItems = Array.isArray(this.childImgArr) ? this.childImgArr : [];
      const type = currentItems[0]?.type;
      const token = ++this.analysisToken;

      this.analysisMap = {};
      this.overviewStats = null;
      this.analysisError = "";

      if (!currentItems.length || !SUPPORTED_ANALYSIS_TYPES.includes(type)) {
        this.analysisLoading = false;
        return;
      }

      this.analysisLoading = true;
      try {
        const analyses = await Promise.all(currentItems.map(async(item, index) => {
          if (type === "场景分类") {
            return analyzeClassificationRecord(item);
          }
          if (type === "目标检测") {
            return analyzeDetectionRecord(item);
          }
          if (type === "地物分类") {
            return analyzeSegmentationRecord(item);
          }
          return analyzeRestorationRecord(item);
        }));

        if (token !== this.analysisToken) {
          return;
        }

        const nextMap = {};
        analyses.forEach((analysis, index) => {
          nextMap[this.analysisKey(currentItems[index], index)] = analysis;
        });
        this.analysisMap = nextMap;

        if (type === "场景分类") {
          this.overviewStats = summarizeClassification(currentItems);
        } else if (type === "目标检测") {
          this.overviewStats = summarizeDetection(currentItems, analyses);
        } else if (type === "地物分类") {
          this.overviewStats = summarizeSegmentation(currentItems, analyses);
        } else if (type === "影像超分重建") {
          this.overviewStats = summarizeRestoration(currentItems, analyses);
        }
      } catch (error) {
        if (token !== this.analysisToken) {
          return;
        }
        this.analysisError = error?.message || "统计计算失败";
      } finally {
        if (token === this.analysisToken) {
          this.analysisLoading = false;
        }
      }
    },
    analysisFor(item, index) {
      return this.analysisMap[this.analysisKey(item, index)] || null;
    },
    analysisTagText(analysis) {
      if (analysis.kind === "classification") {
        return `Top1 ${analysis.topLabel}`;
      }
      if (analysis.kind === "detection") {
        return `${analysis.detectionCount} 个目标`;
      }
      if (analysis.kind === "segmentation") {
        return `${analysis.dominantClass} ${analysis.dominantRatio}%`;
      }
      return `${analysis.scale.widthRatio}x 放大`;
    },
    classificationSummary(item, index) {
      const analysis = this.analysisFor(item, index) || analyzeClassificationRecord(item);
      return `${analysis.topLabel}: ${analysis.topScore}%`;
    },
    itemMetricCards(analysis) {
      if (analysis.kind === "classification") {
        return [
          { label: "Top1 标签", value: analysis.topLabel },
          { label: "Top1 置信度", value: `${analysis.topScore}%` },
          { label: "Top1/Top2 差值", value: `${analysis.confidenceMargin}%` },
          { label: "分布熵", value: analysis.entropy },
        ];
      }

      if (analysis.kind === "segmentation") {
        return [
          { label: "主导类别", value: analysis.dominantClass },
          { label: "主导占比", value: `${analysis.dominantRatio}%` },
          { label: "总采样像素", value: analysis.totalPixels },
          { label: "统计来源", value: analysis.source },
        ];
      }

      if (analysis.kind === "detection") {
        return [
          { label: "目标数量", value: analysis.detectionCount },
          { label: "平均置信度", value: `${analysis.avgConfidence}%` },
          { label: "主导类别", value: analysis.dominantLabel },
          { label: "检测密度", value: `${analysis.detectionDensity} 个/MP` },
          { label: "平均面积占比", value: `${analysis.avgAreaRatio}%` },
          { label: "输入分辨率", value: `${analysis.imageWidth} × ${analysis.imageHeight}` },
        ];
      }

      return [
        { label: "宽度倍率", value: `${analysis.scale.widthRatio}x` },
        { label: "高度倍率", value: `${analysis.scale.heightRatio}x` },
        { label: "像素倍率", value: `${analysis.scale.pixelRatio}x` },
        { label: "输出分辨率", value: `${analysis.afterMetrics.width} × ${analysis.afterMetrics.height}` },
      ];
    },
    itemCharts(analysis) {
      if (analysis.kind === "classification") {
        return [
          {
            title: "Top 5 类别得分",
            option: this.createBarOption(analysis.topEntries, "percent", "概率 (%)"),
          },
          {
            title: "置信度分层",
            option: this.createPieOption(analysis.confidenceBands, "类别分数分层"),
          },
        ];
      }

      if (analysis.kind === "segmentation") {
        return [
          {
            title: "单图地物面积占比",
            option: this.createPieOption(
              analysis.classStats.map((item) => ({
                name: item.name,
                value: item.count,
                itemStyle: { color: item.color },
              })),
              "按像素估计的类别占比",
            ),
          },
          {
            title: "类别面积排名",
            option: this.createBarOption(
              analysis.classStats.map((item) => ({
                name: item.name,
                value: item.ratio,
              })),
              "value",
              "占比 (%)",
            ),
          },
        ];
      }

      if (analysis.kind === "detection") {
        return [
          {
            title: "类别分布",
            option: this.createPieOption(
              analysis.labelStats,
              "当前影像各类别目标数量",
            ),
          },
          {
            title: "置信度分层",
            option: this.createBarOption(
              analysis.confidenceBands,
              "value",
              "目标数量",
            ),
          },
          {
            title: "目标尺度分层",
            option: this.createBarOption(
              analysis.sizeBands,
              "value",
              "目标数量",
            ),
          },
          {
            title: "高置信目标排名",
            option: this.createBarOption(
              analysis.topDetections,
              "value",
              "置信度 (%)",
            ),
          },
        ];
      }

      return [
        {
          title: "前后指标对比",
          option: {
            tooltip: { trigger: "axis" },
            legend: { top: 0 },
            grid: { left: 48, right: 20, top: 42, bottom: 36 },
            xAxis: {
              type: "category",
              data: analysis.comparisonRows.map((row) => row.name),
              axisLabel: {
                interval: 0,
                rotate: 18,
              },
            },
            yAxis: { type: "value" },
            series: [
              {
                name: "处理前",
                type: "bar",
                data: analysis.comparisonRows.map((row) => row.before),
                itemStyle: { color: "#8ca6db" },
              },
              {
                name: "处理后",
                type: "bar",
                data: analysis.comparisonRows.map((row) => row.after),
                itemStyle: { color: "#3b82f6" },
              },
            ],
          },
        },
        {
          title: "指标变化率",
          option: this.createBarOption(
            analysis.comparisonRows.map((row) => ({
              name: row.name,
              value: row.deltaPercent,
            })),
            "value",
            "变化率 (%)",
          ),
        },
      ];
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
  },
};
</script>

<style scoped lang="less">
* {
  font-family: var(--theme-default-fontfamily);
}

.render-mode-bar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  margin-bottom: 10px;
}

.render-mode-bar__label {
  font-size: 13px;
  color: var(--text-secondary);
}

.render-mode-state {
  margin-bottom: 18px;
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
    radial-gradient(circle at top left, rgba(59, 130, 246, 0.12), transparent 36%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(245, 248, 255, 0.98));
  border: 1px solid rgba(59, 130, 246, 0.16);
}

.analysis-shell__head,
.record-analysis__head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
}

.analysis-shell__title,
.record-analysis__title {
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

.chart-grid--record {
  margin-top: 14px;
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
  padding: 12px 2px 8px;
  font-size: 13px;
  color: var(--text-secondary);
}

.analysis-error {
  color: #b91c1c;
}

.index-number {
  font-family: var(--theme-display-fontfamily);
  font-size: 30px;
  margin-left: 5px;
  margin-right: 10px;
  color: var(--theme-heading-color);
}

.img-infor {
  text-align: center;
  font-size: 18px;
  margin-top: 5px;
  margin-bottom: 10px;
  height: 30px;
  line-height: 30px;
  font-weight: 500;
  color: var(--text-secondary);
}

.img-display-box {
  display: flex;
  flex-direction: column;

  .img-display-item {
    display: flex;
    flex-direction: row;
    justify-content: space-evenly;
    flex-wrap: wrap;

    .img-index {
      line-height: 21rem;
    }

    .img-display {
      width: 21rem;
      height: 21rem;
    }

    .img-divider {
      align-items: center;
    }
  }
}

.img-display-item__result {
  display: flex;
  flex-direction: column;
  max-width: 100%;
}

.record-analysis {
  margin-top: 6px;
  padding: 14px;
  border-radius: 16px;
  background: rgba(248, 250, 252, 0.95);
  border: 1px solid rgba(148, 163, 184, 0.16);
}

.el-divider /deep/ {
  background-color: transparent;
}

@media (max-width: 900px) {
  .chart-view {
    height: 240px;
  }

  .img-display-box .img-display-item .img-display {
    width: 18rem;
    height: 18rem;
  }
}
</style>
