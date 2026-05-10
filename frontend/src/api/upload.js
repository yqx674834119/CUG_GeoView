import { requestfile } from "@/api/requestfile.js"
import {request} from "@/api/request.js"
export function createSrc(formdata) {
    return requestfile({
        method: 'POST',
        url: '/api/file/upload',
        data:formdata
    })
}
export function createVideoPreview(formdata) {
    return requestfile({
        method: 'POST',
        url: '/api/file/upload-video-preview',
        data: formdata
    })
}
export function imgUpload(data,funUrl){
    return request({
        method:'POST',
        url:`/api/analysis/${funUrl}`,
        data
    })
}

export function histogramUpload(data){
    return request({
        method:'POST',
        url:'/api/analysis/histogram_match',
        data
    })
}


export function prePhotoHandle(data){
    return request({
        method:'POST',
        url:'/api/analysis/image_pre',
        data
    })
}

export function getCustomModel(model_type){
    return request({
        method:'GET',
        url:`/api/model/list/${model_type}`
    })
}
