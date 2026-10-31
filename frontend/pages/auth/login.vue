<template>
	<view class="page" :style="{ paddingTop: statusBarHeight + 'px' }">
		<image class="hero-image" :src="heroImage" mode="aspectFill" />
		<view class="shade"></view>
		<view class="panel">
			<text class="brand">{{ $tr("羽迹 Track") }}</text>
			<text class="title">{{ $tr("登录账号") }}</text>
			<text class="subtitle">{{ $tr("继续记录训练、约球和聊天。") }}</text>

			<input class="input" v-model="account" :disabled="loading" maxlength="50" :placeholder='$tr("用户名或手机号")' placeholder-class="placeholder" />
			<input class="input" v-model="password" :disabled="loading" maxlength="50" password :placeholder='$tr("密码")' placeholder-class="placeholder" />
			<text v-if="notice" class="form-notice">{{ $tr(notice) }}</text>

			<button class="primary-btn" :disabled="loading" @click="submit">{{ $tr(loading ? '登录中...' : '登录') }}</button>
			<view class="link-row">
				<button class="link-btn" @click="goRegister">{{ $tr("注册新账号") }}</button>
				<button class="link-btn" @click="goForgot">{{ $tr("忘记密码") }}</button>
			</view>
		</view>
	</view>
</template>

<script setup>
import { ref } from 'vue'
import { matchPhotos } from '../../data/app-data'
import { isOnboardingComplete } from '../../utils/store'
import { login } from '../../utils/auth'
import { useAuthPage } from '../../utils/auth-page'
import { getTopSafeAreaHeight } from '../../utils/safe-area'

const statusBarHeight = getTopSafeAreaHeight()
const heroImage = matchPhotos['li-shifeng-malaysia-2026']?.url || 'https://images.unsplash.com/photo-1626224583764-f87db24ac4ea?auto=format&fit=crop&w=1200&q=80'
const account = ref('')
const password = ref('')
const page=useAuthPage({clearSecrets:()=>password.value=''})
const {loading,notice}=page

function goNext() {
	if (isOnboardingComplete()) {
		uni.switchTab({ url: '/pages/index/index' })
		return
	}
	uni.redirectTo({ url: '/pages/onboarding/onboarding' })
}

async function submit() {
	if(!page.canAct())return
	if (!account.value.trim() || !password.value.trim()) {
		page.explain('请输入账号和密码')
		return
	}
    const name=account.value.trim(),secret=password.value
    return page.run('login',options=>login(name,secret,options),{message:'登录成功',success:goNext,clearOnSuccess:true})
}

function goRegister() {
    if(loading.value)return
	uni.navigateTo({ url: '/pages/auth/register' })
}

function goForgot() {
    if(loading.value)return
	uni.navigateTo({ url: '/pages/auth/forgot' })
}
</script>

<style lang="scss" scoped>
.form-notice{display:block;margin-top:20rpx;color:#ffd1b8;font-size:25rpx;line-height:1.6;white-space:pre-wrap}
.page { position: relative; min-height: 100vh; overflow: hidden; background: #121212; color: #FFFFFF; }
.hero-image { position: absolute; inset: 0; width: 100%; height: 100%; background: #2C2C2E; }
.shade { position: absolute; inset: 0; background: linear-gradient(180deg, rgba(18,18,18,.42) 0%, rgba(18,18,18,.78) 46%, #121212 100%); }
.panel { position: relative; z-index: 1; min-height: 100vh; padding: 26vh 32rpx 48rpx; box-sizing: border-box; }
.brand { display: block; color: #CCFF00; font-size: 34rpx; font-weight: 900; }
.title { display: block; margin-top: 16rpx; font-size: 58rpx; font-weight: 900; line-height: 1.12; }
.subtitle { display: block; margin-top: 14rpx; color: #DADADA; font-size: 27rpx; line-height: 1.5; }
.input { width: 100%; height: 88rpx; margin-top: 20rpx; padding: 0 24rpx; border-radius: 14rpx; background: rgba(30,30,30,.95); border: 1rpx solid #2C2C2E; color: #FFFFFF; font-size: 28rpx; box-sizing: border-box; }
.input:first-of-type { margin-top: 42rpx; }
.placeholder { color: #777; }
.primary-btn { width: 100%; min-height: 88rpx; margin-top: 28rpx; padding: 10rpx 24rpx; border-radius: 999rpx; background: #CCFF00; color: #121212; font-size: 30rpx; line-height: 1.25; font-weight: 900; }
.primary-btn[disabled] { opacity: .7; }
.link-row { margin-top: 24rpx; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18rpx; }
.link-btn {
	width: 100%;
	min-height: 64rpx;
	margin: 0;
	padding: 8rpx 12rpx;
	border-radius: 12rpx;
	background: rgba(30,30,30,.9);
	border: 1rpx solid rgba(255,255,255,.14);
	color: #FFFFFF;
	font-size: 25rpx;
	font-weight: 700;
	line-height: 1.25;
	text-align: center;
	box-sizing: border-box;
	white-space: normal;
	word-break: break-word;
	overflow: visible;
}
.link-btn::after { border: 0; }
</style>
