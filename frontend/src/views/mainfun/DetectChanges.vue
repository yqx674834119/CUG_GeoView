<template>
  <div>
    <Tabinfor>
      <template #left>
        <div
          id="sub-title"
        >
          时序变化分析<i
            class="icon-click"
          />
        </div>
      </template>
    </Tabinfor>
    <el-divider />
    <p>
      请选择待分析的<span class="go-bold">影像数据文件夹</span><i
        class="icon-folder-new"
      />或<span
        class="go-bold"
      >影像文件</span><i
        class="icon-upload-new"
      />，请确保影像数据<span class="go-bold">格式符合要求</span>，同组对比影像需<span class="go-bold">分别</span>存放在两个文件夹中
    </p>
    <p style="text-decoration: underline">
      <i
        class="icon-warning"
      />提示：同组对比影像请使用<span class="go-bold">统一命名规则</span>，系统将根据文件名进行<span class="go-bold">自动配对</span>分析
    </p><p>
      
    </p>
    <el-card class="upload-panel upload-panel--double">
      <div
        v-if="fileList1.length||fileList2.length"
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
          <div class="upload-caption">第一时期影像</div>
          <el-upload
            class="upload-card"
            ref="uploadA"
            v-model:file-list="fileList1"
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
            <div
              class="el-upload__tip"
            >
              只能上传一张或多张图片，请在下方上传文件夹
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
          <div class="upload-caption">第二时期影像</div>
          <el-upload
            class="upload-card"
            ref="uploadB"
            v-model:file-list="fileList2"
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
            <div
              class="el-upload__tip"
            >
              只能上传一张或多张图片，请在下方上传文件夹
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
      <div class="slider-box">
        <div class="slider-item">
          <div>自定义窗口：</div>
          <el-slider
            v-model="upload.window_size"
            show-input
            :max="512"
          />
        </div>
        <div class="slider-item">
          <span>自定义步长：</span>
          <el-slider
            v-model="upload.stride"
            show-input
            :max="upload.window_size"
          />
        </div>
      </div>
      <div class="upload-options-row" style="margin-bottom: 20px;">
        <el-checkbox v-model="isSlice" label="开启大图切分" border />
      </div>
      <el-row
        justify="center"
        align="middle"
      >
        <i
          class="iconfont icon-tuxingtuxiangchuli"
        /><p>图像增强：</p>
        <p>
          <label class="prehandle-label container">
            <input
              ref="histogram"
              type="checkbox"
              @change="selectHistogram()"
            >
            <span class="checkmark" />
            <span class="go-bold label-words">直方图匹配</span>
          </label>

          <label class="container prehandle-label">
            <input
              ref="sharpen"
              type="checkbox"
              @change="selectSharpen()"
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
        /> <p>降噪处理：</p>
        <p>
          <label class="container prehandle-label">
            <input
              ref="smooth"
              type="checkbox"

              @change="selectSmooth()"
            >
            <span class="checkmark " />
            <span class="go-bold label-words">平滑</span>
          </label>
          <label class="container prehandle-label">
            <input
              ref="filter"
              type="checkbox"
              @change="selectFilter()"
            >
            <span class="checkmark " />
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
            v-model="upload.model_path"
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
          class=" btn-animate btn-animate__shiny"
          @click="uploadfile"
        >
          开始处理
        </el-button>
      </div>

      <el-divider v-if="!upload.prehandle" />
      <div v-if="upload.prehandle">
        <div v-show="upload.prehandle===1">
          <div
            id="sub-title"
          >
            直方图匹配结果预览
            <i
              class="iconfont icon-dianji"
            />
          </div>
          <el-divider />
          <el-row
            justify="center"
            :gutter="20"
          >
            <el-col
              :xs="24"
              :sm="24"
              :md="7"
              :lg="7"
              :xl="7"
            >
              <div
                v-for="(item,index) in Img1"
                :key="index"
              >
                <el-image
                  :src="item"
                  :preview-src-list="[item]"
                  :preview-teleported="true"
                /><div class="handle-words">
                  第一时期图
                </div>
              </div>
            </el-col>
            <el-col
              :xs="24"
              :sm="24"
              :md="7"
              :lg="7"
              :xl="7"
            >
              <div
                v-for="(item,index) in Img2"
                :key="index"
              >
                <el-image
                  :src="item"
                  :preview-src-list="[item]"
                  :preview-teleported="true"
                /><div class="handle-words">
                  匹配后的第一时期图       <span
                    @click="
                      downloadimgWithWords(
                        ++hisNum,
                        item,
                        `直方图匹配后第一时期图.png`
                      )
                    "
                  ><i class="iconfont icon-xiazai" /></span>
                </div>
              </div>
            </el-col>
            <el-col
              :xs="24"
              :sm="24"
              :md="7"
              :lg="7"
              :xl="7"
            >
              <div
                v-for="(item,index) in Img3"
                :key="index"
              >
                <el-image
                  :src="item"
                  :preview-src-list="[item]"
                  :preview-teleported="true"
                /><div class="handle-words">
                  第二时期图
                </div>
              </div>
            </el-col>
          </el-row>
        </div>
        <div v-show="upload.prehandle === 4">
          <div
            id="sub-title"
          >
            锐化结果预览<i
              class="iconfont icon-dianji"
            />
          </div>
          <el-divider />
          <el-row
            justify="center"
            :gutter="20"
          >
            <el-col
              :xs="10"
              :sm="10"
              :md="6"
              :lg="6"
              :xl="6"
            >
              <div
                v-for="(item,index) in Img1"
                :key="index"
              >
                <el-image
                  :src="item"
                  :preview-src-list="[item]"
                  :preview-teleported="true"
                /><div class="handle-words">
                  第一时期图
                </div>
              </div>
            </el-col>
            <el-col
              :xs="10"
              :sm="10"
              :md="6"
              :lg="6"
              :xl="6"
            >
              <div
                v-for="(item,index) in sharpenImg1"
                :key="index"
              >
                <el-image
                  :src="item"
                  :preview-src-list="[item]"
                  :preview-teleported="true"
                /><div class="handle-words">
                  锐化后的第一时期图       <span
                    @click="
                      downloadimgWithWords(
                        -1,
                        item,
                        `锐化处理后第一时期图.png`
                      )
                    "
                  ><i class="iconfont icon-xiazai" /></span>
                </div>
              </div>
            </el-col>
            <el-col
              :xs="10"
              :sm="10"
              :md="6"
              :lg="6"
              :xl="6"
            >
              <div
                v-for="(item,index) in Img3"
                :key="index"
              >
                <el-image
                  :src="item"
                  :preview-src-list="[item]"
                  :preview-teleported="true"
                /><div class="handle-words">
                  第二时期图
                </div>
              </div>
            </el-col>
            <el-col
              :xs="10"
              :sm="10"
              :md="6"
              :lg="6"
              :xl="6"
            >
              <div
                v-for="(item,index) in sharpenImg2"
                :key="index"
              >
                <el-image
                  :src="item"
                  :preview-src-list="[item]"
                  :preview-teleported="true"
                /><div class="handle-words">
                  锐化后的第二时期图       <span
                    @click="
                      downloadimgWithWords(
                        -1,
                        item,
                        `锐化处理后第二时期图.png`
                      )
                    "
                  ><i class="iconfont icon-xiazai" /></span>
                </div>
              </div>
            </el-col>
          </el-row>
        </div>
      </div>
    </el-card>

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
          对输出的结果图进行<span class="go-bold">多种渲染</span><i
            class="iconfont icon-xuanran"
          />
          <span class="go-bold">，点击图片</span>即可预览
          <i
            class="iconfont icon-duigou"
          />
        </p>
      </template>
      <template #mid>
        <label
          v-if="resultArr.length!==0"
          class="prehandle-label container"
        >
          <input
            ref="hole"
            type="checkbox"
            :checked="resultArr[currentIndex].is_hole"
            @click="toggleHoleStatus"
          >
          <span class="checkmark" />
          <span class="go-bold label-words"><span class="hidden-md-and-down">开启连通域滤波并填充</span>孔洞处理</span>
        </label>
        <span><i
          class="iconfont icon-qiehuan"
          @click="changePreMode"
        >切换预览模式</i></span>
      </template>
      <template #right>
        <p>
          <span class="go-bold"><i
            class="iconfont icon-shuaxin"
            style=" padding-right: 55px;"
            @click="getMore"
          ><span class="hidden-sm-and-down">点击刷新</span></i></span>
        </p>
      </template>
    </Tabinfor>

    <el-card class="render-box">
      <div
        class="render-img-box"
      >
        <div
          v-if="preMode===1"
          class="display-modeA"
        >
          <div
            id="image-slider"
            ref="resultSlider"
            @pointerdown.prevent="startSliderDrag"
          >
            <div
              v-show="!isHiddenMask"
              class="mask-layer"
            >
              <img
                v-if="currentMaskSource && !holeShow"
                :src="currentMaskSource"
                alt="mask"
                class="mask-img"
              >
              <img
                v-if="currentMaskHoleSource && holeShow"
                :src="currentMaskHoleSource"
                alt="mask"
                class="mask-img"
              >
              <img
                v-if="!resultArr[currentIndex]?.data.mask"
                :src="exampleArr[0].data.mask "
                alt="mask"
                class="mask-img"
              >
            </div>
            <img
              v-if="currentBeforeSource"
              :src="currentBeforeSource"
              alt=""
            >
            <img
              v-if="!resultArr[currentIndex]?.before_img"
              :src="exampleArr[0].before_img "
              alt=""
            >
            <div
              class="img-wrapper"
              :style="sliderWrapperStyle"
            >
              <img
                v-if="currentBeforeSecondSource"
                :src="currentBeforeSecondSource"
                alt=""
              >
              <img
                v-if="!resultArr[currentIndex]?.before_img1"
                :src="exampleArr[0].before_img1"
                alt=""
              >
            </div>
            <div
              class="handle"
              :style="sliderHandleStyle"
            >
              <div class="handle-line" />
              <div class="handle-circle">
                &#171;&#187;
              </div>
              <div class="handle-line" />
            </div>
          </div>
        </div>

        <div
          v-if="preMode===2 "
          class="display-modeB"
        >
          <div class="render-img modeB-item">
            <p class="handle-words">
              第一时期
            </p>
            <el-image
              v-if="currentBeforeSource"
              :preview-src-list="[currentBeforeSource]"
              :preview-teleported="true"
              :src="currentBeforeSource"
              fit="cover"
            />
            <el-image
              v-if="!resultArr[currentIndex]?.before_img"
              :preview-src-list="[exampleArr[0].before_img]"
              :preview-teleported="true"
              :src="exampleArr[0].before_img"
              fit="cover"
            />
          </div>

          <div class="render-img modeB-item">
            <p class="handle-words">
              第二时期
            </p>
            <el-image
              v-if="currentBeforeSecondSource"
              :preview-src-list="[currentBeforeSecondSource]"
              :preview-teleported="true"
              :src="currentBeforeSecondSource"
              fit="cover"
            />
            <el-image
              v-if="!resultArr[currentIndex]?.before_img1"
              :preview-src-list="[exampleArr[0].before_img1]"
              :preview-teleported="true"
              :src="exampleArr[0].before_img1"
              fit="cover"
            />
          </div>

          <div class="render-img modeB-item">
            <p class="handle-words">
              预测结果
            </p>
            <div style="position: relative">
              <transition
                enter-active-class="animate__animated animate__bounceIn"
                leave-active-class="animate__animated animate__hinge"
              >
                <div v-if="!holeShow">
                  <el-image
                    v-if="onRenderResult && !holeShow"
                    :preview-src-list="[onRenderResult]"
                    :preview-teleported="true"
                    :src="onRenderResult"
                    fit="cover"
                    style="width: 100%"
                  />
                </div>
              </transition>
              <transition
                enter-active-class="animate__animated animate__bounceIn"
                leave-active-class="animate__animated animate__hinge"
              >
                <div
                  v-if="holeShow"
                  style="position: absolute;top: 0;right: 0;"
                >
                  <el-image
                    v-if="onRenderResult && holeShow"
                    :preview-src-list="[onRenderResult]"
                    :preview-teleported="true"
                    :src="onRenderResult"
                    fit="cover"
                    style="width: 100%"
                  />
                </div>
              </transition>
            </div>
            <el-image
              v-if="!onRenderResult"
              :preview-src-list="[onRenderExample]"
              :preview-teleported="true"
              :src="onRenderExample"
              fit="cover"
              style="width: 100%"
            />
          </div>
        </div>

        <div class="render-select-box">
          <div
            v-show="preMode===2"
            class="rendr-style"
          >
            <el-divider />
            <div class="style-title">
              结果图渲染
            </div>

            <label class="cl-checkbox">
              <div class="render-select">
                <div
                  class="style-words normal"
                  :class="{ 'active-normal': renderstyle === '原图' }"
                  @click="setOneWay('原图',resultArr.length===0,holeShow)"
                >原图</div>
                <div
                  class="style-words woods"
                  :class="{ 'active-woods': renderstyle === '森林' }"
                  @click="setOneWay('森林',resultArr.length===0,holeShow)"
                >森林</div>
                <div
                  class="style-words neon"
                  :class="{ 'active-neon': renderstyle === '霓虹' }"
                  @click="setOneWay('霓虹',resultArr.length===0,holeShow)"
                >霓虹</div>
                <div
                  class="style-words flash"
                  :class="{ 'active-flash': renderstyle === '闪电' }"
                  @click="setOneWay('闪电',resultArr.length===0,holeShow)"
                >闪电</div>
                <div
                  class="style-words aurora"
                  :class="{ 'active-aurora': renderstyle === '极光' }"
                  @click="setOneWay('极光',resultArr.length===0,holeShow)"
                >极光</div>
              </div>
            </label>
          </div>
          <p v-if="resultArr.length===0">
            此图为预设展示图，供参考
          </p>
          <el-divider style="margin-top:0" />
          <div class="style-title">
            选择图片
          </div>
          <div v-if="resultArr.length">
            <div
              v-for="(item, index) in Math.ceil(resultArr.length / 5)"
              :key="index"
              class="list"
            >
              <div
                class="list-number"
                @click="goRenderThese(index)"
              >
                <div>
                  {{ 5 * index + 1 }}-----{{ 5 * (index + 1) }}
                </div>
              </div>
            </div>
            <div
              style="text-align:center"
            >
              下载此图片：<el-button
                type="primary"
                style="width:60px"
                class="btn-animate btn-animate__shiny"
                @click="
                  downloadimgWithWords(
                    resultArr[currentIndex].id,
                    onRenderResult,
                    `变化检测${renderstyle}渲染结果图${holeShow ? '(已孔洞处理)' : '(未孔洞处理)'}.png`
                  )
                "
              >
                下载
              </el-button>
            </div>
            <p
              style="text-align:center"
            >
              <span> <i
                class="iconfont icon-dabaoxiazai"
                @click="goCompress"
              >所有结果图打包</i></span>
            </p>
          </div>
          <el-empty
            v-else
            :image-size="100"
          />

          <div
            v-show="dragShow && resultArr.length!==0"
          >
            <DraggableItem @child-vannish="vanishDrag">
              <template #left-1>
                变化建筑物个数：<span v-show="!holeShow">{{ resultArr[currentIndex]?.data.count }}</span><span v-show="holeShow">
                  {{ resultArr[currentIndex]?.data.count_hole }}
                </span>
              </template>
              <template #rightIcon-1>
                <i
                  v-show="!isHiddenMask"
                  class="iconfont icon-yanjing-kai"
                  @click="hideMask"
                />
                <i
                  v-show="isHiddenMask"
                  class="iconfont icon-yanjing-guan"
                  @click="hideMask"
                />
              </template>
              <template #left-2>
                两时期变化百分比：<span v-show="!holeShow">{{ resultArr[currentIndex]?.data.fractional_variation.toFixed(2) }}%</span><span v-show="holeShow">{{ resultArr[currentIndex]?.data.fractional_variation_hole.toFixed(2) }}%</span>
              </template>
              <div style="text-align: center; margin-top: 10px;">
                <el-button size="small" type="primary" @click="showDetailedAnalysis">详细分析</el-button>
              </div>
            </DraggableItem>
          </div>
        </div>
      </div>

      <!-- Detailed Analysis Dialog -->
      <el-dialog
        v-model="detailedAnalysisVisible"
        title="变化检测详细分析"
        width="60%"
        center
      >
        <div v-if="resultArr[currentIndex]">
          <el-descriptions title="基础统计" :column="2" border>
            <el-descriptions-item label="变化区域个数">
              {{ holeShow ? resultArr[currentIndex].data.count_hole : resultArr[currentIndex].data.count }}
            </el-descriptions-item>
            <el-descriptions-item label="总变化面积 (像素)">
              {{ holeShow ? resultArr[currentIndex].data.total_area_hole : resultArr[currentIndex].data.total_area }}
            </el-descriptions-item>
            <el-descriptions-item label="平均变化面积 (像素)">
               {{ (holeShow ? resultArr[currentIndex].data.avg_area_hole : resultArr[currentIndex].data.avg_area).toFixed(2) }}
            </el-descriptions-item>
            <el-descriptions-item label="变化百分比">
              {{ (holeShow ? resultArr[currentIndex].data.fractional_variation_hole : resultArr[currentIndex].data.fractional_variation).toFixed(2) }}%
            </el-descriptions-item>
          </el-descriptions>

          <el-divider>区域大小分布</el-divider>
          <div style="height: 300px; width: 100%;">
            <v-chart class="chart" :option="sizeDistributionOption" autoresize />
          </div>

          <el-divider>Top 10 最大变化区域 (像素)</el-divider>
          <div style="height: 300px; width: 100%;">
            <v-chart class="chart" :option="topChangesOption" autoresize />
          </div>

          <div style="text-align: center; margin-top: 20px;">
            <el-button type="primary" @click="downloadStats">导出统计数据 (JSON)</el-button>
          </div>

        </div>
      </el-dialog>

      <div class="swiper-img">
        <div
          v-for="(item, index) in 5"
          :key="index"
          class="img-box"
        >
          <el-image
            v-if="resultArr[currentQroup+index]?.after_img"
            :src="resultThumbSource(resultArr[currentQroup+index])"
            :class="{'render-border':onRender===index}"
            @click="goRenderThis(index)"
          />
        </div>
      </div>

      <div
        v-show="!dragShow"
        class="drag-control hidden-md-and-down"
        @click="dragShow=true"
      >
        <i
          class="iconfont icon-cebianshouqi"
        />
      </div>
    </el-card>
  </div>
