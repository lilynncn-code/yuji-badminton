<template>
    <view class="page">
        <view class="hero">
            <image class="hero-img" :src="heroImage" mode="aspectFill" @error="failedHero = heroImage" />
            <view class="hero-mask"></view>
            <view class="hero-copy">
                <text class="eyebrow">{{ $tr(feed.historical ? '历史比赛' : '近期赛事') }}</text>
                <text class="title">{{ $tr(activeEvent?.name || '赛事签表') }}</text>
                <text class="sub">{{ $tr(activeEvent?.location || '查看赛事、轮次和比分') }}</text>
            </view>
        </view>
        <scroll-view class="content" scroll-y>
            <view class="update-wrap"><MatchUpdate :loading="loading" :error="error" :historical="feed.historical" :from-cache="feed.fromCache" :sync="feed.sync" :cached-at="feed.cacheSavedAt" @retry="load" /></view>
            <scroll-view v-if="feed.events.length" class="tabs-scroll" scroll-x>
                <view class="event-tabs"><text v-for="event in feed.events" :key="event.id" class="event-tab" :class="{ active: event.id === activeEvent?.id }" @click="selectEvent(event.id)">{{ $tr(event.name) }}</text></view>
            </scroll-view>
            <view v-if="activeEvent?.start_date" class="event-dates">{{ activeEvent.start_date }} — {{ activeEvent.end_date }}</view>
            <scroll-view v-if="rounds.length" class="tabs-scroll" scroll-x>
                <view class="round-tabs"><text v-for="round in rounds" :key="round" class="round" :class="{ active: round === selectedRound }" @click="activeRound = round">{{ $tr(round) }}</text></view>
            </scroll-view>
            <view v-if="filteredMatches.length" class="match-list">
                <view v-for="match in filteredMatches" :key="match.id" class="match-card" @click="openMatch(match)" :hover-class="'click-feedback'">
                    <image class="match-image" :src="match.displayImage || fallbackImage" mode="aspectFill" @error="match.displayImage = fallbackImage" />
                    <view class="match-body">
                        <view class="match-top"><text>{{ $tr(match.discipline) }} · {{ $tr(match.court || '场地待定') }}</text><text>{{ match.scheduled_at ? formatMatchUpdated(match.scheduled_at) : $tr('时间待定') }}</text></view>
                        <view class="player" :class="{ winner: match.winner === match.player1 }"><text>{{ $tr(match.player1) }}</text><text>{{ match.score1 }}</text></view>
                        <view class="player" :class="{ winner: match.winner === match.player2 }"><text>{{ $tr(match.player2) }}</text><text>{{ match.score2 }}</text></view>
                        <text class="score-text">{{ $tr(match.score_text || '暂无比分') }} · {{ $tr(matchStatusLabel(match.status)) }}</text>
                    </view>
                </view>
            </view>
            <view v-else-if="!loading" class="empty">{{ $tr(feed.fromCache ? '本机暂未保存该赛事的比赛，请联网后重新读取' : '该赛事暂时没有比赛') }}</view>
        </scroll-view>
    </view>
</template>
<script setup>
import { computed, ref } from 'vue'
import { onShow, onHide, onUnload } from '@dcloudio/uni-app'
import { MATCH_FALLBACK_IMAGE, formatMatchUpdated, matchStatusLabel } from '../../utils/match-api'
import { useMatchFeed } from '../../utils/match-feed'
import MatchUpdate from '../../components/MatchUpdate.vue'

const { data: feed, loading, error, load, leave } = useMatchFeed('events')
const fallbackImage = MATCH_FALLBACK_IMAGE
const activeEventId = ref(''), activeRound = ref(''), failedHero = ref('')
const activeEvent = computed(() => feed.value.events.find(event => event.id === activeEventId.value) || feed.value.events[0])
const eventMatches = computed(() => feed.value.items.filter(item => item.event_id === activeEvent.value?.id))
const rounds = computed(() => [...new Set(eventMatches.value.map(item => item.round))])
const selectedRound = computed(() => rounds.value.includes(activeRound.value) ? activeRound.value : rounds.value[0])
const filteredMatches = computed(() => eventMatches.value.filter(item => item.round === selectedRound.value))
const heroImage = computed(() => {
    const value = activeEvent.value?.image_url || eventMatches.value.find(item => item.image_url)?.image_url
    return value && value !== failedHero.value ? value : fallbackImage
})
function selectEvent(id) { activeEventId.value = id; activeRound.value = '' }
function openMatch(match) { uni.navigateTo({ url: `/pages/match/detail?id=${encodeURIComponent(match.id)}` }) }
onShow(load); onHide(leave); onUnload(leave)
</script>
<style lang="scss" scoped>
.page{min-height:100vh;background:#121212;color:#fff;padding-bottom:env(safe-area-inset-bottom)}
.hero{position:relative;height:330rpx;overflow:hidden}.hero-img{width:100%;height:100%;background:#2c2c2e}.hero-mask{position:absolute;inset:0;background:linear-gradient(180deg,rgba(18,18,18,.05),rgba(18,18,18,.94))}.hero-copy{position:absolute;left:32rpx;right:32rpx;bottom:30rpx;display:flex;flex-direction:column}.eyebrow{color:#ccff00;font-size:23rpx;font-weight:800}.title{margin-top:8rpx;font-size:38rpx;font-weight:900;overflow-wrap:anywhere}.sub{margin-top:8rpx;color:#d8d8d8;font-size:23rpx}
.content{height:calc(100vh - 330rpx - 44px - env(safe-area-inset-bottom))}.update-wrap{margin:20rpx 24rpx}.tabs-scroll{width:100%;white-space:nowrap}.event-tabs,.round-tabs{display:inline-flex;gap:14rpx;padding:8rpx 24rpx 14rpx}.event-tab,.round{flex-shrink:0;padding:14rpx 20rpx;border-radius:999rpx;background:#1e1e1e;color:#aaa;font-size:24rpx}.event-tab.active,.round.active{background:#ccff00;color:#121212;font-weight:900}.event-dates{margin:8rpx 24rpx 16rpx;color:#aaa;font-size:23rpx}.match-list{padding:18rpx 24rpx 40rpx}.match-card{margin-bottom:18rpx;border-radius:16rpx;background:#1e1e1e;border:1rpx solid #2c2c2e;overflow:hidden}.match-image{width:100%;height:210rpx;background:#2c2c2e}.match-body{padding:18rpx}.match-top{display:flex;justify-content:space-between;gap:12rpx;color:#aaa;font-size:22rpx}.match-top text{min-width:0;overflow-wrap:anywhere}.player{min-height:62rpx;margin-top:10rpx;padding:10rpx 16rpx;display:flex;align-items:center;justify-content:space-between;gap:18rpx;color:#aaa;border-radius:10rpx;font-size:26rpx}.player text:first-child{flex:1;min-width:0;overflow-wrap:anywhere}.player.winner{color:#fff;background:rgba(204,255,0,.1);font-weight:900}.score-text{display:block;margin-top:12rpx;color:#ccff00;font-size:22rpx}.empty{padding:60rpx 24rpx;color:#aaa;text-align:center;font-size:25rpx}
</style>
