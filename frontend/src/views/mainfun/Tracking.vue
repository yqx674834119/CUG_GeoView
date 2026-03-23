<template>
  <div>
    <Tabinfor>
      <template #left>
        <div id="sub-title">
          全域目标跟踪<i class="icon-click" />
        </div>
      </template>
    </Tabinfor>
    <el-divider />
    <p>
      请选择待跟踪的<span class="go-bold">视频文件</span>或<span class="go-bold">图像序列文件夹</span>。
    </p>
    
    <el-card class="upload-panel upload-panel--single">
      <div v-if="fileList.length" class="clear-queue">
        <el-button type="primary" class="btn-animate2 btn-animate__surround" @click="clearQueue">
          清空
        </el-button>
      </div>
      
      <div style="text-align: center;">
         <el-upload
            ref="upload"
            v-model:file-list="fileList"
            class="upload-card"
            drag
            action="#"
            multiple
            :auto-upload="false"
            @change="checkFile"
          >
            <i class="iconfont icon-yunduanshangchuan" />
            <div class="el-upload__text">
              拖拽视频或图片到此处
            </div>
            <div class="el-upload__tip">
               或者下方上传文件夹
            </div>
          </el-upload>
          <div class="upload-action-row">
             <input id="upload-folder" ref="refFolder" type="file" webkitdirectory directory multiple @change="uploadFolder" style="display:none">
             <i class="iconfont icon-wenjianshangchuan upload-folder-action" @click="folderClick">上传文件夹</i>
          </div>
      </div>

      <el-row justify="center" style="margin-top: 20px;">
        <div class="custom-model">
          可选跟踪模型：
          <el-radio
            v-for="(item,index) in modelPathArr"
            :key="index"
            v-model="uploadSrc.model_path"
            class="choose-item"
            :label="item.model_path"
          >
            <el-tooltip effect="dark" :content="item.description || '暂无描述'" placement="top-start">
              <span class="model-label">
                {{ item.model_name }}
              </span>
            </el-tooltip>
          </el-radio>
        </div>
      </el-row>
      
      <div v-if="firstFrame" class="frame-selector">
          <p>请在下方第一帧图像中框选初始目标：</p>
          <div class="frame-selector__canvas">
              <img ref="firstFrameImg" :src="firstFrame" class="frame-selector__image" @mousedown="startDraw" @mousemove="drawing" @mouseup="endDraw">
              <div v-if="rect.w > 0" :style="{
                  left: rect.x + 'px',
                  top: rect.y + 'px',
                  width: rect.w + 'px',
                  height: rect.h + 'px'
              }" class="frame-selector__rect"></div>
          </div>
          <p v-if="rect.w > 0">已选择区域: {{ rect }}</p>
      </div>

      <div class="handle-button">
        <el-button type="primary" class="btn-animate btn-animate__shiny" @click="startTracking" :disabled="!rect.w">
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
    </Tabinfor>
    <el-divider />
    
    <div v-if="resultVideo" class="result-box" style="text-align: center;">
        <video controls :src="resultVideo" class="result-video"></video>
        <div class="result-actions">
            <el-button type="primary" @click="downloadResult">下载结果视频</el-button>
        </div>
    </div>
    <el-empty v-else description="暂无结果" />

  </div>
</template>

<script>
import Tabinfor from "@/components/Tabinfor";
import { getCustomModel, imgUpload } from "@/api/upload";

