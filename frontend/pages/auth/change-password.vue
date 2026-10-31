<template>
	<view class="page" :style="{ paddingTop: statusBarHeight + 'px' }">
		<view class="nav-row">
			<view class="back-btn" @click="goBack">{{ $tr("‹") }}</view>
			<text class="nav-title">{{ $tr("修改密码") }}</text>
			<view class="nav-space"></view>
		</view>
		<view class="content">
			<text class="title">{{ $tr("修改密码") }}</text>
			<text class="subtitle">{{ $tr("先输入旧密码，再设置一个新密码。") }}</text>

			<input class="input" v-model="form.old_password" :disabled="loading" maxlength="50" password :placeholder='$tr("旧密码")' placeholder-class="placeholder" />
			<input class="input" v-model="form.new_password" :disabled="loading" maxlength="50" password :placeholder='$tr("新密码，至少 6 位，含字母和数字")' placeholder-class="placeholder" />
			<input class="input" v-model="form.confirm_password" :disabled="loading" maxlength="50" password :placeholder='$tr("再输入一次新密码")' placeholder-class="placeholder" />

            <text v-if="notice" class="form-notice">{{ $tr(notice) }}</text>
            <text class="form-help">{{ $tr("保存后其他设备需要重新登录。若提交后连接中断，请尝试用新密码登录确认。离开页面会清空密码。") }}</text>
			<button class="primary-btn" :disabled="loading" @click="submit">{{ $tr(loading ? '提交中...' : '保存新密码') }}</button>
		</view>
	</view>
</template>

<script setup>
import { reactive } from 'vue'
import { changePassword } from '../../utils/auth'
import { useAuthPage, validatePassword } from '../../utils/auth-page'
import { getTopSafeAreaHeight } from '../../utils/safe-area'
const statusBarHeight=getTopSafeAreaHeight()
const form=reactive({old_password:'',new_password:'',confirm_password:''})
const page=useAuthPage({requireLogin:true,clearSecrets:()=>Object.assign(form,{old_password:'',new_password:'',confirm_password:''})})
const {loading,notice}=page
function checkForm(){
    if(!form.old_password||!form.new_password||!form.confirm_password)return '请填写完整信息'
    const invalid=validatePassword(form.new_password,'新密码')
    if(invalid)return invalid
    if(form.new_password!==form.confirm_password)return '两次新密码不一致'
    if(form.old_password===form.new_password)return '新密码不能和旧密码一样'
    return ''
}
async function submit(){
    if(!page.canAct())return
    const message=checkForm()
    if(message){page.explain(message);return}
    const payload={...form}
    return page.run('password',options=>changePassword(payload,options),{message:'密码已修改，请使用新密码登录其他设备',clearOnSuccess:true,success:()=>{
        uni.navigateBack({fail:()=>uni.switchTab({url:'/pages/profile/profile'})})
    }})
}
function goBack(){uni.navigateBack({fail:()=>uni.switchTab({url:'/pages/profile/profile'})})}
</script>

<style lang="scss" scoped>
.form-notice,.form-help{display:block;margin-top:20rpx;font-size:25rpx;line-height:1.6;white-space:pre-wrap}.form-notice{color:#ffd1b8}.form-help{color:#aaa}
.page { min-height: 100vh; background: #121212; color: #FFFFFF; }
.nav-row { height: 88rpx; padding: 0 24rpx; display: flex; align-items: center; justify-content: space-between; }
.back-btn, .nav-space { width: 64rpx; height: 64rpx; flex: 0 0 auto; }
.back-btn { margin: 0; padding: 0; border-radius: 50%; background: #1E1E1E; border: 1rpx solid #2C2C2E; color: #CCFF00; font-size: 46rpx; display: flex; align-items: center; justify-content: center; text-align: center; }
.nav-title { font-size: 32rpx; font-weight: 900; }
.content { padding: 54rpx 32rpx; }
.title { display: block; color: #CCFF00; font-size: 52rpx; font-weight: 900; }
.subtitle { display: block; margin-top: 14rpx; color: #BDBDBD; font-size: 27rpx; line-height: 1.5; }
.input { width: 100%; height: 88rpx; margin-top: 20rpx; padding: 0 24rpx; border-radius: 14rpx; background: #1E1E1E; border: 1rpx solid #2C2C2E; color: #FFFFFF; font-size: 28rpx; box-sizing: border-box; }
.input:first-of-type { margin-top: 42rpx; }
.placeholder { color: #777; }
.primary-btn { width: 100%; height: 88rpx; margin-top: 30rpx; border-radius: 999rpx; background: #CCFF00; color: #121212; font-size: 30rpx; font-weight: 900; }
.primary-btn[disabled] { opacity: .7; }
</style>
