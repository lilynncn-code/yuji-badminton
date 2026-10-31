function key(owner,scope){return `track-clinic-draft-${scope}-${owner}`}
function read(owner,scope){
    const value=uni.getStorageSync(key(owner,scope))
    return value&&typeof value==='object'&&value.data&&typeof value.data==='object'?value:null
}
export function restoreClinicDraft(owner,scope,defaults){return {...defaults,...(read(owner,scope)?.data||{})}}
export function persistClinicDraft(owner,scope,data){
    const previous=read(owner,scope),signature=JSON.stringify(data)
    const saved={data:{...data},signature}
    if(previous?.signature===signature&&previous.request_key)saved.request_key=previous.request_key
    uni.setStorageSync(key(owner,scope),saved)
    return saved
}
export function prepareClinicSend(owner,scope,data){
    const saved=persistClinicDraft(owner,scope,data)
    if(!saved.request_key){
        saved.request_key=`clinic-${Date.now().toString(36)}-${Math.random().toString(36).slice(2,14)}`
        uni.setStorageSync(key(owner,scope),saved)
    }
    return {...saved.data,request_key:saved.request_key}
}
export function clearClinicDraft(owner,scope,requestKey){
    if(read(owner,scope)?.request_key!==requestKey)return false
    uni.removeStorageSync(key(owner,scope));return true
}
