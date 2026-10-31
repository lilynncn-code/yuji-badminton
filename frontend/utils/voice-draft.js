// Keep the exact recording and send number until its result is confirmed.
export function voiceDraftKey(chatId,userId){return `track-voice-send-${chatId}-${userId}`}
export function readVoiceDraft(chatId,userId){
    const draft=uni.getStorageSync(voiceDraftKey(chatId,userId))
    return draft&&typeof draft.path==='string'&&typeof draft.requestKey==='string'?draft:null
}
export async function keepVoiceDraft(filePath,chatId,userId,options={}){
    const draft={path:filePath,saved:false,requestKey:`voice-${Date.now()}-${Math.random().toString(36).slice(2)}`}
    if(uni.saveFile){
        try{draft.path=await new Promise((resolve,reject)=>uni.saveFile({tempFilePath:filePath,success:r=>resolve(r.savedFilePath),fail:reject}));draft.saved=true}
        catch(e){/* The temporary recording can still be retried while available. */}
    }
    try{
        if(options.isCurrent&&!options.isCurrent())throw Error('登录情况已变化，请重新录制')
        if(readVoiceDraft(chatId,userId))throw Error('已有一条待发送录音，请先处理')
        uni.setStorageSync(voiceDraftKey(chatId,userId),draft)
    }
    catch(e){if(draft.saved&&uni.removeSavedFile)uni.removeSavedFile({filePath:draft.path,fail:()=>{}});throw e}
    return draft
}
export function forgetVoiceDraft(chatId,userId,draft){
    if(!draft?.requestKey||readVoiceDraft(chatId,userId)?.requestKey!==draft.requestKey)return false
    uni.removeStorageSync(voiceDraftKey(chatId,userId))
    if(draft?.saved&&uni.removeSavedFile)uni.removeSavedFile({filePath:draft.path,fail:()=>{}})
    return true
}
