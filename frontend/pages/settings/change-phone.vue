<template><view class="page"><text class="title">{{ $tr("更换手机号") }}</text><text class="note">{{ $tr("当前绑定 {0}。先验证当前密码与原手机号，再验证新手机号。完成后其他设备需要重新登录，训练和发布记录会保留。", [maskedPhone]) }}</text>
<view v-if="!changeId" class="card"><input v-model="form.new_phone" :disabled="busy" maxlength="11" type="number" :placeholder='$tr("新手机号")'/><input v-model="form.password" :disabled="busy" maxlength="50" password :placeholder='$tr("当前登录密码")'/><button :disabled="busy||oldSeconds>0" @click="sendOld">{{ $tr(oldSeconds>0?`${oldSeconds}秒后重发`:'给原手机号发送验证码') }}</button><input v-model="form.old_code" :disabled="busy" maxlength="6" type="number" :placeholder='$tr("原手机号收到的6位验证码")'/><button class="primary" :disabled="busy" @click="start">{{ $tr(busy?'验证中…':'验证并向新号码发送验证码') }}</button></view>
<view v-else class="card"><text class="name">{{ $tr("验证新手机号 {0}", [targetPhone]) }}</text><text class="note">{{ $tr("本次验证 {0} 秒后到期。", [remaining]) }}</text><input v-model="newCode" :disabled="busy" maxlength="6" type="number" :placeholder='$tr("新手机号收到的6位验证码")'/><button :disabled="busy||newSeconds>0||remaining<=0" @click="resend">{{ $tr(newSeconds>0?`${newSeconds}秒后重发`:'重新获取新号码验证码') }}</button><button class="primary" :disabled="busy||remaining<=0" @click="finish">{{ $tr(busy?'提交中…':'确认更换手机号') }}</button><button :disabled="busy" @click="restart">{{ $tr("取消本次验证，重新开始") }}</button></view>
<text v-if="notice" class="note">{{ $tr(notice) }}</text><text class="note">{{ $tr("如果提交后网络中断，可用用户名或新手机号重新登录确认。无法接收原手机号短信时，请先恢复原号码的接收能力，目前应用内尚无人工更换流程。") }}</text></view></template>
<script setup>
import { reactive,ref,computed } from 'vue'
import { onShow,onHide,onUnload } from '@dcloudio/uni-app'
import { getUser } from '../../utils/store'
import { getAuthToken } from '../../utils/auth'
import { sendOldPhoneCode,startPhoneChange,resendNewPhoneCode,finishPhoneChange,cancelPhoneChange } from '../../utils/account-api'
const phone=ref(''),busy=ref(false),notice=ref(''),changeId=ref(''),targetPhone=ref(''),newCode=ref('')
const form=reactive({new_phone:'',password:'',old_code:''})
const now=ref(Date.now()),oldUntil=ref(0),newUntil=ref(0),expires=ref(0)
let timer=null,active=false,owner='',operation=0
const account=()=>`${getUser().id||''}:${getAuthToken()}`
const maskedPhone=computed(()=>phone.value.replace(/^(\d{3})\d{4}(\d{4})$/,'$1****$2'))
const oldSeconds=computed(()=>Math.max(0,Math.ceil((oldUntil.value-now.value)/1000)))
const newSeconds=computed(()=>Math.max(0,Math.ceil((newUntil.value-now.value)/1000)))
const remaining=computed(()=>Math.max(0,Math.ceil((expires.value-now.value)/1000)))
onShow(()=>{
    active=true
    if(owner!==account()){
        owner=account();operation++;busy.value=false;phone.value=getUser().phone||''
        notice.value='';changeId.value='';targetPhone.value='';newCode.value=''
        Object.assign(form,{new_phone:'',password:'',old_code:''});oldUntil.value=0;newUntil.value=0;expires.value=0
    }
    now.value=Date.now();clearInterval(timer);timer=setInterval(()=>now.value=Date.now(),1000)
})
function hide(){active=false;clearInterval(timer);form.password='';form.old_code='';newCode.value=''}
onHide(hide);onUnload(hide)
function current(op,who){return operation===op&&owner===who&&account()===who}
function available(){return active&&owner===account()&&!busy.value}
function fail(error){notice.value=error.message||'操作没有完成，请重试';if(active)uni.showToast({title:notice.value,icon:'none'})}
async function perform(action,apply){
    if(!available())return
    const op=++operation,who=owner;busy.value=true
    try{const data=await action();if(current(op,who))apply(data)}
    catch(e){if(current(op,who))fail(e)}
    finally{if(operation===op&&owner===who)busy.value=false}
}
function sendOld(){
    if(oldSeconds.value)return
    return perform(sendOldPhoneCode,data=>{notice.value=data.message;oldUntil.value=Date.now()+60000;now.value=Date.now()})
}
function start(){
    if(!available())return
    if(!/^1[3-9][0-9]{9}$/.test(form.new_phone)||!form.password||! /^[0-9]{6}$/.test(form.old_code)){fail(new Error('请填写新手机号、当前密码和原手机号验证码'));return}
    if(form.new_phone===phone.value){fail(new Error('新手机号不能与原手机号相同'));return}
    const payload={...form}
    return perform(()=>startPhoneChange(payload),data=>{
        targetPhone.value=payload.new_phone;changeId.value=data.change_id;expires.value=new Date(data.expires_at).getTime()
        newUntil.value=Date.now()+60000;now.value=Date.now();notice.value=data.message;form.password='';form.old_code=''
    })
}
function resend(){
    if(newSeconds.value||remaining.value<=0||!changeId.value)return
    return perform(()=>resendNewPhoneCode(changeId.value),data=>{notice.value=data.message;newUntil.value=Date.now()+60000;now.value=Date.now()})
}
async function finish(){
    if(!available()||remaining.value<=0||!changeId.value)return
    if(!/^[0-9]{6}$/.test(newCode.value)){fail(new Error('请填写新手机号收到的6位验证码'));return}
    const op=++operation,who=owner,userId=getUser().id,target=targetPhone.value,id=changeId.value,code=newCode.value
    busy.value=true
    try{
        const data=await finishPhoneChange(id,code)
        if(operation!==op||owner!==who||getUser().id!==userId||getAuthToken()!==data.token)return
        owner=account();phone.value=target;changeId.value='';newCode.value='';targetPhone.value='';form.new_phone='';notice.value=data.message;busy.value=false
        if(active)uni.showToast({title:'手机号已更换',icon:'none'})
    }catch(e){if(current(op,who))fail(e)}
    finally{if(operation===op&&owner===who)busy.value=false}
}
function restart(){
    if(!changeId.value)return
    return perform(()=>cancelPhoneChange(changeId.value),()=>{changeId.value='';newCode.value='';targetPhone.value='';notice.value='已取消，请重新验证原手机号'})
}
</script>
<style scoped>.page{min-height:100vh;background:#121212;padding:30rpx;color:#fff;box-sizing:border-box}.title{font-size:38rpx;font-weight:bold;color:#cf0;display:block}.note{font-size:25rpx;line-height:1.7;color:#aaa;display:block;margin:20rpx 0;white-space:pre-wrap}.name{font-size:29rpx;font-weight:bold;display:block}.card{padding:24rpx;background:#222;border-radius:18rpx;margin:24rpx 0}input{height:88rpx;margin:18rpx 0;padding:0 18rpx;background:#303030;border-radius:12rpx;font-size:27rpx}button{font-size:26rpx;margin:18rpx 0;background:#353535;color:white;white-space:normal}.primary{background:#cf0;color:#111}</style>
