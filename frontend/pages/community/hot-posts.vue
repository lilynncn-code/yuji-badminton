<template>
	<view class="page">
		<view class="hero" @click="openHero" :hover-class="'click-feedback'">
			<text class="eyebrow">{{ $tr("热门帖子") }}</text>
			<text class="title">{{ $tr("中羽热帖") }}</text>
			<text class="sub">{{ $tr("装备争议、打法复盘、同城局情报") }}</text>
		</view>
		<view class="header">
			<text class="section-title">{{ $tr("热门排行") }}</text>
		</view>
		<view class="tabs">
			<text v-for="tab in tabs" :key="tab" class="tab" :class="{ active: activeTab === tab }" @click="activeTab = tab">{{ $tr(tab) }}</text>
		</view>
		<view v-for="post in filteredPosts" :key="post.id" class="post" :hover-class="'click-feedback'" @click="openPost(post)">
			<image class="cover" :src="post.cover" mode="aspectFill" />
			<view class="body">
				<view class="tag">{{ $tr(post.tag) }}</view>
				<text class="post-title">{{ $tr(post.title) }}</text>
				<text class="meta">{{ $tr("{0} 条讨论 · {1} 热度", [post.comments, post.heat]) }}</text>
			</view>
		</view>
	</view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { imageLibrary } from '../../data/app-data'

const tabs = ['全部', '器材', '打法', '约球']
const activeTab = ref('全部')
const posts = [
	{ id: 1, cover: imageLibrary[4].url, tag: '器材', title: '进攻拍是不是一定要高磅？顺义球友实测 4 款球线', comments: 86, heat: 9280 },
	{ id: 2, cover: imageLibrary[0].url, tag: '打法', title: '双打第三拍抢网，慢半拍到底是脚步还是意识？', comments: 121, heat: 13500 },
	{ id: 3, cover: imageLibrary[2].url, tag: '约球', title: '周末顺义新馆体验：灯光、地胶、风口完整反馈', comments: 54, heat: 6200 }
]

const filteredPosts = computed(() => activeTab.value === '全部' ? posts : posts.filter((post) => post.tag === activeTab.value))

function openPost(post) {
	uni.showModal({
		title: post.tag,
		content: `${post.title}\n${post.comments} 条讨论 · ${post.heat} 热度`,
		showCancel: false
	})
}

function openHero() {
	uni.showModal({
		title: '热帖首页',
		content: '这里可以切换话题、浏览帖子和查看热门讨论。',
		showCancel: false
	})
}
</script>

<style lang="scss" scoped>
.page { min-height: 100vh; padding: 36rpx 24rpx calc(40rpx + env(safe-area-inset-bottom)); background: #121212; color: #FFFFFF; }
.hero { margin-bottom: 18rpx; padding: 24rpx; border-radius: 18rpx; background: #1E1E1E; border: 1rpx solid #2C2C2E; }
.eyebrow { display: block; color: #CCFF00; font-size: 22rpx; font-weight: 900; }
.title { display: block; margin-top: 8rpx; color: #FFFFFF; font-size: 44rpx; font-weight: 900; }
.sub { display: block; margin-top: 10rpx; color: #8E8E93; font-size: 24rpx; }
.header { margin: 10rpx 0 18rpx; }
.section-title { display: block; color: #FFFFFF; font-size: 28rpx; font-weight: 800; }
.tabs { display: flex; gap: 12rpx; margin-bottom: 18rpx; }
.tab { flex: 1; height: 60rpx; border-radius: 999rpx; background: #1E1E1E; border: 1rpx solid #2C2C2E; color: #8E8E93; display: flex; align-items: center; justify-content: center; font-size: 24rpx; }
.tab.active { background: rgba(204,255,0,.14); color: #CCFF00; border-color: rgba(204,255,0,.35); }
.post { margin-bottom: 22rpx; border-radius: 18rpx; background: #1E1E1E; overflow: hidden; border: 1rpx solid #2C2C2E; }
.cover { width: 100%; height: 260rpx; }
.body { padding: 22rpx; }
.tag { display: inline-flex; padding: 7rpx 12rpx; border-radius: 8rpx; background: rgba(204,255,0,.1); color: #CCFF00; font-size: 22rpx; }
.post-title { display: block; margin-top: 14rpx; color: #FFFFFF; font-size: 30rpx; font-weight: 800; line-height: 42rpx; }
.meta { display: block; margin-top: 14rpx; color: #8E8E93; font-size: 24rpx; }
</style>
