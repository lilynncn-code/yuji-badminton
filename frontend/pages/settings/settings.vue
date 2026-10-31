<template>
	<view class="page">
		<text class="title">{{ $tr(text.title) }}</text>
		<view class="profile-mini">
			<image class="avatar" :src="user.avatar" mode="aspectFill" />
			<view>
				<text class="name">{{ user.name }}</text>
				<text class="desc">{{ user.city === '未设置城市' ? $tr('未设置城市') : user.city }} · {{ user.levelTag === '羽毛球爱好者' ? $tr('羽毛球爱好者') : user.levelTag }}</text>
			</view>
		</view>
		<text v-if="profileError" class="desc">{{ $tr(profileError) }}</text>
        <button v-if="profileError" @click="loadProfile">{{ $tr("重试读取资料") }}</button>
        <view class="group">
			<view v-for="item in accountSettings" :key="item.label" class="cell" :hover-class="'click-feedback'" @click="openSetting(item)">
				<view>
					<text class="label">{{ $tr(item.label) }}</text>
					<text class="desc">{{ $tr(item.desc) }}</text>
				</view>
				<text class="value">{{ $tr(item.value) }}</text>
			</view>
		</view>
		<view class="group">
			<view v-for="item in settings" :key="item.label" class="cell" :hover-class="'click-feedback'" @click="openSetting(item)">
				<view>
					<text class="label">{{ $tr(item.label) }}</text>
					<text class="desc">{{ $tr(item.desc) }}</text>
				</view>
				<text class="value">{{ $tr(item.value) }}</text>
			</view>
		</view>
		<view class="group">
			<view v-for="item in legalLinks" :key="item.label" class="cell" :hover-class="'click-feedback'" @click="openLegal(item)">
				<view>
					<text class="label">{{ $tr(item.label) }}</text>
					<text class="desc">{{ $tr(item.desc) }}</text>
				</view>
				<text class="value">{{ $tr("查看") }}</text>
			</view>
		</view>
		<view class="language-box">
			<view class="language-head">
				<text class="label">{{ $tr(text.languageTitle) }}</text>
				<text class="desc">{{ $tr(text.languageDesc) }}</text>
			</view>
			<view class="language-row">
				<button
					v-for="item in languages"
					:key="item.code"
					class="language-btn"
					:class="{ active: language === item.code }"
					@click="changeLanguage(item.code)"
				>
					<text class="language-name">{{ item.name }}</text>
					<text class="language-note">{{ $tr(item.note) }}</text>
				</button>
			</view>
		</view>
		<view class="source-box">
			<text class="label">{{ $tr(text.sourceTitle) }}</text>
			<text v-for="source in sources" :key="source.title" class="source" @click="openExternal(source.url)">{{ $tr("{0}：{1}", [source.title, source.note]) }}</text>
		</view>
		<view class="group">
            <view class="cell" @click="openLegal({url: '/pages/profile/people?kind=blocked'})">{{ $tr("屏蔽的球友 ›") }}</view>
            <view class="cell" @click="openLegal({url: '/pages/settings/reports'})">{{ $tr("我的举报记录 ›") }}</view>
            <view v-if="canReview" class="cell" @click="openLegal({url: '/pages/settings/review-reports'})">{{ $tr("处理举报 ›") }}</view>
            <view class="cell" @click="openLegal({url: '/pages/notifications/notifications'})">{{ $tr("站内提醒 ›") }}</view>
            <view class="cell" @click="openLegal({url: '/pages/settings/permissions'})">{{ $tr("手机权限 ›") }}</view>
            <view class="cell" @click="openLegal({url: '/pages/settings/change-phone'})">{{ $tr("更换手机号 ›") }}</view>
            <view class="cell" @click="openLegal({url: '/pages/settings/delete-account'})">{{ $tr("注销账号与删除资料 ›") }}</view>
        </view>
        <button class="logout-btn" :disabled="loggingOut" @click="logout">{{ $tr(loggingOut?'正在退出…':'退出登录') }}</button>
	</view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onShow, onHide, onUnload } from '@dcloudio/uni-app'
import { fetchMyProfile } from '../../utils/profile-api'
import { sources } from '../../data/app-data'
import { getLanguage, getUser, saveLanguage } from '../../utils/store'
import { openExternal } from '../../utils/external'
import { logoutRemote, getAuthToken } from '../../utils/auth'
import { applyAppLanguage, getCopy, setPageTitle } from '../../utils/i18n'

const user = ref(getUser())
const canReview = ref(false)
const profileError=ref(''),loggingOut=ref(false)
let generation=0,active=false,owner='',logoutOperation=0,logoutDone=false
const account=()=>`${getUser().id||''}:${getAuthToken()}`
const language = ref(getLanguage())
const languages = [
	{ code: 'zh-Hans', name: '简体中文', note: '中文界面' },
	{ code: 'en', name: 'English', note: '完整英文' }
]
const text = computed(() => getCopy('settings', language.value))
const accountSettings = computed(() => text.value.accountSettings)
const settings = computed(() => text.value.settings)
const legalLinks = [
	{ label: '用户协议', desc: '查看好羽的使用规则与服务说明', url: '/pages/agreement/agreement' },
	{ label: '隐私政策', desc: '查看好羽如何收集、使用和保护信息', url: '/pages/privacy/privacy' }
]

