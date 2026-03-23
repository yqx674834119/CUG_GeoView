<template>
  <div class="tracking-page">
    <Tabinfor>
      <template #left>
        <div id="sub-title">
          遥感目标跟踪<i class="icon-click" />
        </div>
      </template>
    </Tabinfor>
    <el-divider />
    <p class="intro-text">
      上传按时间顺序命名的遥感图像序列，并在首帧框选目标，系统会输出跟踪预览图、结果视频与轨迹 JSON。
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
          accept=".jpg,.jpeg,.png,.bmp,.tif,.tiff,.webp"
          :auto-upload="false"
          @change="checkFile"
        >
          <i class="iconfont icon-yunduanshangchuan" />
          <div class="el-upload__text">
            拖拽序列帧到此处
          </div>
          <div class="el-upload__tip">
            或点击下方按钮上传文件夹
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
          >上传文件夹</i>
        </div>
      </div>

      <div v-if="sortedNames.length" class="sequence-summary">
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

      <el-row justify="center" class="model-row">
        <div class="custom-model">
          可选跟踪模型：
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

      <div v-if="firstFrame" class="frame-selector">
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
                <span>跟踪预览图</span>
                <el-tag type="success" effect="dark">
                  {{ result.method_used }}
                </el-tag>
              </div>
            </template>
            <el-image
              :src="result.preview_full_url"
              :preview-src-list="[result.preview_full_url]"
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

        <el-col :xs="24" :sm="24" :md="12" :lg="12">
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
              controls
              preload="metadata"
              class="result-video"
              :src="result.output_video_full_url"
            />
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
    </div>
    <el-empty v-else description="暂无结果" />
  </div>
</template>

<script>
import Tabinfor from "@/components/Tabinfor";
import { createSrc, getCustomModel, imgUpload } from "@/api/upload";
import global from "@/global.vue";

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

export default {
  name: "Tracking",
  components: { Tabinfor },
  data() {
    return {
      fileList: [],
      sortedNames: [],
      modelPathArr: [],
      uploadSrc: {
        model_path: "builtin:tracking:auto",
      },
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
    };
  },
  computed: {
    canStart() {
      return this.fileList.length >= 2 && this.rect.w > 0 && this.rect.h > 0;
    },
    resultSummary() {
      return (this.result && this.result.summary) || null;
    },
  },
  created() {
    this.fetchModels();
  },
  beforeUnmount() {
    this.revokeFirstFrameUrl();
  },
  methods: {
    fetchModels() {
      getCustomModel("tracking").then((res) => {
        this.modelPathArr = res.data.data || [];
        if (this.modelPathArr.length > 0) {
          this.uploadSrc.model_path = this.modelPathArr[0].model_path;
        }
      }).catch(() => {});
    },
    clearQueue() {
      this.revokeFirstFrameUrl();
      this.fileList = [];
      this.sortedNames = [];
      this.firstFrame = null;
      this.rect = { x: 0, y: 0, w: 0, h: 0 };
      this.result = null;
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
      this.fileList = this.normalizeElUploadList(fileList);
      this.refreshSequencePreview();
    },
    uploadFolder() {
      this.fileList = this.mergeFileList(
        this.fileList,
        Array.from(this.$refs.refFolder.files || []),
      );
      this.refreshSequencePreview();
    },
    normalizeElUploadList(fileList) {
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
      return accepted;
    },
    mergeFileList(existingList, incomingFiles) {
      const merged = [...existingList];
      for (const file of incomingFiles) {
        if (!this.isSupportedFile(file)) {
          continue;
        }
        merged.push({
          name: file.name,
          raw: file,
          status: "ready",
          uid: `${Date.now()}_${Math.random()}`,
        });
      }
      return merged;
    },
    isSupportedFile(file) {
      const suffix = file.name.substring(file.name.lastIndexOf(".") + 1);
      if (!SUPPORTED_SUFFIXES.includes(suffix)) {
        this.$message.error(`文件 ${file.name} 格式不支持，请上传常见影像格式`);
        return false;
      }
      return true;
    },
    refreshSequencePreview() {
      const ordered = [...this.fileList].sort((a, b) => (
        (a.name || "").localeCompare(b.name || "", undefined, { numeric: true, sensitivity: "base" })
      ));
      this.revokeFirstFrameUrl();
      this.fileList = ordered;
      this.sortedNames = ordered.map((item) => item.name);
      this.rect = { x: 0, y: 0, w: 0, h: 0 };
      this.result = null;
      this.firstFrame = ordered.length ? URL.createObjectURL(ordered[0].raw) : null;
    },
    revokeFirstFrameUrl() {
      if (this.firstFrame && this.firstFrame.startsWith("blob:")) {
        URL.revokeObjectURL(this.firstFrame);
      }
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
      return response.data.data || [];
    },
    async startTracking() {
      if (!this.canStart) {
        this.$message.error("请先上传至少 2 帧图像并框选目标");
        return;
      }
      if (!this.uploadSrc.model_path) {
        this.$message.error("请选择跟踪模型");
        return;
      }

      this.running = true;
      try {
        const uploaded = await this.uploadSequence(this.fileList);
        if (uploaded.length < 2) {
          throw new Error("上传结果不足 2 帧，无法执行目标跟踪");
        }
        const ordered = [...uploaded].sort((a, b) => (
          (a.filename || "").localeCompare(b.filename || "", undefined, { numeric: true, sensitivity: "base" })
        ));
        const img = this.$refs.firstFrameImg;
        const scaleX = img.naturalWidth / img.clientWidth;
        const scaleY = img.naturalHeight / img.clientHeight;
        const rect = [
          Math.round(this.rect.x * scaleX),
          Math.round(this.rect.y * scaleY),
          Math.round(this.rect.w * scaleX),
          Math.round(this.rect.h * scaleY),
        ];

        const payload = {
          model_path: this.uploadSrc.model_path,
          list: ordered.map((item) => ({
            src: item.src,
            filename: item.filename,
          })),
          rect,
        };
        const response = await imgUpload(payload, "tracking");
        const data = response.data.data || {};
        if (!data.preview_path || !data.output_video_path) {
          throw new Error(response.data.msg || "跟踪结果不完整");
        }
        this.result = {
          ...data,
          first_frame_full_url: this.prefixUrl(data.first_frame_input),
          preview_full_url: this.prefixUrl(data.preview_path),
          output_video_full_url: this.prefixUrl(data.output_video_path),
          trajectory_full_url: this.prefixUrl(data.trajectory_path),
        };
        this.$message.success(response.data.msg || "目标跟踪完成");
      } catch (error) {
        console.error(error);
        const message = error?.response?.data?.msg || error?.message || "目标跟踪失败";
        this.$message.error(message);
      } finally {
        this.running = false;
      }
    },
    prefixUrl(path) {
      if (!path) {
        return "";
      }
      if (path.startsWith("http://") || path.startsWith("https://")) {
        return path;
      }
      return `${this.global.BASEURL}${path.replace(/^\//, "")}`;
    },
    downloadFile(url, filename) {
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.click();
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

.custom-model {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.frame-selector {
  margin-top: 24px;
}

.frame-selector__hint {
  color: var(--text-secondary);
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

@media (max-width: 768px) {
  .clear-queue {
    position: static;
    margin-bottom: 16px;
  }

  .result-summary {
    padding-right: 0;
  }
}
</style>
