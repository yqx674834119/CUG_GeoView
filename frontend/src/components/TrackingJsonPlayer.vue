<template>
  <div class="tracking-json-player">
    <div v-if="hasVideoSource" class="tracking-json-player__video-wrap">
      <video
        ref="videoRef"
        class="tracking-json-player__video"
        :src="videoSrc"
        controls
        playsinline
        preload="metadata"
        @loadedmetadata="syncVideoFrame"
        @timeupdate="syncVideoFrame"
      />
      <canvas ref="canvasRef" class="tracking-json-player__canvas" />
    </div>
    <div v-else-if="frameSources.length" class="tracking-json-player__sequence-wrap">
      <img
        ref="imageRef"
        class="tracking-json-player__image"
        :src="frameSources[currentFrameIndex]"
        alt="本地序列帧"
        @load="drawCurrentFrame"
      >
      <canvas ref="imageCanvasRef" class="tracking-json-player__canvas" />
      <el-slider
        v-model="currentFrameIndex"
        :min="0"
        :max="Math.max(frameSources.length - 1, 0)"
        :step="1"
        class="tracking-json-player__slider"
        @input="drawCurrentFrame"
      />
    </div>
    <div class="tracking-json-player__meta">
      当前帧：{{ currentFrameIndex + 1 }} / {{ totalFrames }}
    </div>
  </div>
</template>

<script>
export default {
  name: "TrackingJsonPlayer",
  props: {
    payload: {
      type: Object,
      default() {
        return {};
      },
    },
    videoSrc: {
      type: String,
      default: "",
    },
    frameSources: {
      type: Array,
      default() {
        return [];
      },
    },
  },
  data() {
    return {
      currentFrameIndex: 0,
    };
  },
  computed: {
    hasVideoSource() {
      return !!this.videoSrc;
    },
    frames() {
      return this.payload?.result?.frames || [];
    },
    totalFrames() {
      return this.frames.length || this.frameSources.length || 0;
    },
    imageSize() {
      return this.payload?.source?.primary || {};
    },
  },
  watch: {
    payload: {
      deep: true,
      handler() {
        this.currentFrameIndex = 0;
        this.$nextTick(() => {
          this.syncVideoFrame();
          this.drawCurrentFrame();
        });
      },
    },
    frameSources() {
      this.currentFrameIndex = 0;
      this.$nextTick(this.drawCurrentFrame);
    },
  },
  mounted() {
    this.syncVideoFrame();
    this.drawCurrentFrame();
    window.addEventListener("resize", this.handleResize);
  },
  beforeUnmount() {
    window.removeEventListener("resize", this.handleResize);
  },
  methods: {
    handleResize() {
      this.syncVideoFrame();
      this.drawCurrentFrame();
    },
    frameEntry(index) {
      return this.frames[index] || {};
    },
    normalizedObjects(index) {
      const entry = this.frameEntry(index);
      if (Array.isArray(entry.objects)) {
        return entry.objects;
      }
      if (Array.isArray(entry.bbox)) {
        return [{
          bbox: entry.bbox,
          track_id: 1,
          score: entry.confidence || 0,
          label: "tracked",
        }];
      }
      return [];
    },
    syncVideoFrame() {
      if (!this.hasVideoSource) {
        return;
      }
      const video = this.$refs.videoRef;
      const canvas = this.$refs.canvasRef;
      if (!video || !canvas || !video.videoWidth || !video.videoHeight) {
        return;
      }
      const width = video.clientWidth || video.videoWidth;
      const height = video.clientHeight || video.videoHeight;
      canvas.width = width;
      canvas.height = height;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;

      const duration = video.duration || 0;
      const frameCount = Math.max(this.totalFrames, 1);
      const nextIndex = duration > 0
        ? Math.min(frameCount - 1, Math.round((video.currentTime / duration) * (frameCount - 1)))
        : 0;
      this.currentFrameIndex = nextIndex;
      this.drawObjects(canvas.getContext("2d"), width, height, nextIndex);
    },
    drawCurrentFrame() {
      if (this.hasVideoSource) {
        this.syncVideoFrame();
        return;
      }
      const image = this.$refs.imageRef;
      const canvas = this.$refs.imageCanvasRef;
      if (!image || !canvas || !image.complete || !image.naturalWidth || !image.naturalHeight) {
        return;
      }
      const width = image.clientWidth || image.naturalWidth;
      const height = image.clientHeight || image.naturalHeight;
      canvas.width = width;
      canvas.height = height;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      this.drawObjects(canvas.getContext("2d"), width, height, this.currentFrameIndex);
    },
    drawObjects(ctx, width, height, index) {
      ctx.clearRect(0, 0, width, height);
      const sourceWidth = this.imageSize.width || width;
      const sourceHeight = this.imageSize.height || height;
      ctx.lineWidth = 2;
      ctx.font = "14px sans-serif";
      this.normalizedObjects(index).forEach((object) => {
        const bbox = object.bbox || [];
        if (bbox.length < 4) {
          return;
        }
        const x = (bbox[0] / sourceWidth) * width;
        const y = (bbox[1] / sourceHeight) * height;
        const w = (bbox[2] / sourceWidth) * width;
        const h = (bbox[3] / sourceHeight) * height;
        ctx.strokeStyle = "#22c55e";
        ctx.fillStyle = "#22c55e";
        ctx.strokeRect(x, y, w, h);
        ctx.fillRect(x, Math.max(0, y - 18), 110, 18);
        ctx.fillStyle = "#ffffff";
        const label = object.label || `ID ${object.track_id || "-"}`;
        ctx.fillText(label, x + 4, Math.max(12, y - 5));
      });
    },
  },
};
</script>

<style scoped lang="less">
.tracking-json-player__video-wrap,
.tracking-json-player__sequence-wrap {
  position: relative;
}

.tracking-json-player__video,
.tracking-json-player__image,
.tracking-json-player__canvas {
  width: 100%;
  border-radius: 16px;
}

.tracking-json-player__canvas {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.tracking-json-player__slider {
  margin-top: 16px;
}

.tracking-json-player__meta {
  margin-top: 10px;
  font-size: 13px;
  color: var(--text-secondary);
}
</style>
