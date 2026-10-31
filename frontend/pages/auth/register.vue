<template>
	<view class="page" :style="{ paddingTop: statusBarHeight + 'px', '--top-safe-height': statusBarHeight + 'px' }">
		<view class="nav-row">
			<view class="back-btn" @click="goBack">{{ $tr("‹") }}</view>
			<text class="nav-title">{{ $tr("注册") }}</text>
			<view class="nav-space"></view>
		</view>
		<scroll-view class="content" scroll-y>
			<text class="title">{{ $tr("创建账号") }}</text>
			<text class="subtitle">{{ $tr("注册不需要邮箱，只用用户名、手机号和密码。") }}</text>

			<input class="input" v-model="form.username" :disabled="loading" maxlength="50" :placeholder='$tr("用户名，2至50个字")' placeholder-class="placeholder" />
			<input class="input" v-model="form.phone" :disabled="loading" maxlength="11" type="number" :placeholder='$tr("手机号")' placeholder-class="placeholder" />
			<view class="code-row">
				<input class="input code-input" v-model="form.sms_code" :disabled="loading" type="number" maxlength="6" :placeholder='$tr("6 位验证码")' placeholder-class="placeholder" />
				<button class="code-btn" :disabled="loading || smsSeconds > 0" @click="sendCode">
					{{ $tr(working==='sms'?'发送中…':(smsSeconds > 0 ? smsSeconds + '秒后重发' : '获取验证码')) }}
				</button>
			</view>
			<input class="input" v-model="form.name" :disabled="loading" maxlength="50" :placeholder='$tr("昵称，可不填")' placeholder-class="placeholder" />
			<input class="input" v-model="form.password" :disabled="loading" maxlength="50" password :placeholder='$tr("密码，6至50位，含字母和数字")' placeholder-class="placeholder" />

			<view style="margin:24rpx 0;color:#aaa;font-size:24rpx;line-height:1.8"><text @click="toggleAgreement">{{ $tr("{0} 我已阅读并同意", [agreed ? '☑' : '☐']) }}</text><text style="color:#cf0" @click="openLegal('/pages/agreement/agreement')">{{ $tr("用户协议") }}</text><text>{{ $tr("和") }}</text><text style="color:#cf0" @click="openLegal('/pages/privacy/privacy')">{{ $tr("隐私政策") }}</text></view>
            <text v-if="notice" class="form-notice">{{ $tr(notice) }}</text>
            <text class="form-help">{{ $tr("提交后若连接中断，请先用刚填写的账号登录确认。离开页面会清空密码和验证码。") }}</text>
            <button class="primary-btn" :disabled="loading" @click="submit">{{ $tr(working==='register' ? '注册中...' : '注册并进入') }}</button>
			<view class="plain-btn" @click="goLogin">{{ $tr("已有账号，去登录") }}</view>
		</scroll-view>
	</view>
</template>

<script setup>
import { reactive, ref, toRef, watch } from 'vue'
import { registerWithSms, sendSms } from '../../utils/auth'
import { useAuthPage, useSmsCooldown, validatePhone, validatePassword } from '../../utils/auth-page'
import { getTopSafeAreaHeight } from '../../utils/safe-area'
const statusBarHeight=getTopSafeAreaHeight(),agreed=ref(false)
const form=reactive({username:'',phone:'',name:'',password:'',sms_code:''})
const page=useAuthPage({clearSecrets:()=>{form.password='';form.sms_code=''},onAccountChange:()=>{Object.assign(form,{username:'',phone:'',name:''});agreed.value=false}})
const {loading,working,notice}=page
const {smsSeconds,remember}=useSmsCooldown(toRef(form,'phone'),'register')
watch(()=>form.phone,()=>{form.sms_code='';notice.value=''})
function checkForm(){
    if(!agreed.value)return '请先阅读并同意用户协议和隐私政策'
    if(!form.username.trim())return '请填写用户名'
    if(form.username.trim().length<2)return '用户名至少2个字'
    if(form.username.trim().length>50)return '用户名不能超过50个字'
    if(form.name.trim().length>50)return '昵称不能超过50个字'
    const invalid=validatePhone(form.phone.trim())||validatePassword(form.password)
    if(invalid)return invalid
    if(!/^[0-9]{6}$/.test(form.sms_code.trim()))return '请填写6位验证码'
    return ''
}
async function sendCode(){
    if(!page.canAct()||smsSeconds.value>0)return
    const phone=form.phone.trim(),invalid=validatePhone(phone)
    if(invalid){page.explain(invalid);return}
    return page.run('sms',async()=>{const result=await sendSms(phone,'register');remember(phone);return result},{success:result=>page.explain(`${result?.message||'验证码已发送'}（${phone.slice(0,3)}****${phone.slice(-4)}）`)})
}
async function submit(){
    if(!page.canAct())return
    const message=checkForm()
    if(message){page.explain(message);return}
    const payload={username:form.username.trim(),phone:form.phone.trim(),name:form.name.trim(),password:form.password,sms_code:form.sms_code.trim()}
    return page.run('register',options=>registerWithSms(payload,options),{message:'注册成功',clearOnSuccess:true,success:()=>uni.redirectTo({url:'/pages/onboarding/onboarding'})})
}
function goBack(){uni.navigateBack({fail:()=>uni.reLaunch({url:'/pages/auth/login'})})}
function goLogin(){uni.reLaunch({url:'/pages/auth/login'})}
function toggleAgreement(){if(page.canAct())agreed.value=!agreed.value}
function openLegal(url){if(page.canAct())uni.navigateTo({url})}
</script>

