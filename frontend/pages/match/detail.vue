<template>
    <view class="page">
        <view class="update-wrap"><MatchUpdate :loading="loading" :error="error" :historical="historical" :from-cache="fromCache" :sync="sync" :cached-at="cachedAt" @retry="load" /></view>
        <view v-if="unavailable || (!match && !loading)" class="state error-state">
            <text>{{ $tr(unavailable ? '比赛不存在或已被来源移除，请返回赛事页查看' : '暂时没有这场比赛的已保存内容') }}</text>
            <button class="back-btn" @click="backToBracket">{{ $tr('返回赛事页') }}</button>
        </view>
        <template v-if="match && !unavailable">
            <image class="hero" :src="match.displayImage || fallbackImage" mode="aspectFill" @error="match.displayImage = fallbackImage" />
            <view class="scoreboard">
                <text class="live">{{ $tr(matchStatusLabel(match.status)) }}</text>
                <text class="title">{{ $tr(match.event_name) }} · {{ $tr(match.discipline) }} · {{ $tr(match.round) }}</text>
                <view class="players">
                    <view class="player" :class="{ winner: match.winner === match.player1 }"><text>{{ $tr(match.player1) }}</text><text class="set">{{ match.score1 }}</text></view>
                    <text class="score">{{ match.score_text || $tr('暂无比分') }}</text>
                    <view class="player" :class="{ winner: match.winner === match.player2 }"><text>{{ $tr(match.player2) }}</text><text class="set">{{ match.score2 }}</text></view>
                </view>
                <text class="set-score">{{ match.scheduled_at ? formatMatchUpdated(match.scheduled_at) : $tr('时间待定') }} · {{ $tr(match.court || '场地待定') }}</text>
            </view>
            <view class="stats"><view v-for="item in stats" :key="item.label" class="stat"><text class="value">{{ $tr(item.value) }}</text><text class="label">{{ $tr(item.label) }}</text></view></view>
            <view class="timeline">
                <view class="event"><text class="time">{{ $tr('状态') }}</text><text class="event-text">{{ $tr(matchStatusLabel(match.status)) }}</text></view>
                <view class="event"><text class="time">{{ $tr('报道') }}</text><text class="event-text">{{ $tr(match.report || '暂无报道') }}</text></view>
            </view>
            <view class="source">
                <text v-if="match.image_source" class="source-line">{{ $tr(match.image_source) }}</text>
                <button v-if="match.source_url" class="source-btn" @click="openSource">{{ $tr('查看比赛来源') }}</button>
                <button v-if="match.replay_url" class="replay-btn" @click="openReplay">{{ $tr('打开官方回放') }}</button>
                <button class="back-btn" @click="backToBracket">{{ $tr('返回赛事页') }}</button>
            </view>
        </template>
    </view>
</template>
<script setup>
import { computed, ref } from 'vue'
import { onLoad, onShow, onHide, onUnload } from '@dcloudio/uni-app'
import { MATCH_FALLBACK_IMAGE, fetchMatch, readCachedMatch, historicalMatches, formatMatchUpdated, matchStatusLabel } from '../../utils/match-api'
import { openExternal } from '../../utils/external'
import MatchUpdate from '../../components/MatchUpdate.vue'

