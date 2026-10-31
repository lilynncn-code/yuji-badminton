<template>
	<view class="page" :style="{ paddingTop: statusBarHeight + 'px', '--top-safe-height': statusBarHeight + 'px' }">
		<image class="hero-image" :src="heroImage" mode="aspectFill" />
		<view class="shade"></view>

		<view class="top-row">
			<view>
				<text class="brand">{{ $tr(copy.brand) }}</text>
				<text class="tagline">{{ $tr(copy.tagline) }}</text>
			</view>
			<button class="skip-btn" :disabled="entering" @click="enterApp">{{ $tr(copy.skip) }}</button>
		</view>

		<view class="content">
			<text class="eyebrow">{{ $tr(copy.eyebrow) }}</text>
			<text class="title">{{ $tr(copy.title) }}</text>
			<text class="subtitle">{{ $tr(copy.subtitle) }}</text>

			<view class="language-panel">
				<text class="panel-title">{{ $tr(copy.languageTitle) }}</text>
				<view class="language-row">
					<button
						v-for="item in languages"
						:key="item.code"
						class="language-btn"
						:class="{ active: selectedLanguage === item.code }"
						:disabled="entering"
						@click="selectLanguage(item.code)"
					>
						<text class="language-name">{{ item.name }}</text>
						<text class="language-note">{{ $tr(item.note) }}</text>
					</button>
				</view>
				<text class="subtitle">{{ $tr(copy.languageHelp) }}</text>
			</view>

			<view class="feature-list">
				<view v-for="item in copy.features" :key="item.title" class="feature-item">
					<text class="feature-icon">{{ $tr(item.icon) }}</text>
					<view class="feature-text">
						<text class="feature-title">{{ $tr(item.title) }}</text>
						<text class="feature-desc">{{ $tr(item.desc) }}</text>
					</view>
				</view>
			</view>

			<view class="notice">
				<text>{{ $tr(copy.notice) }}</text>
			</view>

			<text v-if="error" class="subtitle" style="color:#ffd1b8">{{ $tr(error) }}</text>
			<button class="primary-btn" :disabled="entering" @click="enterApp">{{ $tr(entering?copy.entering:copy.start) }}</button>
		</view>
	</view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onShow, onHide, onUnload } from '@dcloudio/uni-app'
import { matchPhotos } from '../../data/app-data'
import { completeOnboarding, getLanguage, saveLanguage, getUser } from '../../utils/store'
import { getAuthToken } from '../../utils/auth'
import { getTopSafeAreaHeight } from '../../utils/safe-area'

const statusBarHeight = getTopSafeAreaHeight()
const selectedLanguage = ref('zh-Hans'),entering=ref(false),error=ref('')
let active=false,owner='',generation=0
const account=()=>`${getUser().id||''}:${getAuthToken()}`
const current=ticket=>active&&owner===account()&&Boolean(getAuthToken())&&ticket===generation
onShow(()=>{active=true;owner=account();generation++;entering.value=false;error.value='';if(!getAuthToken()){uni.reLaunch({url:'/pages/auth/login'});return}try{selectedLanguage.value=getLanguage()}catch{error.value='本机语言设置未能读取，请重新选择后再进入'}})
function leave(){active=false;generation++;entering.value=false}
onHide(leave);onUnload(leave)
const heroImage = matchPhotos['li-shifeng-malaysia-2026']?.url || 'https://images.unsplash.com/photo-1626224583764-f87db24ac4ea?auto=format&fit=crop&w=1200&q=80'

const languages = [
	{ code: 'zh-Hans', name: '简体中文', note: '推荐' },
	{ code: 'en', name: 'English', note: '完整英文' }
]

const copies = {
	'zh-Hans': {
		brand: '羽迹 Track',
		tagline: 'AI 羽毛球训练与球友社区',
		skip: '跳过',
		eyebrow: '首次使用设置',
		title: '开始你的羽毛球训练记录',
		subtitle: '记录练习次数和训练视频、查看赛事资料，并和注册球友约练聊天。',
		languageTitle: '选择 App 语言',
		languageHelp: '页面、训练说明和操作提示会一起切换。',
		entering: '正在进入…',
		features: [
			{ icon: '◉', title: '训练与画面计数', desc: '网页可根据画面记录举臂和移动次数；暂不能判断挥拍或击球动作是否正确。手机相机功能仍在完善。' },
			{ icon: '▣', title: '球友圈与发帖', desc: '发布动态、选择相册图片或图片库素材，自己的帖子 15 分钟内可编辑。' },
			{ icon: '◇', title: '约球与聊天', desc: '向真实本地用户发起聊天请求，对方同意后进入会话。' }
		],
		notice: '相机和相册只会在训练识别、头像编辑、发帖选图时按需请求权限。',
		start: '进入羽迹 Track'
	},
	en: {
		brand: 'Track Badminton',
		tagline: 'AI training and badminton community',
		skip: 'Skip',
		eyebrow: 'First-time setup',
		title: 'Start tracking your badminton life',
		subtitle: 'Save practice counts and videos, browse tournament information, and chat with registered players.',
		languageTitle: 'Choose app language',
		languageHelp: 'Pages, practice instructions and prompts switch together.',
		entering: 'Opening…',
		features: [
			{ icon: '◉', title: 'Practice and camera counts', desc: 'The web version counts arm raises and movement. It does not assess swing or shot technique. Phone camera support is still being improved.' },
			{ icon: '▣', title: 'Posts and highlights', desc: 'Post updates with album photos or built-in image library assets, editable for 15 minutes.' },
			{ icon: '◇', title: 'Find players and chat', desc: 'Send chat requests to local users and start a conversation after approval.' }
		],
		notice: 'Camera and photo permissions are requested only when training, editing avatars, or choosing post images.',
		start: 'Enter Track'
	}
}

