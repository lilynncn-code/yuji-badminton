<template>
	<view class="page">
		<view class="top">
			<text class="title">{{ $tr("球星排名") }}</text>
			<text class="sub">{{ $tr("更新至 {0}", [updateState.date]) }}</text>
		</view>
		<view class="update-card">
			<view>
				<text class="update-title">{{ $tr(updateState.title) }}</text>
				<text class="update-desc">{{ $tr(updateMessage) }}</text>
			</view>
			<button class="refresh-btn" @click="refreshRanking">{{ $tr("刷新") }}</button>
		</view>
		<view class="search-bar">
			<text class="search-icon">{{ $tr("⌕") }}</text>
			<input
				class="search-input"
				:value="searchText"
				:placeholder='$tr("搜索球员、国家、双打组合")'
				placeholder-class="search-placeholder"
				confirm-type="search"
				@input="handleSearchInput"
			/>
		</view>
		<view class="quick-row">
			<text class="quick" :class="{ active: onlyFollowing }" @click="onlyFollowing = !onlyFollowing">{{ $tr("我的关注") }}</text>
			<text class="quick" @click="searchText = ''">{{ $tr("清空搜索") }}</text>
		</view>
		<view class="tabs">
			<text v-for="group in rankingGroups" :key="group.key" class="tab" :class="{ active: activeKey === group.key }" @click="activeKey = group.key">{{ $tr(group.label) }}</text>
		</view>
		<view class="podium">
			<view v-for="player in visiblePlayers.slice(0, 3)" :key="player.rank" class="podium-card" :class="'rank-' + player.rank" @click="openPlayer(player)" :hover-class="'click-feedback'">
				<view class="rank-medal">{{ $tr("#{0}", [player.rank]) }}</view>
				<text class="rank">{{ $tr("#{0}", [player.rank]) }}</text>
				<text class="name">{{ $tr(player.name) }}</text>
				<text class="score">{{ $tr("{0} pts", [player.points]) }}</text>
				<text class="country">{{ $tr(player.country) }}</text>
			</view>
		</view>
		<view class="list">
			<view v-for="player in visiblePlayers" :key="player.rank" class="row" :hover-class="'click-feedback'" @click="openPlayer(player)">
				<text class="row-rank">{{ $tr(player.rank) }}</text>
				<view class="row-main">
					<text class="row-name">{{ $tr(player.name) }}</text>
					<text class="row-meta">{{ $tr("{0} · {1} pts", [player.country, player.points]) }}</text>
				</view>
				<text class="favorite" @click.stop="toggleFollow(player)">{{ following[player.name] ? '★' : '☆' }}</text>
				<text class="trend">{{ $tr(player.trend) }}</text>
			</view>
		</view>
		<view v-if="selectedPlayer" class="mask" @click="selectedPlayer = null">
			<view class="player-panel" @click.stop>
				<view class="player-body">
					<text class="panel-rank">{{ $tr("#{0} · {1}", [selectedPlayer.rank, activeGroupLabel]) }}</text>
					<text class="panel-name">{{ $tr(selectedPlayer.name) }}</text>
					<text class="panel-meta">{{ $tr("{0} · {1} pts", [selectedPlayer.country, selectedPlayer.points]) }}</text>
					<text class="panel-bio">{{ $tr(selectedPlayer.bio) }}</text>
					<view class="action-row">
						<button class="ghost-btn" @click="toggleFollow(selectedPlayer)">{{ $tr(following[selectedPlayer.name] ? '取消关注' : '关注球星') }}</button>
						<button class="follow-btn" @click="chatPlayer(selectedPlayer)">{{ $tr(chatButtonLabel(selectedPlayer)) }}</button>
					</view>
				</view>
			</view>
		</view>
	</view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { translate } from '../../utils/translate'
import { onLoad, onShow } from '@dcloudio/uni-app'
import { rankingGroups } from '../../data/app-data'
import { openExternal } from '../../utils/external'
import { accountKey } from '../../utils/request'
import { getDailyRankingUpdate } from '../../utils/daily-update'

