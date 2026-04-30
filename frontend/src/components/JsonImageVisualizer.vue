<template>
  <div class="json-visualizer">
    <div class="json-visualizer__stage">
      <img
        ref="imageRef"
        :src="imageSrc"
        class="json-visualizer__image"
        alt="本地可视化底图"
        @load="redraw"
      >
      <canvas
        ref="canvasRef"
        class="json-visualizer__canvas"
      />
    </div>
    <div v-if="note" class="json-visualizer__note">
      {{ note }}
    </div>
  </div>
</template>

<script>
const SEGMENTATION_ALPHA = "55";

export default {
  name: "JsonImageVisualizer",
  props: {
    imageSrc: {
      type: String,
      default: "",
    },
    payload: {
      type: Object,
      default() {
        return {};
      },
    },
  },
  computed: {
    renderer() {
      return this.payload?.renderer || "";
    },
    note() {
      return this.payload?.capabilities?.frontend_render_note || "";
    },
  },
  watch: {
    imageSrc() {
      this.$nextTick(this.redraw);
    },
    payload: {
      deep: true,
      handler() {
        this.$nextTick(this.redraw);
      },
    },
  },
  mounted() {
    this.redraw();
    window.addEventListener("resize", this.redraw);
  },
  beforeUnmount() {
    window.removeEventListener("resize", this.redraw);
  },
  methods: {
    redraw() {
      const image = this.$refs.imageRef;
      const canvas = this.$refs.canvasRef;
      if (!image || !canvas || !image.complete || !image.naturalWidth || !image.naturalHeight) {
        return;
      }

      const width = image.clientWidth || image.naturalWidth;
      const height = image.clientHeight || image.naturalHeight;
      canvas.width = width;
      canvas.height = height;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;

      const ctx = canvas.getContext("2d");
      ctx.clearRect(0, 0, width, height);

      if (this.renderer === "semantic_segmentation") {
        this.drawSegmentation(ctx, width, height);
        return;
      }

      if (this.renderer === "object_detection") {
        this.drawDetections(ctx, width, height);
        return;
      }

      if (this.renderer === "registration") {
        this.drawRegistration(ctx, width, height);
        return;
      }

      if (this.renderer === "change_detection") {
        this.drawChangeDetection(ctx, width, height);
      }
    },
    rgba(color, suffix = "") {
      if (!Array.isArray(color) || color.length < 3) {
        return `#3b82f6${suffix}`;
      }
      const [r, g, b] = color.map((value) => Number(value).toString(16).padStart(2, "0"));
      return `#${r}${g}${b}${suffix}`;
    },
    drawPolygon(ctx, points, width, height, strokeStyle, fillStyle) {
      if (!Array.isArray(points) || points.length < 3) {
        return;
      }
      ctx.beginPath();
      points.forEach((point, index) => {
        const x = point[0] * width;
        const y = point[1] * height;
        if (index === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      });
      ctx.closePath();
      if (fillStyle) {
        ctx.fillStyle = fillStyle;
        ctx.fill();
      }
      ctx.strokeStyle = strokeStyle;
      ctx.lineWidth = 2;
      ctx.stroke();
    },
    drawSegmentation(ctx, width, height) {
      const classes = this.payload?.result?.classes || [];
      classes.forEach((segmentClass) => {
        const stroke = this.rgba(segmentClass.color);
        const fill = this.rgba(segmentClass.color, SEGMENTATION_ALPHA);
        (segmentClass.regions || []).forEach((region) => {
          this.drawPolygon(ctx, region.points, width, height, stroke, fill);
        });
      });
    },
    drawDetections(ctx, width, height) {
      const detections = this.payload?.result?.detections || [];
      ctx.font = "14px sans-serif";
      detections.forEach((detection) => {
        ctx.strokeStyle = "#ef4444";
        ctx.fillStyle = "#ef4444";
        ctx.lineWidth = 2;
        if (Array.isArray(detection.polygon) && detection.polygon.length >= 4) {
          ctx.beginPath();
          detection.polygon.forEach((point, index) => {
            const x = (point[0] / (this.payload?.result?.image_size?.width || width)) * width;
            const y = (point[1] / (this.payload?.result?.image_size?.height || height)) * height;
            if (index === 0) {
              ctx.moveTo(x, y);
            } else {
              ctx.lineTo(x, y);
            }
          });
          ctx.closePath();
          ctx.stroke();
        } else if (Array.isArray(detection.box) && detection.box.length >= 4) {
          const sourceWidth = this.payload?.result?.image_size?.width || width;
          const sourceHeight = this.payload?.result?.image_size?.height || height;
          const x1 = (detection.box[0] / sourceWidth) * width;
          const y1 = (detection.box[1] / sourceHeight) * height;
          const x2 = (detection.box[2] / sourceWidth) * width;
          const y2 = (detection.box[3] / sourceHeight) * height;
          ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
          ctx.fillRect(x1, Math.max(0, y1 - 20), Math.max(92, (detection.label || "").length * 10), 18);
          ctx.fillStyle = "#ffffff";
          ctx.fillText(`${detection.label || "目标"} ${Math.round((detection.score || 0) * 100)}%`, x1 + 4, Math.max(13, y1 - 6));
          ctx.fillStyle = "#ef4444";
        }
      });
    },
    drawRegistration(ctx, width, height) {
      const points = this.payload?.result?.moving_corners_on_fixed || [];
      if (!Array.isArray(points) || points.length < 4) {
        return;
      }
      const sourceWidth = this.payload?.source?.secondary?.width || width;
      const sourceHeight = this.payload?.source?.secondary?.height || height;
      ctx.strokeStyle = "#f59e0b";
      ctx.fillStyle = "rgba(245, 158, 11, 0.18)";
      ctx.lineWidth = 3;
      ctx.beginPath();
      points.forEach((point, index) => {
        const x = (point[0] / sourceWidth) * width;
        const y = (point[1] / sourceHeight) * height;
        if (index === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      });
      ctx.closePath();
      ctx.fill();
      ctx.stroke();
    },
    drawChangeDetection(ctx, width, height) {
      const regions = this.payload?.result?.regions || [];
      regions.forEach((region) => {
        this.drawPolygon(ctx, region.points, width, height, "#22c55e", "rgba(34, 197, 94, 0.20)");
      });
    },
  },
};
</script>

<style scoped lang="less">
.json-visualizer {
  width: 21rem;
}

.json-visualizer__stage {
  position: relative;
  width: 21rem;
  height: 21rem;
  border-radius: 14px;
  overflow: hidden;
  background: #f8fafc;
}

.json-visualizer__image,
.json-visualizer__canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.json-visualizer__image {
  object-fit: cover;
}

.json-visualizer__canvas {
  pointer-events: none;
}

.json-visualizer__note {
  margin-top: 8px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-secondary);
}

@media (max-width: 900px) {
  .json-visualizer,
  .json-visualizer__stage {
    width: 18rem;
    height: 18rem;
  }
}
</style>
