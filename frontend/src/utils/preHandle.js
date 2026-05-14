import {createSrc,prePhotoHandle} from '@/api/upload'
import { fetchBackendAssetBlobUrl } from "@/utils/assetChunkTransport";
import { buildUploadFormData } from "@/utils/uploadFormData";

function isChecked(vm, refName) {
  const ref = vm.$refs && vm.$refs[refName];
  return Boolean(ref && ref.checked);
}

function setChecked(vm, refName, value) {
  const ref = vm.$refs && vm.$refs[refName];
  if (ref) {
    ref.checked = value;
  }
}

function selectSharpen(type) {
  if(this.fileList.length  === 0){
    if( this.uploadSrc.prehandle === 4){
      setChecked(this, "sharpen", false);
      this.uploadSrc.prehandle = 0
    }
    else{
      setChecked(this, "sharpen", false);
      this.$message.error('请先上传图片')
    }

  }else{
    if (isChecked(this, "clahe")) {
      setChecked(this, "clahe", false);
    }

    if (!isChecked(this, "sharpen")) {
      this.$message.success("取消锐化处理");
      this.uploadSrc.prehandle=0
    } else {
      this.$message.success("锐化处理");
      this.uploadSrc.prehandle = 4

      let formData = buildUploadFormData(this.fileList, type, { scope: "预处理上传" });
      createSrc(formData).then((res) => {
        this.uploadSrc.list = res.data.data.map((item) => item.src);
        Promise.all(this.uploadSrc.list.slice(0, 3).map((item) => fetchBackendAssetBlobUrl(item))).then((urls) => {
          this.before = urls;
        });

        this.prePhoto.list = this.uploadSrc.list.slice(0, 3);
        this.prePhoto.prehandle = 4;

        prePhotoHandle(this.prePhoto).then((res)=>{

          Promise.all(res.data.data.map((item) => fetchBackendAssetBlobUrl(item))).then((urls) => {
            this.sharpenImg = urls;
          })
        }).catch(()=>{})
      }).catch((rej)=>{})
    }
  }
  }
  function selectClahe(type) {
    if(this.fileList.length === 0){
      if( this.uploadSrc.prehandle === 2){
        setChecked(this, "clahe", false);
        this.uploadSrc.prehandle = 0
      }
      else{
        setChecked(this, "clahe", false);
        this.$message.error('请先上传图片')
      }
    }else{
      if (isChecked(this, "sharpen")) {
        setChecked(this, "sharpen", false);
      }
      if (!isChecked(this, "clahe")) {
        this.$message.success("取消CLAHE处理");
        this.uploadSrc.prehandle = 0
      } else {
        this.$message.success("CLAHE处理");
        this.uploadSrc.prehandle = 2

        let formData = buildUploadFormData(this.fileList, type, { scope: "预处理上传" });
        createSrc(formData).then((res) => {
          this.uploadSrc.list = res.data.data.map((item) => item.src);
          Promise.all(this.uploadSrc.list.slice(0, 3).map((item) => fetchBackendAssetBlobUrl(item))).then((urls) => {
            this.before = urls;
          });

          this.prePhoto.list = this.uploadSrc.list.slice(0, 3)
          this.prePhoto.prehandle = 2

          prePhotoHandle(this.prePhoto).then((res)=>{

            Promise.all(res.data.data.map((item) => fetchBackendAssetBlobUrl(item))).then((urls) => {
              this.claheImg = urls;
            })
          }).catch((rej)=>{})
        }).catch((rej)=>{})
      }
    }
  }
 function selectFilter() {
    if (isChecked(this, "smooth")) {
      setChecked(this, "smooth", false);
    }

    if (!isChecked(this, "filter")) {
      this.$message.success("取消高斯滤波处理");
      this.uploadSrc.denoise = 0
    } else {
      this.$message.success("高斯滤波处理");
      this.uploadSrc.denoise = 5
    }
  }
  function selectSmooth() {
    if (isChecked(this, "filter")) {
      setChecked(this, "filter", false);
    }

    if (!isChecked(this, "smooth")) {
      this.$message.success("取消平滑处理");
      this.uploadSrc.denoise = 0
    } else {
      this.$message.success("平滑处理");
      this.uploadSrc.denoise = 3
    }
  }

  export {selectSharpen,selectFilter,selectSmooth,selectClahe}