<style lang="scss" scoped>
.form-notice,.form-help{display:block;margin-top:20rpx;font-size:25rpx;line-height:1.6;white-space:pre-wrap}.form-notice{color:#ffd1b8}.form-help{color:#aaa}.code-btn[disabled]{opacity:.65}
.page { min-height: 100vh; background: #121212; color: #FFFFFF; }
.nav-row { height: 88rpx; padding: 0 24rpx; display: flex; align-items: center; justify-content: space-between; }
.back-btn, .nav-space { width: 64rpx; height: 64rpx; flex: 0 0 auto; }
.back-btn { margin: 0; padding: 0; border-radius: 50%; background: #1E1E1E; border: 1rpx solid #2C2C2E; color: #CCFF00; font-size: 46rpx; line-height: 1; display: flex; align-items: center; justify-content: center; text-align: center; }
.nav-title { font-size: 32rpx; font-weight: 900; }
.content { height: calc(100vh - 88rpx - var(--top-safe-height)); padding: 34rpx 32rpx calc(60rpx + env(safe-area-inset-bottom)); box-sizing: border-box; }
.title { display: block; color: #CCFF00; font-size: 52rpx; font-weight: 900; }
.subtitle { display: block; margin-top: 14rpx; color: #BDBDBD; font-size: 27rpx; line-height: 1.5; }
.input { width: 100%; height: 88rpx; margin-top: 20rpx; padding: 0 24rpx; border-radius: 14rpx; background: #1E1E1E; border: 1rpx solid #2C2C2E; color: #FFFFFF; font-size: 28rpx; box-sizing: border-box; }
.input:first-of-type { margin-top: 42rpx; }
.code-row { display: grid; grid-template-columns: minmax(0, 1fr) 240rpx; gap: 16rpx; align-items: stretch; margin-top: 20rpx; min-height: 88rpx; }
.code-row .code-input.input { width: 100%; height: 88rpx; margin-top: 0; align-self: center; }
.code-btn { width: 100%; min-height: 88rpx; margin: 0; padding: 8rpx 14rpx; border-radius: 14rpx; background: #2A2A2A; border: 1rpx solid #3A3A3A; color: #ceff0a; font-size: 24rpx; font-weight: 800; line-height: 1.22; text-align: center; box-sizing: border-box; display: flex; align-items: center; justify-content: center; align-self: stretch; }
.code-btn.disabled { opacity: .65; }
.placeholder { color: #777; }
.primary-btn { width: 100%; min-height: 88rpx; margin-top: 30rpx; padding: 10rpx 24rpx; border-radius: 999rpx; background: #CCFF00; color: #121212; font-size: 30rpx; line-height: 1.25; font-weight: 900; }
.primary-btn[disabled] { opacity: .7; }
.plain-btn { width: 100%; min-height: 76rpx; margin-top: 18rpx; padding: 8rpx 16rpx; border-radius: 14rpx; background: #1E1E1E; border: 1rpx solid #2C2C2E; color: #FFFFFF; font-size: 26rpx; line-height: 1.25; text-align: center; display: flex; align-items: center; justify-content: center; box-sizing: border-box; }

@media screen and (max-width: 430px) {
	.code-row { grid-template-columns: 1fr; gap: 12rpx; }
	.code-btn { min-height: 76rpx; font-size: 23rpx; }
}
</style>