</template>


<script>
import {
  createSrc,
  imgUpload,
  histogramUpload,
  getCustomModel
} from "@/api/upload";
import {
  downloadimgWithWords,
  getImgArrayBuffer,
  atchDownload,
} from "@/utils/download.js";
import Tabinfor from "@/components/Tabinfor";
import DraggableItem from "@/components/DraggableItem";
import {
  resolveDataSource,
  resolveRecordSource,
} from "@/utils/mediaTransport";
import { buildUploadFormData } from "@/utils/uploadFormData";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { PieChart, BarChart } from "echarts/charts";
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent
} from "echarts/components";
import VChart from "vue-echarts";

use([
  CanvasRenderer,
  PieChart,
  BarChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent
]);

function isRefChecked(vm, refName) {
  const ref = vm.$refs && vm.$refs[refName];
  return Boolean(ref && ref.checked);
}

function setRefChecked(vm, refName, value) {
  const ref = vm.$refs && vm.$refs[refName];
  if (ref) {
    ref.checked = value;
  }
}

export default {
  name: "Detectchanges",
  components: {
    Tabinfor,
    DraggableItem,
    VChart,
  },
  beforeRouteEnter(to, from, next) {
    next((vm) => {
      document.querySelector(".el-main").scrollTop = 0;
    });
  },
  data() {
    return {
      holeShow:true,
      isSlice: false,
      sliderPosition: 50,
      isDragging: false,
      preMode: 1,
      pairs: [],
      hisPairs: [],
      shaPairs: [],
      canUpload: true,
      onRender: 0,
      isUpload: true,
      hisNum: 0,
      value:null,
      renderstyle: "原图",
      funtype: "变化检测",
      scrollTop: "",

      currentQroup: 0,
      currentIndex: 0,

      fileList1: [],
      fileList2: [],

      uploadSrc1: [],
      uploadSrc2: [],
      uploadSrc: [],
      upload: {
        window_size:256,
        stride:128,
        list: [
          {
            first: "",
            second: "",
          },
        ],
        prehandle: 0,
        denoise: 0,
        model_path:''
      },
      modelPathArr:[],
      //直方图处理
      uploadSrc3: [],
      uploadSrc4: [],
      histogramSrc: [],
      myhistogram: {
        list: [
          {
            first: "",
            second: "",
          },
        ],
        prehandle: 0,
      },
      Img1: [],
      Img2: [],
      Img3: [],

      //锐化处理
      sharpenSrc1: [],
      sharpenSrc2: [],
      sharpenSrc: [],
      mysharpen: {
        list: [
          {
            first: "",
            second: "",
          },
        ],
        prehandle: 0,
      },
      sharpenImg1: [],
      sharpenImg2: [],

      preHandle: {
        list: [
          {
            first: "",
            second: "",
          },
        ],
      },

      hole: {
        id: "",
      },
      resultArr:[],
      devidedArr:[],
      onRenderResult:'',
      exampleArr:[{
          before_img : require("@/assets/image/example/test_50_1.png"),
          before_img1: require("@/assets/image/example/test_50_2.png"),
          after_img:require('@/assets/image/example/normal.png'),
          data:{
              0:require('@/assets/image/example/flash.png'),
              1:require('@/assets/image/example/aurora.png'),
              2:require('@/assets/image/example/woods.png'),
              3:require('@/assets/image/example/neon.png'),
            mask:require('@/assets/image/example/mask.png')
          }
      }],
      onRenderExample:require('@/assets/image/example/normal.png'),
      isHiddenMask:false,
      dragShow:true,
      sizeValue:[0,200],
      detailedAnalysisVisible: false,
      sizeDistributionOption: {},
      topChangesOption: {},
    };
  },
  computed: {
    currentRecord() {
      return this.resultArr[this.currentIndex] || null;
    },
    currentBeforeSource() {
      if (!this.currentRecord) {
        return "";
      }
      return resolveRecordSource(this.currentRecord, "before_img") || "";
    },
    currentBeforeSecondSource() {
      if (!this.currentRecord) {
        return "";
      }
      return resolveRecordSource(this.currentRecord, "before_img1") || "";
    },
    currentMaskSource() {
      if (!this.currentRecord) {
        return "";
      }
      return resolveDataSource(this.currentRecord, "mask") || "";
    },
    currentMaskHoleSource() {
      if (!this.currentRecord) {
        return "";
      }
      return resolveDataSource(this.currentRecord, "mask_hole") || "";
    },
    sliderWrapperStyle() {
      return {
        clipPath: `inset(0 0 0 ${this.sliderPosition}%)`,
        WebkitClipPath: `inset(0 0 0 ${this.sliderPosition}%)`,
      };
    },
    sliderHandleStyle() {
      return {
        left: `${this.sliderPosition}%`,
      };
    },
  },
  beforeUnmount() {
    this.removeSliderListeners();
  },
  created() {
    this.getMore();
    this.getCustomModel('change_detection').then((res)=>{
      this.modelPathArr = res.data.data
      this.upload.model_path = this.modelPathArr[0]?.model_path
    }).catch((rej)=>{})
  },

  methods: {
    downloadimgWithWords,
    imgUpload,
    getCustomModel,
    createSrc,
    getImgArrayBuffer,
    atchDownload,
    histogramUpload,
    resultThumbSource(item) {
      if (!item) {
        return "";
      }
      return this.holeShow
        ? (resolveDataSource(item, "hole") || "")
        : (resolveRecordSource(item, "after_img") || "");
    },
    clearQueue() {
      this.fileList1 = [];
      this.fileList2 = [];
      this.$message.success("清除成功");
    },
    goRenderThis(index) {
      this.currentIndex = this.currentQroup;
      this.currentIndex += index;
      this.onRender = index;
      this.syncDisplayMode();
      this.resetSliderPosition();
      this.setOneWay(this.renderstyle)
    },
    goRenderThese(index) {
      this.currentQroup = 5 * index;
      this.currentIndex = 5 * index;
      this.goRenderThis(0);
    },
    setOneWay(style,isShowExample,holeStyle) {
      this.renderstyle = style;
      const current = this.resultArr[this.currentIndex];
      if(isShowExample){
        switch (style){
          case '原图': this.onRenderExample = this.exampleArr[0].after_img;break
          case '森林': this.onRenderExample = this.exampleArr[0].data[2];break
          case '霓虹': this.onRenderExample = this.exampleArr[0].data[3];break
          case '闪电': this.onRenderExample = this.exampleArr[0].data[0];break
          case '极光': this.onRenderExample = this.exampleArr[0].data[1];break
        }
        return
      }
      if (!current) {
        this.onRenderResult = "";
        return;
      }
      if(!holeStyle){
        switch (style){
          case '原图': this.onRenderResult = resolveRecordSource(current, "after_img");break
          case '森林': this.onRenderResult = resolveDataSource(current, "2");break
          case '霓虹': this.onRenderResult = resolveDataSource(current, "3");break
          case '闪电': this.onRenderResult = resolveDataSource(current, "0");break
          case '极光': this.onRenderResult = resolveDataSource(current, "1");break
        }
      }else{
        switch (style){
          case '原图': this.onRenderResult = resolveDataSource(current, "hole");break
          case '森林': this.onRenderResult = resolveDataSource(current, "hole_style.2");break
          case '霓虹': this.onRenderResult = resolveDataSource(current, "hole_style.3");break
          case '闪电': this.onRenderResult = resolveDataSource(current, "hole_style.0");break
          case '极光': this.onRenderResult = resolveDataSource(current, "hole_style.1");break
        }
      }

    },
    uploadfile() {
      this.uploadSrc = [];
      if(this.upload.window_size===this.upload.stride){
        this.$message.error('窗口大小不能等于步长')
        return
      }
      if (
          this.fileList1.length !== this.fileList2.length ||
          this.fileList1.length === 0
      ) {
        this.$message.error("请按照要求上传文件夹或图片！");
      } else {
        let formData1 = buildUploadFormData(this.fileList1, "变化检测", {
          isSlice: this.isSlice,
          scope: "变化检测上传A",
        });
        let formData2 = buildUploadFormData(this.fileList2, "变化检测", {
          isSlice: this.isSlice,
          scope: "变化检测上传B",
        });
        let upload1 = new Promise((resolve, reject) => {
            this.createSrc(formData1).then((res) => {
              this.uploadSrc1 = res.data.data;
              resolve();
            }).catch((rej)=>{})
        });
        let upload2 = new Promise((resolve, reject) => {
          this.createSrc(formData2).then((res) => {
            this.uploadSrc2 = res.data.data;
            resolve();
          }).catch((rej)=>{})
        });
        Promise.all([upload1, upload2])
            .then((val) => {
              this.uploadSrc = this.uploadSrc1.concat(this.uploadSrc2);
              this.uploadSrc = this.uploadSrc.map((item) => {
                return {
                  filename: item.filename.substring(
                      item.filename.indexOf("/") + 1,
                      item.length
                  ),
                  src: item.src,
                };
              });

              this.pairs = this.uploadSrc.map((item) => {
                return item.filename.substring(
                    item.filename.indexOf("/") + 1,
                    item.length
                );
              });

              this.checkPairs(this.pairs);
              if (!this.canUpload) {
                this.$message.error(
                    "检测到命名对应失败的图片，请检查您的文件命名"
                );
              } else {
                this.upload.list = this.getList(this.uploadSrc);
                this.imgUpload(this.upload,'change_detection')
                    .then((res) => {
                      this.$refs.uploadA.clearFiles();
                      this.$refs.uploadB.clearFiles();
                      this.fileList1 = [];
                      this.fileList2 = [];
                      this.$message.success("上传成功");
                      this.isUpload = true;
                      this.resultArr = res?.data?.data?.records || [];
                      this.currentIndex = 0;
                      this.currentQroup = 0;
                      this.getMore();
                      this.setOneWay(this.renderstyle, this.resultArr.length === 0, this.holeShow);
                      if (this.upload.list.length >= 10) {
                        this.$confirm(
                            "上传图片过多，是否压缩?",
                            "提示",
                            {
                              confirmButtonText: "确定",
                              cancelButtonText: "取消",
                              type: "warning",
                            }
                        )
                            .then(() => {
                              this.goCompress(this.upload.list.length);
                            })
                            .catch(() => {});
                      }
                    })
                    .catch((rej) => {});
              }
            })
            .catch((rej) => {});
      }
    },
    getList(beforeData) {
      //算法参考
      //https://blog.csdn.net/weixin_45575273/article/details/108321137?utm_medium=distribute.pc_aggpage_search_result.none-task-blog-2~aggregatepage~first_rank_ecpm_v1~rank_v31_ecpm-3-108321137-null-null.pc_agg_new_rank&utm_term=%E6%95%B0%E7%BB%84%E4%B8%AD%E7%9A%84%E5%AF%B9%E8%B1%A1id%E7%9B%B8%E5%90%8C%E7%9A%84%E5%AF%B9%E8%B1%A1%E7%BB%84%E6%88%90%E4%B8%80%E4%B8%AA%E6%96%B0%E6%95%B0%E7%BB%84&spm=1000.2123.3001.4430
      let tempArr = [];
      let afterData = [];
      for (let i = 0; i < beforeData.length; i++) {
        if (tempArr.indexOf(beforeData[i].filename) === -1) {
          afterData.push(beforeData[i]);
          tempArr.push(beforeData[i].filename);
        } else {
          for (let j = 0; j < afterData.length; j++) {
            Reflect.deleteProperty(afterData[j], "photo_id");
            // Reflect.deleteProperty(afterData[j], "filename");
            afterData[j].first = afterData[j].src;
            afterData[j].second = beforeData[i + j].src;
            // Reflect.deleteProperty(afterData[j], "src");
          }
          break;
        }
      }
      return  afterData;
    },
    goCompress(num) {
      this.$message.info("暂无批量下载");
    },
    getMore() {
      this.resetSliderPosition();
    },
    selectHistogram() {
      if (isRefChecked(this, "histogram")) {
        if (
            this.fileList1.length !== this.fileList2.length ||
            this.fileList1.length === 0
        ) {
          if (this.upload.prehandle === 1) {
            setRefChecked(this, "histogram", false);
            this.upload.prehandle = 0;
          } else {
            setRefChecked(this, "histogram", false);
            this.$message.error("请先按要求上传图片");
          }
        } else {
          this.upload.prehandle = 1;
          this.myhistogram.prehandle = 1;
          this.$message.success("直方图处理");
          if (isRefChecked(this, "sharpen")) {
            setRefChecked(this, "sharpen", false);
          }
          let formData1 = buildUploadFormData(this.fileList1, "变化检测", {
            scope: "变化检测直方图上传A",
          });
          let formData2 = buildUploadFormData(this.fileList2, "变化检测", {
            scope: "变化检测直方图上传B",
          });
          let upload3 = new Promise((resolve, reject) => {
            this.createSrc(formData1).then((res) => {
              this.uploadSrc3 = res.data.data.splice(0, 3);
              this.Img1 = this.uploadSrc3.map((item) => {
                return toBackendAssetUrl(item.src);
              });
              resolve();
            }).catch((rej)=>{})
          });
          let upload4 = new Promise((resolve, reject) => {
            this.createSrc(formData2).then((res) => {
              this.uploadSrc4 = res.data.data.splice(0, 3);
              this.Img3 = this.uploadSrc4.map((item) => {
                return toBackendAssetUrl(item.src);
              });
              resolve();
            }).catch((rej)=>{})
          });
          Promise.all([upload3, upload4]).then((val) => {
            this.histogramSrc = this.uploadSrc3.concat(this.uploadSrc4);
            //https://blog.csdn.net/qq_27342239/article/details/118078113去除“/”前的字符
            this.histogramSrc = this.histogramSrc.map((item) => {
              return {
                filename: item.filename.substring(
                    item.filename.indexOf("/") + 1,
                    item.length
                ),
                src: item.src,
              };
            });

            this.hisPairs = this.histogramSrc.map((item) => {
              return item.filename.substring(
                  item.filename.indexOf("/") + 1,
                  item.length
              );
            });

            this.checkPairs(this.hisPairs);

            if (!this.canUpload) {
              this.$message.error(
                  "检测到命名对应失败的图片，请检查您的文件命名"
              );
              this.Img1 = [];
              this.Img3 = [];
            } else {
              this.myhistogram.list = this.getList(this.histogramSrc);
              this.histogramUpload(this.myhistogram).then((res) => {
                this.Img2 = res.data.data.map((item) => {
                  return toBackendAssetUrl(item);
                });
                this.Img2 = this.Img2.splice(0, 3);
              }).catch((rej)=>{})
            }
          }).catch((rej)=>{})
        }
      } else {
        this.$message.success("取消直方图处理");
        this.upload.prehandle = 0;
        this.myhistogram.prehandle = 0;
      }
    },
    selectSharpen() {
      if (
          this.fileList1.length !== this.fileList2.length ||
          this.fileList1.length === 0
      ) {
        if (this.upload.prehandle === 4) {
          setRefChecked(this, "sharpen", false);
          this.upload.prehandle = 0;
        } else {
          setRefChecked(this, "sharpen", false);
          this.$message.error("请先按要求上传图片");
        }
      } else {
        if (isRefChecked(this, "histogram")) {
          setRefChecked(this, "histogram", false);
        }

        if (!isRefChecked(this, "sharpen")) {
          this.myhistogram.prehandle = 0;
          this.$message.success("取消锐化处理");
          this.upload.prehandle = 0;
        } else {
          this.$message.success("锐化处理");
          this.upload.prehandle = 4;
          this.mysharpen.prehandle = 4;
          let formData1 = buildUploadFormData(this.fileList1, "变化检测", {
            scope: "变化检测锐化上传A",
          });
          let formData2 = buildUploadFormData(this.fileList2, "变化检测", {
            scope: "变化检测锐化上传B",
          });
          let upload1 = new Promise((resolve, reject) => {
            this.createSrc(formData1).then((res) => {
              this.sharpenSrc1 = res.data.data.splice(0, 3);
              this.Img1 = this.sharpenSrc1.map((item) => {
                return toBackendAssetUrl(item.src);
              });
              resolve();
            }).catch((rej)=>{})
          });
          let upload2 = new Promise((resolve, reject) => {
            this.createSrc(formData2).then((res) => {
              this.sharpenSrc2 = res.data.data.splice(0, 3);
              this.Img3 = this.sharpenSrc2.map((item) => {
                return toBackendAssetUrl(item.src);
              });
              resolve();
            }).catch((rej)=>{})
          });
          Promise.all([upload1, upload2]).then((val) => {
            this.sharpenSrc = this.sharpenSrc1.concat(this.sharpenSrc2);
            this.sharpenSrc = this.sharpenSrc.map((item) => {
              return {
                filename: item.filename.substring(
                    item.filename.indexOf("/") + 1,
                    item.length
                ),
                src: item.src,
              };
            });
            this.shaPairs = this.sharpenSrc.map((item) => {
              return item.filename.substring(
                  item.filename.indexOf("/") + 1,
                  item.length
              );
            });

            this.checkPairs(this.hisPairs);

            if (!this.canUpload) {
              this.$message.error(
                  "检测到命名对应失败的图片，请检查您的文件命名"
              );
              this.Img1 = [];
              this.Img3 = [];
            } else {
              this.mysharpen.list =  this.getList(this.sharpenSrc);
              this.histogramUpload(this.mysharpen).then((res) => {
                this.sharpenImg1 = res.data.data.map((item) => {
                  return toBackendAssetUrl(item.first);
                });

                this.sharpenImg2 = res.data.data.map((item) => {
                  return toBackendAssetUrl(item.second);
                });
              }).catch(()=>{})
            }
          }).catch((rej)=>{})
        }
      }
    },

    selectFilter() {
      if (isRefChecked(this, "smooth")) {
        setRefChecked(this, "smooth", false);
      }
      if (!isRefChecked(this, "filter")) {
        this.$message.success("取消高斯滤波处理");
        this.upload.denoise = 0;
      } else {
        this.$message.success("高斯滤波处理");
        this.upload.denoise = 5;
      }
    },
    selectSmooth() {
      if (isRefChecked(this, "filter")) {
        setRefChecked(this, "filter", false);
      }
      if (!isRefChecked(this, "smooth")) {
        this.$message.success("取消平滑处理");
        this.upload.denoise = 0;
      } else {
        this.$message.success("平滑处理");
        this.upload.denoise = 3;
      }
    },
    toggleHoleStatus() {
      this.resultArr[this.currentIndex].is_hole = !this.resultArr[this.currentIndex].is_hole
      this.holeShow = !this.holeShow
      this.resetSliderPosition();
      this.setOneWay(this.renderstyle,this.resultArr.length===0,this.holeShow)
    },
    uploadFirst() {
      this.checkFile1(...this.$refs.refFileA.files);
      if (this.canUpload) {
        this.fileList1.push(...this.$refs.refFileA.files);
      } else {
        setTimeout(() => {
          this.$message.error("检测到您上传的文件夹内存在不符合规范的图片类型");
        }, 1000);
      }
    },
    uploadSecond() {
      this.checkFile2(...this.$refs.refFileB.files);
      if (this.canUpload) {
        this.fileList2.push(...this.$refs.refFileB.files);
      } else {
        setTimeout(() => {
          this.$message.error("检测到您上传的文件夹内存在不符合规范的图片类型");
        }, 1000);
      }
    },
    file1Click() {
      document.querySelector("#upload-fileA").click();
    },
    file2Click() {
      document.querySelector("#upload-fileB").click();
    },
    checkFile1(file) {
      // 支持 TIFF 格式用于遥感影像
      const whiteList = ["jpg", "jpeg", "png", "JPG", "JPEG", "tif", "tiff", "TIF", "TIFF"];
      const fileSuffix = file.name.substring(file.name.lastIndexOf(".") + 1);
      if (whiteList.indexOf(fileSuffix) === -1) {
        this.$message.error("只允许上传jpg, jpeg, png, tif, tiff格式,请重新上传");
        this.fileList1 = [];
        this.canUpload = false;
      } else {
        this.canUpload = true;
      }
    },
    checkFile2(file) {
      // 支持 TIFF 格式用于遥感影像
      const whiteList = ["jpg", "jpeg", "png", "JPG", "JPEG", "tif", "tiff", "TIF", "TIFF"];
      const fileSuffix = file.name.substring(file.name.lastIndexOf(".") + 1);
      if (whiteList.indexOf(fileSuffix) === -1) {
        this.$message.error("只允许上传jpg, jpeg, png, tif, tiff格式,请重新上传");
        this.fileList2 = [];
        this.canUpload = false;
      } else {
        this.canUpload = true;
      }
    },
    checkPairs(list) {
      let s = list.join(",") + ",";
      let j = 0;
      for (let i = 0; i < list.length; i++) {
        if (s.replace(list[i] + ",", "").indexOf(list[i] + ",") > -1) {
        } else {
          j++;
          break;
        }
      }
      this.canUpload = j === 0;
    },
    changePreMode() {
      if (this.preMode === 1) {
        this.preMode = 2;
      } else {
        this.preMode = 1;
      }
      this.resetSliderPosition();
    },
    resetSliderPosition() {
      this.sliderPosition = 50;
    },
    updateSliderPosition(clientX) {
      const slider = this.$refs.resultSlider;
      if (!slider) return;

      const { left, width } = slider.getBoundingClientRect();
      if (!width) return;

      const position = ((clientX - left) / width) * 100;
      this.sliderPosition = Math.min(100, Math.max(0, Number(position.toFixed(4))));
    },
    startSliderDrag(event) {
      if (this.preMode !== 1) return;
      this.isDragging = true;
      this.updateSliderPosition(event.clientX);
      this.removeSliderListeners();
      window.addEventListener("pointermove", this.onSliderDrag);
      window.addEventListener("pointerup", this.stopSliderDrag);
      window.addEventListener("pointercancel", this.stopSliderDrag);
    },
    onSliderDrag(event) {
      if (!this.isDragging) return;
      this.updateSliderPosition(event.clientX);
    },
    stopSliderDrag() {
      this.isDragging = false;
      this.removeSliderListeners();
    },
    removeSliderListeners() {
      window.removeEventListener("pointermove", this.onSliderDrag);
      window.removeEventListener("pointerup", this.stopSliderDrag);
      window.removeEventListener("pointercancel", this.stopSliderDrag);
    },
    vanishDrag(){
      this.dragShow = false
    },
    hideMask(){
      this.isHiddenMask = !this.isHiddenMask
      this.resetSliderPosition();
    },
    showDetailedAnalysis() {
      if (!this.resultArr[this.currentIndex]) return;
      
      const data = this.holeShow 
          ? this.resultArr[this.currentIndex].data.size_distribution_hole 
          : this.resultArr[this.currentIndex].data.size_distribution;

      if (!data) {
          this.$message.warning("增强的统计数据尚不可用，请确保后端已更新。");
          return;
      }

      this.sizeDistributionOption = {
        title: {
          text: '变化区域大小分布',
          left: 'center'
        },
        tooltip: {
          trigger: 'item',
          formatter: '{a} <br/>{b} : {c} ({d}%)'
        },
        legend: {
          orient: 'vertical',
          left: 'left',
          data: ['小型 (<100px)', '中型 (100-500px)', '大型 (>500px)']
        },
        series: [
          {
            name: '区域大小',
            type: 'pie',
            radius: ['40%', '70%'],
            avoidLabelOverlap: false,
            itemStyle: {
              borderRadius: 10,
              borderColor: '#fff',
              borderWidth: 2
            },
            label: {
              show: false,
              position: 'center'
            },
            emphasis: {
              label: {
                show: true,
                fontSize: 20,
                fontWeight: 'bold'
              }
            },
            labelLine: {
              show: false
            },
            data: [
              { value: data.small, name: '小型 (<100px)' },
              { value: data.medium, name: '中型 (100-500px)' },
              { value: data.large, name: '大型 (>500px)' }
            ]
          }
        ]
      };
      
      
      // Top 10 Changes Chart
      const topChanges = this.holeShow 
          ? this.resultArr[this.currentIndex].data.top_changes_hole 
          : this.resultArr[this.currentIndex].data.top_changes;

      if (topChanges && topChanges.length > 0) {
        this.topChangesOption = {
          tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' }
          },
          grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
          },
          xAxis: {
            type: 'category',
            data: topChanges.map((_, i) => `Rank ${i + 1}`),
            axisTick: { alignWithLabel: true }
          },
          yAxis: {
            type: 'value',
            name: '像素面积'
          },
          series: [
            {
              name: '面积',
              type: 'bar',
              barWidth: '60%',
              data: topChanges,
              itemStyle: {
                 color: '#3398DB'
              }
            }
          ]
        };
      } else {
        this.topChangesOption = {};
      }

      this.detailedAnalysisVisible = true;
    },
    downloadStats() {
       if (!this.resultArr[this.currentIndex]) return;
       const data = this.resultArr[this.currentIndex].data;
       const content = JSON.stringify(data, null, 2);
       const blob = new Blob([content], { type: "application/json" });
       const link = document.createElement("a");
       link.href = URL.createObjectURL(blob);
       link.download = `analysis_stats_${this.resultArr[this.currentIndex].id}.json`;
       link.click();
       URL.revokeObjectURL(link.href);
    }
  },
};
</script>

