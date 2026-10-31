const keyFor = owner => `track-training-records-${owner}`
const limit = 30
function clone(value) { return JSON.parse(JSON.stringify(value)) }
function valid(item) {
    const p=item?.payload
    return p&&/^[a-zA-Z0-9_-]{8,64}$/.test(p.request_key||'')&&typeof p.training_type==='string'&&p.training_type.trim().length>0&&p.training_type.length<=80
        &&Number.isInteger(p.duration_seconds)&&p.duration_seconds>=1&&p.duration_seconds<=14400
        &&Number.isInteger(p.reps)&&p.reps>=0&&p.reps<=10000&&Number.isFinite(p.score)&&p.score>=0&&p.score<=100
        &&['manual','pose'].includes(p.recording_method)&&typeof p.advice==='string'&&p.advice.length<=5000
        &&(!p.task_id||(typeof p.task_id==='string'&&p.task_id.length<=80))&&Number.isFinite(new Date(item.finished_at).getTime())
}
export function readTrainingRecordDrafts(owner) {
    if(!owner)return []
    const stored=uni.getStorageSync(keyFor(owner))
    if(stored===undefined||stored===null||stored==='')return []
    if(!Array.isArray(stored)||stored.length>limit||stored.some(item=>!valid(item))||new Set(stored.map(item=>item.payload.request_key)).size!==stored.length){
        throw new Error('本机待确认训练无法完整读取，请保留本机资料并稍后重试')
    }
    return clone(stored)
}
export function keepTrainingRecordDraft(owner, payload) {
    if(!owner)throw new Error('请先登录后再保留训练记录')
    const item={payload:clone(payload),finished_at:new Date().toISOString()}
    if(!valid(item))throw new Error('本次训练内容未读完整，请保留当前页面并重试保存')
    const drafts=readTrainingRecordDrafts(owner),prior=drafts.find(row=>row.payload.request_key===payload.request_key)
    if(prior){
        if(JSON.stringify(prior.payload)!==JSON.stringify(item.payload))throw new Error('本次待确认训练内容不一致，请先到训练记录核对')
        return prior
    }
    if(drafts.length>=limit)throw new Error('本机已有30次待确认训练，请先到训练记录保存或核对后再开始')
    drafts.push(item)
    uni.setStorageSync(keyFor(owner),drafts)
    return clone(item)
}
export function clearTrainingRecordDraft(owner, requestKey) {
    const drafts=readTrainingRecordDrafts(owner),next=drafts.filter(row=>row.payload.request_key!==requestKey)
    if(next.length===drafts.length)return true
    if(next.length)uni.setStorageSync(keyFor(owner),next)
    else uni.removeStorageSync(keyFor(owner))
    return true
}
