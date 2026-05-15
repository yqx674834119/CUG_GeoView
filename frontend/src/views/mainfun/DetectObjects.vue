<template>
  <div>
    <Tabinfor>
      <template #left>
        <div
          id="sub-title"
        >
          多目标变化检测模块<i
            class="icon-click"
          />
        </div>
      </template>
    </Tabinfor>
    <el-divider />
    <p>
      请选择待识别的<span class="go-bold">影像数据文件夹</span><i class="icon-folder-new" />或<span
        class="go-bold"
      >影像文件</span><i class="icon-upload-new" />
    </p>
    <p>
      支持多目标（车辆、船只、飞机、建筑物、储气罐）位置检测与标注，支持多模型选择。
    </p>
    <el-row
      type="flex"
      justify="center"
    >
      <el-col :span="24">
        <el-card class="upload-panel upload-panel--single">
          <div
            v-if="fileList.length"
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
          <el-upload
            ref="upload"
            v-model:file-list="fileList"
            class="upload-card"
            drag
            action="#"
            multiple
            :auto-upload="false"
            @change="beforeUpload(fileList[fileList.length - 1].raw)"
          >
            <i class="iconfont icon-yunduanshangchuan" />
            <div class="el-upload__text">
              将文件拖到此处，或<em>点击上传</em>
            </div>
            <div
           
              class="el-upload__tip"
            >
              只能上传一张或多张图片，请在下方上传文件夹
            </div>
          </el-upload>
          <el-row justify="center" class="upload-action-row">
            <input
              id="folder"
              ref="uploadFile"
              type="file"
              webkitdirectory
              directory
              multiple
              @change="uploadMore()"
            >
            <i
              class="iconfont icon-wenjianshangchuan upload-folder-action"
              @click="fileClick"
            >上传文件夹</i>
          </el-row>

          <el-row justify="center" class="upload-helper-row">
            <p>
              <label class="prehandle-label container">
                <input
                  ref="cut"
                  type="checkbox"

                  @change="select()"
                >
                <span class="checkmark" />
                <span class="go-bold label-words">上传时编辑图片</span><i
                  class="iconfont icon-crop-full"
                />
              </label>
            </p>
          </el-row>
          <div class="upload-options-row" style="margin-bottom: 20px;">
            <el-checkbox v-model="isSlice" label="开启大图切分" border />
          </div>
          <el-row
            justify="center"
            align="middle"
          >
            <i
              class="iconfont icon-tuxingtuxiangchuli"
            />
            <p>图像增强：</p>
            <p>
              <label class="prehandle-label container">
                <input
                  ref="clahe"
                  type="checkbox"
                  @change="selectClahe(2)"
                >
                <span class="checkmark" />
                <span class="go-bold label-words">CLAHE</span>
              </label>
            </p>
            <p>
              <label class="prehandle-label container">
                <input
                  ref="sharpen"
                  type="checkbox"
                  @change="selectSharpen(2)"
                >
                <span class="checkmark" />
                <span class="go-bold label-words">锐化</span>
              </label>
            </p>
          </el-row>
          <el-row
            justify="center"
            align="middle"
          >
            <i
              class="iconfont icon-agora_AIjiangzao"
            />
            <p>降噪处理：</p>
            <p>
              <label class="prehandle-label container">
                <input
                  ref="smooth"
                  type="checkbox"
                  @change="selectSmooth()"
                >
                <span class="checkmark" />
                <span class="go-bold label-words">平滑</span>
              </label>
              <label class="prehandle-label container">
                <input
                  ref="filter"
                  type="checkbox"

                  @change="selectFilter()"
                >
                <span class="checkmark" />
                <span class="go-bold label-words">滤波</span>
              </label>
            </p>
          </el-row>
          <el-row justify="center">
            <div class="custom-model">
              可选训练模型：
              <span v-if="modelPathArr.length===0">未检测到模型文件，请查看上传目录是否有误</span>
              <el-radio
                v-for="(item,index) in modelPathArr"
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
                    <i class="iconfont icon-tishi model-label__icon" />
                  </span>
                </el-tooltip>
              </el-radio>
            </div>
          </el-row>
          <div class="handle-button">
            <el-button
              type="primary"
              class="btn-animate btn-animate__shiny"
              @click="upload('目标检测','object_detection')"
            >
              开始处理
            </el-button>
          </div>
          <el-divider v-if="!uploadSrc.prehandle" />
          <div v-if="uploadSrc.prehandle">
            <div v-if="uploadSrc.prehandle===2">
              <div
                id="sub-title"
              >
                CLAHE处理结果预览<i
                  class="iconfont icon-dianji"
                />
              </div>   
            </div>
            <div v-else-if="uploadSrc.prehandle===4">
              <div
                id="sub-title"
              >
                锐化处理结果预览<i
                  class="iconfont icon-dianji"
                />
              </div>   
            </div>
            <el-divider />
            <el-row
              justify="center"
              :gutter="20"
            >
              <el-col
                :xs="24"
                :sm="24"
                :md="6"
                :lg="6"
                :xl="6"
              >
                <div
                  v-for="(item,index) in before"
                  :key="index"
                >
                  <el-image
                    :src="item"
                    :preview-src-list="[item]"
                    :preview-teleported="true"
                  /><div class="handle-words">
                    原图
                  </div>
                </div>
              </el-col>
              <el-col
                :md="2"
                :lg="2"
                :xl="2"
              />
              <el-col
                v-if="uploadSrc.prehandle===2"
                :xs="24"
                :sm="24"
                :md="6"
                :lg="6"
                :xl="6"
              >
                <div
                  v-for="(item,index) in claheImg"
                  :key="index"
                >
                  <el-image
                    :src="item"
                    :preview-src-list="[item]"
                    :preview-teleported="true"
                  /><div class="handle-words">
                    CLAHE处理后       <span
                      @click="
                        downloadimgWithWords(
                          -1,
                          item,
                          `CLAHE处理图.png`
                        )
                      "
                    ><i class="iconfont icon-xiazai" /></span>
                  </div>
                </div>
              </el-col>
              <el-col
                v-if="uploadSrc.prehandle===4"
                :xs="24"
                :sm="24"
                :md="6"
                :lg="6"
                :xl="6"
              >
                <div
                  v-for="(item,index) in sharpenImg"
                  :key="index"
                >
                  <el-image
                    :src="item"
                    :preview-src-list="[item]"
                    :preview-teleported="true"
                  /><div class="handle-words">
                    锐化处理后      <span
                      @click="
                        downloadimgWithWords(
                          -1,
                          item,
                          `锐化处理图.png`
                        )
                      "
                    ><i class="iconfont icon-xiazai" /></span>
                  </div>
                </div>
              </el-col>
            </el-row>
          </div>
        </el-card>
      </el-col>
    </el-row>
    <Tabinfor>
      <template #left>
        <div
          id="sub-title"
        >
          结果图预览<i
            class="iconfont icon-dianji"
          />
        </div>
      </template>
    </Tabinfor>
    <el-divider />
    <Tabinfor>
      <template #left>
        <p>
          <span class="go-bold">点击图片</span>即可预览
          <i
            class="iconfont icon-duigou"
          />
          <span><span class="go-bold">滑轮滚动</span>即可放大缩小</span>
        </p>
      </template>
      <template #mid>
        <p v-if="isUpload">
          <i
            class="iconfont icon-dabaoxiazai"
            @click="goCompress('目标检测')"
          >结果图打包</i>
        </p>
      </template>
      <template #right>
        <span class="go-bold"><i
          class="iconfont icon-shuaxin"
          style="padding-right:55px"
          @click="getMore"
        ><span class="hidden-sm-and-down">点击刷新</span></i></span>
      </template>
    </Tabinfor>
    <el-card
      v-if="imgArr.length"
      class="comparison-control-panel"
    >
      <div class="comparison-control-panel__head">
        <div>
          <div class="comparison-panel__title">两图目标变化对比</div>
          <div class="comparison-panel__meta">
            选择左侧和右侧两个结果后，点击“变化检测”按钮生成目标变化对比结果。
          </div>
        </div>
        <el-tag
          v-if="imgArr.length >= 2"
          effect="dark"
          type="info"
        >
          可选 {{ imgArr.length }} 个结果
        </el-tag>
      </div>

      <div
        v-if="imgArr.length >= 2"
        class="comparison-control-row"
      >
        <el-select
          v-model="selectedComparisonLeft"
          class="comparison-select"
          placeholder="选择左侧结果"
        >
          <el-option
            v-for="option in comparisonOptions"
            :key="`left_${option.value}`"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
        <el-select
          v-model="selectedComparisonRight"
          class="comparison-select"
          placeholder="选择右侧结果"
        >
          <el-option
            v-for="option in comparisonOptions"
            :key="`right_${option.value}`"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
        <el-button
          type="primary"
          class="btn-animate btn-animate__shiny comparison-trigger"
          @click="runDetectionComparison"
        >
          变化检测
        </el-button>
      </div>
      <div
        v-else
        class="comparison-empty-tip"
      >
        至少需要 2 条识别结果才能进行两图目标变化对比。
      </div>
    </el-card>
    <el-card
      v-if="detectionComparison"
      class="comparison-panel"
    >
      <div class="comparison-panel__head">
        <div>
          <div class="comparison-panel__title">两图目标变化对比</div>
          <div class="comparison-panel__meta">
            {{ detectionComparison.scopeText }}
          </div>
        </div>
        <el-tag effect="dark" type="warning">
          变化对比
        </el-tag>
      </div>

      <div class="comparison-metric-row">
        <div class="comparison-metric-card">
          <div class="comparison-metric-card__label">目标数量变化</div>
          <div class="comparison-metric-card__value">
            {{ detectionComparison.detectionDeltaText }}
          </div>
          <div class="comparison-metric-card__desc">
            图像2相对图像1的识别目标数量变化
          </div>
        </div>
        <div class="comparison-metric-card">
          <div class="comparison-metric-card__label">平均置信度变化</div>
          <div class="comparison-metric-card__value">
            {{ detectionComparison.confidenceDeltaText }}
          </div>
          <div class="comparison-metric-card__desc">
            两张图平均识别置信度差值
          </div>
        </div>
        <div class="comparison-metric-card">
          <div class="comparison-metric-card__label">新增类别</div>
          <div class="comparison-metric-card__value">
            {{ detectionComparison.newLabelsText }}
          </div>
          <div class="comparison-metric-card__desc">
            仅在图像2中出现的类别
          </div>
        </div>
        <div class="comparison-metric-card">
          <div class="comparison-metric-card__label">消失类别</div>
          <div class="comparison-metric-card__value">
            {{ detectionComparison.disappearedLabelsText }}
          </div>
          <div class="comparison-metric-card__desc">
            图像1存在但图像2未再出现的类别
          </div>
        </div>
      </div>

      <div class="comparison-preview-grid">
        <div class="comparison-preview-card">
          <div class="comparison-preview-card__title">图像1识别结果</div>
          <div class="comparison-preview-card__meta">
            {{ detectionComparison.firstRecordTitle }}
          </div>
          <el-image
            :src="comparisonImageSrc(detectionComparison.firstRecord, 'after_img')"
            :preview-src-list="[comparisonImageSrc(detectionComparison.firstRecord, 'after_img')]"
            :preview-teleported="true"
            fit="cover"
            class="comparison-preview-card__image"
          />
        </div>
        <div class="comparison-preview-card">
          <div class="comparison-preview-card__title">图像2识别结果</div>
          <div class="comparison-preview-card__meta">
            {{ detectionComparison.secondRecordTitle }}
          </div>
          <el-image
            :src="comparisonImageSrc(detectionComparison.secondRecord, 'after_img')"
            :preview-src-list="[comparisonImageSrc(detectionComparison.secondRecord, 'after_img')]"
            :preview-teleported="true"
            fit="cover"
            class="comparison-preview-card__image"
          />
        </div>
      </div>

      <v-chart
        class="comparison-chart"
        :option="detectionComparisonChartOption"
        autoresize
      />
    </el-card>
    <el-dialog
      v-model="cutVisible"
      :modal="false"
      title="编辑"
      width="75%"
      top="0"
    >
      <MyVueCropper
        :fileimg="fileimg"
        :funtype="funtype"
        :file="file"
        :child_prehandle="uploadSrc.prehandle"
        :child_denoise="uploadSrc.denoise"
        :child-model-path="uploadSrc.model_path"
        @cut-changed="notvisible"
        @child-refresh="getMore"
      />
    </el-dialog>
    <ImgShow
      :img-arr="imgArr"
    />
  </div>