<style scoped lang="less">
* {
  font-family: var(--theme-default-fontfamily);
}
.list {
  text-align: center;
  cursor: pointer;
  width: auto;
  height: 20px;
  background-color: var(--theme-tag-bg);
  position: relative;
  margin-bottom: 10px;
}
.list-number:hover::after {
  width: 100%;
  background: var(--theme--color);
}
.list-number::after {
  position: absolute;
  content: "";
  width: 0;
  height: 100%;
  top: 0;
  left: 0;
  border-radius: 2px 2px 0 0;
  transition: 0.4s;
  z-index: -1;
}
.list:hover * {
  color: var(--text-inverse) !important;
}
.list-number {
  z-index: 1;
  overflow: hidden;
  margin: 0 auto;
  width: auto;
  height: 20px;
  position: relative !important;
  border-radius: 2px !important;
}
.swiper-img {
  display: flex;
  flex-wrap: nowrap;
  flex-direction: row;
  width: 100%;
  margin-top: 30px;
  .img-box {
    flex: 1;
    height: 100%;
    overflow: hidden;
    opacity: 0.7;
    transition: all 0.6s;
    margin-right: 10px;
    justify-content: space-between;
  }
}
#sub-title{
  font-size: 25px;
}
#sub-title:hover:after {
  left: 0;
  right: 0;
  width: 220px;
}
.render-box {
  .render-img {
    // width: 100%;
    max-height: 600px;
    overflow: hidden;

  }
  .render-style {
    height: auto;
  }
}
.chart {
  height: 300px;
}
.cl-checkbox {
  display: block;
  height: auto;
  text-align: center;
}

