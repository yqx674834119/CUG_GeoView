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
const SEGMENTATION_MASK_OPACITY = 0.42;

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
  data() {
    return {
      renderTicket: 0,
    };
  },
  computed: {
    renderer() {
      return this.payload?.renderer || "";
    },
    note() {
      if (this.payload?.capabilities?.frontend_render_note) {
        return this.payload.capabilities.frontend_render_note;
      }
      if (this.renderer === "scene_classification") {
        return "分类标签与置信度由后端 JSON 直接驱动，底图仍使用原始输入影像。";
      }
      if (this.renderer === "image_restoration") {
        return "超分页的 JSON 模式展示浏览器端重建预览与目标输出尺寸，不替代模型原始输出图。";
      }
      return "";
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
      const ticket = ++this.renderTicket;

      if (this.renderer === "semantic_segmentation") {
        this.drawSegmentation(ctx, width, height, ticket);
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
        this.drawChangeDetection(ctx, width, height, ticket);
        return;
      }

      if (this.renderer === "scene_classification") {
        this.drawSceneClassification(ctx, width, height);
        return;
      }

      if (this.renderer === "image_restoration") {
        this.drawRestoration(ctx, width, height, image);
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
    loadHtmlImage(src) {
      return new Promise((resolve, reject) => {
        if (!src) {
          reject(new Error("empty_src"));
          return;
        }
        const image = new Image();
        image.onload = () => resolve(image);
        image.onerror = () => reject(new Error(`failed_to_load:${src}`));
        image.src = src;
      });
    },
    buildSegmentationColorMap(classes) {
      const colorMap = {};
      (classes || []).forEach((segmentClass) => {
        colorMap[Number(segmentClass.index)] = Array.isArray(segmentClass.color)
          ? segmentClass.color
          : [59, 130, 246];
      });
      return colorMap;
    },
    async drawIndexedMask(ctx, width, height, maskSrc, colorMap, ticket, opacity = SEGMENTATION_MASK_OPACITY) {
      try {
        const maskImage = await this.loadHtmlImage(maskSrc);
        if (ticket !== this.renderTicket) {
          return false;
        }
        const sourceWidth = maskImage.naturalWidth || maskImage.width;
        const sourceHeight = maskImage.naturalHeight || maskImage.height;
        if (!sourceWidth || !sourceHeight) {
          return false;
        }

        const maskCanvas = document.createElement("canvas");
        maskCanvas.width = sourceWidth;
        maskCanvas.height = sourceHeight;
        const maskCtx = maskCanvas.getContext("2d", { willReadFrequently: true });
        maskCtx.drawImage(maskImage, 0, 0, sourceWidth, sourceHeight);
        const maskData = maskCtx.getImageData(0, 0, sourceWidth, sourceHeight);
        const output = maskCtx.createImageData(sourceWidth, sourceHeight);
        const alpha = Math.round(255 * opacity);

        for (let i = 0; i < maskData.data.length; i += 4) {
          const classIndex = maskData.data[i];
          if (!Object.prototype.hasOwnProperty.call(colorMap, classIndex)) {
            continue;
          }
          const [r, g, b] = colorMap[classIndex];
          output.data[i] = r;
          output.data[i + 1] = g;
          output.data[i + 2] = b;
          output.data[i + 3] = alpha;
        }

        maskCtx.clearRect(0, 0, sourceWidth, sourceHeight);
        maskCtx.putImageData(output, 0, 0);
        ctx.save();
        ctx.imageSmoothingEnabled = false;
        ctx.drawImage(maskCanvas, 0, 0, width, height);
        ctx.restore();
        return true;
      } catch (error) {
        return false;
      }
    },
    async drawOverlayImage(ctx, width, height, overlaySrc, ticket) {
      try {
        const overlayImage = await this.loadHtmlImage(overlaySrc);
        if (ticket !== this.renderTicket) {
          return false;
        }
        ctx.drawImage(overlayImage, 0, 0, width, height);
        return true;
      } catch (error) {
        return false;
      }
    },
    async drawSegmentation(ctx, width, height, ticket) {
      const maskSrc = this.payload?.result?.mask_path;
      const classes = this.payload?.result?.classes || [];
      const colorMap = this.buildSegmentationColorMap(classes);
      if (maskSrc && await this.drawIndexedMask(ctx, width, height, maskSrc, colorMap, ticket)) {
        return;
      }
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
    async drawChangeDetection(ctx, width, height, ticket) {
      const maskSrc = this.payload?.result?.mask_path;
      if (maskSrc && await this.drawOverlayImage(ctx, width, height, maskSrc, ticket)) {
        return;
      }
      const regions = this.payload?.result?.regions || [];
      regions.forEach((region) => {
        this.drawPolygon(ctx, region.points, width, height, "#22c55e", "rgba(34, 197, 94, 0.20)");
      });
    },
    drawSceneClassification(ctx, width, height) {
      const scores = (this.payload?.result?.scores || []).slice(0, 5);
      if (!scores.length) {
        return;
      }

      const panelWidth = Math.min(width * 0.72, 220);
      const rowHeight = 28;
      const panelHeight = 28 + (scores.length * rowHeight);
      ctx.fillStyle = "rgba(15, 23, 42, 0.72)";
      ctx.fillRect(12, 12, panelWidth, panelHeight);
      ctx.fillStyle = "#ffffff";
      ctx.font = "bold 14px sans-serif";
      ctx.fillText("Top 分类结果", 24, 32);

      scores.forEach((entry, index) => {
        const top = 44 + (index * rowHeight);
        const percent = Math.max(0, Math.min(100, Math.round((Number(entry.score) || 0) * 100)));
        ctx.fillStyle = "rgba(255,255,255,0.16)";
        ctx.fillRect(24, top, panelWidth - 48, 12);
        ctx.fillStyle = "#38bdf8";
        ctx.fillRect(24, top, ((panelWidth - 48) * percent) / 100, 12);
        ctx.fillStyle = "#ffffff";
        ctx.font = "12px sans-serif";
        ctx.fillText(`${entry.label || "未知"} ${percent}%`, 24, top - 4);
      });
    },
    drawRestoration(ctx, width, height, image) {
      const targetWidth = Number(this.payload?.result?.output_size?.width) || 0;
      const targetHeight = Number(this.payload?.result?.output_size?.height) || 0;
      const zoomSize = Math.max(56, Math.round(Math.min(width, height) * 0.24));
      const cropX = Math.max(0, Math.round(width * 0.36));
      const cropY = Math.max(0, Math.round(height * 0.28));
      const destSize = Math.max(88, Math.round(Math.min(width, height) * 0.34));
      const destX = width - destSize - 16;
      const destY = 16;

      ctx.strokeStyle = "#22c55e";
      ctx.lineWidth = 2;
      ctx.strokeRect(cropX, cropY, zoomSize, zoomSize);
      ctx.fillStyle = "rgba(15, 23, 42, 0.72)";
      ctx.fillRect(destX - 8, destY - 8, destSize + 16, destSize + 48);

      try {
        ctx.imageSmoothingEnabled = false;
        ctx.drawImage(image, cropX, cropY, zoomSize, zoomSize, destX, destY, destSize, destSize);
      } catch (error) {
        return;
      }

      ctx.strokeStyle = "#f59e0b";
      ctx.strokeRect(destX, destY, destSize, destSize);
      ctx.fillStyle = "#ffffff";
      ctx.font = "12px sans-serif";
      ctx.fillText("JSON 超分预览", destX, destY + destSize + 18);
      ctx.fillText(
        `${targetWidth || image.naturalWidth} x ${targetHeight || image.naturalHeight}`,
        destX,
        destY + destSize + 34,
      );
      ctx.imageSmoothingEnabled = true;
    },
  },
};
</script>

<style scoped lang="less">
.json-visualizer {
  width: 100%;
  max-width: 21rem;
}

.json-visualizer__stage {
  position: relative;
  width: 100%;
  aspect-ratio: 1 / 1;
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
  .json-visualizer {
    max-width: 18rem;
  }
}
</style>
