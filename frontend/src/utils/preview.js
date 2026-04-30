
import { isBackendPhotoAssetPath, toBackendAssetUrl } from "@/utils/backendAssetUrl";
import { ASSET_PREVIEW_PLACEHOLDER, getBackendAssetPreviewDataUrl } from "@/utils/assetPreview";

function initialPreviewSrc(pic) {
    return isBackendPhotoAssetPath(pic) ? ASSET_PREVIEW_PLACEHOLDER : toBackendAssetUrl(pic);
}

function loadPreviewInto(vm, target, pic, maxSize = 1400) {
    getBackendAssetPreviewDataUrl(pic, maxSize)
        .then((dataUrl) => {
            vm[target] = dataUrl;
        })
        .catch(() => {});
}

function previewOnePic(pic) {
    this.flag = 1
    this.fbflag = 1
    this.previewPic1 = initialPreviewSrc(pic)
    this.preVisible = true;
    loadPreviewInto(this, "previewPic1", pic)
}
function previewTwoPic(pic1, pic2) {
    this.flag = 2
    this.fbflag = 2
    this.previewPic1 = initialPreviewSrc(pic1)
    this.previewPic2 = initialPreviewSrc(pic2)
    this.preVisible = true
    loadPreviewInto(this, "previewPic1", pic1)
    loadPreviewInto(this, "previewPic2", pic2)
}
function previewThreePic(pic1, pic2, pic3) {
    this.flag = 3
    this.fbflag = 3
    this.previewPic1 = initialPreviewSrc(pic1)
    this.previewPic2 = initialPreviewSrc(pic2)
    this.previewPic3 = initialPreviewSrc(pic3)
    this.preVisible = true
    loadPreviewInto(this, "previewPic1", pic1)
    loadPreviewInto(this, "previewPic2", pic2)
    loadPreviewInto(this, "previewPic3", pic3)
}

export { previewOnePic, previewTwoPic, previewThreePic }