</template>
<script>
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { BarChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  TooltipComponent,
} from "echarts/components";
import VChart from "vue-echarts";

import {atchDownload, downloadimgWithWords, getImgArrayBuffer} from "@/utils/download.js";
import {createSrc, imgUpload,getCustomModel} from "@/api/upload";
import {getUploadImg, goCompress, upload} from "@/utils/getUploadImg";
import {selectClahe, selectFilter, selectSharpen, selectSmooth,} from "@/utils/preHandle";
import { analyzeDetectionRecord } from "@/utils/frontAnalysis";
import { resolveRecordSource } from "@/utils/mediaTransport";
import ImgShow from "@/components/ImgShow";
import Tabinfor from "@/components/Tabinfor";
import MyVueCropper from "@/components/MyVueCropper";

use([
  CanvasRenderer,
  BarChart,
  GridComponent,
  LegendComponent,
  TooltipComponent,
]);

export default {
  name: "Detectobjects",
  components: {
    ImgShow,
    Tabinfor,
    MyVueCropper,
    VChart,
  },
  beforeRouteEnter(to, from, next) {
    next((vm) => {
      document.querySelector(".el-main").scrollTop = 0;
    });
  },
  data() {
    return {
      isUpload:true,
      canUpload:true,
      claheImg:[],
      sharpenImg:[],
      before:[],
      fileimg: "",
      file: {},
      isNotCut: true,
      cutVisible: false,
      funtype: "目标检测",
      scrollTop: "",
      fit: "fill",

      fileList: [],
      uploadSrc: {
        list: [],
        prehandle: 0,
        denoise: 0,
        model_path:''
      },
      modelPathArr:[],
      prePhoto:{
        list:[],
        prehandle:0,
        type:4
      },
      imgArr:[],
      isSlice: false,
      selectedComparisonLeft: null,
      selectedComparisonRight: null,
      comparedPair: null,
    };
  },
  watch:{
    uploadSrc:{
      handler(newVal,oldVal){
        this.uploadSrc = newVal
      },
      deep:true,
      immediate:true
    },
    imgArr: {
      handler(records) {
        if (!Array.isArray(records) || records.length < 2) {
          this.selectedComparisonLeft = null;
          this.selectedComparisonRight = null;
          this.comparedPair = null;
          return;
        }
        this.selectedComparisonLeft = 0;
        this.selectedComparisonRight = 1;
        this.comparedPair = null;
      },
      deep: true,
      immediate: true
    }
  },
  computed: {
    comparisonOptions() {
      return (Array.isArray(this.imgArr) ? this.imgArr : []).map((item, index) => ({
        value: index,
        label: this.comparisonOptionLabel(item, index),
      }));
    },
    detectionComparison() {
      if (!this.comparedPair) {
        return null;
      }

      const firstRecord = this.imgArr[this.comparedPair.left];
      const secondRecord = this.imgArr[this.comparedPair.right];
      if (!firstRecord || !secondRecord) {
        return null;
      }

      const records = [firstRecord, secondRecord];
      const [firstAnalysis, secondAnalysis] = records.map((item) => analyzeDetectionRecord(item));
      const firstLabels = Object.fromEntries(firstAnalysis.labelStats.map((item) => [item.name, item.value]));
      const secondLabels = Object.fromEntries(secondAnalysis.labelStats.map((item) => [item.name, item.value]));
      const labelNames = Array.from(new Set([
        ...Object.keys(firstLabels),
        ...Object.keys(secondLabels),
      ]));
      const labelRows = labelNames.map((name) => ({
        name,
        first: firstLabels[name] || 0,
        second: secondLabels[name] || 0,
      }));

      const newLabels = labelNames.filter((name) => !firstLabels[name] && secondLabels[name]);
      const disappearedLabels = labelNames.filter((name) => firstLabels[name] && !secondLabels[name]);
      const detectionDelta = secondAnalysis.detectionCount - firstAnalysis.detectionCount;
      const confidenceDelta = Number((secondAnalysis.avgConfidence - firstAnalysis.avgConfidence).toFixed(2));
      const scopeText = `当前对比基于 ${this.comparisonOptionLabel(firstRecord, this.comparedPair.left)} 与 ${this.comparisonOptionLabel(secondRecord, this.comparedPair.right)} 生成。`;

      return {
        firstRecord,
        secondRecord,
        firstRecordTitle: `目标数 ${firstAnalysis.detectionCount} / 主导类别 ${firstAnalysis.dominantLabel}`,
        secondRecordTitle: `目标数 ${secondAnalysis.detectionCount} / 主导类别 ${secondAnalysis.dominantLabel}`,
        detectionDeltaText: `${detectionDelta > 0 ? "+" : ""}${detectionDelta}`,
        confidenceDeltaText: `${confidenceDelta > 0 ? "+" : ""}${confidenceDelta}%`,
        newLabelsText: newLabels.length ? newLabels.join("、") : "无",
        disappearedLabelsText: disappearedLabels.length ? disappearedLabels.join("、") : "无",
        labelRows,
        scopeText,
      };
    },
    detectionComparisonChartOption() {
      if (!this.detectionComparison) {
        return null;
      }
      return {
        tooltip: { trigger: "axis" },
        legend: { top: 0 },
        grid: { left: 50, right: 20, top: 40, bottom: 54 },
        xAxis: {
          type: "category",
          data: this.detectionComparison.labelRows.map((item) => item.name),
          axisLabel: {
            interval: 0,
            rotate: 18,
          },
        },
        yAxis: { type: "value", name: "目标数" },
        series: [
          {
            name: "图像1",
            type: "bar",
            data: this.detectionComparison.labelRows.map((item) => item.first),
            itemStyle: { color: "#64748b", borderRadius: [6, 6, 0, 0] },
          },
          {
            name: "图像2",
            type: "bar",
            data: this.detectionComparison.labelRows.map((item) => item.second),
            itemStyle: { color: "#f97316", borderRadius: [6, 6, 0, 0] },
          },
        ],
      };
    }
  },
  created() {
    this.getUploadImg("目标检测");
    this.getCustomModel('object_detection').then((res)=>{
      this.modelPathArr = res.data.data
      this.uploadSrc.model_path = this.modelPathArr[0]?.model_path
    }).catch((rej)=>{})
  },
  methods: {
    getImgArrayBuffer,
    atchDownload,
    downloadimgWithWords,
    imgUpload,
    getCustomModel,
    createSrc,
    getUploadImg,
    upload,
    goCompress,
    selectSharpen,
    selectFilter,
    selectSmooth,
    selectClahe,
    comparisonOptionLabel(record, index) {
      const rawSource = String(record?.before_img || record?.after_img || "");
      const filename = rawSource.split("/").pop()?.split("?")[0] || `结果 ${index + 1}`;
      const groupId = record?.id ? `第${record.id}组` : `结果 ${index + 1}`;
      return `${groupId} - ${filename}`;
    },
    comparisonImageSrc(record, field) {
      return record?.[`_${field}_preview`] || resolveRecordSource(record, field) || record?.[field] || "";
    },
    runDetectionComparison() {
      if (this.selectedComparisonLeft === null || this.selectedComparisonRight === null) {
        this.$message.warning("请先选择左右两个结果");
        return;
      }
      if (this.selectedComparisonLeft === this.selectedComparisonRight) {
        this.$message.warning("左右结果不能选择同一条记录");
        return;
      }
      this.comparedPair = {
        left: this.selectedComparisonLeft,
        right: this.selectedComparisonRight,
      };
      this.$message.success("两图目标变化对比已生成");
    },
    checkUpload() {
      this.isUpload = this.afterImg.length !== 0;
    },
    clearQueue() {
      this.fileList = [];
      this.imgArr = [];
      this.isUpload = false;
      this.selectedComparisonLeft = null;
      this.selectedComparisonRight = null;
      this.comparedPair = null;
      this.$message.success("清除成功");
    },
    notvisible() {
      this.cutVisible = false;
      this.fileList = [];
    },
    getMore(records) {
      if (Array.isArray(records) && records.length) {
        this.imgArr = records;
        this.isUpload = true;
        return;
      }
      this.getUploadImg("目标检测");
    },
    uploadMore() {
            this.beforeUpload(...this.$refs.uploadFile.files)
        if(this.canUpload){
          this.fileList.push(...this.$refs.uploadFile.files);
        }else{
          setTimeout(() => {
              this.$message.error('检测到您上传的文件夹内存在不符合规范的图片类型')
          }, 1000);
        
        }
    },
    fileClick() {
      document.querySelector("#folder").click();
    },
    beforeUpload(file) {
      const cutRef = this.$refs && this.$refs.cut;
      this.cutVisible = Boolean(cutRef && cutRef.checked);
      const fileSuffix = file.name.substring(file.name.lastIndexOf(".") + 1)
      // 支持 TIFF 格式用于遥感影像
      const whiteList = ['jpg','jpeg','png','JPG','JPEG','tif','tiff','TIF','TIFF']
      if (whiteList.indexOf(fileSuffix) === -1) {
        this.$message.error("只允许上传jpg, jpeg, png, tif, tiff格式,请重新上传");
        this.fileList= []
        this.canUpload = false
        this.cutVisible = false;
      }
      else{
        this.canUpload = true
        this.fileimg = window.URL.createObjectURL(new Blob([file]));
      }
    },
    select() {
      const cutRef = this.$refs && this.$refs.cut;
      this.isNotCut = Boolean(cutRef && cutRef.checked);
    },
  },
};
</script>
<style lang="less" scoped>
* {
  font-family: var(--theme-default-fontfamily);
}
#sub-title{
  font-size: 25px;
}
#sub-title:hover:after {
  left: 0%;
  right: 0%;
  width: 220px;
}
.clear-queue {
  position: absolute;
  left: 5px;
  top: 10%;
  z-index: 100;
}

