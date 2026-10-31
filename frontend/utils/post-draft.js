function key(owner){return `post-draft-${owner}`}
function normalize(data){
    return {title:typeof data?.title==='string'?data.title:'',content:typeof data?.content==='string'?data.content:'',
        images:Array.isArray(data?.images)?data.images.filter(v=>typeof v==='string').slice(0,6):[],videoUrl:typeof data?.videoUrl==='string'?data.videoUrl:'',tags:Array.isArray(data?.tags)?data.tags.filter(v=>typeof v==='string'):['我的发布']}
}
export function postRequestSnapshot(data){return JSON.stringify({content:[(data.title||'我的羽毛球动态').trim(),(data.content||'').trim()].filter(Boolean).join('\n'),video_url:data.videoUrl||'',image_urls:data.images||[]})}
function withKey(data,source){
    const saved=normalize(data),snapshot=postRequestSnapshot(saved)
    if(/^[A-Za-z0-9_-]{8,64}$/.test(source?.requestKey||'')&&source.requestSnapshot===snapshot){saved.requestKey=source.requestKey;saved.requestSnapshot=snapshot}
    return saved
}
export function restorePostDraft(owner){const source=uni.getStorageSync(key(owner));return withKey(source,source)}
export function persistPostDraft(owner,data,known){const saved=withKey(data,known||restorePostDraft(owner));uni.setStorageSync(key(owner),saved);return saved}
export function preparePostSend(owner,data,known){
    const saved=persistPostDraft(owner,data,known)
    if(!saved.requestKey){saved.requestKey=`post-${Date.now().toString(36)}-${Math.random().toString(36).slice(2,14)}`;saved.requestSnapshot=postRequestSnapshot(saved);uni.setStorageSync(key(owner),saved)}
    return saved
}
export function clearPostDraft(owner,requestKey){if(restorePostDraft(owner).requestKey!==requestKey)return false;uni.removeStorageSync(key(owner));return true}
