
import { toBackendAssetUrl } from "@/utils/backendAssetUrl";

function previewOnePic(pic) {
    this.flag = 1
    this.fbflag = 1
    this.previewPic1 = toBackendAssetUrl(pic)
    this.preVisible = true;
}
function previewTwoPic(pic1, pic2) {
    this.flag = 2
    this.fbflag = 2
    this.previewPic1 = toBackendAssetUrl(pic1)
    this.previewPic2 = toBackendAssetUrl(pic2)
    this.preVisible = true
}
function previewThreePic(pic1, pic2, pic3) {
    this.flag = 3
    this.fbflag = 3
    this.previewPic1 = toBackendAssetUrl(pic1)
    this.previewPic2 = toBackendAssetUrl(pic2)
    this.previewPic3 = toBackendAssetUrl(pic3)
    this.preVisible = true
}

export { previewOnePic, previewTwoPic, previewThreePic }
