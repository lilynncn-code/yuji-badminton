<template>
	<view class="page" :style="{ paddingTop: statusBarHeight + 'px' }">
		<view class="nav-row">
			<view class="back-btn" @click="goBack">{{ $tr("‹") }}</view>
			<text class="nav-title">{{ $tr("忘记密码") }}</text>
			<view class="nav-space"></view>
		</view>
		<view class="content">
			<text class="title">{{ $tr("重设密码") }}</text>
			<text class="subtitle">{{ $tr("输入用户名或手机号，再填写注册时的手机号。") }}</text>

			<input class="input" v-model="form.account" :disabled="loading" maxlength="50" :placeholder='$tr("用户名或手机号")' placeholder-class="placeholder" />
			<input class="input" v-model="form.phone" :disabled="loading" maxlength="11" type="number" :placeholder='$tr("注册手机号")' placeholder-class="placeholder" />
			<view class="code-row">
				<input class="input code-input" v-model="form.sms_code" :disabled="loading" type="number" maxlength="6" :placeholder='$tr("6 位验证码")' placeholder-class="placeholder" />
				<button class="code-btn" :disabled="loading || smsSeconds > 0" @click="sendCode">
					{{ $tr(working==='sms'?'发送中…':(smsSeconds > 0 ? smsSeconds + '秒后重发' : '获取验证码')) }}
				</button>
			</view>
			<input class="input" v-model="form.new_password" :disabled="loading" maxlength="50" password :placeholder='$tr("新密码，6至50位，含字母和数字")' placeholder-class="placeholder" />

            <input class="input" v-model="form.confirm_password" :disabled="loading" maxlength="50" password :placeholder='$tr("再输入一次新密码")' placeholder-class="placeholder" />
            <text v-if="notice" class="form-notice">{{ $tr(notice) }}</text>
            <text class="form-help">{{ $tr("提交后若连接中断，请尝试用新密码登录确认。离开页面会清空密码和验证码。") }}</text>
			<button class="primary-btn" :disabled="loading" @click="submit">{{ $tr(working==='reset' ? '提交中...' : '重设并登录') }}</button>
		</view>
	</view>
</template>

<script setup>
import { reactive, toRef, watch } from 'vue'
import { isOnboardingComplete } from '../../utils/store'
import { resetPasswordBySms, sendSms } from '../../utils/auth'
import { useAuthPage, useSmsCooldown, validatePhone, validatePassword } from '../../utils/auth-page'
import { getTopSafeAreaHeight } from '../../utils/safe-area'
const statusBarHeight=getTopSafeAreaHeight()
const form=reactive({account:'',phone:'',new_password:'',confirm_password:'',sms_code:''})
const page=useAuthPage({clearSecrets:()=>{form.new_password='';form.confirm_password='';form.sms_code=''},onAccountChange:()=>{form.account='';form.phone=''}})
const {loading,working,notice}=page
const {smsSeconds,remember}=useSmsCooldown(toRef(form,'phone'),'reset_password')
watch(()=>form.phone,()=>{form.sms_code='';notice.value=''})
async function sendCode(){
    if(!page.canAct()||smsSeconds.value>0)return
    const phone=form.phone.trim(),invalid=validatePhone(phone)
    if(invalid){page.explain(invalid);return}
    return page.run('sms',async()=>{const result=await sendSms(phone,'reset_password');remember(phone);return result},{success:result=>page.explain(`${result?.message||'验证码已发送'}（${phone.slice(0,3)}****${phone.slice(-4)}）`)})
}
function checkForm(){
    if(!form.account.trim())return '请填写用户名或手机号'
    if(form.account.trim().length>50)return '用户名或手机号不能超过50个字'
    const invalid=validatePhone(form.phone.trim())||validatePassword(form.new_password,'新密码')
    if(invalid)return invalid
    if(form.new_password!==form.confirm_password)return '两次新密码不一致'
    if(!/^[0-9]{6}$/.test(form.sms_code.trim()))return '请填写6位验证码'
    return ''
}
async function submit(){
    if(!page.canAct())return
    const message=checkForm()
    if(message){page.explain(message);return}
    const payload={account:form.account.trim(),phone:form.phone.trim(),new_password:form.new_password,sms_code:form.sms_code.trim()}
    return page.run('reset',options=>resetPasswordBySms(payload,options),{message:'密码已重设',clearOnSuccess:true,success:()=>{
        if(isOnboardingComplete())uni.switchTab({url:'/pages/index/index'})
        else uni.redirectTo({url:'/pages/onboarding/onboarding'})
    }})
}
function goBack(){uni.navigateBack({fail:()=>uni.reLaunch({url:'/pages/auth/login'})})}
</script>

<style lang="scss" scoped>
.form-notice,.form-help{display:block;margin-top:20rpx;font-size:25rpx;line-height:1.6;white-space:pre-wrap}.form-notice{color:#ffd1b8}.form-help{color:#aaa}.code-btn[disabled]{opacity:.65}
.page { min-height: 100vh; background: #121212; color: #FFFFFF; }
.nav-row { height: 88rpx; padding: 0 24rpx; display: flex; align-items: center; justify-content: space-between; }
.back-btn, .nav-space { width: 64rpx; height: 64rpx; flex: 0 0 auto; }
.back-btn { margin: 0; padding: 0; border-radius: 50%; background: #1E1E1E; border: 1rpx solid #2C2C2E; color: #CCFF00; font-size: 46rpx; line-height: 1; display: flex; align-items: center; justify-content: center; text-align: center; }
.nav-title { font-size: 32rpx; font-weight: 900; }
.content { padding: 54rpx 32rpx; }
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

@media screen and (max-width: 430px) {
	.code-row { grid-template-columns: 1fr; gap: 12rpx; }
	.code-btn { min-height: 76rpx; font-size: 23rpx; }
}
</style>