const activeKey = ref('ms')
const updateState = ref(getDailyRankingUpdate())
const updateMessage = ref('历史资料')
const selectedPlayer = ref(null)
const following = ref(uni.getStorageSync(accountKey('star-following')) || {})
const searchText = ref('')
const onlyFollowing = ref(false)
const activePlayers = computed(() => rankingGroups.find((group) => group.key === activeKey.value)?.players || [])
const activeGroupLabel = computed(() => rankingGroups.find((group) => group.key === activeKey.value)?.label || '排名')
const visiblePlayers = computed(() => {
	const keyword = searchText.value.trim().toLowerCase()
	return activePlayers.value.filter((player) => {
		const matchesSearch = !keyword || [player.name, player.country].flatMap(value => [value, translate(value)]).join(' ').toLowerCase().includes(keyword)
		const matchesFollow = !onlyFollowing.value || following.value[player.name]
		return matchesSearch && matchesFollow
	})
})

function openPlayer(player) {
	selectedPlayer.value = player
}

function toggleFollow(player) {
	following.value = { ...following.value, [player.name]: !following.value[player.name] }
	uni.setStorageSync(accountKey('star-following'), following.value)
	uni.showToast({ title: following.value[player.name] ? `已关注 ${player.name}` : `已取消关注 ${player.name}`, icon: 'none' })
}

function chatButtonLabel() { return '找注册球友聊天' }
function chatPlayer() { uni.switchTab({ url: '/pages/match-making/match-making' }) }
function refreshRanking() { openExternal('https://bwfbadminton.com/rankings/') }
function handleSearchInput(event) {
	searchText.value = event.detail.value
}

onLoad((query) => {
	if (query.group && rankingGroups.some((group) => group.key === query.group)) {
		activeKey.value = query.group
	}
	if (query.keyword) {
		searchText.value = decodeURIComponent(query.keyword)
	}
})

onShow(() => {
	updateState.value = getDailyRankingUpdate()
})
</script>