.comparison-panel {
  margin-bottom: 18px;
  border-radius: 18px;
  border: 1px solid rgba(249, 115, 22, 0.18);
  background:
    radial-gradient(circle at top right, rgba(249, 115, 22, 0.1), transparent 32%),
    linear-gradient(180deg, rgba(255, 250, 245, 0.98), rgba(255, 255, 255, 0.98));
}

.comparison-control-panel {
  margin-bottom: 18px;
  border-radius: 18px;
  border: 1px solid rgba(59, 130, 246, 0.16);
  background:
    radial-gradient(circle at top right, rgba(59, 130, 246, 0.08), transparent 30%),
    linear-gradient(180deg, rgba(246, 250, 255, 0.98), rgba(255, 255, 255, 0.98));
}

.comparison-control-panel__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 14px;
}

.comparison-control-row {
  margin-top: 16px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
}

.comparison-select {
  width: 100%;
}

.comparison-trigger {
  min-width: 120px;
}

.comparison-empty-tip {
  margin-top: 14px;
  padding: 14px 16px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.84);
  border: 1px dashed rgba(148, 163, 184, 0.28);
  color: var(--text-secondary);
}

.comparison-panel__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 14px;
}

.comparison-panel__title {
  font-size: 18px;
  font-weight: 700;
  color: var(--theme-heading-color);
}

