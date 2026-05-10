import {request} from  "@/api/request.js"

export function historyGetPage(page,limit,type){
    const params = {
        page: page,
        limit: limit
    }
    if (typeof type === "string" && type.trim() !== "") {
        params.type = type
    }
    return request({
        method:'GET',
        url:'/api/history/list',
        params
    })
}

export function historyDelete(data){
    return request({
        method:'DELETE',
        url:'api/history/batchRemove',
        data
    })
}
