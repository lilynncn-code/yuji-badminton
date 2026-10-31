<template><view class="page">
<text class="title">{{ $tr("今日基础练习") }}</text><text class="note">{{ $tr("按北京时间安排；自己练习并填写次数，计时不判断动作是否标准，也不代替学习关卡。") }}</text>
<view v-if="error" class="card"><text>{{ $tr(error) }}</text><button :disabled="loading||saving" @click="load">{{ $tr("重新读取安排") }}</button></view>
<text v-if="loading" class="note">{{ $tr("正在读取今日安排…") }}</text>
<text v-if="saving" class="note">{{ $tr("正在确认本组保存结果，请稍候…") }}</text><text v-if="saveNotice" class="note">{{ $tr(saveNotice) }}</text><text v-if="draftError" class="error">{{ $tr(draftError) }}</text>
<view v-if="plan">
<text v-if="!ready&&!loading&&!saving" class="note">{{ $tr("安排尚未读清，请重新读取后继续。") }}</text>
<text class="summary">{{ $tr("{0} · 共 {1} 分 {2} 秒 · 已保存 {3}/{4} 组", [plan.day, Math.floor(plan.total_seconds/60), plan.total_seconds%60, completedCount, plan.steps.length]) }}</text>
<view v-for="step in plan.steps" :key="step.index" class="step-row" :class="{done:step.completed,current:step.index===current?.index}"><text>{{ $tr("{0} {1}", [step.completed?'✓':step.index+1, step.title]) }}</text><text>{{ $tr(step.completed?`已保存 ${step.actual_reps} 次`:`${step.seconds} 秒 · ${step.reps} 次`) }}</text></view>
<view v-if="current" class="card practice">
<text class="step-title">{{ $tr("第 {0} 组 · {1}", [current.index+1, current.title]) }}</text><text v-for="(line,index) in current.instructions" :key="index" class="instruction">{{ $tr("{0}. {1}", [index+1, line]) }}</text>
<text class="clock">{{ $tr(formatDuration(elapsed)) }}</text><text class="note">{{ $tr("本组目标 {0}{1}", [formatDuration(current.seconds), elapsed>=current.seconds?'，计时已到；填写实际次数后保存。':'，离开页面会暂停。']) }}</text>
<view class="actions"><button :disabled="loading||saving||confirming||!ready" @click="toggle">{{ $tr(running?'暂停':elapsed?'继续练习':'开始本组') }}</button><button :disabled="loading||saving||confirming||!ready||!elapsed" @click="restart">{{ $tr("本组重新计时") }}</button></view>
<view class="reps"><text>{{ $tr("实际完成次数") }}</text><input v-model="reps" type="number" maxlength="4" :disabled="saving||loading||confirming||!ready" :placeholder='$tr("练习后填写")' /></view>
<button class="primary" :disabled="saving||loading||confirming||!ready||running||elapsed<current.seconds" @click="save">{{ $tr(saving?'正在保存…':'保存本组并继续') }}</button><text v-if="saveError" class="error">{{ $tr(saveError) }}</text>
</view>
<view v-else class="card"><text class="step-title">{{ $tr("今天的四组练习都已保存") }}</text><text class="note">{{ $tr("每组都有独立训练记录，可到训练历史查看。明天会按新的日期安排，学习关卡可以继续练习。") }}</text><button @click="openHistory">{{ $tr("查看训练记录") }}</button></view>
</view></view></template>
<script setup>
import {ref,computed,watch} from 'vue'
import {onShow,onHide,onUnload} from '@dcloudio/uni-app'
import {request} from '../../utils/request'
import {createPracticeTimer} from '../../utils/practice-timer'
import {getAuthToken} from '../../utils/auth'
const plan=ref(null),loading=ref(false),saving=ref(false),error=ref(''),saveError=ref(''),elapsed=ref(0),running=ref(false),reps=ref('')
const ready=ref(false),confirming=ref(false),draftError=ref(''),saveNotice=ref('')
const current=computed(()=>plan.value?.steps.find(step=>!step.completed))
const completedCount=computed(()=>plan.value?.steps.filter(step=>step.completed).length||0)
const timer=createPracticeTimer()
let poll=null,generation=0,active=false,owner='',session='',confirmation=0,suppress=false,checkedDay=''
const memory=new Map(),pendingSaves=new Map()
const userId=()=>String(uni.getStorageSync('track-user')?.id||'')
const sameAccount=()=>owner===userId()&&session===getAuthToken()&&Boolean(session)
const currentPage=ticket=>active&&sameAccount()&&ticket===generation
const today=()=>new Date(Date.now()+8*3600000).toISOString().slice(0,10)
function draftKey(){return `daily-practice-${owner}-${plan.value?.day||''}`}
function remember(){
    if(!owner||!current.value)return
    const key=draftKey(),data={index:current.value.index,milliseconds:Math.min(3600000,timer.milliseconds()),reps:reps.value}
    memory.set(key,data)
    try{uni.setStorageSync(key,data);draftError.value=''}catch{draftError.value='本机未能保留计时和次数，当前页面仍保留；关闭应用后可能无法找回，请检查可用空间。'}
}
watch(reps,()=>{if(!suppress&&active&&sameAccount()&&ready.value)remember()},{flush:'sync'})
function pause(){timer.pause();timer.restore(timer.milliseconds());elapsed.value=timer.seconds();running.value=false;clearInterval(poll);poll=null;remember()}
function leave(){pause();active=false;generation++;confirmation++;confirming.value=false;loading.value=false;ready.value=false}
onShow(()=>{
    generation++;confirmation++;confirming.value=false;loading.value=false;active=true;ready.value=false
    const next=userId()
    if(owner!==next||session!==getAuthToken()){
        clearInterval(poll);poll=null;timer.restore();plan.value=null;elapsed.value=0;running.value=false;suppress=true;reps.value='';suppress=false
        error.value='';saveError.value='';draftError.value='';saveNotice.value=''
    }
    owner=next;session=getAuthToken();saving.value=pendingSaves.has(owner)
    if(!session){uni.reLaunch({url:'/pages/auth/login'});return}
    if(!saving.value)load()
});onHide(leave);onUnload(leave)
function restoreProgress(){
    const key=draftKey();let draft=memory.get(key)
    if(!memory.has(key)){try{draft=uni.getStorageSync(key)}catch{draftError.value='本机计时暂时无法读取，请检查可用空间；当前安排仍可使用。'}}
    suppress=true;timer.restore();elapsed.value=0;reps.value=''
    if(current.value&&draft?.index===current.value.index){timer.restore(draft.milliseconds);elapsed.value=timer.seconds();reps.value=String(draft.reps||'')}
    else{
        memory.set(key,null)
        try{uni.removeStorageSync(key)}catch{draftError.value='旧的本机计时未能清理；已保存的训练记录仍保留。'}
    }
    suppress=false
}
async function load(){
    if(!active||!sameAccount()||loading.value||saving.value||confirming.value)return
    if(ready.value)pause()
    const ticket=++generation;loading.value=true;ready.value=false;error.value=''
    try{
        const next=await request('/training/daily')
        if(!currentPage(ticket))return
        plan.value=next;checkedDay=today();restoreProgress();saveError.value='';ready.value=true;if(saveNotice.value)saveNotice.value='本组已保存'
    }catch(e){if(currentPage(ticket)){error.value=e.message;if(saveNotice.value)saveNotice.value='本组已保存；最新安排未读到，请重新读取'}}finally{if(currentPage(ticket))loading.value=false}
}
function validDay(){
    if(plan.value&&checkedDay===today())return true
    pause();ready.value=false;error.value='日期已变化，请重新读取今日安排';return false
}
function tick(){
    if(!active||!sameAccount()||!ready.value||!current.value){pause();return}
    if(!validDay())return
    const previous=elapsed.value;elapsed.value=Math.min(3600,timer.seconds());if(elapsed.value!==previous)remember()
    if((previous<current.value.seconds&&elapsed.value>=current.value.seconds)||elapsed.value>=3600)pause()
}
function toggle(){
    if(!active||!sameAccount()||!ready.value||loading.value||saving.value||confirming.value||!current.value||!validDay())return
    if(running.value){pause();return}
    if(elapsed.value>=3600){saveError.value='已计时一小时，请保存本组或重新计时';return}
    saveNotice.value='';timer.start();running.value=true;clearInterval(poll);poll=setInterval(tick,250)
}
function restart(){
    if(!active||!sameAccount()||!ready.value||loading.value||saving.value||confirming.value||!current.value||!elapsed.value||!validDay())return
    pause();const ticket=generation,operation=++confirmation,key=draftKey(),index=current.value.index,before=JSON.stringify(memory.get(key));confirming.value=true
    const finish=confirm=>{
        if(operation!==confirmation)return
        confirming.value=false
        if(!confirm||!currentPage(ticket)||saving.value||!ready.value||key!==draftKey()||index!==current.value?.index||!validDay())return
        if(JSON.stringify(memory.get(key))!==before){saveError.value='本组填写内容已变化，请重新确认';return}
        timer.restore();elapsed.value=0;reps.value='';saveError.value='';saveNotice.value='';remember()
    }
    try{uni.showModal({title:'本组重新计时',content:'只清除本组尚未保存的计时和次数，前面已保存的练习保留。',success:r=>finish(r.confirm),fail:()=>finish(false)})}catch{finish(false)}
}
async function save(){
    if(!active||!sameAccount()||!ready.value||!current.value||running.value||loading.value||saving.value||confirming.value||!validDay())return
    const count=Number(reps.value),step=current.value
    if(!Number.isInteger(count)||count<step.reps||count>1000){saveError.value=`请填写${step.reps}至1000之间的实际次数；次数不够可以继续练习。`;return}
    if(elapsed.value<step.seconds)return
    pause();saving.value=true;saveError.value='';saveNotice.value='';const ticket=generation,uid=owner,day=plan.value.day,job={}
    pendingSaves.set(uid,job)
    let confirmed=false
    try{
        await request(`/training/daily/${day}/${step.index}`,{method:'POST',data:{duration_seconds:elapsed.value,reps:count}})
        confirmed=true
        if(currentPage(ticket)){saveNotice.value='本组已保存，正在读取最新安排';uni.showToast({title:'本组已保存',icon:'none'})}
    }catch(e){if(currentPage(ticket)){saveError.value=e.message;if(e.status===409){ready.value=false;error.value='日期或安排已变化，请重新读取后继续'}}}
    finally{
        if(pendingSaves.get(uid)===job)pendingSaves.delete(uid)
        if(owner===uid){saving.value=pendingSaves.has(uid);if(confirmed)saveNotice.value='本组已保存，正在读取最新安排';if(active&&sameAccount()&&(confirmed||ticket!==generation))await load()}
    }
}
function formatDuration(value){return `${String(Math.floor(value/60)).padStart(2,'0')}:${String(value%60).padStart(2,'0')}`}
function openHistory(){if(active&&sameAccount())uni.navigateTo({url:'/pages/ai-coach/history'})}
</script>
<style scoped>.page{min-height:100vh;padding:28rpx 24rpx calc(40rpx + env(safe-area-inset-bottom));background:#121212;color:#fff;box-sizing:border-box}.title{display:block;color:#cf0;font-size:38rpx;font-weight:bold}.note,.instruction{display:block;color:#aaa;font-size:25rpx;line-height:1.7;margin:16rpx 0;white-space:pre-wrap;word-break:break-word}.summary{display:block;font-size:27rpx;margin:28rpx 0}.step-row{display:flex;justify-content:space-between;gap:16rpx;padding:22rpx 16rpx;border-bottom:1rpx solid #333;font-size:25rpx}.step-row text:last-child{color:#aaa;flex-shrink:0}.done{color:#aaa}.current{color:#cf0;background:#242a16}.card{margin-top:28rpx;padding:28rpx 24rpx;background:#222;border-radius:18rpx}.step-title{display:block;font-size:30rpx;font-weight:bold}.instruction{color:#ddd}.clock{display:block;font-size:72rpx;text-align:center;color:#cf0;margin-top:28rpx;font-weight:bold;font-variant-numeric:tabular-nums}.actions{display:flex;gap:16rpx}.actions button{flex:1}.reps{display:flex;align-items:center;justify-content:space-between;gap:20rpx;font-size:26rpx;margin:24rpx 0}.reps input{min-width:0;width:220rpx;height:64rpx;line-height:64rpx;padding:0 16rpx;box-sizing:border-box;background:#151515;border-radius:12rpx;color:#fff}button{margin-top:20rpx;background:#333;color:#fff;font-size:26rpx;white-space:normal}.primary{background:#cf0;color:#121212;font-weight:bold}.primary[disabled]{background:#3b4522;color:#999}.error{display:block;color:#ffba8f;font-size:25rpx;line-height:1.6;margin-top:18rpx}</style>
