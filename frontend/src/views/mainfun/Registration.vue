<template>
  <div class="registration-demo-page">
    <Tabinfor>
      <template #left>
        <div id="sub-title">
          多模态自动配准<i class="icon-click" />
        </div>
      </template>
    </Tabinfor>
    <el-divider />
    <p class="intro-text">
      上传 Sentinel-1 参考影像与 Sentinel-2 影像或其他遥感影像，系统将结合多模态信息完成复杂干扰背景下的小尺度目标检测，并输出配准检测结果。
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
          配准检测模型：
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
      <div v-if="resultCard.record?.visual_payload" class="render-mode-bar">
        <span class="render-mode-bar__label">结果渲染模式</span>
        <el-radio-group v-model="renderMode" size="small">
          <el-radio-button label="legacy">原始模式</el-radio-button>
          <el-radio-button label="json">JSON 本地可视化</el-radio-button>
        </el-radio-group>
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
                :src="resultCard.moving_preview_url"
                :preview-src-list="[resultCard.moving_preview_url]"
                :preview-teleported="true"
                fit="cover"
              />
            </div>
          </el-card>
        </el-col>

        <el-col :xs="24" :sm="24" :md="8" :lg="8">
          <el-card class="result-card">
            <div class="result-card__title">配准检测结果</div>
            <div class="result-card__meta">
              {{ resultCard.model_name }}
            </div>
            <div class="result-image-box">
              <JsonImageVisualizer
                v-if="renderMode === 'json' && resultCard.record?.visual_payload"
                :image-src="resultCard.moving_preview_url"
                :payload="resultCard.record.visual_payload"
              />
              <el-image
                v-else
                :src="resultCard.output_full_url"
                :preview-src-list="[resultCard.output_full_url]"
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
import Tabinfor from "@/components/Tabinfor";
import JsonImageVisualizer from "@/components/JsonImageVisualizer";
import { createSrc, getCustomModel, imgUpload } from "@/api/upload";
import { historyGetPage } from "@/api/history";
import { toBackendAssetUrl } from "@/utils/backendAssetUrl";
import { registerUploadedSources } from "@/utils/localSourceRegistry";

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

export default {
  name: "Registration",
  components: { Tabinfor, JsonImageVisualizer },
  data() {
    return {
      fixedFileList: [],
      movingFileList: [],
      fixedPreviewUrl: "",
      movingPreviewUrl: "",
      modelPathArr: [],
      uploadSrc: {
        model_path: ORIENTED_MODEL_PATH,
      },
      running: false,
      resultCard: null,
      renderMode: "legacy",
    };
  },
  created() {
    this.fetchModels();
  },
  beforeUnmount() {
    revokeObjectUrl(this.fixedPreviewUrl);
    revokeObjectUrl(this.movingPreviewUrl);
  },
  methods: {
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
    updatePreview(typeName, fileList) {
      const nextFile = fileList[0];
      const nextUrl = nextFile ? URL.createObjectURL(nextFile.raw) : "";
      if (typeName === "fixed") {
        revokeObjectUrl(this.fixedPreviewUrl);
        this.fixedPreviewUrl = nextUrl;
      } else {
        revokeObjectUrl(this.movingPreviewUrl);
        this.movingPreviewUrl = nextUrl;
      }
    },
    checkFixed(file, fileList) {
      this.fixedFileList = this.normalizeSingleFileList(fileList, "Sentinel-1 参考影像");
      this.updatePreview("fixed", this.fixedFileList);
    },
    checkMoving(file, fileList) {
      this.movingFileList = this.normalizeSingleFileList(fileList, "Sentinel-2 影像");
      this.updatePreview("moving", this.movingFileList);
    },
    clearQueue() {
      this.fixedFileList = [];
      this.movingFileList = [];
      this.resultCard = null;
      if (this.$refs.uploadA) {
        this.$refs.uploadA.clearFiles();
      }
      if (this.$refs.uploadB) {
        this.$refs.uploadB.clearFiles();
      }
      revokeObjectUrl(this.fixedPreviewUrl);
      revokeObjectUrl(this.movingPreviewUrl);
      this.fixedPreviewUrl = "";
      this.movingPreviewUrl = "";
      this.$message.success("清除成功");
    },
    async uploadMovingImage() {
      const formData = new FormData();
      const current = this.movingFileList[0];
      formData.append("files", current.raw || current);
      formData.append("type", "目标检测");
      const response = await createSrc(formData);
      const items = response.data.data || [];
      if (!items.length) {
        throw new Error("上传结果为空");
      }
      registerUploadedSources(items, [current]);
      return items[0];
    },
    async findLatestDetectionRecord(uploadedSrc) {
      const response = await historyGetPage(1, 20, "目标检测");
      const items = response.data.data || [];
      const matched = items.find((item) => item.before_img === uploadedSrc && item.after_img);
      return matched || items.find((item) => item.after_img) || null;
    },
    async startDemo() {
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
        const uploaded = await this.uploadMovingImage();
        const response = await imgUpload({
          model_path: this.uploadSrc.model_path,
          list: [uploaded.src],
          prehandle: 0,
          denoise: 0,
        }, "object_detection");

        const record = response?.data?.data?.records?.[0] || await this.findLatestDetectionRecord(uploaded.src);
        if (!record || !record.after_img) {
          throw new Error("未获取到检测结果");
        }

        const selectedModel = this.modelPathArr[0] || {};
        this.resultCard = {
          fixed_preview_url: this.fixedPreviewUrl,
          moving_preview_url: this.movingPreviewUrl,
          output_full_url: toBackendAssetUrl(record.after_img),
          model_name: selectedModel.model_name || REGISTRATION_MODEL_NAME,
          record,
        };
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
  margin-bottom: 16px;
}

.render-mode-bar__label {
  font-size: 13px;
  color: var(--text-secondary);
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
}
</style>
