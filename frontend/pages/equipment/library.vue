<template>
	<view class="page">
		<view class="hero">
			<image class="hero-img" :src="heroImage" mode="aspectFill" />
			<view class="hero-copy">
				<text class="title">{{ $tr("智能器材库") }}</text>
				<text class="sub">{{ $tr("尤尼克斯、李宁、熏风、胜利、川崎装备分类") }}</text>
			</view>
		</view>

		<scroll-view class="category-row" scroll-x>
			<text
				v-for="category in categories"
				:key="category"
				class="category"
				:class="{ active: activeCategory === category }"
				@click="activeCategory = category"
				:hover-class="'click-feedback'"
			>
				{{ $tr(category) }}
			</text>
		</scroll-view>

		<view class="brand-row">
			<text
				v-for="brand in brands"
				:key="brand"
				class="brand"
				:class="{ active: activeBrand === brand }"
				@click="activeBrand = brand"
			>
				{{ $tr(brand) }}
			</text>
		</view>

		<view class="tools">
            <input v-model="search" :placeholder='$tr("搜索名称、简介")' maxlength="80" />
            <view class="tool-row"><button @click="onlySaved=!onlySaved">{{ $tr(onlySaved?'查看全部':'我的收藏') }}</button><button @click="showCompare=!showCompare">{{ $tr("比较已选 {0} 件", [compared.length]) }}</button></view>
            <picker :range="needs.map(item => $tr(item))" @change="need=needs[$event.detail.value]"><view class="need">{{ $tr("按简介选用途：{0}", [need]) }}</view></picker>
            <text class="note">{{ $tr("资料是本地参考，价格和尺寸会因门店、时间、尺码而变化，请购买前再核实。") }}</text>
            <text v-if="loadingSaved" class="note">{{ $tr("正在读取本人的收藏…") }}</text>
            <text v-if="loadError" class="note">{{ $tr(loadError) }}<text @click="loadSaved">{{ $tr("· 重试读取收藏") }}</text></text>
            <text v-if="saveError" class="note">{{ $tr(saveError) }}</text>
            <view v-if="showCompare" class="compare"><view v-for="item in compareItems" :key="item.id"><text class="name">{{ $tr(item.name) }}</text><text class="note">{{ $tr("{0} · {1}", [item.brand, item.category]) }}</text><text class="note">{{ $tr(item.desc) }}</text><text class="spec-line">{{ $tr("参考价：{0}", [item.price]) }}</text><text class="spec-line">{{ $tr("重量：{0}", [item.weight]) }}</text><text class="spec-line">{{ $tr("规格：{0}", [item.spec]) }}</text><text class="note">{{ $tr("适合：{0}", [item.suitable]) }}</text><button @click="toggleCompare(item)">{{ $tr("移出比较") }}</button></view><text v-if="!compared.length" class="note">{{ $tr("请在器材卡片中选择最多三件。") }}</text></view>
        </view>
        <view class="equipment-list">
            <text v-if="!filteredEquipment.length" class="note">{{ $tr("没有符合条件的器材，试试其他分类或用途。") }}</text>
			<view v-for="item in filteredEquipment" :key="item.id" class="equipment-card" @click="openEquipment(item)" :hover-class="'click-feedback'">
				<image class="equipment-img" :src="displayImage(item)" mode="aspectFit" @error="markImageFailed(item)" />
				<view class="info">
					<view class="meta-row">
						<text class="brand-pill">{{ $tr(item.brand) }}</text>
						<text class="category-pill">{{ $tr(item.category) }}</text>
					</view>
					<text class="name">{{ $tr(item.name) }}</text>
					<text class="desc">{{ $tr(item.desc) }}</text>
                    <text class="spec-line">{{ $tr("参考价：{0}", [item.price]) }}</text>
                    <text class="spec-line">{{ $tr("重量：{0}", [item.weight]) }}</text>
                    <view class="tool-row"><button :disabled="saving||loadingSaved||!savedReady" @click.stop="toggleSaved(item)">{{ $tr(!savedReady?'收藏状态待读取':saved.includes(item.id)?'已收藏':'收藏') }}</button><button @click.stop="toggleCompare(item)">{{ $tr(compared.includes(item.id)?'移出比较':'加入比较') }}</button></view>
				</view>
			</view>
		</view>

		<view v-if="selectedEquipment" class="mask" @click="selectedEquipment = null">
			<view class="panel" @click.stop>
				<image class="panel-img" :src="displayImage(selectedEquipment)" mode="aspectFit" @error="markImageFailed(selectedEquipment)" />
				<text class="panel-brand">{{ $tr("{0} · {1}", [selectedEquipment.brand, selectedEquipment.category]) }}</text>
				<text class="panel-name">{{ $tr(selectedEquipment.name) }}</text>
				<text class="panel-desc">{{ $tr(selectedEquipment.desc) }}</text>
				<text class="spec-line">{{ $tr("参考价：{0}", [selectedEquipment.price]) }}</text>
				<text class="spec-line">{{ $tr("重量：{0}", [selectedEquipment.weight]) }}</text>
				<text class="spec-line">{{ $tr("规格：{0}", [selectedEquipment.spec]) }}</text>
				<text class="spec-line">{{ $tr("适合：{0}", [selectedEquipment.suitable]) }}</text>
				<text class="panel-usage">{{ $tr("使用建议：{0}", [selectedEquipment.usage]) }}</text>
				<button class="close-btn" @click="selectedEquipment = null">{{ $tr("关闭") }}</button>
			</view>
		</view>
	</view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { translate } from '../../utils/translate'
