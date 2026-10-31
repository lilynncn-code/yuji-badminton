<template>
	<view class="page" :style="{ paddingTop: statusBarHeight + 'px', '--top-safe-height': statusBarHeight + 'px' }">
		<view class="nav-bar">
			<text class="brand">{{ $tr("羽迹 Track") }}</text>
			<button class="reminders" @click="openReminders">{{ $tr("提醒{0}", [reminderCount ? ` ${reminderCount > 99 ? '99+' : reminderCount}` : '']) }}</button>
			<view class="location" :hover-class="'click-feedback'" :hover-stay-time="80" @click="changeCity">
				<text>{{ city === '选择城市' ? $tr(city) : city }}</text>
				<text class="chevron">{{ $tr("⌄") }}</text>
			</view>
		</view>

		<scroll-view class="content" scroll-y>
			<view class="search-box">
				<text class="search-icon">{{ $tr("⌕") }}</text>
				<input
					class="search-input"
					:value="searchKeyword"
					:placeholder="$tr(copy.searchPlaceholder)"
					placeholder-class="placeholder"
					confirm-type="search"
					@input="handleSearchInput"
					@confirm="submitSearch"
				/>
			</view>
			<view v-if="searchKeyword" class="search-panel">
				<view v-if="searchResults.length">
					<view v-for="player in searchResults" :key="player.key" class="search-result" @click="openPlayerResult(player)" :hover-class="'click-feedback'">
						<image class="search-avatar" :src="player.photo" mode="aspectFill" />
						<view class="search-main">
							<text class="search-name">{{ $tr(player.name) }}</text>
							<text class="search-meta">{{ $tr("{0} · {1} · #{2}", [player.groupLabel, player.country, player.rank]) }}</text>
						</view>
						<text class="search-go">{{ $tr("›") }}</text>
					</view>
				</view>
				<view v-else class="empty-search">{{ $tr(copy.noPlayers) }}</view>
			</view>

			<view class="daily-update-strip" @click="openTournamentBracket" :hover-class="'click-feedback'">
				<text class="daily-update-title">{{ $tr(tournamentDaily.title) }}</text>
				<text class="daily-update-desc">{{ $tr(tournamentDaily.summary) }}</text>
				<text class="daily-update-arrow">{{ $tr("›") }}</text>
			</view>
			<view class="match-state"><MatchUpdate :loading="matchLoading" :error="matchError" :historical="matchFeed.historical" :from-cache="matchFeed.fromCache" :sync="matchFeed.sync" :cached-at="matchFeed.cacheSavedAt" @retry="loadHomeMatches" /></view>

			<scroll-view class="match-scroll" scroll-x show-scrollbar="false">
				<view class="match-row">
					<view v-for="match in matches" :key="match.id" class="match-card" :hover-class="'click-feedback'" :hover-stay-time="80" @click="goMatch(match.id)">
						<image class="match-photo" :src="match.displayImage" mode="aspectFill" @error="markImageFailed(match)" />
						<view class="match-photo-mask"></view>
						<view class="match-left">
							<text class="tournament">{{ $tr(match.tournamentName) }}</text>
							<text class="match-category">{{ $tr(match.category) }}</text>
						</view>
						<view class="match-center">
							<view class="player-row">
								<text class="player">{{ $tr(match.player1) }}</text>
								<text v-if="match.isServing === 'player1'" class="serve-icon">{{ $tr("◉") }}</text>
							</view>
							<text class="score">{{ $tr(match.score) }}</text>
							<view class="player-row">
								<text class="player">{{ $tr(match.player2) }}</text>
								<text v-if="match.isServing === 'player2'" class="serve-icon">{{ $tr("◉") }}</text>
							</view>
						</view>
						<view class="match-right" @click.stop="showMatchBrief(match)">
							<view class="status-button" :hover-class="'click-feedback'" :hover-stay-time="80">
								<text>{{ $tr(copy.matchBrief) }}</text>
							</view>
						</view>
					</view>
				</view>
			</scroll-view>

			<view class="shortcut-grid">
				<view
					v-for="item in shortcuts"
					:key="item.label"
					class="shortcut-item"
					:hover-class="'click-feedback'"
					:hover-stay-time="80"
					@click="handleShortcut(item)"
				>
					<view class="shortcut-icon">
						<text>{{ $tr(item.icon) }}</text>
					</view>
					<text class="shortcut-label">{{ $tr(item.label) }}</text>
				</view>
			</view>
			<view class="coach-entry" @click="openAiCoach" :hover-class="'click-feedback'">
				<view class="coach-top">
					<view class="coach-icon">{{ $tr("AI") }}</view>
					<view class="coach-copy">
						<text class="entry-title">{{ $tr(copy.coachTitle) }}</text>
						<text class="entry-desc">{{ $tr(copy.coachDesc) }}</text>
					</view>
					<text class="entry-arrow">{{ $tr("›") }}</text>
				</view>
				<view class="coach-data">
					<view class="coach-stat">
						<text class="coach-value">{{ $tr(summary?.sessions ?? '—') }}</text>
						<text class="coach-label">{{ $tr("累计训练次数") }}</text>
					</view>
					<view class="coach-stat">
						<text class="coach-value">{{ $tr("{0} 天", [summary?.streak ?? '—']) }}</text>
						<text class="coach-label">{{ $tr(copy.trainingStreak) }}</text>
					</view>
					<view class="coach-stat">
						<text class="coach-value">{{ $tr(summary?.xp ?? '—') }}</text>
						<text class="coach-label">{{ $tr("学习分") }}</text>
					</view>
				</view>
				<view v-if="summaryError" class="summary-note" @click.stop><text>{{ $tr(summaryError) }}</text><button :disabled="summaryLoading" @click.stop="loadHomeSummary">{{ $tr("重新读取训练统计") }}</button></view>
				<view class="coach-plan">
					<view class="plan-line">
						<text class="plan-dot"></text>
						<text>{{ $tr("完成下一关训练，记录属于你的进步") }}</text>
					</view>
					<view class="plan-line">
						<text class="plan-dot"></text>
						<text>{{ $tr("先学习动作要点，再完成实际训练") }}</text>
					</view>
				</view>
				<button class="coach-btn" @click.stop="openAiCoach">{{ $tr(copy.startTraining) }}</button>
			</view>

			<view class="home-windows">
				<view class="window-card chat-window" @click="openChatCenter" :hover-class="'click-feedback'">
					<view class="window-head">
						<text class="window-title">{{ $tr(copy.chat) }}</text>
						<text class="window-link">{{ $tr(copy.open) }}</text>
					</view>
					<text class="window-sub">{{ chatPreview.titleIsUser ? chatPreview.title : $tr(chatPreview.title) }}</text>
					<text class="window-desc">{{ chatPreview.descIsUser ? chatPreview.desc : $tr(chatPreview.desc) }}</text>

				</view>
				<view class="window-card court-window" @click="openNearbyCourts" :hover-class="'click-feedback'">
					<view class="window-head">
						<text class="window-title">{{ $tr(copy.nearbyCourts) }}</text>
						<text class="window-link">{{ $tr(copy.view) }}</text>
					</view>
                    <text class="window-sub">{{ $tr("查找当前位置附近的球馆") }}</text>
                    <text class="window-desc">{{ $tr("查看地址与电话，联系球馆确认开放时间和订场。") }}</text>
				</view>
			</view>
		</scroll-view>
	</view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { translate } from '../../utils/translate'
