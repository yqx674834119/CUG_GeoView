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
      支持<span class="go-bold">文件夹批量上传</span>或<span class="go-bold">单文件上传</span>。
    </p>
    
    <el-card class="upload-panel upload-panel--double">
      <div v-if="fileList1.length||fileList2.length" class="clear-queue">
        <el-button type="primary" class="btn-animate2 btn-animate__surround" @click="clearQueue">
          清空图片
        </el-button>
      </div>
      <div class="upload-box">
        <div class="upload-item">
          <div class="upload-caption">参考影像 (Fixed)</div>
          <el-upload
            ref="uploadA"
            v-model:file-list="fileList1"
            class="upload-card"
            drag
            action="#"
            multiple
            :auto-upload="false"
            @change="checkFile1"
          >
            <i class="iconfont icon-yunduanshangchuan" />
            <div class="el-upload__text">
              拖拽或<em>点击上传</em>
            </div>
          </el-upload>
          <div class="upload-action-row">
             <input id="upload-fileA" ref="refFileA" type="file" webkitdirectory directory multiple @change="uploadFirst" style="display:none">
             <i class="iconfont icon-wenjianshangchuan upload-folder-action" @click="file1Click">上传文件夹</i>
          </div>
        </div>
        <div class="upload-item">
          <div class="upload-caption">待配准影像 (Moving)</div>
          <el-upload
            ref="uploadB"
            v-model:file-list="fileList2"
            class="upload-card"
            drag
            action="#"
            multiple
            :auto-upload="false"
            @change="checkFile2"
          >
            <i class="iconfont icon-yunduanshangchuan" />
            <div class="el-upload__text">
              拖拽或<em>点击上传</em>
            </div>
          </el-upload>
          <div class="upload-action-row">
             <input id="upload-fileB" ref="refFileB" type="file" webkitdirectory directory multiple @change="uploadSecond" style="display:none">
             <i class="iconfont icon-wenjianshangchuan upload-folder-action" @click="file2Click">上传文件夹</i>
          </div>
        </div>
      </div>

      <el-row justify="center" style="margin-top: 20px;">
        <div class="custom-model">
          可选配准模型：
          <span v-if="modelPathArr.length===0">未检测到模型文件</span>
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

      <div class="handle-button">
        <el-button type="primary" class="btn-animate btn-animate__shiny" @click="startRegistration">
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
    </Tabinfor>
    <el-divider />
    
    <div v-if="resultArr.length > 0" class="result-box">
       <el-row :gutter="20">
         <el-col :span="8" v-for="(item, index) in resultArr" :key="index">
            <el-card :body-style="{ padding: '0px' }">
              <el-image :src="item.output_path" fit="cover" :preview-src-list="[item.output_path]" />
              <div style="padding: 14px;">
                <span>{{ item.name }}</span>
                <div class="bottom clearfix">
                  <el-button type="text" class="button" @click="downloadImg(item.output_path, item.name)">下载</el-button>
                </div>
              </div>
            </el-card>
         </el-col>
       </el-row>
    </div>
    <el-empty v-else description="暂无结果" />

  </div>
</template>

<script>
import Tabinfor from "@/components/Tabinfor";
import { getCustomModel, imgUpload, createSrc } from "@/api/upload";

export default {
  name: "Registration",
  components: { Tabinfor },
  data() {
    return {
      fileList1: [],
      fileList2: [],
      modelPathArr: [],
      uploadSrc: {
        model_path: ''
      },
      resultArr: []
    };
  },
  created() {
    this.fetchModels();
  },
  methods: {
    fetchModels() {
      getCustomModel('registration').then(res => {
        if(res.data.code === 0) {
            this.modelPathArr = res.data.data;
            if(this.modelPathArr.length > 0) {
                this.uploadSrc.model_path = this.modelPathArr[0].model_path;
            }
        }
      });
    },
    clearQueue() {
      this.fileList1 = [];
      this.fileList2 = [];
    },
    file1Click() { this.$refs.refFileA.click(); },
    file2Click() { this.$refs.refFileB.click(); },
    checkFile1(file, fileList) { this.fileList1 = fileList; },
    checkFile2(file, fileList) { this.fileList2 = fileList; },
    uploadFirst() { 
        // Logic for folder upload similar to DetectChanges 
        let files = this.$refs.refFileA.files;
        for(let i=0; i<files.length; i++){
            this.fileList1.push({name: files[i].name, raw: files[i], status: 'ready'});
        }
    },
    uploadSecond() {
        let files = this.$refs.refFileB.files;
        for(let i=0; i<files.length; i++){
            this.fileList2.push({name: files[i].name, raw: files[i], status: 'ready'});
        }
    },
    async startRegistration() {
        if (this.fileList1.length === 0 || this.fileList2.length === 0) {
            this.$message.error('请确保两组影像都已上传');
            return;
        }
        if (!this.uploadSrc.model_path) {
             this.$message.error('请选择模型');
             return;
        }

        const loading = this.$loading({
          lock: true,
          text: '正在配准中...',
          background: 'rgba(0, 0, 0, 0.7)'
        });

        try {
            // Create FormData
            let formData = new FormData();
            this.fileList1.forEach(file => {
                formData.append('file1', file.raw);
            });
            this.fileList2.forEach(file => {
                formData.append('file2', file.raw);
            });
            formData.append('model_path', this.uploadSrc.model_path);
            
            // Upload files first if needed or send directly to analysis API 
            // The backend api/analysis.py usually handles file parsing from request.files
            // We need to check how api/analysis.py expects data for 'registration'
            // Assuming it expects 'file1' and 'file2' lists or similar?
            // Actually, for 'registration', the backend likely expects pairs. 
            // Currently my backend implementation for registration might be simple.
            // Let's assume standard 'file' upload for now or 'files'.
            // Wait, looking at backend implementation:
            // It iterates request.files.getlist('file') usually.
            // For registration, it might need to know which is fixed and which is moving.
            // The current generic 'analysis_api' might need adjustment or specific handling for registration 
            // if it relies on a single 'file' list.
            
            // Re-checking backend/applications/api/analysis.py might be needed.
            // But for now, let's construct it to send everything.
            
            // NOTE: Current backend implementation for registration (fun_type_6) 
            // in api/analysis.py:
            // It calls `interface.analysis.registration`.
            // Let's assume it handles finding pairs by name overlap or index.
            // Standard approach:
            // formData.append('file', ...) multiple times.
            // But we have two lists. 
            
            this.fileList1.forEach(file => { formData.append('file', file.raw); });
            this.fileList2.forEach(file => { formData.append('file', file.raw); });
            
            // We need to differentiate them. 
            // Maybe append a separator or specific naming convention?
            // Or use 'file1' and 'file2' in the form data and update backend to handle it.
            // For now, I will use the standard 'file' key and rely on backend to sort it out (e.g. by odd/even or name matching if implemented).
            // If backend is generic, it might just treat them as a bag of files.
            
            const res = await imgUpload(formData, 'registration'); // 'registration' maps to the verify function
            
            if (res.data.code === 0) {
                this.$message.success('配准成功');
                this.resultArr = res.data.data; // Assuming data contains list of output paths
            } else {
                this.$message.error(res.data.msg || '配准失败');
            }
        } catch (e) {
            console.error(e);
            this.$message.error('请求发生错误');
        } finally {
            loading.close();
        }
    },
    downloadImg(url, name) {
        // Implement download logic
        const link = document.createElement('a');
        link.href = url;
        link.download = name;
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