import { onShow,onHide,onUnload } from '@dcloudio/uni-app'
import { getUser } from '../../utils/store'
import { getAuthToken } from '../../utils/auth'
import { getFavorites, setFavorite } from '../../utils/social-api'
import { badmintonEquipment, equipmentCategories, equipmentFallbackImages } from '../../data/app-data'

const search=ref(''), onlySaved=ref(false), saved=ref([]), saving=ref(false), loadError=ref(''), compared=ref([]), showCompare=ref(false), need=ref('全部')
const loadingSaved=ref(false),savedReady=ref(false),saveError=ref('')
let owner='',token='',active=false,pageGeneration=0,readGeneration=0,pendingSave=null
function context(){return {owner,token,page:pageGeneration}}
function sameOwner(c){return c.owner===owner&&c.owner===String(getUser()?.id||'')&&c.token===getAuthToken()}
function current(c){return active&&c.page===pageGeneration&&sameOwner(c)}
const needs=['全部','入门训练','双打衔接','进攻发力','稳定支撑']
const words={'入门训练':['训练','入门','日常'],'双打衔接':['双打','衔接','连贯'],'进攻发力':['进攻','重杀','突击'],'稳定支撑':['支撑','稳定','防守']}
const compareItems=computed(()=>badmintonEquipment.filter(i=>compared.value.includes(i.id)))
onShow(()=>{
    const next=String(getUser()?.id||''),nextToken=getAuthToken()
    if(next!==owner||nextToken!==token){owner=next;token=nextToken;saved.value=[];savedReady.value=false;compared.value=[];showCompare.value=false;onlySaved.value=false;selectedEquipment.value=null;loadError.value='';saveError.value=''}
    active=true;pageGeneration++;saving.value=Boolean(pendingSave&&sameOwner(pendingSave));if(!saving.value)loadSaved()
})
function leave(){active=false;pageGeneration++;readGeneration++;loadingSaved.value=false}
onHide(leave);onUnload(leave)
async function loadSaved(){
    if(!active||saving.value)return
    const c=context(),generation=++readGeneration;loadingSaved.value=true;loadError.value=''
    try{const data=await getFavorites('equipment');if(current(c)&&generation===readGeneration){saved.value=data.items;savedReady.value=true}}
    catch(e){if(current(c)&&generation===readGeneration){savedReady.value=false;loadError.value=e.message||'收藏读取失败，请重试'}}
    finally{if(current(c)&&generation===readGeneration)loadingSaved.value=false}
}
async function toggleSaved(item){
    if(!active||saving.value||loadingSaved.value||!savedReady.value||!sameOwner(context()))return
    const c=context(),value=!saved.value.includes(item.id);pendingSave=c;saving.value=true;saveError.value='';readGeneration++
    try{await setFavorite('equipment',item.id,value);if(active&&sameOwner(c)){saved.value=value?[...new Set([...saved.value,item.id])]:saved.value.filter(id=>id!==item.id);loadError.value=''}}
    catch(e){if(active&&sameOwner(c))saveError.value=e.message||'收藏尚未确认，请核对状态后重试'}
    finally{if(pendingSave===c)pendingSave=null;if(active&&sameOwner(c)){saving.value=false;loadSaved()}}
}
function toggleCompare(item){if(compared.value.includes(item.id)){compared.value=compared.value.filter(id=>id!==item.id);return}if(compared.value.length>=3){uni.showToast({title:'最多比较三件器材',icon:'none'});return}compared.value.push(item.id)}
const categories = ['全部', ...equipmentCategories]
const brands = ['全部', '尤尼克斯', '李宁', '熏风', '胜利', '川崎']
const activeCategory = ref('全部')
const activeBrand = ref('全部')
const selectedEquipment = ref(null)
const failedImages = ref({})
const heroImage = equipmentFallbackImages.hero

const filteredEquipment = computed(() => badmintonEquipment.filter((item) => {
	const categoryOk = activeCategory.value === '全部' || item.category === activeCategory.value
	const brandOk = activeBrand.value === '全部' || item.brand === activeBrand.value
	const searchable = [item.name, item.desc, item.brand].flatMap(value => [value, translate(value)]).join(' ').toLowerCase()
	return categoryOk && brandOk && (!onlySaved.value || saved.value.includes(item.id)) && (!search.value.trim() || searchable.includes(search.value.trim().toLowerCase())) && (need.value==='全部' || words[need.value].some(word=>item.desc.includes(word)))
}))