onShow(() => {
    active=true
    if(logoutDone&&!getAuthToken()){uni.reLaunch({url:'/pages/auth/login'});return}
    if(owner!==account()){owner=account();logoutOperation++;loggingOut.value=false;logoutDone=false}
    user.value=getUser();canReview.value=false
    language.value=getLanguage();applyAppLanguage(language.value);setPageTitle('settings',language.value)
    loadProfile()
})
async function loadProfile(){
    if(!active||owner!==account())return
    const ticket=++generation,who=owner
    profileError.value='';canReview.value=false
    try{const profile=await fetchMyProfile();if(active&&ticket===generation&&who===account()){user.value=profile;canReview.value=Boolean(profile.canReviewReports)}}
    catch(e){if(active&&ticket===generation&&who===account())profileError.value=e.message||'资料暂时没有读到，请重试'}
}
function hide(){active=false;generation++;canReview.value=false}
onHide(hide);onUnload(hide)

function openSetting(item) {
	if (item.url) {
		uni.navigateTo({ url: item.url })
		return
	}
	uni.showModal({ title: item.label, content: item.desc, showCancel: false })
}

function openLegal(item) {
	uni.navigateTo({ url: item.url })
}

function changeLanguage(nextLanguage) {
	if(!active||owner!==account()||loggingOut.value||!languages.some(item=>item.code===nextLanguage))return
	try {
		language.value = saveLanguage(nextLanguage)
		applyAppLanguage(language.value)
		setPageTitle('settings', language.value)
		uni.showToast({ title: text.value.languageSaved, icon: 'none' })
	}catch{
		uni.showToast({title:'语言未能保存在本机，请检查可用空间后重试',icon:'none'})
	}
}

async function logout() {
    if(!active||owner!==account()||loggingOut.value)return
    const op=++logoutOperation,who=owner
    loggingOut.value=true
    try{
        await logoutRemote()
        if(op!==logoutOperation||owner!==who||getAuthToken())return
        logoutDone=true
        if(active)uni.reLaunch({url:'/pages/auth/login'})
    }catch(error){if(active&&op===logoutOperation&&who===account())uni.showToast({title:error.message,icon:'none'})}
    finally{if(op===logoutOperation)loggingOut.value=false}
}

</script>

<style lang="scss" scoped>
.page { min-height: 100vh; padding: 44rpx 24rpx; background: #121212; color: #FFFFFF; box-sizing: border-box; }
.title { display: block; margin-bottom: 28rpx; color: #CCFF00; font-size: 44rpx; font-weight: 900; }
.profile-mini, .group, .language-box, .source-box { margin-bottom: 22rpx; border-radius: 18rpx; background: #1E1E1E; border: 1rpx solid #2C2C2E; overflow: hidden; }
.profile-mini { padding: 24rpx; display: flex; align-items: center; gap: 18rpx; }
.avatar { width: 90rpx; height: 90rpx; border-radius: 50%; background: #2C2C2E; }
.name { display: block; font-size: 32rpx; font-weight: 900; }
.cell { min-height: 112rpx; padding: 20rpx 24rpx; display: flex; align-items: center; justify-content: space-between; border-bottom: 1rpx solid #2C2C2E; }
.cell:last-child { border-bottom: 0; }
.label { display: block; font-size: 28rpx; font-weight: 800; }
.desc, .source { display: block; margin-top: 8rpx; color: #8E8E93; font-size: 22rpx; line-height: 1.5; }
.value { color: #CCFF00; font-size: 24rpx; margin-left: 24rpx; white-space: nowrap; }
.language-box { padding: 24rpx; }
.language-head { margin-bottom: 18rpx; }
.language-row { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14rpx; }
.language-btn { min-height: 90rpx; padding: 16rpx; border-radius: 14rpx; background: #242424; border: 2rpx solid transparent; color: #FFFFFF; display: flex; flex-direction: column; align-items: flex-start; justify-content: center; text-align: left; white-space: normal; }
.language-btn.active { border-color: #CCFF00; background: rgba(204,255,0,.1); }
.language-name { display: block; font-size: 26rpx; font-weight: 900; }
.language-note { display: block; margin-top: 8rpx; color: #8E8E93; font-size: 21rpx; }
.source-box { padding: 24rpx; }
.logout-btn { width: 100%; height: 82rpx; margin-top: 28rpx; border-radius: 999rpx; background: #2C2C2E; color: #FFFFFF; font-size: 28rpx; font-weight: 900; }
</style>
