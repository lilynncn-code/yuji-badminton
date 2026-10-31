function key(owner){return `track-game-draft-${owner}`}
function read(owner){
    const value=uni.getStorageSync(key(owner))
    return value&&typeof value==='object'&&value.data&&typeof value.data==='object'?value:null
}
export function restoreGameDraft(owner,defaults){
    const data=read(owner)?.data||{}
    return Object.fromEntries(Object.entries(defaults).map(([field,fallback])=>[field,typeof data[field]===typeof fallback?data[field]:fallback]))
}
export function persistGameDraft(owner,data){
    const previous=read(owner),signature=JSON.stringify(data)
    const saved=previous?.signature===signature?{...previous,data:{...data}}:{data:{...data},signature}
    uni.setStorageSync(key(owner),saved)
    return saved
}
export function prepareGameSend(owner,data,payload){
    const saved=persistGameDraft(owner,data),fingerprint=JSON.stringify(payload)
    if(!saved.request_key||saved.fingerprint!==fingerprint){
        saved.request_key=`game-${Date.now().toString(36)}-${Math.random().toString(36).slice(2,14)}`
        saved.fingerprint=fingerprint
        uni.setStorageSync(key(owner),saved)
    }
    return {...payload,request_key:saved.request_key}
}
export function clearGameDraft(owner,requestKey){
    if(read(owner)?.request_key!==requestKey)return false
    uni.removeStorageSync(key(owner));return true
}