.style-title {
  text-align: center;
  font-size: 22px;
  font-family: var(--theme-display-fontfamily);
  font-weight: 700;
  margin-bottom: 20px;
  color: var(--theme-heading-color);
}
.img-index {
  text-align: center;
  height: 428px;
  align-content: center;
  line-height: 428px;
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
}
.clear-queue {
  left: 0;
  position: absolute;
  top: 20%;
  z-index: 100;
}
.render-border {
  border: var(--theme--color) 0.5rem solid;
}
.mask-img{
  position: absolute;
  top: 0;
  z-index:2
}
.render-img-box #image-slider {
  position: relative;
  width: min(100%, 650px);
  aspect-ratio: 1 / 1;
  overflow: hidden;
  border-radius: 1em;
  cursor: col-resize;
  display: inline-block;
  touch-action: none;
  background: var(--theme-card-bg);
}

.render-img-box #image-slider > img,
.render-img-box #image-slider .img-wrapper img,
.render-img-box #image-slider .mask-img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  pointer-events: none;
  user-select: none;
}

.render-img-box #image-slider .mask-layer {
  position: absolute;
  inset: 0;
  z-index: 2;
  pointer-events: none;
}

.render-img-box #image-slider .img-wrapper {
  position: absolute;
  inset: 0;
  z-index: 1;
}

