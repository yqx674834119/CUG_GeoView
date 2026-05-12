//https://blog.csdn.net/tattoo_jie/article/details/122251905压缩打包功能
import JSZIP from "jszip"
import FileSaver from 'file-saver'

import {hideFullScreenLoading} from "@/utils/loading";
import { isBackendPhotoAssetPath, toBackendAssetUrl } from "@/utils/backendAssetUrl";

function saveBlob(blob, filename) {
  const url = window.URL.createObjectURL(blob);
  const ele = document.createElement("a");
  ele.style.display = "none";
  ele.href = url;
  ele.download = filename;
  document.querySelectorAll("body")[0].appendChild(ele);
  ele.click();
  ele.remove();
  window.URL.revokeObjectURL(url);
}

function buildDownloadName(index, funtype) {
  return index === -1 ? `${funtype}` : `第${index}组${funtype}`;
}

function downloadimgWithWords(index, src, funtype) {
  const filename = buildDownloadName(index, funtype);
  if (isBackendPhotoAssetPath(src)) {
    fetch(toBackendAssetUrl(src))
      .then((response) => {
        if (!response.ok) {
          throw new Error(`download failed: ${response.status}`);
        }
        return response.blob();
      })
      .then((blob) => saveBlob(blob, filename))
      .catch(() => {});
    return;
  }

  fetch(toBackendAssetUrl(src))
    .then((response) => {
      if (!response.ok) {
        throw new Error(`download failed: ${response.status}`);
      }
      return response.blob();
    })
    .then((blob) => saveBlob(blob, filename));
}
function getImgArrayBuffer(url) {
  if (isBackendPhotoAssetPath(url)) {
    return fetch(toBackendAssetUrl(url)).then((response) => {
      if (!response.ok) {
        throw new Error(`download failed: ${response.status}`);
      }
      return response.blob();
    });
  }

  return new Promise((resolve, reject) => {
    //通过请求获取文件blob格式
    let xmlhttp = new XMLHttpRequest();
    xmlhttp.open("GET", toBackendAssetUrl(url), true);
    xmlhttp.responseType = "blob";
    xmlhttp.onload = function () {
      if (this.status === 200) {
        resolve(this.response);
      } else {
        reject(this.status);
      }
    };
    xmlhttp.send();
  });
}
//批量下载
function atchDownload(compressImg) {
  // this.images 是要下载的图片数组  [{url: 图片地址, id: 图片名称}]
  // 定时器 loading

  let _this = this;
  let zip = new JSZIP();
  let cache = {};
  let promises = [];
  for (let item of compressImg) {
    const promise = _this.getImgArrayBuffer(item.after_img).then((data) => {    //获取单个文件的promise返回
      // 下载文件, 并存成ArrayBuffer对象(blob)
      zip.file(item.id + ".png", data, { binary: true }); // 逐个添加文件
      cache[item.id] = data;
    });
    promises.push(promise);
  }

  Promise.all(promises)
    .then(() => {
      zip.generateAsync({ type: "blob" }).then((content) => {

        // 生成Blob二进制流
        FileSaver.saveAs(content, "打包图片"); // 利用file-saver保存文件  自定义文件名
        _this.$message.success("压缩完成！");
        hideFullScreenLoading()
      });
    })
    .catch((res) => {
        hideFullScreenLoading()
      _this.$message.error('压缩失败！')
    });
}


export { downloadimgWithWords, getImgArrayBuffer, atchDownload}
