<template>
  <div>
    <Tabinfor>
      <template #left>
        <div id="sub-title">
          多模态自动配准<i class="icon-click" />
        </div>
      </template>
    </Tabinfor>
    <el-divider />
    <p>
      请选择待配准的<span class="go-bold">参考影像</span>和<span class="go-bold">待配准影像</span>。
      当前版本优先解决 Sentinel-1 / Sentinel-2 风格的
      <span class="go-bold">SAR-光学快速对齐</span>，先保证上传、配对、结果预览和下载闭环可用。
    </p>
    <p style="text-decoration: underline">
      <i class="icon-warning" />
      提示：系统会先按<span class="go-bold">文件名去扩展名精确匹配</span>，
      无法匹配时再按<span class="go-bold">剩余顺序</span>回退配对。
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
          <div class="upload-caption">参考影像 (Fixed)</div>
          <el-upload
            ref="uploadA"
            v-model:file-list="fixedFileList"
            class="upload-card"
            drag
            action="#"
            multiple
            :auto-upload="false"
            @change="checkFile1"
          >
            <i class="iconfont icon-yunduanshangchuan" />
            <div class="el-upload__text">
              将文件夹或图片拖到此处，或<em>点击上传</em>
            </div>
            <div class="el-upload__tip">
              支持 jpg / png / tif / tiff 等常见遥感影像格式
            </div>
          </el-upload>
          <div class="upload-action-row">
            <input
              id="upload-fileA"
              ref="refFileA"
              type="file"
              webkitdirectory
              directory
              multiple
              @change="uploadFirst"
            >
            <i
              class="iconfont icon-wenjianshangchuan upload-folder-action"
              @click="file1Click"
            >上传文件夹</i>
          </div>
        </div>

        <div class="upload-item">
          <div class="upload-caption">待配准影像 (Moving)</div>
          <el-upload
            ref="uploadB"
            v-model:file-list="movingFileList"
            class="upload-card"
            drag
            action="#"
            multiple
            :auto-upload="false"
            @change="checkFile2"
          >
            <i class="iconfont icon-yunduanshangchuan" />
            <div class="el-upload__text">
              将文件夹或图片拖到此处，或<em>点击上传</em>
            </div>
            <div class="el-upload__tip">
              建议与参考影像保持相同覆盖区，系统会自动生成配准对
            </div>
          </el-upload>
          <div class="upload-action-row">
            <input
              id="upload-fileB"
              ref="refFileB"
              type="file"
              webkitdirectory
              directory
              multiple
              @change="uploadSecond"
            >
            <i
              class="iconfont icon-wenjianshangchuan upload-folder-action"
              @click="file2Click"
            >上传文件夹</i>
          </div>
        </div>
      </div>

      <div class="pairing-summary">
        <div class="summary-head">
          <span class="summary-title">自动配对预览</span>
          <span class="summary-meta">
            已生成 {{ draftPairs.length }} 对，
            未匹配参考 {{ unmatchedFixed.length }} 张，
            未匹配待配准 {{ unmatchedMoving.length }} 张
          </span>
        </div>

        <el-table
          v-if="draftPairs.length"
          :data="draftPairs"
          size="small"
          max-height="240"
          border
        >
          <el-table-column prop="pair_name" label="配准对" min-width="180" />
          <el-table-column prop="first_name" label="参考影像" min-width="180" />
          <el-table-column prop="second_name" label="待配准影像" min-width="180" />
          <el-table-column prop="pairing_strategy" label="配对方式" width="120">
            <template #default="scope">
              <el-tag
                :type="scope.row.pairing_strategy === '同名匹配' ? 'success' : 'warning'"
                effect="plain"
              >
                {{ scope.row.pairing_strategy }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
        <el-empty
          v-else
          description="上传两组影像后将在这里生成自动配对结果"
        />

        <div
          v-if="unmatchedFixed.length || unmatchedMoving.length"
          class="pairing-warning"
        >
          <div v-if="unmatchedFixed.length">
            未匹配参考影像：{{ unmatchedFixed.join("、") }}
          </div>
          <div v-if="unmatchedMoving.length">
            未匹配待配准影像：{{ unmatchedMoving.join("、") }}
          </div>
        </div>
      </div>

      <el-row justify="center" class="model-row">
        <div class="custom-model">
          可选配准模型：
          <span v-if="modelPathArr.length === 0">未检测到模型配置</span>
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
          @click="startRegistration"
        >
          开始配准
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
        <div v-if="summary" class="result-summary">
          成功 {{ summary.success_pairs }} / {{ summary.total_pairs }}
        </div>
      </template>
    </Tabinfor>
    <el-divider />

    <div
      v-if="failedArr.length"
      class="failed-box"
    >
      <el-alert
        type="warning"
        :closable="false"
        show-icon
        title="以下影像对未能成功配准，已保留本批次其他成功结果"
      />
      <el-table
        :data="failedArr"
        size="small"
        border
        style="margin-top: 12px;"
      >
        <el-table-column prop="pair_name" label="配准对" min-width="180" />
        <el-table-column prop="message" label="失败原因" min-width="280" />
      </el-table>
    </div>

    <div v-if="resultArr.length" class="result-box">
      <el-row :gutter="20">
        <el-col
          v-for="(item, index) in resultArr"
          :key="index"
          :xs="24"
          :sm="24"
          :md="12"
          :lg="12"
          :xl="12"
        >
          <el-card class="result-card">
            <div class="result-card__head">
              <div>
                <div class="result-card__title">{{ item.pair_name }}</div>
                <div class="result-card__meta">
                  {{ item.method_used }} / {{ item.transform_type }}
                </div>
              </div>
              <el-tag type="success" effect="dark">
                匹配点 {{ item.inlier_count }}/{{ item.match_count }}
              </el-tag>
            </div>

            <div class="result-grid">
              <div class="result-image">
                <el-image
                  :src="item.fixed_input_full_url"
                  :preview-src-list="[item.fixed_input_full_url]"
                  :preview-teleported="true"
                  fit="cover"
                />
                <div class="result-image__label">参考影像</div>
              </div>
              <div class="result-image">
                <el-image
                  :src="item.moving_input_full_url"
                  :preview-src-list="[item.moving_input_full_url]"
                  :preview-teleported="true"
                  fit="cover"
                />
                <div class="result-image__label">待配准影像</div>
              </div>
              <div class="result-image">
                <el-image
                  :src="item.output_full_url"
                  :preview-src-list="[item.output_full_url]"
                  :preview-teleported="true"
                  fit="cover"
                />
                <div class="result-image__label">配准结果</div>
              </div>
              <div class="result-image">
                <el-image
                  :src="item.overlay_full_url"
                  :preview-src-list="[item.overlay_full_url, item.checkerboard_full_url]"
                  :preview-teleported="true"
                  fit="cover"
                />
                <div class="result-image__label">叠加预览</div>
              </div>
            </div>

            <div class="metric-row">
              <span>内点率：{{ formatRatio(item.inlier_ratio) }}</span>
              <span>RMSE：{{ formatRmse(item.rmse) }}</span>
            </div>

            <div class="result-actions">
              <el-button
                type="primary"
                link
                @click="downloadImg(item.output_full_url, `${item.pair_name}_registered.png`)"
              >
                下载配准结果
              </el-button>
              <el-button
                type="primary"
                link
                @click="downloadImg(item.overlay_full_url, `${item.pair_name}_overlay.png`)"
              >
                下载叠加图
              </el-button>
              <el-button
                type="primary"
                link
                @click="downloadImg(item.checkerboard_full_url, `${item.pair_name}_checkerboard.png`)"
              >
                下载棋盘图
              </el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
    <el-empty v-else description="暂无配准结果" />
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
  name: "Registration",
  components: { Tabinfor },
  data() {
    return {
      fixedFileList: [],
      movingFileList: [],
      draftPairs: [],
      unmatchedFixed: [],
      unmatchedMoving: [],
      modelPathArr: [],
      uploadSrc: {
        model_path: "builtin:registration:auto",
      },
      resultArr: [],
      failedArr: [],
      summary: null,
      running: false,
      global: {
        BASEURL: global.BASEURL,
      },
    };
  },
  created() {
    this.fetchModels();
  },
  methods: {
    fetchModels() {
      getCustomModel("registration").then((res) => {
        this.modelPathArr = res.data.data || [];
        if (this.modelPathArr.length > 0) {
          this.uploadSrc.model_path = this.modelPathArr[0].model_path;
        }
      }).catch(() => {});
    },
    clearQueue() {
      this.fixedFileList = [];
      this.movingFileList = [];
      this.draftPairs = [];
      this.unmatchedFixed = [];
      this.unmatchedMoving = [];
      if (this.$refs.uploadA) {
        this.$refs.uploadA.clearFiles();
      }
      if (this.$refs.uploadB) {
        this.$refs.uploadB.clearFiles();
      }
      if (this.$refs.refFileA) {
        this.$refs.refFileA.value = "";
      }
      if (this.$refs.refFileB) {
        this.$refs.refFileB.value = "";
      }
      this.$message.success("清除成功");
    },
    file1Click() {
      this.$refs.refFileA.click();
    },
    file2Click() {
      this.$refs.refFileB.click();
    },
    uploadFirst() {
      this.fixedFileList = this.mergeFileList(
        this.fixedFileList,
        Array.from(this.$refs.refFileA.files || []),
      );
      this.refreshDraftPairs();
    },
    uploadSecond() {
      this.movingFileList = this.mergeFileList(
        this.movingFileList,
        Array.from(this.$refs.refFileB.files || []),
      );
      this.refreshDraftPairs();
    },
    checkFile1(file, fileList) {
      this.fixedFileList = this.normalizeElUploadList(fileList);
      this.refreshDraftPairs();
    },
    checkFile2(file, fileList) {
      this.movingFileList = this.normalizeElUploadList(fileList);
      this.refreshDraftPairs();
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
    refreshDraftPairs() {
      const fixedEntries = this.fixedFileList.map((item) => ({
        filename: item.name,
        raw: item.raw,
      }));
      const movingEntries = this.movingFileList.map((item) => ({
        filename: item.name,
        raw: item.raw,
      }));
      const pairInfo = this.buildPairs(fixedEntries, movingEntries, false);
      this.draftPairs = pairInfo.pairs;
      this.unmatchedFixed = pairInfo.unmatchedFixed;
      this.unmatchedMoving = pairInfo.unmatchedMoving;
    },
    buildPairs(fixedEntries, movingEntries, useUploadedSrc) {
      const movingBuckets = new Map();
      for (const item of movingEntries) {
        const key = this.normalizePairKey(item.filename);
        if (!movingBuckets.has(key)) {
          movingBuckets.set(key, []);
        }
        movingBuckets.get(key).push(item);
      }

      const pairs = [];
      const unmatchedFixed = [];
      const leftoverMoving = [];

      for (const fixed of fixedEntries) {
        const key = this.normalizePairKey(fixed.filename);
        const candidates = movingBuckets.get(key) || [];
        if (candidates.length) {
          const moving = candidates.shift();
          pairs.push(this.toPairRecord(fixed, moving, "同名匹配", useUploadedSrc));
        } else {
          unmatchedFixed.push(fixed);
        }
      }

      for (const bucket of movingBuckets.values()) {
        leftoverMoving.push(...bucket);
      }

      const fallbackCount = Math.min(unmatchedFixed.length, leftoverMoving.length);
      const remainingFixed = unmatchedFixed.slice(fallbackCount);
      const remainingMoving = leftoverMoving.slice(fallbackCount);

      for (let index = 0; index < fallbackCount; index += 1) {
        pairs.push(
          this.toPairRecord(
            unmatchedFixed[index],
            leftoverMoving[index],
            "顺序回退",
            useUploadedSrc,
          ),
        );
      }

      return {
        pairs,
        unmatchedFixed: remainingFixed.map((item) => item.filename),
        unmatchedMoving: remainingMoving.map((item) => item.filename),
      };
    },
    toPairRecord(fixed, moving, pairingStrategy, useUploadedSrc) {
      const pairName = this.derivePairName(fixed.filename, moving.filename);
      const record = {
        pair_name: pairName,
        first_name: fixed.filename,
        second_name: moving.filename,
        pairing_strategy: pairingStrategy,
      };
      if (useUploadedSrc) {
        record.first = fixed.src;
        record.second = moving.src;
      }
      return record;
    },
    normalizePairKey(filename) {
      return filename
        .replace(/\.[^.]+$/, "")
        .trim()
        .toLowerCase()
        .replace(/[\s_-]+/g, "");
    },
    derivePairName(firstName, secondName) {
      const firstStem = firstName.replace(/\.[^.]+$/, "");
      const secondStem = secondName.replace(/\.[^.]+$/, "");
      return `${firstStem}__${secondStem}`;
    },
    async uploadGroup(fileList) {
      const formData = new FormData();
      for (const item of fileList) {
        formData.append("files", item.raw || item);
        formData.append("type", "自动配准");
      }
      const response = await createSrc(formData);
      return response.data.data || [];
    },
    async startRegistration() {
      if (this.fixedFileList.length === 0 || this.movingFileList.length === 0) {
        this.$message.error("请确保两组影像都已上传");
        return;
      }
      if (!this.uploadSrc.model_path) {
        this.$message.error("请选择配准模型");
        return;
      }

      this.running = true;
      try {
        this.resultArr = [];
        this.failedArr = [];
        this.summary = null;
        const [fixedUploaded, movingUploaded] = await Promise.all([
          this.uploadGroup(this.fixedFileList),
          this.uploadGroup(this.movingFileList),
        ]);

        const pairInfo = this.buildPairs(fixedUploaded, movingUploaded, true);
        this.draftPairs = pairInfo.pairs.map((item) => ({
          pair_name: item.pair_name,
          first_name: item.first_name,
          second_name: item.second_name,
          pairing_strategy: item.pairing_strategy,
        }));
        this.unmatchedFixed = pairInfo.unmatchedFixed;
        this.unmatchedMoving = pairInfo.unmatchedMoving;

        if (pairInfo.pairs.length === 0) {
          this.$message.error("没有生成可用的配准对，请检查两组影像命名或数量");
          return;
        }

        const payload = {
          model_path: this.uploadSrc.model_path,
          list: pairInfo.pairs.map((item) => ({
            first: item.first,
            second: item.second,
            pair_name: item.pair_name,
            pairing_strategy: item.pairing_strategy,
          })),
        };

        const response = await imgUpload(payload, "registration");
        const data = response.data.data || {};
        this.summary = data.summary || null;
        const results = data.results || [];
        this.resultArr = results.filter((item) => item.status === "success").map((item) => ({
          ...item,
          fixed_input_full_url: this.prefixUrl(item.fixed_input),
          moving_input_full_url: this.prefixUrl(item.moving_input),
          output_full_url: this.prefixUrl(item.output_path),
          overlay_full_url: this.prefixUrl(item.overlay_path),
          checkerboard_full_url: this.prefixUrl(item.checkerboard_path),
        }));
        this.failedArr = results.filter((item) => item.status !== "success").map((item) => ({
          pair_name: item.pair_name,
          message: item.message || "未知错误",
        }));

        if (!this.resultArr.length && this.failedArr.length) {
          this.$message.warning("本批次配准未成功，请检查失败原因后重试");
          return;
        }

        this.$message.success(response.data.msg || "配准成功");
      } catch (error) {
        console.error(error);
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
    formatRatio(value) {
      if (value === null || value === undefined) {
        return "暂无";
      }
      return `${(Number(value) * 100).toFixed(1)}%`;
    },
    formatRmse(value) {
      if (value === null || value === undefined || Number.isNaN(Number(value))) {
        return "暂无";
      }
      return Number(value).toFixed(2);
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

#sub-title:hover:after {
  left: 0;
  right: 0;
  width: 220px;
}

.registration-panel {
  position: relative;
}

.clear-queue {
  position: absolute;
  left: 5px;
  top: 10%;
  z-index: 100;
}

.pairing-summary {
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
  margin-bottom: 12px;
}

.summary-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

.summary-meta {
  font-size: 14px;
  color: var(--text-secondary);
}

.pairing-warning {
  margin-top: 12px;
  font-size: 14px;
  color: var(--theme-warning-color);
  line-height: 1.8;
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

.handle-button {
  margin-top: 20px;
  text-align: center;
}

.result-summary {
  padding-right: 40px;
  font-weight: 600;
  color: var(--theme-active-color);
}

.failed-box {
  margin-bottom: 20px;
}

.result-card {
  margin-bottom: 20px;
}

.result-card__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 16px;
}

.result-card__title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

.result-card__meta {
  margin-top: 4px;
  color: var(--text-secondary);
  font-size: 13px;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.result-image {
  background: var(--theme-surface-secondary);
  border-radius: 12px;
  padding: 10px;
}

.result-image :deep(.el-image) {
  width: 100%;
  aspect-ratio: 1 / 1;
  border-radius: 10px;
  overflow: hidden;
}

.result-image__label {
  margin-top: 8px;
  text-align: center;
  color: var(--text-secondary);
  font-size: 13px;
}

.metric-row {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 14px;
  color: var(--text-secondary);
  font-size: 14px;
}

.result-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 20px;
  margin-top: 8px;
}

@media (max-width: 768px) {
  .result-grid {
    grid-template-columns: 1fr;
  }

  .result-summary {
    padding-right: 0;
  }
}
</style>