import { onShow, onHide, onUnload } from '@dcloudio/uni-app'
import { matchPhotos, playerPhotos, rankingGroups } from '../../data/app-data'
import { getUser } from '../../utils/store'
import { getAuthToken } from '../../utils/auth'
import { fetchChatInbox } from '../../utils/chat-api'
import { fetchTrainingSummary } from '../../utils/training-api'
import { fetchNotificationCount } from '../../utils/notifications-api'
import { MATCH_FALLBACK_IMAGE, matchStatusLabel } from '../../utils/match-api'
import { useMatchFeed } from '../../utils/match-feed'
import MatchUpdate from '../../components/MatchUpdate.vue'
import { saveMyProfile } from '../../utils/profile-api'
import { applyAppLanguage, getAppLanguage, getCopy, setPageTitle } from '../../utils/i18n'
import { getTopSafeAreaHeight } from '../../utils/safe-area'

const statusBarHeight = getTopSafeAreaHeight()

const searchKeyword = ref('')
const language = ref(getAppLanguage())
const copy = computed(() => getCopy('home', language.value))
const chatThreads = ref([])
const pendingChatRequests = ref(0)
const summary = ref(null),summaryError=ref(''),summaryLoading=ref(false),changingCity=ref(false)
const city = ref(getUser().city || '选择城市')
const homeError = ref('')
const { data: matchFeed, loading: matchLoading, error: matchError, load: loadHomeMatches, leave: leaveMatches } = useMatchFeed('home')
const reminderCount = ref(0)
let reminderPoll=null,homeGeneration=0,homeOwner='',homeToken='',homeActive=false,summaryRead=0
function homeContext(){return {owner:homeOwner,token:homeToken,page:homeGeneration}}
function currentHome(c){return homeActive&&c.page===homeGeneration&&c.owner===String(getUser()?.id||'')&&c.owner===homeOwner&&c.token===getAuthToken()}
function openReminders(){uni.navigateTo({url:'/pages/notifications/notifications'})}
async function loadReminderCount(){const c=homeContext();try{const data=await fetchNotificationCount();if(currentHome(c))reminderCount.value=data.unread_count}catch(e){/* Preserve the last confirmed count. */}}
function leaveHome(){leaveMatches();homeActive=false;homeGeneration++;summaryRead++;changingCity.value=false;summaryLoading.value=false;clearInterval(reminderPoll)}
onHide(leaveHome);onUnload(leaveHome)
const chatPreview = computed(() => {
    if (homeError.value) return { title: '消息暂未加载', desc: homeError.value }
    if (chatThreads.value.length) return { title: chatThreads.value[0].otherName, titleIsUser: !chatThreads.value[0].otherNameIsDefault, desc: chatThreads.value[0].lastMessage || copy.value.chatReady, descIsUser: !!chatThreads.value[0].lastMessage && !chatThreads.value[0].lastMessageIsSystem }
    const incoming = pendingChatRequests.value
    if (incoming) return { title: `${incoming} 条待处理申请`, desc: copy.value.chatRequestsDesc }
    return { title: copy.value.noMessage, desc: copy.value.noMessageDesc }
})
async function loadAccountData() {
    const c=homeContext()
    city.value = getUser().city || '选择城市'
    loadHomeSummary()
    try{const inbox=await fetchChatInbox({kind:'threads',limit:1});if(currentHome(c)){chatThreads.value=inbox.threads;pendingChatRequests.value=inbox.summary.pending_incoming;homeError.value=''}}
    catch(e){if(currentHome(c)){homeError.value=e.message||'消息暂未读取';chatThreads.value=[];pendingChatRequests.value=0}}
}
async function loadHomeSummary(){
    if(!homeActive)return
    const c=homeContext(),generation=++summaryRead;summaryLoading.value=true;summaryError.value=''
    try{const stats=await fetchTrainingSummary();if(currentHome(c)&&generation===summaryRead)summary.value=stats}
    catch(e){if(currentHome(c)&&generation===summaryRead){summary.value=null;summaryError.value=e.message||'训练统计读取失败'}}
    finally{if(currentHome(c)&&generation===summaryRead)summaryLoading.value=false}
}
const tournamentDaily = computed(() => ({
    title: '近期比赛',
    summary: matchFeed.value.historical ? '内置历史资料，联网后尝试更新' : '查看近期赛事、轮次和比分'
}))
const fallbackMatchImage = MATCH_FALLBACK_IMAGE
const matches = computed(() => matchFeed.value.items.slice(0, 6).map(item => ({
    id: item.id, tournamentName: item.event_name,
    category: `${item.discipline || '比赛'} ${item.round || ''} · ${matchStatusLabel(item.status)}`.trim(),
    player1: item.player1, player2: item.player2, score: item.score_text || '暂无比分',
    isServing: '', displayImage: item.displayImage || fallbackMatchImage, raw: item
})))
const allPlayers = rankingGroups.flatMap((group) => group.players.map((player) => ({
	...player,
	groupKey: group.key,
	groupLabel: group.label,
	key: `${group.key}-${player.rank}-${player.name}`,
	photo: playerPhotos[player.name]?.url || matchPhotos['li-shifeng-malaysia-2026'].url
})))
const searchResults = computed(() => {
	const keyword = searchKeyword.value.trim().toLowerCase()
	if (!keyword) return []
	return allPlayers
		.filter((player) => [player.name, player.country, player.groupLabel].flatMap(value => [value, translate(value)]).join(' ').toLowerCase().includes(keyword))
		.slice(0, 6)
})

