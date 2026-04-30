import { historyGetPage } from "@/api/history"
import { showFullScreenLoading } from "@/utils/loading";
import { toBackendAssetUrl } from "@/utils/backendAssetUrl";
import { hydrateAssetPreviews } from "@/utils/assetPreview";
import { registerUploadedSources } from "@/utils/localSourceRegistry";

function getUploadImg(type) {
  historyGetPage(1, 20, type).then((res) => {
    this.imgArr = res.data.data
    this.imgArr.forEach((item) => {
      item.before_img_url = toBackendAssetUrl(item.before_img);
      item.after_img_url = toBackendAssetUrl(item.after_img);
    });
    hydrateAssetPreviews(this.imgArr, ["before_img", "after_img"], 420);
    this.isUpload = this.imgArr.length !== 0;
  }).catch((rej) => { })
}

function goCompress(type, num) {
  this.historyGetPage(1, num, type).then((res) => {
    this.atchDownload(
      res.data.data.map((item) => {
        return { after_img: item.after_img, id: item.id };
      })
    );
  }).catch((rej) => { });
}

function upload(type, funUrl) {
  if (this.fileList.length === 0) {
    this.$message.error("请上传图片！");
  } else {
    let formData = new FormData();
    let _this = this;
    for (const item of this.fileList) {
      formData.append("files", item) || formData.append('files', item.raw);
      formData.append("type", type);
      if (this.isSlice) {
        formData.append("isSlice", this.isSlice);
      }
    }
    this.createSrc(formData).then((res) => {
      const uploadedItems = res.data.data || [];
      registerUploadedSources(uploadedItems, this.fileList);
      this.uploadSrc.list = uploadedItems.map((item) => {
        return item.src;
      });
      this.imgUpload(this.uploadSrc, funUrl).then((res) => {
        this.fileList = []
        this.$message.success("上传成功！");
        this.getMore()
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


export { getUploadImg, goCompress, upload }