const fallbackImage = MATCH_FALLBACK_IMAGE
const matchId = ref(''), match = ref(null), sync = ref({}), loading = ref(false), error = ref('')
const historical = ref(false), fromCache = ref(false), cachedAt = ref(''), unavailable = ref(false)
let readId = 0
const stats = computed(() => match.value ? [{ label: '项目', value: match.value.discipline || '待定' }, { label: '胜者', value: match.value.winner || '待定' }, { label: '轮次', value: match.value.round || '待定' }] : [])
function backToBracket() { uni.redirectTo({ url: '/pages/tournament/bracket' }) }
function openReplay() { if (match.value?.replay_url) openExternal(match.value.replay_url) }
function openSource() { if (match.value?.source_url) openExternal(match.value.source_url) }
function leave() { readId++; loading.value = false }
function restore() {
    const cached = readCachedMatch(matchId.value)
    if (cached) {
        match.value = cached.item; sync.value = cached.sync || {}; cachedAt.value = cached.cacheSavedAt; fromCache.value = true
    } else if (matchId.value.startsWith('history-')) {
        match.value = historicalMatches().items.find(item => item.id === matchId.value) || null
        historical.value = !!match.value
    }
}
async function load() {
    const current = ++readId, isCurrent = () => current === readId
    loading.value = true; error.value = ''
    try {
        if (!matchId.value) { unavailable.value = true; return }
        const data = await fetchMatch(matchId.value, { isCurrent })
        if (!isCurrent()) return
        match.value = data.item; sync.value = data.sync; fromCache.value = false; historical.value = false; unavailable.value = false; cachedAt.value = ''
    } catch (e) {
        if (!isCurrent() || e.stale) return
        if (e.status === 404 && !historical.value) { match.value = null; unavailable.value = true; sync.value = {}; fromCache.value = false }
        else { error.value = e.status === 404 ? '当前查看的是内置历史比赛，请返回赛事页读取最新内容' : e.message || '比赛读取失败'; if (!historical.value && match.value) fromCache.value = true }
    } finally { if (isCurrent()) loading.value = false }
}
onLoad(query => { matchId.value = String(query?.id || ''); restore() })
onShow(load); onHide(leave); onUnload(leave)
</script>
<style lang="scss" scoped>
.page{min-height:100vh;background:#121212;color:#fff;padding:0 24rpx 36rpx;box-sizing:border-box}.update-wrap{padding:20rpx 0}.hero{width:calc(100% + 48rpx);height:330rpx;margin-left:-24rpx;background:#2c2c2e}.scoreboard{margin-top:-42rpx;position:relative;z-index:2;padding:26rpx 20rpx;border-radius:22rpx;background:#1e1e1e;border:1rpx solid rgba(204,255,0,.18)}.live{color:#ccff00;font-size:24rpx;font-weight:900}.title{display:block;margin-top:10rpx;color:#d8d8d8;font-size:24rpx;line-height:1.4}.players{margin-top:24rpx;display:flex;align-items:stretch;justify-content:space-between;gap:12rpx}.player{flex:1;min-width:0;min-height:118rpx;padding:18rpx 10rpx;border-radius:14rpx;background:#242424;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10rpx;font-size:26rpx;font-weight:900;text-align:center;overflow-wrap:anywhere}.player.winner{background:rgba(204,255,0,.12);color:#ccff00}.set{color:#aaa;font-size:22rpx}.score{flex:0 1 150rpx;min-width:0;color:#fff;font-size:24rpx;font-weight:900;display:flex;align-items:center;justify-content:center;text-align:center;line-height:1.5;overflow-wrap:anywhere}.set-score{display:block;margin-top:24rpx;text-align:center;color:#aaa;font-size:24rpx}.stats{margin:24rpx 0;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14rpx}.stat{min-height:112rpx;padding:18rpx 10rpx;border-radius:16rpx;background:#1e1e1e;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;overflow-wrap:anywhere}.value{color:#ccff00;font-size:24rpx;font-weight:900;line-height:1.4}.label{margin-top:8rpx;color:#aaa;font-size:22rpx}.timeline{border-radius:18rpx;background:#1e1e1e;overflow:hidden}.event{padding:24rpx;border-bottom:1rpx solid #2c2c2e;display:flex;gap:18rpx}.time{flex:0 0 60rpx;color:#ccff00;font-size:24rpx;font-weight:900}.event-text{flex:1;min-width:0;overflow-wrap:anywhere;color:#fff;font-size:26rpx;line-height:38rpx}.source{margin-top:22rpx;padding:22rpx;border-radius:16rpx;background:#1e1e1e;border:1rpx solid #2c2c2e;color:#d8d8d8;font-size:24rpx;line-height:1.5}.source-line{display:block;overflow-wrap:anywhere}.replay-btn,.source-btn,.back-btn{width:100%;min-height:70rpx;margin-top:18rpx;padding:14rpx;border-radius:28rpx;background:#ccff00;color:#121212;font-size:25rpx;font-weight:900}.state{padding:70rpx 28rpx;text-align:center;color:#aaa;font-size:28rpx}.error-state{display:flex;flex-direction:column;align-items:stretch}.back-btn{background:#2c2c2e;color:#fff}
</style>