.render-img-box #image-slider .img-wrapper img {
  position: absolute;
  top: 0;
  left: 0;
  max-width: 100%;
}

.render-img-box #image-slider .handle {
  border: 0 solid red;
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: var(--image-slider-handle-width);
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  user-select: none;
  z-index: 3;
  pointer-events: none;
}

.render-img-box #image-slider .handle-circle {
  color: white;
  border: 2px solid white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: space-evenly;
}

.render-img-box #image-slider .handle-line {
  width: 2px;
  flex-grow: 1;
  background: white;
}

@media (max-width: 768px) {
  :root {
    --image-slider-width: 90vw;
  }
}
.el-row{
  position: inherit;
}
.style-words {
  line-height: 30px;
  height: 30px;
  transition: all 0.4s;
  margin-bottom: 10px;
  cursor: pointer;
  font-size: 18px;
}
.style-words:hover {
  color: white;
}
.normal:hover {
  background-color: var(--theme--color);
}
.woods:hover {
  background-image: linear-gradient(#9be15d, #00e3ae 100%);
}
.neon:hover {
  background-image: linear-gradient(135deg, #f761a1 15%, #8c1bab 100%);
}
.flash:hover {
  background-image: linear-gradient(135deg, #c2ffd8 10%, #465efb 100%);
}
.aurora:hover {
  background-image: linear-gradient(#011142, #00bbc9 100%);
}
.active-normal {
  background-color: var(--theme-active-color);
}
.active-woods {
  background-image: linear-gradient(#9be15d, #00e3ae 100%);
}
.active-neon {
  background-image: linear-gradient(135deg, #f761a1 15%, #8c1bab 100%);
}
.active-flash {
  background-image: linear-gradient(135deg, #c2ffd8 10%, #465efb 100%);
}
.active-aurora {
  background-image: linear-gradient(#011142, #00bbc9 100%);
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
.folder-row{
  display: flex;
  flex-direction: row;
  justify-content: space-evenly;
}
.render-mode-bar {
  display: flex;
  align-items: center;
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
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.render-mode-state__text {
  font-size: 12px;
  color: var(--text-secondary);
}

.upload-box{
  display: flex;
  flex-direction:row;
  justify-content: space-evenly;
  flex-wrap: wrap;
}
.render-img-box{
  display: flex;
  justify-content: space-evenly;
  flex-wrap: wrap;
  flex-direction: row;
  .display-modeB{
    display: flex;
    flex-wrap: wrap ;
    flex-direction: row;
    justify-content: center;
    width: 80%;
    .modeB-item{
      margin: 10px;
      width:31%;
    }
  }
  .render-select-box{
    width: 200px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    position: relative;
  }
}

.render-select{
  display: flex;
  flex-direction: column;
}
.drag-control{
  position: absolute;
  right: 20px;
  top: 400px;
  width: 33px;
  height: 20px;
  text-align: center;
  padding: 5px;
  color: var(--theme-active-color);
  background: var(--theme-tag-bg);
  border-radius: 0.2rem;
  .iconfont {
    display: block;
    &:hover{
      background-color: var(--bg-hover);
    }
  }
}
.slider-box{
  display: flex;
  justify-content: center;
  align-items: center;
  flex-direction: column;
  .slider-item{
    margin: 10px;
    width: 450px;
  }
}

</style>
