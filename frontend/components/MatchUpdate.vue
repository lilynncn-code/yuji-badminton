<template>
    <view class="match-update" :class="{ stale: historical || fromCache || error || sync.using_old_data }" aria-live="polite">
        <view class="update-copy">
            <text class="update-title">{{ $tr(loading ? '正在更新比赛' : historical ? '内置历史比赛，供离线查看' : (error || fromCache || sync.using_old_data) ? '暂时无法更新，显示上次成功内容' : '已读取后台比赛') }}</text>
            <text v-if="historical" class="update-line">{{ $tr('资料日期：2026年5月，不是最新比赛') }}</text>
            <text v-else class="update-line">{{ $tr('最近成功更新：') }}{{ $tr(formatMatchUpdated(sync.latest_updated_at)) }}</text>
            <text v-if="!historical && sync.source_updated_at" class="update-line">{{ $tr('来源更新时间：') }}{{ $tr(formatMatchUpdated(sync.source_updated_at)) }}</text>
            <text v-if="!historical && cachedAt" class="update-line">{{ $tr('本机保存：') }}{{ $tr(formatMatchUpdated(cachedAt)) }}</text>
            <text v-if="error || sync.last_error" class="update-line">{{ $tr(error || sync.last_error) }}</text>
        </view>
        <button class="match-retry" :disabled="loading" @click="$emit('retry')">{{ $tr('重新读取') }}</button>
    </view>
</template>
<script setup>
import { formatMatchUpdated } from '../utils/match-api'
defineProps({ loading: Boolean, historical: Boolean, fromCache: Boolean, error: { type: String, default: '' }, sync: { type: Object, default: () => ({}) }, cachedAt: { type: String, default: '' } })
defineEmits(['retry'])
</script>
<style scoped>
.match-update{padding:16rpx 18rpx;border-radius:16rpx;background:#1e1e1e;border:1rpx solid #454b2b;display:flex;align-items:center;gap:16rpx;color:#a9afa3;font-size:22rpx;line-height:1.5}.match-update.stale{border-color:#68512f;color:#ffd08a}.update-copy{flex:1;min-width:0;overflow-wrap:anywhere}.update-title,.update-line{display:block}.update-title{color:#eee;font-weight:700}.update-line{margin-top:5rpx}.match-retry{flex:0 0 126rpx;min-height:60rpx;margin:0;padding:10rpx 12rpx;border-radius:28rpx;background:#ccff00;color:#121212;font-size:23rpx;line-height:1.4}.match-retry[disabled]{background:#3f492a;color:#c4ccab}
</style>
