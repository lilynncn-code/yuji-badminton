<template>
<view class="page">
    <text class="title">{{ $tr("技术诊所") }}</text><text class="note">{{ $tr("球友经验交流。回答来自各位球友，不保证是教练意见。") }}</text>
    <view v-if="creating" class="card">
        <input v-model="draft.title" :disabled="busy" maxlength="100" :placeholder='$tr("一句话说明你的问题")'/>
        <textarea v-model="draft.content" :disabled="busy" maxlength="2000" :placeholder='$tr("说明动作、遇到的困难和练习情况")'/>
        <text class="note">{{ $tr("选择视频后会上传，获得视频地址的人可以观看。请勿上传私人内容；仅供自己重看的录像请保存到训练记录。") }}</text>
        <button :disabled="busy" @click="chooseClip">{{ $tr("附上动作视频（可选）") }}</button>
        <text v-if="draft.video_url" class="note">{{ $tr("视频已上传；发布后会显示给球友。") }}</text>
        <button v-if="draft.video_url" :disabled="busy" @click="draft.video_url=''">{{ $tr("移除视频") }}</button>
        <text class="note">{{ $tr("未发送的文字按账号保存在本机，重新打开可继续填写。") }}</text>
        <button class="primary" :disabled="busy" @click="submit">{{ $tr(busy?'保存中':'发布问题') }}</button>
    </view>
    <view v-else-if="question">
        <view class="card">
            <text class="name">{{ question.title }}</text>
            <text class="note" @click="openPerson(question.author.id)">{{ question.author.name + ' · ' + $tr(formatTimeLabel(utcTime(question.created_at))) }}</text>
            <text class="body">{{ question.content }}</text>
            <video v-if="question.video_url" id="question-clip" ref="clipRef" :src="absoluteUrl(question.video_url)" controls @error="clipError=true"/>
            <text v-if="clipError" class="note">{{ $tr("视频暂时无法播放，请检查网络或视频格式。") }}</text>
            <view v-if="question.video_url" class="row"><button @click="step(-0.04)">{{ $tr("后退0.04秒") }}</button><button @click="step(0.04)">{{ $tr("前进0.04秒") }}</button><button @click="slow=!slow;speed()">{{ $tr(slow?'恢复原速':'半速回放') }}</button></view>
            <button v-if="question.video_url" @click="chooseReference">{{ $tr("选择另一段视频对照") }}</button>
            <video v-if="referenceClip" id="reference-clip" :src="referenceClip" controls/>
            <text v-if="referenceClip" class="note">{{ $tr("对照视频仅留在当前页面，不会发布。可分别暂停、拖动比较。") }}</text>
            <view class="row"><button :disabled="busy||loading||!savedKnown" @click="favorite">{{ $tr(saved?'取消收藏':'收藏问题') }}</button><button :disabled="busy" @click="newQuestion">{{ $tr("再提一个问题") }}</button></view>
            <text v-if="favoriteError" class="note">{{ $tr("收藏状态未能读取：{0}", [favoriteError]) }}</text>
            <button v-if="question.author.id===selfId" :disabled="busy" @click="removeQuestion">{{ $tr("删除我的问题") }}</button>
        </view>
        <view class="card">
            <text class="name">{{ $tr("回答 {0}", [question.answer_count]) }}</text>
            <text v-if="focusId" class="accent">{{ $tr("已找到提醒对应的回答，下面已突出显示。") }}</text>
            <text v-if="focusNote" class="note">{{ $tr(focusNote) }}</text>
            <button v-if="focusId||focusNote" :disabled="loading||busy" @click="showLatest">{{ $tr("查看最新回答") }}</button>
            <button v-if="question.answers_has_more" :disabled="loading||moreLoading||busy" @click="loadMore">{{ $tr(moreLoading?'正在读取…':'更早的回答') }}</button>
            <text v-if="moreError" class="note">{{ $tr(moreError) }}</text>
            <button v-if="moreError" :disabled="moreLoading||busy" @click="loadMore">{{ $tr("重试读取更早回答") }}</button>
            <view v-for="reply in displayedAnswers" :id="'answer-'+reply.id" :key="reply.id" class="answer" :class="{focused:reply.id===focusId}">
                <text v-if="question.accepted_answer_id===reply.id" class="accent">{{ $tr("提问者觉得有帮助{0}", [pinnedAnswerId===reply.id?' · 较早的回答':'']) }}</text>
                <text class="note" @click="openPerson(reply.author.id)">{{ reply.author.name + ' · ' + $tr(formatTimeLabel(utcTime(reply.created_at))) }}</text>
                <text class="body">{{reply.content}}</text>
                <button v-if="question.author.id===selfId&&reply.author.id!==selfId&&question.accepted_answer_id!==reply.id" :disabled="busy||loading||moreLoading" @click="accept(reply)">{{ $tr("这条回答有帮助") }}</button>
                <button v-if="reply.author.id===selfId" :disabled="busy" @click="removeAnswer(reply)">{{ $tr("删除我的回答") }}</button>
            </view>
            <text v-if="!question.answer_count" class="note">{{ $tr("还没有回答，欢迎补充练习建议。") }}</text>
            <text v-else-if="!question.answers_has_more" class="note">{{ $tr(focusId?'已读到最早的回答；可查看最新回答':'已显示全部回答') }}</text>
        </view>
        <view class="card"><textarea v-model="answerText" :disabled="busy" maxlength="2000" :placeholder='$tr("写下你的建议，最多2000字")'/><button class="primary" :disabled="busy||loading||moreLoading" @click="answer">{{ $tr(busy?'保存中':'提交回答') }}</button></view>
    </view>
    <text v-if="loading" class="note">{{ $tr("正在读取问题…") }}</text><text v-if="error" class="note">{{ $tr(error) }}</text>
    <button v-if="!creating&&id" :disabled="loading||busy" @click="load">{{ $tr(error?'重新加载':'刷新回答') }}</button>
