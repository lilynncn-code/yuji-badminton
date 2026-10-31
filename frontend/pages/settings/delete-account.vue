<template><view class="page"><text class="title">{{ $tr("注销账号") }}</text>
<view class="card"><text class="heading">{{ $tr("注销后无法恢复，请先保存需要的内容") }}</text>
<text>{{ $tr("会删除账号、手机号、个人资料、训练记录和视频、动态、留言、技术诊所中的提问回答、收藏、关注及屏蔽记录。") }}</text>
<text>{{ $tr("与你有关的聊天会话会从双方列表删除，里面双方发送的文字、图片和语音会一并删除。对方已经另行保存的副本无法收回。") }}</text>
<text>{{ $tr("你发起的球局及参与名单会删除；参加其他球局的报名会退出。其他人的独立内容和账号保留。") }}</text>
<text>{{ $tr("用于处理他人举报的记录会保留处理状态，已删除内容的副本会清除。你可以选择退出登录来保留资料。") }}</text></view>
<view class="card"><text>{{ $tr("当前绑定 {0}", [maskedPhone]) }}</text>
<input v-model="password" :disabled="busy" password maxlength="50" :placeholder='$tr("当前登录密码")'/>
<button :disabled="busy||seconds>0" @click="sendCode">{{ $tr(seconds>0?`${seconds}秒后重发`:'发送注销验证码') }}</button>
<input v-model="code" :disabled="busy" maxlength="6" type="number" :placeholder='$tr("手机收到的6位验证码")'/>
<input v-model="confirmation" :disabled="busy" maxlength="6" :placeholder='$tr("输入“确认注销”")'/>
<button class="danger" :disabled="busy||!confirmationValid||!password||code.length!==6" @click="confirmDelete">{{ $tr(busy?'正在处理…':'注销并永久删除资料') }}</button>
</view><text class="note">{{ $tr(notice) }}</text><text class="note">{{ $tr("提交后若网络中断，请重新登录确认账号是否仍存在。不要反复提交。无法接收当前号码短信时，请先恢复收取能力。") }}</text>
</view></template>
<script setup>
import { ref,computed } from 'vue'
import { onShow,onHide,onUnload } from '@dcloudio/uni-app'
import { getUser } from '../../utils/store'
import { getAuthToken } from '../../utils/auth'
import { sendDeletionCode,deleteAccount } from '../../utils/account-api'
const password=ref(''),code=ref(''),confirmation=ref(''),busy=ref(false),notice=ref(''),phone=ref('')
const maskedPhone=computed(()=>phone.value.replace(/^(\d{3})\d{4}(\d{4})$/,'$1****$2'))
const confirmationValid=computed(()=>['确认注销','DELETE'].includes(confirmation.value))
const now=ref(Date.now()),until=ref(0),seconds=computed(()=>Math.max(0,Math.ceil((until.value-now.value)/1000)))
let timer=null,active=false,owner='',operation=0,pageVisit=0,completed=false
const account=()=>`${getUser().id||''}:${getAuthToken()}`
onShow(()=>{
    active=true;pageVisit++
    if(completed&&!getAuthToken()){uni.reLaunch({url:'/pages/auth/login'});return}
    if(owner!==account()){
        owner=account();operation++;busy.value=false;completed=false;phone.value=getUser().phone||''
        password.value='';code.value='';confirmation.value='';notice.value='';until.value=0
    }
    now.value=Date.now();clearInterval(timer);timer=setInterval(()=>now.value=Date.now(),1000)
})
function hide(){active=false;pageVisit++;clearInterval(timer);password.value='';code.value='';confirmation.value=''}
onHide(hide);onUnload(hide)
function current(op,who){return operation===op&&owner===who&&account()===who}
function fail(e){notice.value=e.message||'操作没有完成，请重试';if(active)uni.showToast({title:notice.value,icon:'none'})}
async function sendCode(){
    if(!active||owner!==account()||busy.value||seconds.value)return
    const op=++operation,who=owner;busy.value=true
    try{const data=await sendDeletionCode();if(current(op,who)){notice.value=data.message;until.value=Date.now()+60000;now.value=Date.now()}}
    catch(e){if(current(op,who))fail(e)}finally{if(operation===op&&owner===who)busy.value=false}
}
function confirmDelete(){
    if(!active||owner!==account()||busy.value||!confirmationValid.value||!password.value||!/^[0-9]{6}$/.test(code.value))return
    const visit=pageVisit,who=owner,typedConfirmation=confirmation.value,payload={password:password.value,sms_code:code.value,confirmation:'确认注销'}
    uni.showModal({title:'永久注销账号',content:'确认永久删除资料、双方聊天会话、你发起的球局及其他上述内容？这一步无法撤销。',confirmText:'确认注销',success:async r=>{
        if(!r.confirm||!active||visit!==pageVisit||owner!==who||account()!==who||busy.value)return
        if(password.value!==payload.password||code.value!==payload.sms_code||confirmation.value!==typedConfirmation){fail(new Error('填写内容已变化，请重新确认'));return}
        const op=++operation;busy.value=true
        try{
            const data=await deleteAccount(payload)
            if(operation!==op||owner!==who||getAuthToken())return
            completed=true;password.value='';code.value='';confirmation.value='';notice.value=data.message
            if(active){uni.showToast({title:'账号已注销',icon:'none'});uni.reLaunch({url:'/pages/auth/login'})}
        }catch(e){if(current(op,who))fail(e)}finally{if(operation===op&&owner===who)busy.value=false}
    }})
}
</script>
<style scoped>.page{min-height:100vh;padding:30rpx;background:#121212;color:#fff;box-sizing:border-box}.title{font-size:38rpx;color:#cf0;font-weight:bold}.card{padding:24rpx;background:#222;border-radius:18rpx;margin:24rpx 0}.card text{display:block;font-size:26rpx;line-height:1.8;margin-bottom:18rpx}.heading{font-weight:bold;color:#ffb8b8}input{height:88rpx;margin:18rpx 0;padding:0 18rpx;background:#303030;border-radius:12rpx;font-size:27rpx}button{font-size:26rpx;margin:18rpx 0;background:#353535;color:white;white-space:normal}.danger{background:#8f3030;color:white}.note{font-size:25rpx;line-height:1.7;color:#aaa;display:block;margin:20rpx 0}</style>