const shortcuts = computed(() => [
	{ label: copy.value.shortcuts[0], icon: '⌗', url: '/pages/tournament/bracket' },
	{ label: copy.value.shortcuts[1], icon: '♛', url: '/pages/ranking/ranking' },
	{ label: copy.value.shortcuts[2], icon: '⌁', url: '/pages/equipment/library' },
	{ label: copy.value.shortcuts[3], icon: '◌', url: '/pages/chat/inbox' }
])

onShow(() => {
	const next=String(getUser()?.id||''),token=getAuthToken()
    if(homeOwner!==next||homeToken!==token){chatThreads.value=[];pendingChatRequests.value=0;summary.value=null;summaryError.value='';homeError.value='';reminderCount.value=0}
    homeOwner=next;homeToken=token;homeActive=true;homeGeneration++;changingCity.value=false;loadReminderCount();clearInterval(reminderPoll);reminderPoll=setInterval(loadReminderCount,15000)
	language.value = getAppLanguage()
	applyAppLanguage(language.value)
	setPageTitle('home', language.value)
    loadAccountData()
	loadHomeMatches()
})

function goMatch(id) {
	uni.navigateTo({ url: `/pages/match/detail?id=${encodeURIComponent(id)}` })
}

function showMatchBrief(match) {
	uni.showToast({ title: `${match.score} ${copy.value.matchBriefToast}`, icon: 'none' })
	uni.navigateTo({ url: `/pages/match/detail?id=${encodeURIComponent(match.id)}` })
}