.comparison-panel__meta {
  margin-top: 6px;
  color: var(--text-secondary);
  font-size: 13px;
}

.comparison-metric-row {
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.comparison-metric-card {
  padding: 14px 16px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.comparison-metric-card__label {
  color: var(--text-secondary);
  font-size: 13px;
}

.comparison-metric-card__value {
  margin-top: 8px;
  font-size: 28px;
  line-height: 1.1;
  color: var(--theme-heading-color);
  font-family: var(--theme-display-fontfamily);
}

.comparison-metric-card__desc {
  margin-top: 8px;
  color: var(--text-secondary);
  font-size: 12px;
}

.comparison-preview-grid {
  margin-top: 18px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 14px;
}

.comparison-preview-card {
  padding: 14px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.comparison-preview-card__title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}

.comparison-preview-card__meta {
  margin-top: 6px;
  color: var(--text-secondary);
  font-size: 12px;
}

.comparison-preview-card__image {
  margin-top: 12px;
  width: 100%;
  min-height: 240px;
  border-radius: 14px;
  overflow: hidden;
}

.comparison-chart {
  margin-top: 18px;
  width: 100%;
  height: 320px;
}

.custom-model {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.el-radio {
  height: auto !important;
  margin-bottom: 15px;
  margin-right: 30px;
  display: inline-flex;
  align-items: center;
}

.el-radio /deep/ .el-radio__label {
  display: flex;
  align-items: center;
  padding-left: 10px;
}

.el-radio /deep/ .el-radio__input {
  margin-top: 0;
}

@media (max-width: 768px) {
  .comparison-control-row {
    grid-template-columns: 1fr;
  }

  .comparison-trigger {
    width: 100%;
  }

  .comparison-chart {
    height: 280px;
  }
}
</style>