function displayImage(item) {
	return failedImages.value[item.id] ? '/static/logo.png' : item.image
}

function markImageFailed(item) {
	failedImages.value = { ...failedImages.value, [item.id]: true }
}

function openEquipment(item) {
	selectedEquipment.value = item
}
</script>

<style lang="scss" scoped>
.tools{padding:0 24rpx 24rpx}.tools input{background:#282828;padding:20rpx;border-radius:14rpx;color:white;font-size:26rpx}.tool-row{display:flex;gap:12rpx;margin-top:18rpx}.tool-row button,.compare button{flex:1;background:#303030;color:#ccff00;font-size:24rpx}.need{padding:20rpx 0;color:#ccff00;font-size:26rpx}.note{display:block;color:#aaa;font-size:24rpx;line-height:1.6;margin:12rpx 0}.spec-line{display:block;color:#d8e7a4;font-size:23rpx;line-height:1.55;margin-top:6rpx}.panel-usage{display:block;margin-top:14rpx;padding-top:14rpx;border-top:1rpx solid #3a3a3a;color:#d8e7a4;font-size:25rpx;line-height:1.65}.compare{display:flex;overflow-x:auto;gap:16rpx;margin-top:20rpx}.compare>uni-view{flex:0 0 280rpx;background:#222;padding:20rpx;border-radius:16rpx}

.page { min-height: 100vh; background: #121212; color: #FFFFFF; padding-bottom: calc(32rpx + env(safe-area-inset-bottom)); }
.hero { position: relative; height: 360rpx; overflow: hidden; }
.hero-img { width: 100%; height: 100%; opacity: .9; }
.hero::after { content: ""; position: absolute; inset: 0; background: linear-gradient(180deg, rgba(18,18,18,.05), #121212); }
.hero-copy { position: absolute; left: 32rpx; right: 32rpx; bottom: 36rpx; z-index: 1; display: flex; flex-direction: column; }
.title { color: #CCFF00; font-size: 48rpx; font-weight: 900; }
.sub { margin-top: 10rpx; color: #FFFFFF; font-size: 26rpx; line-height: 1.4; }
.category-row { width: 100%; white-space: nowrap; padding: 24rpx 0 10rpx; }
.category { display: inline-flex; margin-left: 24rpx; padding: 14rpx 20rpx; border-radius: 999rpx; background: #1E1E1E; color: #8E8E93; font-size: 24rpx; white-space: nowrap; }
.category:last-child { margin-right: 24rpx; }
.category.active { background: #CCFF00; color: #121212; font-weight: 900; }
.brand-row { padding: 12rpx 24rpx 24rpx; display: flex; flex-wrap: wrap; gap: 12rpx; }
.brand { padding: 12rpx 16rpx; border-radius: 12rpx; background: #1E1E1E; color: #8E8E93; font-size: 23rpx; border: 1rpx solid #2C2C2E; }
.brand.active { color: #CCFF00; border-color: rgba(204,255,0,.38); background: rgba(204,255,0,.1); }
.equipment-list { padding: 0 24rpx; }
.equipment-card { margin-bottom: 22rpx; border-radius: 18rpx; background: #1E1E1E; overflow: hidden; border: 1rpx solid #2C2C2E; }
.equipment-img { width: 100%; height: 340rpx; background: #F7F7F2; }
.info { padding: 22rpx; }
.meta-row { display: flex; gap: 10rpx; margin-bottom: 14rpx; }
.brand-pill, .category-pill { padding: 7rpx 12rpx; border-radius: 8rpx; font-size: 22rpx; }
.brand-pill { background: rgba(204,255,0,.12); color: #CCFF00; }
.category-pill { background: #2C2C2E; color: #D8D8D8; }
.name { display: block; font-size: 32rpx; font-weight: 900; line-height: 1.3; }
.desc { display: block; margin-top: 10rpx; color: #CFCFCF; font-size: 25rpx; line-height: 1.55; }
.mask { position: fixed; inset: 0; z-index: 20; display: flex; align-items: flex-end; background: rgba(0,0,0,.58); }
.panel { width: 100%; padding: 24rpx 24rpx calc(30rpx + env(safe-area-inset-bottom)); border-radius: 24rpx 24rpx 0 0; background: #181818; box-sizing: border-box; }
.panel-img { width: 100%; height: 330rpx; border-radius: 14rpx; background: #F7F7F2; }
.panel-brand { display: block; margin-top: 18rpx; color: #CCFF00; font-size: 24rpx; font-weight: 900; }
.panel-name { display: block; margin-top: 8rpx; font-size: 36rpx; font-weight: 900; line-height: 1.3; }
.panel-desc { display: block; margin-top: 12rpx; color: #D8D8D8; font-size: 27rpx; line-height: 1.55; }
.close-btn { width: 100%; height: 78rpx; margin-top: 22rpx; border-radius: 999rpx; background: #CCFF00; color: #121212; font-size: 28rpx; font-weight: 900; }
</style>
