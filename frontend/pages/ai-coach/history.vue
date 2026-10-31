<template>
<view class="page"><text class="title">{{ $tr("训练记录") }}</text>
<view class="card"><text>{{ $tr("累计 {0} 次 · {1} 分钟", [summary?.sessions ?? '—', summary?.total_minutes ?? '—']) }}</text><text>{{ $tr("连续训练 {0} 天", [summary?.streak ?? '—']) }}</text><text v-if="summaryError">{{ $tr(summaryError) }}</text><button v-if="summaryError" @click="loadSummary">{{ $tr("重新读取统计") }}</button></view>
<view v-if="recordDraftError" class="card"><text>{{ $tr(recordDraftError) }}</text><button @click="restoreRecordDrafts">{{ $tr("重新读取待确认训练") }}</button></view>
<view v-if="recordDrafts.length" class="card"><text class="name">{{ $tr("本机尚待确认的训练 · {0} 次", [recordDrafts.length]) }}</text><text>{{ $tr("可能尚未保存，也可能已保存但未收到回应。确认会沿用原来的保存编号，不重复增加训练；补存后按实际保存时间显示。视频需要在已保存记录中另行确认。") }}</text></view>
<view v-for="draft in recordDrafts" :key="draft.payload.request_key" class="card">
<text class="name">{{ $tr(draft.payload.training_type) }}</text><text>{{ $tr("{0}结束 · {1} 秒 · {2} 次", [formatTimeLabel(draft.finished_at), draft.payload.duration_seconds, draft.payload.reps]) }}</text><text>{{ $tr(draft.payload.advice) }}</text>
<text v-if="recordDraftMessages[draft.payload.request_key]">{{ $tr(recordDraftMessages[draft.payload.request_key]) }}</text>
<button :disabled="Boolean(recordDraftBusy[draft.payload.request_key])" @click="saveRecordDraft(draft)">{{ $tr(recordDraftBusy[draft.payload.request_key]?'正在确认保存…':'确认保存这次训练') }}</button>
<button :disabled="Boolean(recordDraftBusy[draft.payload.request_key])" @click="discardRecordDraft(draft)">{{ $tr("移除本机待确认项") }}</button>
</view>
<view v-if="error" class="card"><text>{{ $tr(error) }}</text><button :disabled="loading" @click="retryList">{{ $tr("重新加载") }}</button></view>
<view v-if="loading&&!records.length" class="card">{{ $tr("正在读取训练记录…") }}</view>
<view v-else-if="loaded&&!error&&!records.length" class="card">{{ $tr("还没有训练记录，完成一次训练后会显示在这里。") }}</view>
<view v-for="record in records" :key="record.id" class="card"><text class="name">{{ $tr(record.training_type) }}</text><text>{{ $tr("{0} · {1} 秒", [formatTimeLabel(utcTime(record.created_at)), record.duration_seconds]) }}</text><text>{{ $tr("{0} 次 · {1}", [record.reps || 0, record.recording_method === 'pose' ? '画面计数' : '自己记录']) }}</text><text>{{ $tr(record.advice) }}</text>
<view v-if="courseLocation(record)" class="course-location"><text>{{ $tr("课程位置：{0} · 第 {1} 部分 · 第 {2} 题", [courseLocation(record).plan, courseLocation(record).part, courseLocation(record).question]) }}</text><button @click="openCourseLocation(record)">{{ $tr("查看课程位置") }}</button></view>
<text v-if="pending[record.id]&&!record.media_url">{{ $tr("这段视频还未确认保存。重新打开后可以继续保存；需要重新选择时，请选择原来那段视频。") }}</text>
<button v-if="!record.media_url" :disabled="Boolean(uploading)" @click="chooseClip(record)">{{ $tr(uploading===record.id?'视频保存中…':pending[record.id]?'继续保存视频':'附上本次训练视频') }}</button>
<button v-if="pending[record.id]&&!record.media_url" :disabled="Boolean(uploading)" @click="selectClip(record)">{{ $tr("重新选择原视频") }}</button>
<button v-if="pending[record.id]&&!record.media_url" :disabled="Boolean(uploading)" @click="abandon(record)">{{ $tr("放弃待保存视频") }}</button>
<text v-if="videoErrors[record.id]">{{ $tr(videoErrors[record.id]) }}</text>
<button v-if="record.media_type==='video' && record.media_url" :disabled="Boolean(loadingVideo)||Boolean(uploading)" @click="play(record)">{{ $tr(loadingVideo===record.id?'正在读取视频…':'重看训练视频') }}</button>
<video v-if="playingId===record.id && videoUrl" id="history-video" :src="videoUrl" controls @error="playbackError(record)" style="width:100%"/>
<button v-if="record.media_url && record.media_type==='video'" :disabled="Boolean(uploading)" @click="removeVideo(record)">{{ $tr("删除训练视频") }}</button></view>
<button v-if="hasMore" :disabled="loading" @click="loadMore">{{ $tr(loading?'正在读取…':'继续加载更早记录') }}</button>
<text v-else-if="records.length" class="end-note">{{ $tr("已显示全部训练记录") }}</text>
</view></template>
<script setup>
import { ref } from 'vue'
import { onShow, onHide, onUnload } from '@dcloudio/uni-app'
import { fetchTrainingHistory, fetchTrainingSummary, loadTrainingVideo, uploadTrainingVideo, attachTrainingVideo, findTrainingVideoUpload, abandonTrainingVideoUpload, saveTrainingRecord } from '../../utils/training-api'
import { readTrainingVideoDraft, prepareTrainingVideoDraft, updateTrainingVideoDraft, clearTrainingVideoDraft } from '../../utils/training-video-draft'
import { readTrainingRecordDrafts, clearTrainingRecordDraft } from '../../utils/training-record-draft'
import { accountKey, utcTime, request } from '../../utils/request'
import { getAuthToken } from '../../utils/auth'
import { formatTimeLabel, getUser } from '../../utils/store'
const records=ref([]),summary=ref(null),summaryError=ref(''),error=ref('')
const loadingVideo=ref(0),playingId=ref(0),videoUrl=ref(''),uploading=ref(0)
const loading=ref(false),loaded=ref(false),hasMore=ref(false),pending=ref({}),videoErrors=ref({})
const recordDrafts=ref([]),recordDraftError=ref(''),recordDraftMessages=ref({}),recordDraftBusy=ref({})
const recordDraftJobs=new Map()
let active=false,owner='',pageGeneration=0,listGeneration=0,summaryGeneration=0,videoGeneration=0,retryMore=false
let paths=new Map()
function context(){return {page:pageGeneration,owner,token:getAuthToken()}}
function current(c){return Boolean(active&&c.token&&c.page===pageGeneration&&c.owner===String(getUser()?.id||'')&&c.token===getAuthToken())}
function revoke(url){
    // #ifdef H5
    if(url?.startsWith('blob:'))URL.revokeObjectURL(url)
    // #endif
}
function releaseVideo(){
    videoGeneration++;uni.createVideoContext('history-video').stop()
    revoke(videoUrl.value);videoUrl.value='';playingId.value=0;loadingVideo.value=0
}
function leave(){active=false;pageGeneration++;listGeneration++;summaryGeneration++;loading.value=false;uploading.value=0;releaseVideo()}
onHide(leave);onUnload(leave)
onShow(()=>{
    const next=String(getUser()?.id||'')
    if(owner!==next){owner=next;paths=new Map();records.value=[];summary.value=null;pending.value={};videoErrors.value={};loaded.value=false;hasMore.value=false;recordDrafts.value=[];recordDraftMessages.value={}}
    active=true;pageGeneration++;releaseVideo()
    if(!getAuthToken()){recordDrafts.value=[];uni.reLaunch({url:'/pages/auth/login'});return}
    restoreRecordDrafts();load();loadSummary()
})
function restoreRecordDrafts(){
    const c=context()
    if(!current(c))return
    try{recordDrafts.value=readTrainingRecordDrafts(owner);recordDraftError.value=''}
    catch(e){recordDrafts.value=[];recordDraftError.value=e.message||'本机待确认训练暂时无法读取'}
    recordDraftBusy.value=Object.fromEntries(recordDrafts.value.map(row=>[row.payload.request_key,recordDraftJobs.has(`${owner}:${row.payload.request_key}`)]))
}
function recordDraftCurrent(draft){return recordDrafts.value.some(row=>row.payload.request_key===draft.payload.request_key&&JSON.stringify(row.payload)===JSON.stringify(draft.payload))}
async function saveRecordDraft(draft){
    const c=context(),key=draft.payload.request_key,jobKey=`${c.owner}:${key}`
    if(!current(c)||!recordDraftCurrent(draft)||recordDraftJobs.has(jobKey))return
    const job={};recordDraftJobs.set(jobKey,job);recordDraftBusy.value[key]=true;recordDraftMessages.value[key]=''
    let confirmed=false,message=''
    try{
        await saveTrainingRecord({...draft.payload});confirmed=true
        try{clearTrainingRecordDraft(c.owner,key)}catch{message='本次训练已保存，但本机待确认项未能清理；再次确认不会重复增加记录。'}
    }catch(e){message=e.message||'本次保存还未确认，请检查网络后重试'}
    finally{
        if(recordDraftJobs.get(jobKey)===job)recordDraftJobs.delete(jobKey)
        if(active&&owner===c.owner&&current(context())){
            restoreRecordDrafts()
            if(c.token===getAuthToken()){
                recordDraftMessages.value[key]=message
                if(confirmed){uni.showToast({title:'本次训练已保存',icon:'none'});load();loadSummary()}
            }
        }
    }
}
function discardRecordDraft(draft){
    const c=context(),key=draft.payload.request_key,jobKey=`${c.owner}:${key}`
    if(!current(c)||!recordDraftCurrent(draft)||recordDraftJobs.has(jobKey))return
    let handled=false
    uni.showModal({title:'移除本机待确认项',content:'只移除这条本机待确认内容，不删除已保存到账号的训练。如果这次训练尚未保存，移除后将无法从本机继续保存。确定继续吗？',success:r=>{
        if(handled)return
        handled=true
        if(!r.confirm||!current(c)||!recordDraftCurrent(draft)||recordDraftJobs.has(jobKey))return
        try{clearTrainingRecordDraft(c.owner,key);restoreRecordDrafts();delete recordDraftMessages.value[key]}
        catch{recordDraftMessages.value[key]='本机待确认项未能移除，原内容仍保留，请检查可用空间后重试'}
    }})
}
function restorePending(){
    const drafts={}
    for(const r of records.value){try{const saved=readTrainingVideoDraft(owner,r.id);if(saved){if(r.media_url&&r.media_url===saved.url)clearTrainingVideoDraft(owner,r.id,saved.request_key);else drafts[r.id]=saved}}catch{videoErrors.value[r.id]='待保存视频信息无法读取，请稍后重新打开'}}
    pending.value=drafts
}
function changedList(){listGeneration++;loading.value=false}
function applyRecord(saved){
    changedList()
    const record=records.value.find(r=>r.id===saved.id)
    if(record)Object.assign(record,saved)
}
function chooseClip(record){
    if(uploading.value)return
    if(pending.value[record.id]){saveVideo(record);return}
    selectClip(record)
}
function selectClip(record){
    const c=context()
    uni.chooseVideo({sourceType:['album'],maxDuration:300,success:r=>{
        if(!current(c)||uploading.value||record.media_url)return
        if(r.size>32*1024*1024){videoErrors.value[record.id]='请选择不超过32MB的视频';return}
        try{pending.value[record.id]=prepareTrainingVideoDraft(owner,record.id)}
        catch{videoErrors.value[record.id]='待保存信息没有保存成功，请检查手机存储后重试';return}
        paths.set(record.id,r.tempFilePath);saveVideo(record)
    }})
}
async function saveVideo(record){
    if(uploading.value)return
    const c=context(),draft=pending.value[record.id]
    if(!draft||!current(c))return
    uploading.value=record.id;videoErrors.value[record.id]=''
    try{
        let clip=null
        {
            try{clip=await findTrainingVideoUpload(draft.request_key)}catch(e){if(e.status!==404)throw e}
            if(!current(c))return
            if(!clip){
                const path=paths.get(record.id)
                if(!path){videoErrors.value[record.id]='还未确认上传成功，请点击“重新选择原视频”选回同一段视频';return}
                clip=await uploadTrainingVideo(path,draft.request_key)
            }
            // Save the returned identity even if the page was left; never erase a newer draft.
            if(!updateTrainingVideoDraft(c.owner,record.id,draft.request_key,clip))return
            if(!current(c))return
            pending.value[record.id]={...draft,media_id:clip.id,url:clip.url}
        }
        if(!current(c))return
        const saved=await attachTrainingVideo(record.id,clip.id)
        clearTrainingVideoDraft(c.owner,record.id,draft.request_key)
        if(!current(c))return
        delete pending.value[record.id];paths.delete(record.id);applyRecord(saved)
        uni.showToast({title:'训练视频已保存，仅本人可看',icon:'none'})
    }catch(e){if(current(c))videoErrors.value[record.id]=e.message||'视频尚未确认保存，请重试'}
    finally{if(current(c))uploading.value=0}
}
function abandon(record){
    if(uploading.value)return
    const c=context(),draft=pending.value[record.id]
    if(!draft)return
    uni.showModal({title:'放弃待保存视频',content:'放弃这次待保存的视频，训练次数和时长仍保留。确定继续吗？',success:async r=>{
        if(!r.confirm||!current(c)||uploading.value||pending.value[record.id]?.request_key!==draft.request_key)return
        uploading.value=record.id
        try{
            await abandonTrainingVideoUpload(draft.request_key)
            clearTrainingVideoDraft(c.owner,record.id,draft.request_key)
            if(!current(c))return
            delete pending.value[record.id];paths.delete(record.id);videoErrors.value[record.id]=''
        }catch(e){
            if(!current(c))return
            if(e.status===409){
                try{const saved=await request(`/training/${record.id}`);if(!current(c))return;if(saved.media_url){clearTrainingVideoDraft(c.owner,record.id,draft.request_key);delete pending.value[record.id];paths.delete(record.id);applyRecord(saved)}}catch{}
            }
            if(current(c))videoErrors.value[record.id]=e.message
        }finally{if(current(c))uploading.value=0}
    }})
}
async function play(record){
    if(loadingVideo.value||uploading.value)return
    releaseVideo();const generation=videoGeneration,c=context();loadingVideo.value=record.id;videoErrors.value[record.id]=''
    try{
        const url=await loadTrainingVideo(record.media_url)
        if(!current(c)||generation!==videoGeneration){revoke(url);return}
        videoUrl.value=url;playingId.value=record.id
    }catch(e){if(current(c)&&generation===videoGeneration)videoErrors.value[record.id]=e.message||'视频读取失败，请重试'}
    finally{if(current(c)&&generation===videoGeneration)loadingVideo.value=0}
}
function playbackError(record){if(playingId.value!==record.id)return;releaseVideo();videoErrors.value[record.id]='视频暂时无法播放，请重新读取；也可以换一段手机支持的视频。'}
function removeVideo(record){
    if(uploading.value)return
    const mediaId=record.media_url?.match(/^\/media\/(\d+)\/file$/)?.[1],c=context()
    if(!mediaId){videoErrors.value[record.id]='这条旧记录没有可删除的视频';return}
    uni.showModal({title:'删除训练视频',content:'引用这段视频的训练记录都会移除视频，训练次数和时长仍保留。确定删除吗？',success:async r=>{
        if(!r.confirm||!current(c)||uploading.value||record.media_url!==`/media/${mediaId}/file`)return
        uploading.value=record.id;releaseVideo()
        try{
            await request(`/media/${mediaId}`,{method:'DELETE'})
            if(!current(c))return
            changedList()
            for(const item of records.value)if(item.media_url===`/media/${mediaId}/file`){item.media_url=null;item.media_type=null}
            videoErrors.value[record.id]=''
        }catch(e){if(current(c))videoErrors.value[record.id]=e.message}
        finally{if(current(c))uploading.value=0}
    }})
}
async function loadSummary(){
    const c=context(),generation=++summaryGeneration;summaryError.value=''
    try{const stats=await fetchTrainingSummary();if(current(c)&&generation===summaryGeneration)summary.value=stats}
    catch(e){if(current(c)&&generation===summaryGeneration)summaryError.value=e.message}
}
async function load(more=false){
    if(more&&(loading.value||!hasMore.value))return
    const c=context(),generation=++listGeneration;loading.value=true;error.value='';retryMore=more
    try{
        const history=await fetchTrainingHistory(more?records.value[records.value.length-1]?.id:undefined)
        if(!current(c)||generation!==listGeneration)return
        if(more){const ids=new Set(records.value.map(r=>r.id));records.value.push(...history.records.filter(r=>!ids.has(r.id)))}
        else records.value=history.records
        hasMore.value=history.has_more;loaded.value=true;restorePending()
    }catch(e){if(current(c)&&generation===listGeneration)error.value=e.message}
    finally{if(current(c)&&generation===listGeneration)loading.value=false}
}
function loadMore(){return load(true)}
function retryList(){return load(retryMore)}
const coursePlans={
    1:'新手起飞岛',2:'双打节奏岛',3:'防守反击岛',4:'进攻爆发岛',5:'双打战术岛',6:'高手比赛岛'
}
function courseLocation(record){
    const match=String(record?.task_id||'').match(/^unit-(\d+)-m(\d+)-t(\d+)$/)
    if(!match||!coursePlans[Number(match[1])])return null
    return {unit:Number(match[1]),part:Number(match[2]),question:Number(match[3]),plan:coursePlans[Number(match[1])],taskId:match[0]}
}
function openCourseLocation(record){
    const location=courseLocation(record)
    if(!location)return
    try{uni.setStorageSync(accountKey('pending-course-task'),location.taskId)}catch{videoErrors.value[record.id]='课程位置暂时无法保存，请稍后重试';return}
    uni.switchTab({url:'/pages/ai-coach/ai-coach'})
}
</script>
<style scoped>.page{min-height:100vh;background:#121212;color:#fff;padding:24rpx;box-sizing:border-box}.title{font-size:40rpx;color:#cf0;font-weight:800}.card{margin-top:24rpx;background:#222;padding:24rpx;border-radius:18rpx}.card text{display:block;line-height:1.8}.name{font-weight:800;color:#cf0}.course-location{margin-top:12rpx;padding-top:12rpx;border-top:1px solid #3a3a3a}.course-location text{color:#d8e7a4;font-size:25rpx}button{margin-top:18rpx;padding:14rpx 20rpx;border-radius:12rpx;background:#353535;color:#cf0;font-size:27rpx;line-height:1.5;white-space:normal}button[disabled]{color:#aaa}.end-note{display:block;color:#aaa;text-align:center;margin:28rpx 0;font-size:24rpx}</style>