const copy = computed(() => copies[selectedLanguage.value] || copies['zh-Hans'])

function selectLanguage(language) {
	if(!current(generation)||entering.value||!languages.some(item=>item.code===language))return
	try{saveLanguage(language);selectedLanguage.value=language;error.value=''}catch{error.value='语言未能保存在本机，请检查可用空间后重试'}
}

function enterApp() {
	if(!current(generation)||entering.value)return
	const ticket=generation;entering.value=true;error.value=''
	try{
		completeOnboarding(selectedLanguage.value)
		if(!current(ticket))return
		uni.switchTab({url:'/pages/index/index',fail:()=>{if(current(ticket)){entering.value=false;error.value='首次设置已保存，但首页未打开，请重新进入'}}})
	}catch{if(current(ticket)){entering.value=false;error.value='首次设置未能保存在本机，请检查可用空间后重试'}}
}
</script>

<style lang="scss" scoped>
.page {
	position: relative;
	min-height: 100vh;
	overflow: hidden;
	background: #121212;
	color: #FFFFFF;
}

.hero-image {
	position: absolute;
	inset: 0;
	width: 100%;
	height: 54vh;
	background: #2C2C2E;
}

.shade {
	position: absolute;
	inset: 0;
	background: linear-gradient(180deg, rgba(18,18,18,.12) 0%, rgba(18,18,18,.7) 42%, #121212 58%, #121212 100%);
}

.top-row {
	position: relative;
	z-index: 1;
	height: 104rpx;
	padding: 0 28rpx;
	display: flex;
	align-items: center;
	justify-content: space-between;
}

.brand {
	display: block;
	color: #CCFF00;
	font-size: 36rpx;
	font-weight: 900;
}

.tagline {
	display: block;
	margin-top: 6rpx;
	color: rgba(255,255,255,.78);
	font-size: 21rpx;
}

.skip-btn {
	height: 58rpx;
	padding: 0 24rpx;
	border-radius: 999rpx;
	background: rgba(18,18,18,.48);
	color: #FFFFFF;
	font-size: 24rpx;
}

.content {
	position: relative;
	z-index: 1;
	min-height: calc(100vh - 104rpx - var(--top-safe-height));
	padding: 34vh 28rpx calc(28rpx + env(safe-area-inset-bottom));
	box-sizing: border-box;
}

.eyebrow {
	display: block;
	color: #CCFF00;
	font-size: 24rpx;
	font-weight: 800;
}

.title {
	display: block;
	margin-top: 12rpx;
	max-width: 660rpx;
	font-size: 56rpx;
	line-height: 1.08;
	font-weight: 900;
}

.subtitle {
	display: block;
	margin-top: 18rpx;
	max-width: 660rpx;
	color: #DADADA;
	font-size: 28rpx;
	line-height: 1.48;
}

.language-panel,
.feature-list,
.notice {
	margin-top: 24rpx;
	border-radius: 18rpx;
	background: rgba(30,30,30,.92);
	border: 1rpx solid #2C2C2E;
}

.language-panel {
	padding: 20rpx;
}

.panel-title {
	display: block;
	margin-bottom: 16rpx;
	font-size: 26rpx;
	font-weight: 900;
}

.language-row {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 14rpx;
}

.language-btn {
	min-width: 0;
	min-height: 92rpx;
	padding: 16rpx;
	border-radius: 14rpx;
	background: #242424;
	border: 2rpx solid transparent;
	color: #FFFFFF;
	display: flex;
	flex-direction: column;
	align-items: flex-start;
	justify-content: center;
	text-align: left;
	white-space: normal;
}

.language-btn.active {
	border-color: #CCFF00;
	background: rgba(204,255,0,.1);
}

.language-name,
.language-note {
	display: block;
}

.language-name {
	font-size: 26rpx;
	font-weight: 900;
}

.language-note {
	margin-top: 8rpx;
	color: #8E8E93;
	font-size: 21rpx;
}

.feature-list {
	overflow: hidden;
}

.feature-item {
	min-height: 118rpx;
	padding: 20rpx;
	display: flex;
	align-items: center;
	border-bottom: 1rpx solid #2C2C2E;
}

.feature-item:last-child {
	border-bottom: 0;
}

.feature-icon {
	width: 62rpx;
	height: 62rpx;
	margin-right: 18rpx;
	border-radius: 16rpx;
	background: rgba(204,255,0,.12);
	color: #CCFF00;
	text-align: center;
	line-height: 62rpx;
	font-size: 28rpx;
}

.feature-text {
	flex: 1;
	min-width: 0;
}

.feature-title {
	display: block;
	font-size: 28rpx;
	font-weight: 900;
}

.feature-desc {
	display: block;
	margin-top: 8rpx;
	color: #AFAFAF;
	font-size: 22rpx;
	line-height: 1.42;
}

.notice {
	padding: 18rpx 20rpx;
	color: #AFAFAF;
	font-size: 22rpx;
	line-height: 1.48;
}

.primary-btn {
	width: 100%;
	height: 88rpx;
	margin-top: 24rpx;
	border-radius: 999rpx;
	background: #CCFF00;
	color: #121212;
	font-size: 30rpx;
	font-weight: 900;
}
</style>