function markImageFailed(match) {
	match.raw.displayImage = fallbackMatchImage
}

function handleShortcut(item) {
	if (item.url) {
		uni.navigateTo({ url: item.url })
		return
	}
	uni.showToast({ title: `${item.label} ${copy.value.soon}`, icon: 'none' })
}

function changeCity() {
    if(!homeActive||changingCity.value)return
    const c=homeContext()
    uni.showModal({ title: '选择城市', editable: true, placeholderText: '例如：上海', content: '', success: async result => {
        if (!result.confirm||!currentHome(c)||changingCity.value) return
        const value = result.content?.trim()
        if (!value || value.length > 80) { uni.showToast({ title: '请填写80字以内的城市名称', icon: 'none' }); return }
        changingCity.value=true
        try { const saved = await saveMyProfile({city:value},{isCurrent:()=>currentHome(c)});if(!currentHome(c))return;city.value=saved.city;uni.showToast({title:saved.localCacheError?'城市已保存，本机同步待重试':'城市已保存，同城球友会按此筛选',icon:'none'}) }
        catch (error) { if(currentHome(c))uni.showToast({title:error.message,icon:'none'}) }
        finally{if(currentHome(c))changingCity.value=false}
    } })
}

function handleSearchInput(event) {
	searchKeyword.value = event.detail.value
}

function submitSearch() {
	if (!searchResults.value.length) {
		uni.showToast({ title: copy.value.noPlayers, icon: 'none' })
		return
	}
	openPlayerResult(searchResults.value[0])
}

function openPlayerResult(player) {
	uni.navigateTo({ url: `/pages/ranking/ranking?group=${player.groupKey}&keyword=${encodeURIComponent(player.name)}` })
}

function openAiCoach() {
	uni.switchTab({ url: '/pages/ai-coach/ai-coach' })
}

function openChatCenter() {
	uni.navigateTo({ url: '/pages/chat/inbox' })
}

function openNearbyCourts() {
	uni.navigateTo({ url: '/pages/courts/nearby' })
}

function openTournamentBracket() {
	uni.navigateTo({ url: '/pages/tournament/bracket' })
}
</script>

