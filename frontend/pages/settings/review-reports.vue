<template>
    <view class="page">
        <text class="title">{{ $tr("处理举报") }}</text>
        <text class="note">{{ $tr("逐条核查当时内容与当前内容，再填写处理依据。与本人有关的举报交由其他处理人员核查。") }}</text>
        <view class="tabs"><button :class="{active:state==='pending'}" :disabled="saving||confirming" @click="changeState('pending')">{{ $tr("等待处理") }}</button><button :class="{active:state==='resolved'}" :disabled="saving||confirming" @click="changeState('resolved')">{{ $tr("已处理") }}</button></view>
        <button :disabled="loading||saving||confirming" @click="load()">{{ $tr("刷新列表") }}</button>
        <text v-if="error" class="error">{{ $tr(error) }}</text>
        <button v-if="error&&allowed" :disabled="loading||saving" @click="load(failedMore)">{{ $tr("重新读取") }}</button>
        <text v-if="loading&&!items.length" class="note">{{ $tr("正在读取…") }}</text>
        <text v-else-if="!items.length&&!error" class="note">{{ $tr(state==='pending'?'暂无等待处理的举报':'暂无已处理记录') }}</text>
        <view v-for="item in items" :key="item.id" class="card">
            <text class="heading">{{ $tr("编号 {0} · {1} {2}", [item.id, typeName(item.target_type), item.target_id]) }}</text>
            <text class="note">{{ $tr("提交于 {0}", [formatTimeLabel(utcTime(item.created_at))]) }}</text>
            <text class="label">{{ $tr("举报原因") }}</text><text class="content">{{ item.reason }}</text>
            <text class="label">{{ $tr("提交时的内容") }}</text><text class="content">{{ item.snapshot || $tr('未保留文字') }}</text>
            <text class="label">{{ $tr("当前内容") }}</text><text class="content">{{ item.target_available ? item.current_content : $tr('内容已不存在或已被移除') }}</text>
            <template v-if="item.status==='pending'&&item.can_handle">
                <text v-if="item.target_type==='user'" class="note">{{ $tr("账号举报可登记核查结果；此入口不会停用或删除账号。") }}</text>
                <text class="label">{{ $tr("处理方式") }}</text>
                <view class="choices"><button v-for="choice in choices(item)" :key="choice.value" :class="{active:drafts[item.id]?.action===choice.value}" :disabled="saving||confirming||!ready" @click="drafts[item.id].action=choice.value">{{ $tr(choice.label) }}</button></view>
                <textarea v-model="drafts[item.id].result" :disabled="saving||confirming||!ready" maxlength="500" :placeholder='$tr("填写核查依据及结果，将向举报人展示（2至500字）")' />
                <text v-if="saveErrors[item.id]" class="error">{{ $tr(saveErrors[item.id]) }}</text>
                <button class="submit" :disabled="saving||loading||confirming||!ready" @click="submit(item)">{{ $tr(saving===item.id?'正在保存…':confirming===item.id?'等待确认…':'确认处理') }}</button>
            </template>
            <text v-else-if="item.status==='pending'" class="note">{{ $tr(item.handle_note) }}</text>
            <template v-else><text class="label">{{ $tr(actionName(item.action)) }}</text><text class="content">{{ item.result }}</text><text class="note">{{ $tr(formatTimeLabel(utcTime(item.resolved_at))) }}</text></template>
        </view>
        <button v-if="hasMore&&allowed" :disabled="loading||saving" @click="load(true)">{{ $tr("更早的记录") }}</button>
        <text v-else-if="items.length&&!error" class="note">{{ $tr("已显示全部记录") }}</text>
    </view>
