function key(owner,recordId){return `track-training-video-${recordId}-${owner}`}
export function readTrainingVideoDraft(owner,recordId){
    const saved=uni.getStorageSync(key(owner,recordId))
    return saved&&/^[a-zA-Z0-9_-]{8,64}$/.test(saved.request_key||'')?{...saved}:null
}
export function prepareTrainingVideoDraft(owner,recordId){
    const saved=readTrainingVideoDraft(owner,recordId)||{request_key:`video-${Date.now().toString(36)}-${Math.random().toString(36).slice(2,14)}`}
    uni.setStorageSync(key(owner,recordId),saved)
    return saved
}
export function updateTrainingVideoDraft(owner,recordId,requestKey,clip){
    const saved=readTrainingVideoDraft(owner,recordId)
    if(saved?.request_key!==requestKey)return false
    uni.setStorageSync(key(owner,recordId),{...saved,media_id:clip.id,url:clip.url})
    return true
}
export function clearTrainingVideoDraft(owner,recordId,requestKey){
    try{
        if(readTrainingVideoDraft(owner,recordId)?.request_key!==requestKey)return false
        uni.removeStorageSync(key(owner,recordId));return true
    }catch{return false}
}