<style lang="scss" scoped>
.summary-note{color:#ccc;font-size:24rpx;line-height:1.6;margin-top:16rpx}.summary-note button{color:#ccff00;background:#333;font-size:24rpx;margin-top:12rpx}
.match-state{margin:0 24rpx 18rpx}
.reminders{margin:0 16rpx 0 auto;padding:0 18rpx;background:#242424;color:#cf0;font-size:24rpx;line-height:60rpx;border-radius:24rpx;white-space:nowrap}
$bg-main: #121212;
$bg-card: #1E1E1E;
$brand-primary: #CCFF00;
$brand-accent: #FF5722;
$text-white: #FFFFFF;
$text-gray: #8E8E93;
$border-color: #2C2C2E;

.page {
	min-height: 100vh;
	background: $bg-main;
	padding-bottom: calc(24rpx + env(safe-area-inset-bottom));
}

.nav-bar {
	position: sticky;
	top: var(--top-safe-height);
	z-index: 50;
	height: 88rpx;
	padding: 0 24rpx;
	display: flex;
	align-items: center;
	justify-content: space-between;
	background: $bg-main;
}

.brand {
	color: $brand-primary;
	font-size: 38rpx;
	font-weight: 800;
}

.location {
	display: flex;
	align-items: center;
	gap: 6rpx;
	color: $text-gray;
	font-size: 26rpx;
}

.chevron {
	font-size: 24rpx;
}

.content {
	height: calc(100vh - 88rpx - var(--top-safe-height) - env(safe-area-inset-bottom));
}

.search-box {
	margin: 24rpx;
	height: 72rpx;
	border-radius: 40rpx;
	background: $bg-card;
	display: flex;
	align-items: center;
	padding: 0 28rpx;
}

.search-icon {
	color: $text-gray;
	font-size: 34rpx;
	margin-right: 14rpx;
}

.search-input {
	flex: 1;
	height: 72rpx;
	color: $text-white;
	font-size: 28rpx;
}

.placeholder {
	color: $text-gray;
	font-size: 28rpx;
}

.search-panel { margin: -10rpx 24rpx 20rpx; border-radius: 18rpx; background: $bg-card; border: 1rpx solid $border-color; overflow: hidden; }
.search-result { min-height: 92rpx; padding: 14rpx 18rpx; display: flex; align-items: center; border-bottom: 1rpx solid $border-color; }
.search-result:last-child { border-bottom: 0; }
.search-avatar { width: 62rpx; height: 62rpx; margin-right: 16rpx; border-radius: 50%; background: #2C2C2E; }
.search-main { flex: 1; min-width: 0; }
.search-name { display: block; color: $text-white; font-size: 26rpx; font-weight: 900; }
.search-meta { display: block; margin-top: 6rpx; color: $text-gray; font-size: 21rpx; }
.search-go { color: $brand-primary; font-size: 36rpx; }
.empty-search { padding: 24rpx; color: $text-gray; font-size: 24rpx; text-align: center; }

.daily-update-strip {
	margin: 0 24rpx 18rpx;
	min-height: 82rpx;
	padding: 16rpx 18rpx;
	border-radius: 16rpx;
	background: #1E1E1E;
	border: 1rpx solid rgba(204,255,0,.22);
	display: grid;
	grid-template-columns: 1fr auto;
	column-gap: 12rpx;
	align-items: center;
}

.daily-update-title {
	display: block;
	color: $text-white;
	font-size: 25rpx;
	font-weight: 900;
}

.daily-update-desc {
	display: block;
	margin-top: 6rpx;
	color: $text-gray;
	font-size: 21rpx;
}

.daily-update-arrow {
	grid-row: 1 / span 2;
	grid-column: 2;
	color: $brand-primary;
	font-size: 36rpx;
}

.match-scroll { width: 100%; white-space: nowrap; }
.match-row { display: inline-flex; gap: 18rpx; padding: 0 24rpx 20rpx; }

.match-card {
	position: relative;
	width: calc(100vw - 48rpx);
	min-height: 236rpx;
	padding: 28rpx 24rpx;
	border-radius: 16rpx;
	background: $bg-card;
	box-shadow: 0 4rpx 20rpx rgba(204, 255, 0, 0.08);
	display: flex;
	align-items: center;
	gap: 12rpx;
	border: 1rpx solid rgba(204, 255, 0, 0.08);
	overflow: hidden;
}

.match-photo {
	position: absolute;
	inset: 0;
	width: 100%;
	height: 100%;
	opacity: .42;
}

.match-photo-mask {
	position: absolute;
	inset: 0;
	background: linear-gradient(90deg, rgba(18,18,18,.92), rgba(18,18,18,.68) 48%, rgba(18,18,18,.9));
}

.match-left,
.match-right,
.match-center {
	position: relative;
	z-index: 1;
}

.match-left,
.match-right {
	width: 112rpx;
	flex: 0 0 112rpx;
	min-width: 0;
}

.live-row {
	display: flex;
	align-items: center;
	gap: 8rpx;
	margin-bottom: 22rpx;
}

.live-dot {
	width: 14rpx;
	height: 14rpx;
	border-radius: 50%;
	background: $brand-accent;
	animation: blink 1s ease-in-out infinite;
}

.live-text {
	color: $brand-accent;
	font-size: 22rpx;
	font-weight: 700;
}

.tournament {
	display: block;
	color: $text-gray;
	font-size: 24rpx;
	line-height: 1.35;
}

.match-category {
	display: inline-flex;
	max-width: 100%;
	margin-top: 14rpx;
	padding: 7rpx 12rpx;
	border-radius: 999rpx;
	background: rgba(204,255,0,.14);
	color: $brand-primary;
	font-size: 21rpx;
	font-weight: 900;
	line-height: 1.2;
	text-align: center;
	white-space: normal;
	word-break: break-word;
}

.match-center {
	min-width: 0;
	flex: 1;
	align-items: center;
	display: flex;
	flex-direction: column;
}

.player-row {
	min-height: 42rpx;
	display: flex;
	align-items: center;
	justify-content: center;
	text-align: center;
}

.player {
	color: $text-white;
	font-size: 28rpx;
	font-weight: 600;
	line-height: 1.25;
	white-space: normal;
	word-break: break-word;
}

.serve-icon {
	color: $brand-primary;
	font-size: 22rpx;
	margin-left: 10rpx;
}

.score {
	color: $brand-primary;
	font-size: 28rpx;
	font-weight: 900;
	margin: 8rpx 0;
	white-space: normal;
	text-align: center;
	overflow-wrap: anywhere;
}

.match-right {
	display: flex;
	justify-content: flex-end;
}

.status-button {
	min-width: 96rpx;
	min-height: 64rpx;
	padding: 8rpx 16rpx;
	border-radius: 999rpx;
	border: 2rpx solid $brand-primary;
	display: flex;
	align-items: center;
	justify-content: center;
	color: $brand-primary;
	font-size: 23rpx;
	line-height: 1.2;
	font-weight: 700;
	text-align: center;
	box-sizing: border-box;
	white-space: normal;
	word-break: break-word;
}

.shortcut-grid {
	margin: 32rpx 0;
	padding: 0 24rpx;
	display: grid;
	grid-template-columns: repeat(4, 1fr);
	gap: 22rpx 14rpx;
}

.shortcut-item {
	display: flex;
	flex-direction: column;
	align-items: center;
	min-width: 0;
}

.shortcut-icon {
	width: 96rpx;
	height: 96rpx;
	border-radius: 50%;
	background: $bg-card;
	display: flex;
	align-items: center;
	justify-content: center;
	color: $brand-primary;
	font-size: 42rpx;
	border: 1rpx solid $border-color;
}

.shortcut-label {
	width: 100%;
	margin-top: 14rpx;
	color: $text-white;
	font-size: 26rpx;
	line-height: 1.25;
	text-align: center;
	word-break: break-word;
}

.coach-entry {
	margin: 0 24rpx 28rpx;
	padding: 26rpx 24rpx;
	border-radius: 22rpx;
	background: linear-gradient(135deg, rgba(204,255,0,.18), rgba(30,30,30,1) 48%, rgba(46,60,38,.9));
	border: 1rpx solid rgba(204,255,0,.22);
	box-shadow: 0 16rpx 38rpx rgba(0,0,0,.28);
}

.coach-top {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 20rpx;
}

.coach-icon {
	width: 72rpx;
	height: 72rpx;
	border-radius: 18rpx;
	background: #CCFF00;
	color: #121212;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 26rpx;
	font-weight: 900;
	flex: 0 0 auto;
}

.coach-copy {
	flex: 1;
	min-width: 0;
}

.entry-title {
	display: block;
	color: #FFFFFF;
	font-size: 38rpx;
	font-weight: 900;
}

.entry-desc {
	display: block;
	margin-top: 10rpx;
	color: #D8D8D8;
	font-size: 24rpx;
	line-height: 1.45;
}

.entry-arrow {
	color: #CCFF00;
	font-size: 42rpx;
}

.coach-data {
	margin-top: 24rpx;
	display: grid;
	grid-template-columns: repeat(3, 1fr);
	gap: 12rpx;
}

.coach-stat {
	min-height: 96rpx;
	border-radius: 16rpx;
	background: rgba(18,18,18,.72);
	border: 1rpx solid rgba(204,255,0,.18);
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
}

.coach-value {
	color: $brand-primary;
	font-size: 32rpx;
	font-weight: 900;
}

.coach-label {
	margin-top: 6rpx;
	color: $text-gray;
	font-size: 21rpx;
}

.coach-plan {
	margin-top: 20rpx;
	padding: 18rpx;
	border-radius: 16rpx;
	background: rgba(18,18,18,.54);
}

.plan-line {
	display: flex;
	align-items: flex-start;
	gap: 12rpx;
	color: #E6E6E6;
	font-size: 23rpx;
	line-height: 1.45;
}

.plan-line + .plan-line {
	margin-top: 12rpx;
}

.plan-dot {
	width: 12rpx;
	height: 12rpx;
	margin-top: 10rpx;
	border-radius: 50%;
	background: $brand-primary;
	flex: 0 0 auto;
}

@media screen and (max-width: 430px) {
	.live-match {
		padding: 24rpx 18rpx;
		gap: 8rpx;
	}

	.match-left,
	.match-right {
		width: 92rpx;
		flex-basis: 92rpx;
	}

	.tournament {
		font-size: 22rpx;
	}

	.player {
		font-size: 25rpx;
	}

	.status-button {
		min-width: 82rpx;
		padding: 8rpx 10rpx;
		font-size: 21rpx;
	}

	.shortcut-grid {
		grid-template-columns: repeat(2, 1fr);
	}

	.coach-data {
		grid-template-columns: 1fr;
	}

	.home-windows {
		grid-template-columns: 1fr;
	}
}

.coach-btn {
	width: 100%;
	min-height: 78rpx;
	margin-top: 22rpx;
	padding: 10rpx 24rpx;
	border-radius: 999rpx;
	background: $brand-primary;
	color: #121212;
	font-size: 28rpx;
	line-height: 1.25;
	font-weight: 900;
	text-align: center;
	white-space: normal;
	word-break: break-word;
}

.home-windows {
	margin: 0 24rpx 28rpx;
	display: grid;
	grid-template-columns: repeat(2, 1fr);
	gap: 16rpx;
}

.window-card {
	min-height: 260rpx;
	padding: 22rpx;
	border-radius: 18rpx;
	background: $bg-card;
	border: 1rpx solid $border-color;
	box-sizing: border-box;
}

.chat-window {
	background: linear-gradient(180deg, rgba(66,133,244,.16), #1E1E1E 72%);
}

.court-window {
	background: linear-gradient(180deg, rgba(204,255,0,.13), #1E1E1E 72%);
}

.window-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 12rpx;
}

.window-title {
	min-width: 0;
	color: $text-white;
	font-size: 30rpx;
	font-weight: 900;
	line-height: 1.25;
}

.window-link {
	flex: 0 0 auto;
	color: $brand-primary;
	font-size: 22rpx;
	font-weight: 900;
}

.window-sub {
	display: block;
	margin-top: 18rpx;
	color: $text-white;
	font-size: 26rpx;
	font-weight: 800;
	line-height: 1.35;
}

.window-desc {
	display: block;
	margin-top: 8rpx;
	color: $text-gray;
	font-size: 22rpx;
	line-height: 1.45;
}

.chat-bubble-row {
	margin-top: 18rpx;
	display: flex;
	flex-direction: column;
	gap: 10rpx;
}

.bubble {
	max-width: 100%;
	padding: 10rpx 14rpx;
	border-radius: 14rpx;
	background: #2C2C2E;
	color: #D8D8D8;
	font-size: 21rpx;
	line-height: 1.35;
	align-self: flex-start;
	word-break: break-word;
}

.bubble.mine {
	background: rgba(204,255,0,.18);
	color: $brand-primary;
	align-self: flex-end;
}

.court-item {
	margin-top: 16rpx;
	padding-top: 14rpx;
	border-top: 1rpx solid $border-color;
}

.court-name {
	display: block;
	color: $text-white;
	font-size: 23rpx;
	font-weight: 800;
	line-height: 1.35;
}

.court-meta {
	display: block;
	margin-top: 6rpx;
	color: $text-gray;
	font-size: 20rpx;
	line-height: 1.35;
}

@keyframes blink {
	0%, 100% {
		opacity: 1;
	}
	50% {
		opacity: 0.25;
	}
}

</style>
