import { showFullScreenLoading } from "@/utils/loading";
import { registerUploadedSources } from "@/utils/localSourceRegistry";
import { buildUploadFormData } from "@/utils/uploadFormData";

function getUploadImg() {
  this.imgArr = [];
  this.isUpload = false;
}

function goCompress() {
  this.$message.info("暂无批量下载");
}

function extractAnalysisRecords(response) {
  const records = response?.data?.data?.records;
  return Array.isArray(records) ? records : [];
}

function setAnalysisRecords(vm, response) {
  const records = extractAnalysisRecords(response);
  if (records.length) {
    vm.imgArr = records;
    vm.isUpload = true;
  }
  return records;
}

function upload(type, funUrl) {
  if (this.fileList.length === 0) {
    this.$message.error("请上传图片！");
  } else {
    let formData = buildUploadFormData(this.fileList, type, {
      isSlice: this.isSlice,
      scope: "文件上传",
    });
    let _this = this;
    this.createSrc(formData).then((res) => {
      const uploadedItems = res.data.data || [];
      registerUploadedSources(uploadedItems, this.fileList);
      this.uploadSrc.list = uploadedItems.map((item) => {
        return item.src;
      });
      this.imgUpload(this.uploadSrc, funUrl).then((res) => {
        setAnalysisRecords(this, res);
        this.fileList = []
        this.$message.success("上传成功！");
      }).catch(() => { })
      if (this.uploadSrc.list.length >= 10 && type !== '场景分类') {
        this.$confirm("上传图片过多，是否压缩?", "提示", {
          confirmButtonText: "确定",
          cancelButtonText: "取消",
          type: "warning",
        })
          .then(() => {
            showFullScreenLoading('#load', '压缩中')
            this.goCompress(type, this.uploadSrc.list.length)
          }).catch(() => {

          })
      }
      _this.$refs.upload.clearFiles();
    }).catch((rej) => { })
  }
}


export { extractAnalysisRecords, getUploadImg, goCompress, setAnalysisRecords, upload }