</view>
</template>
<script setup>
import {computed,nextTick,ref,watch} from 'vue'
import {onLoad,onShow,onHide,onUnload} from '@dcloudio/uni-app'
import {request,uploadVideo,absoluteUrl,utcTime} from '../../utils/request'
import {getFavorites,setFavorite} from '../../utils/social-api'
import {getUser,formatTimeLabel} from '../../utils/store'
import {getAuthToken} from '../../utils/auth'
import {restoreClinicDraft,persistClinicDraft,prepareClinicSend,clearClinicDraft} from '../../utils/clinic-draft'
const selfId=ref(0),id=ref(''),creating=ref(false),question=ref(null),busy=ref(false),error=ref(''),saved=ref(false),savedKnown=ref(false),favoriteError=ref(''),answerText=ref(''),referenceClip=ref(''),slow=ref(false),clipRef=ref(null),clipError=ref(false)
const loading=ref(false),moreLoading=ref(false),moreError=ref(''),focusId=ref(0),focusNote=ref('')
const draft=ref({title:'',content:'',video_url:''})
const pinnedAnswerId=computed(()=>{
    const accepted=question.value?.accepted_answer
    return accepted&&!question.value.answers.some(a=>a.id===accepted.id)?accepted.id:0
})
const displayedAnswers=computed(()=>{
    if(!question.value)return []
    return pinnedAnswerId.value?[question.value.accepted_answer,...question.value.answers]:question.value.answers
})
let revision=0,active=false,olderCursor=0,completedQuestion=null,session='',suppressDraft=false
const questionReady=ref(false)
function sameAccount(owner=selfId.value,token=session){return owner===Number(getUser().id)&&token===getAuthToken()}
function current(ticket){return active&&ticket===revision&&sameAccount()}
function restoreDrafts(){
    suppressDraft=true
    try{
        draft.value=restoreClinicDraft(selfId.value,'question',{title:'',content:'',video_url:''})
        answerText.value=id.value?restoreClinicDraft(selfId.value,'answer-'+id.value,{content:''}).content:''
    }catch{draft.value={title:'',content:'',video_url:''};answerText.value='';error.value='本机草稿无法读取，请检查存储空间后重试'}
    finally{suppressDraft=false}
}
function persist(scope,data){try{persistClinicDraft(selfId.value,scope,data)}catch{error.value='草稿未能保存在本机，请检查存储空间后再发送'}}
function confirmDraft(owner,scope,key,token){
    try{return clearClinicDraft(owner,scope,key)}
    catch{if(active&&sameAccount(owner,token))error.value='内容已保存，但本机草稿未能清理；重开后可能仍会显示';return null}
}
watch(draft,()=>{if(!suppressDraft&&active&&sameAccount()&&selfId.value)persist('question',draft.value)},{deep:true,flush:'sync'})
watch(answerText,()=>{if(!suppressDraft&&active&&sameAccount()&&id.value&&!creating.value)persist('answer-'+id.value,{content:answerText.value})},{flush:'sync'})
onLoad(options=>{id.value=String(options.id||'');focusId.value=Number(options.answer)||0;creating.value=options.new==='1'||!id.value})
onShow(()=>{
    const owner=Number(getUser().id)
    revision++;loading.value=false;moreLoading.value=false;busy.value=false;questionReady.value=false
    if(selfId.value!==owner||session!==getAuthToken()){question.value=null;referenceClip.value='';savedKnown.value=false;saved.value=false;focusNote.value='';error.value='';moreError.value='';favoriteError.value=''}
    selfId.value=owner;session=getAuthToken();active=true
    if(!session){uni.reLaunch({url:'/pages/auth/login'});return}
    if(completedQuestion?.owner===owner&&creating.value){id.value=String(completedQuestion.id);creating.value=false;completedQuestion=null}
    restoreDrafts()
    if(!creating.value)load()
})
function leave(){active=false;revision++;loading.value=false;moreLoading.value=false;busy.value=false;questionReady.value=false;uni.createVideoContext('question-clip').pause();uni.createVideoContext('reference-clip').pause()}
onHide(leave);onUnload(leave)
function applyQuestion(data){question.value=data;questionReady.value=true;olderCursor=data.answers[0]?.id||0;moreError.value='';clipError.value=false}
async function load(){
    if(!active||!sameAccount()||busy.value||creating.value||!id.value)return
    const ticket=++revision;loading.value=true;moreLoading.value=false;error.value='';favoriteError.value='';savedKnown.value=false
    questionReady.value=false
    const target=focusId.value,path='/clinic/'+id.value
    const result=await Promise.allSettled([request(path+(target?'?answer_id='+target:'')),getFavorites('clinic')])
    if(!current(ticket))return
    let detail=result[0]
    if(detail.status==='rejected'&&detail.reason.status===404&&target){
        try{detail={status:'fulfilled',value:await request(path)}}catch(e){detail={status:'rejected',reason:e}}
        if(!current(ticket))return
        if(detail.status==='fulfilled'){focusId.value=0;focusNote.value='提醒对应的回答已删除或暂时无法查看，以下显示最新回答。'}
    }
    if(detail.status==='fulfilled'){
        applyQuestion(detail.value)
        if(focusId.value){await nextTick();if(current(ticket))uni.pageScrollTo({selector:'#answer-'+focusId.value,duration:0})}
    }else{
        error.value=detail.reason.message
        question.value=null;referenceClip.value=''
    }
    if(!current(ticket))return
    if(result[1].status==='fulfilled'){saved.value=result[1].value.items.includes(String(id.value));savedKnown.value=true}
    else favoriteError.value=result[1].reason.message
    if(current(ticket))loading.value=false
}
async function loadMore(){
    if(!active||!sameAccount()||loading.value||moreLoading.value||busy.value||!questionReady.value||!question.value?.answers_has_more)return
    const ticket=revision;moreLoading.value=true;moreError.value=''
    try{
        const data=await request('/clinic/'+id.value+'/answers'+(olderCursor?'?before_id='+olderCursor:''))
        if(!current(ticket))return
        const known=new Set(question.value.answers.map(a=>a.id))
        question.value.answers=[...data.items.filter(a=>!known.has(a.id)),...question.value.answers]
        question.value.answers_has_more=data.has_more;question.value.answer_count=data.answer_count
        question.value.accepted_answer_id=data.accepted_answer_id;question.value.accepted_answer=data.accepted_answer
        olderCursor=data.items[0]?.id||olderCursor
    }catch(e){if(current(ticket)){moreError.value=e.message;if([403,404].includes(e.status))question.value=null}}
    finally{if(current(ticket))moreLoading.value=false}
}
function showLatest(){if(!active||!sameAccount()||busy.value)return;focusId.value=0;focusNote.value='';load()}
function newQuestion(){if(!active||!sameAccount()||busy.value)return;revision++;loading.value=false;moreLoading.value=false;focusId.value=0;focusNote.value='';error.value='';creating.value=true;id.value='';question.value=null;questionReady.value=false;referenceClip.value='';restoreDrafts();uni.createVideoContext('question-clip').pause();uni.createVideoContext('reference-clip').pause()}
async function run(action,apply){
    if(busy.value||!active||!sameAccount())return
    const ticket=++revision;busy.value=true;loading.value=false;moreLoading.value=false;error.value=''
    try{const data=await action(ticket);if(current(ticket))apply?.(data)}
    catch(e){if(current(ticket)){error.value=e.message;uni.showToast({title:e.message,icon:'none'})}}
    finally{if(current(ticket))busy.value=false}
}
function chooseClip(){
    if(!active||!sameAccount()||busy.value||!creating.value)return
    const ticket=revision
    uni.chooseVideo({sourceType:['album'],maxDuration:120,success:r=>{
        if(!current(ticket))return
        if(r.size>32*1024*1024){uni.showToast({title:'请选择不超过32MB的视频',icon:'none'});return}
        run(()=>uploadVideo(r.tempFilePath),url=>draft.value.video_url=url)
    }})
}
function chooseReference(){if(!active||!sameAccount()||busy.value||loading.value||!questionReady.value)return;const ticket=revision;uni.chooseVideo({sourceType:['album'],success:r=>{if(current(ticket))referenceClip.value=r.tempFilePath}})}
function submit(){
    if(!active||!sameAccount()||busy.value||!creating.value)return
    const owner=selfId.value,token=session
    if(draft.value.title.trim().length<2||draft.value.content.trim().length<2){error.value='请写清楚标题和问题';return}
    if(draft.value.title.trim().length>100||draft.value.content.trim().length>2000){error.value='标题最多100字，问题说明最多2000字';return}
    let payload
    try{payload=prepareClinicSend(owner,'question',{title:draft.value.title.trim(),content:draft.value.content.trim(),video_url:draft.value.video_url})}
    catch{error.value='发送前未能保存本机草稿，请检查存储空间后重试';return}
    let cleared=false
    return run(async()=>{
        const data=await request('/clinic',{method:'POST',data:payload})
        cleared=confirmDraft(owner,'question',payload.request_key,token)
        if(cleared===true)completedQuestion={owner,id:data.id}
        return data
    },data=>{
        if(cleared!==true){error.value='问题已发布，但本机草稿未清除或已有新内容；新输入仍保留。请返回问题列表查看结果。';return}
        id.value=String(data.id);applyQuestion(data);creating.value=false;saved.value=false;savedKnown.value=true;focusId.value=0;focusNote.value=''
        draft.value={title:'',content:'',video_url:''};answerText.value='';completedQuestion=null
    })
}
function answer(){
    if(!active||!sameAccount()||busy.value||loading.value||moreLoading.value||creating.value||!questionReady.value||!question.value)return
    if(answerText.value.trim().length<2){error.value='请写下具体建议';return}
    if(answerText.value.trim().length>2000){error.value='回答最多2000字';return}
    const owner=selfId.value,token=session,target=id.value,scope='answer-'+target
    let payload
    try{payload=prepareClinicSend(owner,scope,{content:answerText.value.trim()})}
    catch{error.value='发送前未能保存本机草稿，请检查存储空间后重试';return}
    let cleared=false
    return run(async()=>{
        const data=await request('/clinic/'+target+'/answers',{method:'POST',data:payload})
        cleared=confirmDraft(owner,scope,payload.request_key,token);return data
    },data=>{applyQuestion(data);if(cleared===true)answerText.value='';focusId.value=0;focusNote.value=''})
}
function accept(reply){if(!questionReady.value||loading.value||question.value?.author.id!==selfId.value||reply.author.id===selfId.value||!displayedAnswers.value.some(row=>row.id===reply.id))return;const target=id.value;return run(()=>request('/clinic/'+target+'/accepted/'+reply.id,{method:'PUT'}),data=>{applyQuestion(data);focusId.value=0;focusNote.value=''})}
function favorite(){if(!questionReady.value||loading.value||!savedKnown.value)return;const next=!saved.value,target=id.value;return run(()=>setFavorite('clinic',target,next),()=>saved.value=next)}
function removeQuestion(){
    if(!active||!sameAccount()||busy.value||loading.value||!questionReady.value||question.value?.author.id!==selfId.value)return
    const ticket=revision,target=id.value
    uni.showModal({title:'删除问题',content:'问题与回答将一起删除，确定吗？',success:r=>{if(r.confirm&&current(ticket)&&target===id.value)run(()=>request('/clinic/'+target,{method:'DELETE'}),()=>uni.navigateBack())}})
}
function removeAnswer(reply){
    if(!active||!sameAccount()||busy.value||loading.value||!questionReady.value||reply.author.id!==selfId.value||!displayedAnswers.value.some(row=>row.id===reply.id))return
    const ticket=revision,target=id.value
    uni.showModal({title:'删除回答',content:'确认删除这条回答吗？',success:r=>{
        if(r.confirm&&current(ticket)&&target===id.value)run(async operation=>{await request('/clinic/'+target+'/answers/'+reply.id,{method:'DELETE'});if(!current(operation)||target!==id.value)return;return request('/clinic/'+target)},data=>{if(data){applyQuestion(data);focusId.value=0;focusNote.value=''}})
    }})
}
function openPerson(uid){if(active&&sameAccount()&&!busy.value&&uid!==selfId.value)uni.navigateTo({url:'/pages/match-making/group-detail?id='+uid})}
function speed(){uni.createVideoContext('question-clip').playbackRate(slow.value?0.5:1)}
function step(delta){
// #ifdef H5
const root=clipRef.value?.$el||clipRef.value;const video=root?.tagName==='VIDEO'?root:root?.querySelector?.('video');if(video){video.pause();video.currentTime=Math.max(0,Math.min(video.duration||0,video.currentTime+delta));return}
// #endif
uni.showToast({title:'请暂停后拖动视频进度条查看动作',icon:'none'})
}
</script>
<style scoped>
.page{min-height:100vh;padding:26rpx;background:#121212;color:white;box-sizing:border-box}.title{display:block;font-size:40rpx;color:#ccff00;font-weight:bold}.name{display:block;font-size:32rpx;font-weight:bold;line-height:1.5}.note{display:block;font-size:25rpx;line-height:1.7;color:#aaa;margin:14rpx 0;white-space:pre-wrap;word-break:break-word}.body{display:block;font-size:28rpx;line-height:1.7;white-space:pre-wrap;word-break:break-word}.card{background:#222;border-radius:18rpx;padding:24rpx;margin:24rpx 0}.answer{border-bottom:1rpx solid #444;padding:18rpx 0}.answer.focused{background:rgba(204,255,0,.08);outline:2rpx solid #ccff00;padding:20rpx}.accent{display:block;color:#ccff00;font-size:24rpx;line-height:1.7}.row{display:flex;flex-wrap:wrap;gap:10rpx}.row button{flex:1;min-width:140rpx;padding:10rpx;font-size:23rpx}button{background:#333;color:white;font-size:25rpx;border-radius:12rpx;margin:18rpx 0;white-space:normal}button[disabled]{opacity:.5}.primary{background:#ccff00;color:#121212}video{width:100%;height:400rpx;margin:20rpx 0;background:#050505}input,textarea{background:#303030;border-radius:12rpx;font-size:28rpx;padding:20rpx;color:white;width:100%;box-sizing:border-box;margin-bottom:20rpx}input{height:90rpx}textarea{height:240rpx}
</style>