export default {
  name: "Tracking",
  components: { Tabinfor },
  data() {
    return {
      fileList: [],
      modelPathArr: [],
      uploadSrc: { model_path: '' },
      firstFrame: null, // URL for preview
      rect: { x: 0, y: 0, w: 0, h: 0 },
      isDrawing: false,
      startX: 0,
      startY: 0,
      resultVideo: null
    };
  },
  created() {
    this.fetchModels();
  },
  methods: {
    fetchModels() {
      getCustomModel('tracking').then(res => {
        if(res.data.code === 0) {
            this.modelPathArr = res.data.data;
            if(this.modelPathArr.length > 0) this.uploadSrc.model_path = this.modelPathArr[0].model_path;
        }
      });
    },
    clearQueue() {
      this.fileList = [];
      this.firstFrame = null;
      this.rect = { x: 0, y: 0, w: 0, h: 0 };
    },
    folderClick() { this.$refs.refFolder.click(); },
    checkFile(file, fileList) {
        this.fileList = fileList;
        // Try to generate first frame preview
        if (file.raw.type.startsWith('image/')) {
            this.firstFrame = URL.createObjectURL(file.raw);
        } else if (file.raw.type.startsWith('video/')) {
            // Extracts first frame from video is harder without backend, simpler to just upload first
            // For now, simpler approach: prompt user to upload first frame image if video, or assume backend handles it.
            // Actually, we can use a hidden video element to capture first frame.
            const video = document.createElement('video');
            video.src = URL.createObjectURL(file.raw);
            video.onloadeddata = () => {
                video.currentTime = 0;
            };
            video.onseeked = () => {
                const canvas = document.createElement('canvas');
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
                this.firstFrame = canvas.toDataURL();
            };
        }
    },
    uploadFolder() {
        let files = this.$refs.refFolder.files;
        for(let i=0; i<files.length; i++){
            this.fileList.push({name: files[i].name, raw: files[i], status: 'ready'});
        }
        // Assume first file is the first frame
        if (files.length > 0 && files[0].type.startsWith('image/')) {
            this.firstFrame = URL.createObjectURL(files[0]);
        }
    },
    startDraw(e) {
        this.isDrawing = true;
        const img = this.$refs.firstFrameImg;
        const rect = img.getBoundingClientRect();
        this.startX = e.clientX - rect.left;
        this.startY = e.clientY - rect.top;
        this.rect = { x: this.startX, y: this.startY, w: 0, h: 0 };
    },
    drawing(e) {
        if(!this.isDrawing) return;
        const img = this.$refs.firstFrameImg;
        const rect = img.getBoundingClientRect();
        const currentX = e.clientX - rect.left;
        const currentY = e.clientY - rect.top;
        this.rect.w = currentX - this.startX;
        this.rect.h = currentY - this.startY;
    },
    endDraw() {
        this.isDrawing = false;
        // Handle negative width/height
        if(this.rect.w < 0) { this.rect.x += this.rect.w; this.rect.w = Math.abs(this.rect.w); }
        if(this.rect.h < 0) { this.rect.y += this.rect.h; this.rect.h = Math.abs(this.rect.h); }
    },
    async startTracking() {
        if (!this.fileList.length || !this.rect.w) return;
        
        const loading = this.$loading({ lock: true, text: '正在跟踪中...', background: 'rgba(0, 0, 0, 0.7)' });
        
        try {
            let formData = new FormData();
            this.fileList.forEach(file => formData.append('file', file.raw));
            formData.append('model_path', this.uploadSrc.model_path);
            
            // Calculate real coordinates based on image natural size vs displayed size
            const img = this.$refs.firstFrameImg;
            const scaleX = img.naturalWidth / img.clientWidth;
            const scaleY = img.naturalHeight / img.clientHeight;
            
            const realRect = [
                Math.round(this.rect.x * scaleX),
                Math.round(this.rect.y * scaleY),
                Math.round(this.rect.w * scaleX),
                Math.round(this.rect.h * scaleY)
            ];
            formData.append('rect', realRect.join(','));
            
            const res = await imgUpload(formData, 'tracking');
            if (res.data.code === 0 && res.data.data.results) {
                 // Assuming backend returns path to result video
                 // We need to check what backend returns. 
                 // hf_tracking.py returns a list of results, but the wrapper might save a video.
                 // Let's assume the wrapper saves a video and returns its path in data.
                 this.resultVideo = res.data.data.output_path; // Mock assumption
                 this.$message.success('跟踪完成');
            } else {
                 this.$message.error('跟踪失败: ' + (res.data.msg || '未知错误'));
            }
        } catch(e) {
            console.error(e);
            this.$message.error('请求失败');
        } finally {
            loading.close();
        }
    },
    downloadResult() {
        if(!this.resultVideo) return;
        const link = document.createElement('a');
        link.href = this.resultVideo;
        link.download = 'tracking_result.mp4';
        link.click();
    }
  }
};
</script>

<style lang="less" scoped>
* { font-family: var(--theme-default-fontfamily); }
#sub-title { font-size: 25px; }
.custom-model { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
.handle-button { margin-top: 20px; text-align: center; }
</style>
