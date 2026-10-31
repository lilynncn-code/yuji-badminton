function key(owner,postId){return `post-comment-send-${postId}-${owner}`}
export function commentDraftSignature(data){return JSON.stringify([String(data?.content||'').trim(),String(data?.replyTo?.id||'')])}
function normalize(value){
    const reply=value?.replyTo
    return {content:typeof value?.content==='string'?value.content:'',replyTo:reply&&/^[1-9][0-9]*$/.test(String(reply.id))?{id:String(reply.id),authorName:String(reply.authorName||'球友')}:null,
        ...(/^[A-Za-z0-9_-]{8,64}$/.test(value?.requestKey||'')?{requestKey:value.requestKey}:{})}
}
export function restoreCommentDraft(owner,postId){return normalize(uni.getStorageSync(key(owner,postId)))}
export function persistCommentDraft(owner,postId,data,known){
    const previous=known||restoreCommentDraft(owner,postId),saved=normalize(data)
    delete saved.requestKey
    if(commentDraftSignature(previous)===commentDraftSignature(saved)&&previous.requestKey)saved.requestKey=previous.requestKey
    if(!saved.content&&!saved.replyTo)uni.removeStorageSync(key(owner,postId))
    else uni.setStorageSync(key(owner,postId),saved)
    return saved
}
export function prepareCommentSend(owner,postId,data,known){
    const saved=persistCommentDraft(owner,postId,data,known)
    if(!saved.requestKey){saved.requestKey=`comment-${Date.now().toString(36)}-${Math.random().toString(36).slice(2,14)}`;uni.setStorageSync(key(owner,postId),saved)}
    return saved
}
export function clearCommentDraft(owner,postId,requestKey){
    if(restoreCommentDraft(owner,postId).requestKey!==requestKey)return false
    uni.removeStorageSync(key(owner,postId));return true
}
