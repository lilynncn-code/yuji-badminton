function key(owner,chat){return `track-chat-send-${chat}-${owner}`}
export function chatDraftSignature(data){return JSON.stringify([data.text||'',data.image||''])}
export function readChatDraft(owner,chat){
    const saved=uni.getStorageSync(key(owner,chat))
    if(saved===undefined||saved===null||saved==='')return {text:'',image:''}
    if(typeof saved!=='object'||typeof saved.text!=='string'||typeof saved.image!=='string'||
       (saved.requestKey!==undefined&&typeof saved.requestKey!=='string')||
       (saved.uploadedImage!==undefined&&typeof saved.uploadedImage!=='string'))throw Error('本机聊天草稿无法读取，请检查存储空间')
    return {...saved}
}
export function saveChatDraft(owner,chat,data,prior){
    const stored=readChatDraft(owner,chat)
    const same=value=>value&&chatDraftSignature(value)===chatDraftSignature(data)
    const source=same(prior)?prior:same(stored)?stored:null
    const saved={text:data.text||'',image:data.image||'',...(source?.requestKey?{requestKey:source.requestKey}:{}),...(source?.uploadedImage?{uploadedImage:source.uploadedImage}:{})}
    uni.setStorageSync(key(owner,chat),saved)
    return saved
}
export function prepareChatSend(owner,chat,data,prior){
    const saved=saveChatDraft(owner,chat,data,prior)
    if(!saved.requestKey)saved.requestKey=`chat-${Date.now().toString(36)}-${Math.random().toString(36).slice(2,14)}-${Math.random().toString(36).slice(2,14)}`
    uni.setStorageSync(key(owner,chat),saved)
    return saved
}
export function saveChatUpload(owner,chat,sent){
    const stored=readChatDraft(owner,chat)
    if(stored.requestKey!==sent.requestKey||chatDraftSignature(stored)!==chatDraftSignature(sent))return false
    uni.setStorageSync(key(owner,chat),{...stored,uploadedImage:sent.uploadedImage})
    return true
}
export function clearChatDraft(owner,chat,sent){
    const stored=readChatDraft(owner,chat)
    if(stored.requestKey!==sent.requestKey||chatDraftSignature(stored)!==chatDraftSignature(sent))return false
    uni.removeStorageSync(key(owner,chat))
    return true
}
