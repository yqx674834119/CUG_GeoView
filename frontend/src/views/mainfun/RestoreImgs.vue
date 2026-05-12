<template>
  <div>
    <Tabinfor>
      <template #left>
        <div
          id="sub-title"
        >
          影像超分重建<i
            class="iconfont icon-dianji"
          />
        </div>
      </template>
    </Tabinfor>
    <el-divider />
    <p>
      请上传包含<span class="go-bold">图片的文件夹</span><i class="iconfont icon-wenjianjia" />或者<span
        class="go-bold"
      >图片</span><i class="iconfont icon-tupiantianjia" />，<i class="iconfont icon-zidingyi" />
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
              支持上传 PNG/JPG/TIFF 格式遥感影像，请在下方上传文件夹
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
              @click="upload('影像超分重建','image_restoration')"
            >
              开始处理
            </el-button>
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
        <p v-if="imgArr.length">
          <i
            class="iconfont icon-dabaoxiazai"
            @click="goCompress('影像超分重建')"
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
    <ImgShow :img-arr="imgArr" />
  </div>
</template>
<script>
import {createSrc,imgUpload,getCustomModel} from "@/api/upload";
import {getUploadImg, goCompress, upload} from "@/utils/getUploadImg";
import Tabinfor from "@/components/Tabinfor";
import MyVueCropper from "@/components/MyVueCropper";
import ImgShow from "@/components/ImgShow";

export default {
  name: "Restoreimgs",
  components: {
    Tabinfor,
    MyVueCropper,
    ImgShow,
  },
  beforeRouteEnter(to, from, next) {
    next((vm) => {
      document.querySelector(".el-main").scrollTop = 0;
    });
  },
  data() {
    return {
      canUpload:true,
      fileimg: "",
      file: {},
      isNotCut: true,
      cutVisible: false,
      funtype: "影像超分重建",
      scrollTop: "",
      fit: "fill",
      fileList: [],
      uploadSrc: {
        list: [],
        model_path:''
      },
      modelPathArr:[],
      imgArr:[],
      isSlice: false
    };
  },
  watch:{
    uploadSrc:{
      handler(newVal,oldVal){
        this.uploadSrc = newVal
      },
      deep:true,
      immediate:true
    }
  },
  created() {
    this.getUploadImg("影像超分重建")
    this.getCustomModel('image_restoration').then((res)=>{
      // Show all available models including 2x and 4x
      this.modelPathArr = res.data.data;
      this.uploadSrc.model_path = this.modelPathArr[0]?.model_path
    }).catch((rej)=>{})
  },
  methods: {
    imgUpload,
    getCustomModel,
    createSrc,
    getUploadImg,
    upload,
    goCompress,
    clearQueue() {
      this.fileList = [];
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
      this.getUploadImg("影像超分重建");
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
}
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
  position: relative;
  left: -20px;
  top: 14%;
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
.custom-pic{
  width: 256px;
  height: 256px;
}

.restore-img-box #image-slider {
  position: relative;
  width: min(100%, 580px);
  aspect-ratio: 1 / 1;
  overflow: hidden;
  border-radius: 1em;
  cursor: col-resize;
  display: inline-block;
  touch-action: none;
  background: var(--theme-card-bg);
}

.restore-img-box #image-slider > img,
.restore-img-box #image-slider .img-wrapper img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  pointer-events: none;
  user-select: none;
}

.restore-img-box #image-slider .img-wrapper {
  position: absolute;
  top: 0;
  right: 0;
  height: 100%;
  width: 50%;
  overflow: hidden;
  z-index: 1;
}

.restore-img-box #image-slider .img-wrapper img {
  position: absolute;
  top: 0;
  right: 0;
  max-width: none;
}

.restore-img-box #image-slider .handle {
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
  z-index: 2;
  pointer-events: none;
}

.restore-img-box #image-slider .handle-circle {

  color: white;
  border: 2px solid white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: space-evenly;
}

.restore-img-box #image-slider .handle-line {
  width: 2px;
  flex-grow: 1;
  background: white;
}

//.el-row{
//  position: inherit;
//  //获取滑窗容器的左偏移量
//}
.restore-img{
  display: flex;
  flex-direction: row;
  justify-content: space-around;
  flex-wrap: wrap;
}
.style-title {
  text-align: center;
  font-size: 22px;
  font-family: var(--theme-display-fontfamily);
  font-weight: 700;
  margin-bottom: 20px;
  color: var(--theme-heading-color);
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
  background: var(--theme-active-color);
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
}
.list-number {
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
.render-border {
  border: var(--theme--color) 0.5rem solid;
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
.restore-img-box{
  display: flex;
  justify-content: space-evenly;
  flex-wrap: wrap;
  flex-direction: row;
  .choose-restore{
    width: 250px;
    display: flex;
    flex-wrap: wrap;
    flex-direction: column;
    justify-content:center;
  }
}
</style>
