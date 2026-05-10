<template>
  <div>
    <Tabinfor>
      <template #left>
        <div id="sub-title">
          场景分类<i class="iconfont icon-dianji" />
        </div>
      </template>
    </Tabinfor>
    <el-divider />
    <p>
      请上传包含<span class="go-bold">图片的文件夹</span><i class="iconfont icon-wenjianjia" />或者<span class="go-bold">图片</span><i
        class="iconfont icon-tupiantianjia" />，<i class="iconfont icon-zidingyi" />
    </p>
    <el-row type="flex" justify="center">
      <el-col :span="24">
        <el-card class="upload-panel upload-panel--single">
          <div v-if="fileList.length" class="clear-queue">
            <el-button type="primary" class="btn-animate2 btn-animate__surround" @click="clearQueue">
              清空图片
            </el-button>
          </div>
          <el-upload ref="upload" v-model:file-list="fileList" class="upload-card" drag action="#" multiple
            :auto-upload="false" @change="beforeUpload(fileList[fileList.length - 1].raw)">
            <i class="iconfont icon-yunduanshangchuan" />
            <div class="el-upload__text">
              将文件拖到此处，或<em>点击上传</em>
            </div>
            <div class="el-upload__tip">
              只能上传一张或多张图片，请在下方上传文件夹
            </div>
          </el-upload>
          <el-row justify="center" class="upload-action-row">
            <input id="folder" ref="uploadFile" type="file" webkitdirectory directory multiple @change="uploadMore()">
            <i class="iconfont icon-wenjianshangchuan upload-folder-action" @click="fileClick">上传文件夹</i>
          </el-row>

          <el-row justify="center" class="upload-helper-row">
            <p>
              <label class="prehandle-label container">
                <input ref="cut" type="checkbox" @change="select()">
                <span class="checkmark" />
                <span class="go-bold label-words">上传时编辑图片</span><i class="iconfont icon-crop-full" />
              </label>
            </p>
          </el-row>
          <div class="upload-options-row" style="margin-bottom: 20px;">
            <el-checkbox v-model="isSlice" label="开启大图切分" border />
          </div>
          <el-row justify="center">
            <div class="custom-model">
              可选训练模型：
              <span v-if="modelPathArr.length === 0">未检测到模型文件，请查看上传目录是否有误</span>
              <el-radio v-for="(item, index) in modelPathArr" :key="index" v-model="uploadSrc.model_path"
                class="choose-item" :label="item.model_path">
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
            <el-button type="primary" class="btn-animate btn-animate__shiny" @click="upload('场景分类', 'classification')">
              开始处理
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
    <Tabinfor>
      <template #left>
        <div id="sub-title">
          结果图预览<i class="iconfont icon-dianji" />
        </div>
      </template>
    </Tabinfor>
    <el-divider />
    <Tabinfor>
      <template #left>
        <p>
          <span class="go-bold">点击图片</span>即可预览
          <i class="iconfont icon-duigou" />
          <span><span class="go-bold">滑轮滚动</span>即可放大缩小</span>
        </p>
      </template>

      <template #right>
        <span class="go-bold"><i class="iconfont icon-shuaxin" style="padding-right:55px" @click="getMore"><span
              class="hidden-sm-and-down">点击刷新</span></i></span>
      </template>
    </Tabinfor>
    <el-dialog v-model="cutVisible" :modal="false" title="编辑" width="75%" top="0">
      <MyVueCropper :fileimg="fileimg" :funtype="funtype" :file="file" :child_prehandle="uploadSrc.prehandle"
        :child_denoise="uploadSrc.denoise" :child-model-path="uploadSrc.model_path" @cut-changed="notvisible"
        @child-refresh="getMore" />
    </el-dialog>
    <ImgShow :img-arr="imgArr" />
  </div>
</template>
<script>
import { createSrc, imgUpload, getCustomModel } from "@/api/upload";
import { historyGetPage } from "@/api/history";
import { getUploadImg, upload } from "@/utils/getUploadImg";
import ImgShow from '@/components/ImgShow'
import Tabinfor from "@/components/Tabinfor";
import MyVueCropper from "@/components/MyVueCropper";

export default {
  name: "Classification",
  components: {
    Tabinfor,
    MyVueCropper,
    ImgShow
  },
  beforeRouteEnter(to, from, next) {
    next((vm) => {
      document.querySelector(".el-main").scrollTop = 0;
    });
  },
  data() {
    return {
      isUpload: true,
      canUpload: true,
      before: [],
      fileimg: "",
      file: {},
      isNotCut: true,
      cutVisible: false,
      funtype: "场景分类",
      scrollTop: "",
      fit: "fill",
      fileList: [],
      uploadSrc: {
        list: [],
        model_path: ''
      },
      modelPathArr: [],
      imgArr: [],
      isSlice: false,
    };
  },
  watch: {
    uploadSrc: {
      handler(newVal, oldVal) {
        this.uploadSrc = newVal
      },
      deep: true,
      immediate: true
    }
  },
  created() {
    this.getUploadImg("场景分类");
    this.getCustomModel('classification').then((res) => {
      this.modelPathArr = res.data.data
      this.uploadSrc.model_path = this.modelPathArr[0]?.model_path
    }).catch((rej) => { })
  },
  methods: {
    imgUpload,
    getCustomModel,
    historyGetPage,
    createSrc,
    getUploadImg,
    upload,
    checkUpload() {
      this.isUpload = this.beforeImg.length !== 0;
    },
    clearQueue() {
      this.fileList = [];
      this.$message.success("清除成功");
    },
    notvisible() {
      this.cutVisible = false;
      this.fileList = [];
    },
    getMore() {
      this.getUploadImg("场景分类");
    },
    uploadMore() {
      this.beforeUpload(...this.$refs.uploadFile.files)
      if (this.canUpload) {
        this.fileList.push(...this.$refs.uploadFile.files);
      } else {
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
      const whiteList = ['jpg', 'jpeg', 'png', 'JPG', 'JPEG', 'tif', 'tiff', 'TIF', 'TIFF']
      if (whiteList.indexOf(fileSuffix) === -1) {
        this.$message.error("只允许上传jpg, jpeg, png, tif, tiff格式,请重新上传");
        this.fileList = []
        this.canUpload = false
        this.cutVisible = false;
      }
      else {
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

#sub-title {
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

.img-index {
  align-items: center;
  display: flex;
  flex-direction: column;
  justify-content: space-evenly;
  flex-wrap: wrap;
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
  width: 256px;
  height: 30px;
  font-weight: 500;
  color: var(--text-secondary);
}

.custom-pic {
  width: 256px;
  height: 256px;
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
</style>