<style lang="scss" scoped>
.page { min-height: 100vh; background: #121212; color: #FFFFFF; padding: 36rpx 24rpx calc(36rpx + env(safe-area-inset-bottom)); box-sizing: border-box; }
.top { margin-bottom: 24rpx; }
.title { display: block; color: #CCFF00; font-size: 44rpx; font-weight: 900; }
.sub { display: block; margin-top: 10rpx; color: #8E8E93; font-size: 24rpx; }
.update-card { min-height: 104rpx; margin-bottom: 18rpx; padding: 18rpx 20rpx; border-radius: 16rpx; background: #1E1E1E; border: 1rpx solid rgba(204,255,0,.22); display: flex; align-items: center; justify-content: space-between; gap: 18rpx; box-sizing: border-box; }
.update-title { display: block; color: #FFFFFF; font-size: 27rpx; font-weight: 900; }
.update-desc { display: block; margin-top: 8rpx; color: #8E8E93; font-size: 22rpx; line-height: 1.35; }
.refresh-btn { flex: 0 0 auto; height: 60rpx; padding: 0 22rpx; border-radius: 999rpx; background: #CCFF00; color: #121212; font-size: 24rpx; font-weight: 900; }
.search-bar { height: 76rpx; margin-bottom: 16rpx; padding: 0 20rpx; border-radius: 16rpx; background: #1E1E1E; border: 1rpx solid #2C2C2E; display: flex; align-items: center; gap: 12rpx; color: #8E8E93; font-size: 25rpx; }
.search-icon { color: #CCFF00; font-size: 30rpx; }
.search-input { flex: 1; height: 76rpx; color: #FFFFFF; font-size: 25rpx; }
.search-placeholder { color: #8E8E93; font-size: 25rpx; }
.quick-row { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12rpx; margin-bottom: 18rpx; }
.quick { height: 58rpx; border-radius: 999rpx; background: #1E1E1E; color: #8E8E93; display: flex; align-items: center; justify-content: center; font-size: 23rpx; border: 1rpx solid #2C2C2E; }
.quick.active { background: rgba(204,255,0,.14); color: #CCFF00; border-color: rgba(204,255,0,.45); }
.tabs { display: flex; gap: 14rpx; margin-bottom: 26rpx; }
.tab { flex: 1; height: 64rpx; border-radius: 999rpx; background: #1E1E1E; color: #8E8E93; display: flex; align-items: center; justify-content: center; font-size: 26rpx; }
.tab.active { background: #CCFF00; color: #121212; font-weight: 900; }
.podium { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16rpx; align-items: end; margin-bottom: 28rpx; }
.podium-card { position: relative; min-height: 250rpx; padding: 22rpx 10rpx; border-radius: 16rpx; background: #1E1E1E; display: flex; flex-direction: column; align-items: center; border: 1rpx solid #2C2C2E; box-sizing: border-box; }
.rank-1 { min-height: 300rpx; border-color: rgba(204,255,0,.5); }
.rank-medal { width: 108rpx; height: 108rpx; border-radius: 50%; background: rgba(204,255,0,.12); color: #CCFF00; display: flex; align-items: center; justify-content: center; font-size: 32rpx; font-weight: 900; border: 2rpx solid rgba(204,255,0,.35); }
.rank { margin-top: 12rpx; color: #CCFF00; font-size: 28rpx; font-weight: 900; }
.name { margin-top: 12rpx; font-size: 25rpx; font-weight: 800; text-align: center; line-height: 1.3; }
.score, .country { margin-top: 8rpx; color: #8E8E93; font-size: 20rpx; text-align: center; }
.list { border-radius: 18rpx; overflow: hidden; background: #1E1E1E; border: 1rpx solid #2C2C2E; }
.row { min-height: 100rpx; padding: 0 24rpx; display: flex; align-items: center; border-bottom: 1rpx solid #2C2C2E; }
.row:last-child { border-bottom: 0; }
.row-rank { width: 70rpx; color: #8E8E93; font-size: 26rpx; }
.row-main { flex: 1; min-width: 0; }
.row-name { display: block; font-size: 28rpx; font-weight: 800; }
.row-meta { display: block; margin-top: 6rpx; color: #8E8E93; font-size: 22rpx; }
.favorite { width: 42rpx; color: #CCFF00; font-size: 30rpx; text-align: center; }
.trend { color: #CCFF00; font-size: 23rpx; margin-left: 10rpx; }
.mask { position: fixed; inset: 0; z-index: 20; display: flex; align-items: flex-end; background: rgba(0,0,0,.58); }
.player-panel { width: 100%; max-height: 86vh; border-radius: 26rpx 26rpx 0 0; background: #181818; overflow: hidden; }
.player-body { padding: 26rpx 24rpx calc(30rpx + env(safe-area-inset-bottom)); }
.panel-rank { color: #CCFF00; font-size: 24rpx; font-weight: 900; }
.panel-name { display: block; margin-top: 8rpx; font-size: 42rpx; font-weight: 900; }
.panel-meta, .panel-bio, .photo-source { display: block; margin-top: 12rpx; color: #D8D8D8; font-size: 26rpx; line-height: 1.55; }
.panel-meta { color: #8E8E93; }
.photo-source { color: #8E8E93; font-size: 22rpx; }
.follow-btn { width: 100%; height: 78rpx; margin-top: 24rpx; border-radius: 999rpx; background: #CCFF00; color: #121212; font-size: 28rpx; font-weight: 900; }
.action-row { margin-top: 24rpx; display: grid; grid-template-columns: repeat(2, 1fr); gap: 12rpx; }
.ghost-btn { height: 78rpx; border-radius: 999rpx; background: #2C2C2E; color: #FFFFFF; font-size: 28rpx; font-weight: 900; }
.follow-btn { margin-top: 0; }
</style>