</template>
<script setup>
import {ref} from 'vue'
import {onShow,onHide,onUnload} from '@dcloudio/uni-app'
import {request,utcTime} from '../../utils/request'
import {getUser,formatTimeLabel} from '../../utils/store'
import {getAuthToken} from '../../utils/auth'
const items=ref([]),state=ref('pending'),loading=ref(false),saving=ref(0),error=ref(''),allowed=ref(true),hasMore=ref(false),failedMore=ref(false),drafts=ref({}),saveErrors=ref({})
const ready=ref(false),confirming=ref(0)
let generation=0,owner='',active=false,confirmOperation=0,pendingSave=null
const account=()=>`${getUser().id||''}:${getAuthToken()}`
const sameAccount=()=>active&&owner===account()&&Boolean(getAuthToken())
function typeName(kind){return {user:'球友',post:'动态',comment:'留言'}[kind]||'内容'}
function actionName(action){return {no_violation:'核查后未发现违规',remove_content:'已移除内容',already_unavailable:'内容已不存在',record_result:'已登记核查结果'}[action]||'处理结果'}
function choices(item){return item.target_available?[{value:'no_violation',label:'未发现违规'},...(item.can_remove?[{value:'remove_content',label:'移除违规内容'}]:[]),...(item.target_type==='user'?[{value:'record_result',label:'登记核查结果'}]:[])]:[{value:'already_unavailable',label:'内容已不存在'}]}
function current(ticket){return sameAccount()&&ticket===generation}
function denied(){items.value=[];drafts.value={};allowed.value=false;ready.value=false;hasMore.value=false}
async function load(more=false){
    if(!sameAccount()||loading.value||saving.value||confirming.value)return
    const ticket=++generation;loading.value=true;error.value='';failedMore.value=more
    if(!more)ready.value=false
    const before=more?items.value[items.value.length-1]?.id:0
    try{
        const data=await request('/social/review/reports?state='+state.value+(before?'&before_id='+before:''))
        if(!current(ticket))return
        allowed.value=true
        const known=new Set(items.value.map(r=>r.id))
        items.value=more?[...items.value,...data.items.filter(r=>!known.has(r.id))]:data.items
        for(const item of data.items){
            const old=drafts.value[item.id]||{result:''}
            const options=choices(item)
            drafts.value[item.id]={result:old.result,action:options.some(o=>o.value===old.action)?old.action:options[0].value}
        }
        hasMore.value=data.has_more;ready.value=true
    }catch(e){if(current(ticket)){error.value=e.message;if(e.status===403)denied()}}
    finally{if(current(ticket))loading.value=false}
}
function changeState(value){
    if(!sameAccount()||saving.value||confirming.value||state.value===value)return
    generation++;loading.value=false;state.value=value;items.value=[];hasMore.value=false;load()
}
async function submit(item){
    if(!sameAccount()||!ready.value||saving.value||loading.value||confirming.value||!item.can_handle||!items.value.includes(item))return
    const draft=drafts.value[item.id],result=String(draft?.result||'').trim(),action=draft?.action
    if(result.length<2||result.length>500){saveErrors.value[item.id]='请填写2至500字的核查依据和结果';return}
    if(!choices(item).some(c=>c.value===action)){saveErrors.value[item.id]='内容状态已变化，请刷新后重试';return}
    const ticket=generation,confirmation=++confirmOperation
    confirming.value=item.id
    const confirm=await new Promise(resolve=>{try{uni.showModal({title:'确认处理这条举报',content:action==='remove_content'?'确认移除这条内容？相关留言或提醒也会停止显示。处理结果将向举报人展示。':'确认提交处理结果？举报人可以在自己的记录中查看。',success:r=>resolve(r.confirm),fail:()=>resolve(false)})}catch(e){resolve(false)}})
    if(confirmation!==confirmOperation)return
    confirming.value=0
    if(!confirm||!current(ticket)||saving.value||!ready.value||!item.can_handle||!items.value.includes(item))return
    if(drafts.value[item.id]?.action!==action||String(drafts.value[item.id]?.result||'').trim()!==result){saveErrors.value[item.id]='填写内容已变化，请重新确认';return}
    const job={owner,id:item.id};pendingSave=job
    saving.value=item.id;saveErrors.value[item.id]=''
    try{
        const saved=await request('/social/review/reports/'+item.id,{method:'POST',data:{action,result}})
        if(!current(ticket))return
        Object.assign(item,saved,{can_handle:false})
        if(action==='remove_content'){item.current_content='';item.target_available=false}
        delete drafts.value[item.id]
        uni.showToast({title:'处理结果已保存',icon:'none'})
    }catch(e){if(current(ticket)){saveErrors.value[item.id]=e.message;if(e.status===403){error.value=e.message;denied()}}}
    finally{
        if(pendingSave===job){
            pendingSave=null
            if(owner===job.owner){saving.value=0;if(sameAccount()&&ticket!==generation)load()}
        }
    }
}
function leave(){active=false;generation++;confirmOperation++;confirming.value=0;loading.value=false;ready.value=false}
onShow(()=>{
    generation++;confirmOperation++;confirming.value=0;loading.value=false;ready.value=false
    if(owner!==account()){items.value=[];drafts.value={};saveErrors.value={};hasMore.value=false;state.value='pending';error.value=''}
    owner=account();active=true;allowed.value=true;saving.value=pendingSave?.owner===owner?pendingSave.id:0
    if(!getAuthToken()){uni.reLaunch({url:'/pages/auth/login'});return}
    load()
})
onHide(leave);onUnload(leave)
</script>
<style scoped>
.page{min-height:100vh;padding:28rpx;background:#121212;color:white;box-sizing:border-box}.title{display:block;color:#ccff00;font-size:38rpx;font-weight:bold}.note,.error{display:block;margin-top:16rpx;font-size:25rpx;line-height:1.7;white-space:pre-wrap;word-break:break-word}.note{color:#aaa}.error{color:#ffb5a8}.card{margin-top:28rpx;padding:24rpx;background:#222;border-radius:16rpx}.heading,.label{display:block;font-size:28rpx;font-weight:bold}.label{margin-top:24rpx;color:#ddd}.content{display:block;margin-top:12rpx;white-space:pre-wrap;word-break:break-word;font-size:28rpx;line-height:1.7}.tabs,.choices{display:flex;flex-wrap:wrap;gap:12rpx}.tabs{margin-top:20rpx}button{margin:20rpx 0 0;padding:8rpx 20rpx;background:#333;color:white;font-size:26rpx;white-space:normal}button.active,.submit{background:#ccff00;color:#111}button[disabled]{opacity:.5}textarea{margin-top:22rpx;padding:20rpx;width:100%;min-height:180rpx;background:#151515;border:1px solid #555;border-radius:12rpx;color:white;box-sizing:border-box}
</style>
