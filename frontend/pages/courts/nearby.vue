<template>
	<view class="page">
		<scroll-view class="content" scroll-y>
			<view class="hero">
				<text class="hero-title">{{ $tr("球馆查找") }}</text>
				<text class="hero-copy">{{ $tr(heroCopy) }}</text>
                <input v-model="city" :disabled="loading" class="search-input" maxlength="80" :placeholder='$tr("城市，如上海")' />
                <input v-model="keyword" :disabled="loading" class="search-input" maxlength="80" :placeholder='$tr("球馆名称或区域，可不填")' confirm-type="search" @confirm="searchCity" />
                <button :disabled="loading" @click="searchCity">{{ $tr("按城市查找") }}</button>
                <view class="range-row"><text v-for="km in [5,10,20]" :key="km" :class="{selected:radius===km*1000}" @click="selectRadius(km*1000)">{{ $tr("附近 {0} 公里", [km]) }}</text></view>
                <button :disabled="loading" @click="searchNearby">{{ $tr("使用当前位置查找") }}</button>
                <text v-if="lastQuery" class="hero-copy">{{ $tr("{0}。修改条件后，请点“按城市查找”或“使用当前位置查找”开始新查询。", [queryCopy]) }}</text>
                <text class="hero-copy">{{ $tr("不想提供定位时，也可以直接填写城市查找。球馆信息来自高德地图，订场前请电话确认。") }}</text>
			</view>

			<view v-for="court in courts" :key="court.id" class="court-card" @click="openCourt(court)" :hover-class="'click-feedback'">
				<view class="card-head">
					<view class="court-main">
						<text class="court-name">{{ $tr(court.name) }}</text>
						<text class="court-address">{{ $tr(court.address) }}</text>
					</view>
					<view v-if="court.distance || court.distance_text" class="distance-pill">
						<text>{{ $tr(court.distance || court.distance_text) }}</text>
					</view>
				</view>
				<text class="court-hours">{{ $tr(court.hours) }}</text><button v-if="court.tel" @click.stop="callCourt(court)">{{ $tr("致电球馆确认或订场") }}</button>
				<view class="tag-row">
					<text v-for="item in court.features" :key="item" class="tag">{{ $tr(item) }}</text>
				</view>
			</view>
            <view v-if="hasMore || (loadError && lastQuery)" class="more"><button :disabled="loading" @click="loadMore">{{ $tr(loading?'正在查找…':(loadError?'重试本次查找':'继续加载')) }}</button></view>
		</scroll-view>
	</view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onShow, onHide, onUnload } from '@dcloudio/uni-app'
import { fetchNearbyCourts, fetchCityCourts } from '../../utils/integrations-api'
import { getUser } from '../../utils/store'
import { getAuthToken } from '../../utils/auth'

const initialText='填写城市或使用当前位置查找羽毛球馆。'
const loading=ref(false),courts=ref([]),statusText=ref(initialText)
const city=ref(''),keyword=ref(''),radius=ref(5000),hasMore=ref(false),loadError=ref(false),lastQuery=ref(null)
let loadTicket=0,page=0,locationTimer=null,pageActive=false,owner=''
const account=()=>`${getUser().id||''}:${getAuthToken()}`
const heroCopy=computed(()=>loading.value?'正在查找球馆…':statusText.value)
const queryCopy=computed(()=>{
    const query=lastQuery.value
    if(!query)return ''
    return `本次查找：${query.kind==='city'?query.city:`所选位置附近 ${query.radius/1000} 公里`}${query.keyword?` · ${query.keyword}`:''}`
})
onShow(()=>{
    pageActive=true
    if(owner!==account()){
        loadTicket++;clearTimeout(locationTimer);owner=account();loading.value=false
        courts.value=[];hasMore.value=false;loadError.value=false;lastQuery.value=null;page=0
        city.value=getUser().city||'';keyword.value='';radius.value=5000;statusText.value=initialText
    }
    uni.setNavigationBarTitle({title:'球馆查找'})
})
function stopLoads(){
    if(loading.value&&lastQuery.value){loadError.value=true;statusText.value='查找尚未完成，可以重试本次查找。'}
    pageActive=false;loadTicket++;clearTimeout(locationTimer);loading.value=false
}
onHide(stopLoads);onUnload(stopLoads)
function current(ticket,who){return pageActive&&ticket===loadTicket&&who===account()&&who===owner}
function selectRadius(value){if(!loading.value)radius.value=value}
function openCourt(court){
    if(!pageActive||owner!==account())return
    const point=parseLocation(court.location),ticket=loadTicket,who=owner
    if(point){uni.openLocation({...point,name:court.name,address:court.address,fail:()=>{if(current(ticket,who))showCourt(court)}});return}
    showCourt(court)
}
function showCourt(court){uni.showModal({title:court.name,content:`${court.address}\n${court.hours}${court.tel?`\n电话：${court.tel}`:''}`,showCancel:false})}
function callCourt(court){
    if(!pageActive||owner!==account())return
    const phone=String(court.tel||'').split(';').map(v=>v.trim()).find(Boolean)
    if(!phone)return
    const ticket=loadTicket,who=owner
    uni.makePhoneCall({phoneNumber:phone,fail:()=>{if(current(ticket,who))uni.showToast({title:'未能拨打电话，请手动拨打球馆号码',icon:'none'})}})
}
function parseLocation(value){
    if(typeof value!=='string')return null
    const parts=value.split(',').map(v=>v.trim())
    if(parts.length!==2||parts.some(v=>!v))return null
    const [longitude,latitude]=parts.map(Number)
    return Number.isFinite(latitude)&&Number.isFinite(longitude)&&Math.abs(latitude)<=90&&Math.abs(longitude)<=180?{latitude,longitude}:null
}
function startSearch(query){
    const ticket=++loadTicket;clearTimeout(locationTimer)
    courts.value=[];hasMore.value=false;loadError.value=false;loading.value=true;page=0;lastQuery.value=query
    return ticket
}
function searchCity(){
    if(loading.value||!pageActive||owner!==account())return
    if(!city.value.trim()){uni.showToast({title:'请先填写城市',icon:'none'});return}
    const query={kind:'city',city:city.value.trim(),keyword:keyword.value.trim()}
    return runSearch(query,1,startSearch(query),owner)
}
function searchNearby(){
    if(loading.value||!pageActive||owner!==account())return
    const radiusAtStart=radius.value,keywordAtStart=keyword.value.trim(),who=owner
    const ticket=startSearch(null)
    const fail=()=>{if(!current(ticket,who))return;statusText.value='未能取得位置。你可以填写城市查找，或允许定位后再试。';loading.value=false;loadError.value=true;loadTicket++}
    locationTimer=setTimeout(fail,10000)
    uni.getLocation({type:'gcj02',success:location=>{
        if(!current(ticket,who))return;clearTimeout(locationTimer)
        if(!Number.isFinite(location.latitude)||!Number.isFinite(location.longitude)||Math.abs(location.latitude)>90||Math.abs(location.longitude)>180){fail();return}
        const query={kind:'nearby',latitude:location.latitude,longitude:location.longitude,radius:radiusAtStart,keyword:keywordAtStart}
        lastQuery.value=query
        runSearch(query,1,ticket,who)
    },fail:()=>{if(!current(ticket,who))return;clearTimeout(locationTimer);fail()}})
}
function loadMore(){
    if(loading.value||!pageActive||owner!==account()||!lastQuery.value||(!hasMore.value&&!loadError.value))return
    loading.value=true
    return runSearch({...lastQuery.value},page+1,++loadTicket,owner)
}
async function runSearch(query,nextPage,ticket,who){
    try{
        const result=await (query.kind==='city'?fetchCityCourts({...query,page:nextPage}):fetchNearbyCourts({...query,page:nextPage}))
        if(!current(ticket,who))return
        if(result.source!=='amap')throw new Error(result.message||'球馆查询暂时不可用，请稍后再试')
        const items=Array.isArray(result.items)?result.items:[]
        courts.value=nextPage===1?items:[...courts.value,...items.filter(item=>!courts.value.some(old=>old.id===item.id))]
        page=nextPage;lastQuery.value={...query};hasMore.value=Boolean(result.has_more);loadError.value=false
        statusText.value=result.message||(query.kind==='city'?`已查找 ${query.city} 的球馆。`:'已查找当前位置附近的球馆。')
    }catch(error){if(current(ticket,who)){statusText.value=error.message||'查找没有完成，请重试';loadError.value=true}}
    finally{if(current(ticket,who))loading.value=false}
}
</script>

<style lang="scss" scoped>
.hero button,.more button{background:#ccff00;color:#121212}.hero button[disabled],.more button[disabled]{background:#353535;color:#b5b5b5}
.search-input{height:80rpx;margin-top:20rpx;padding:0 18rpx;background:#292929;border-radius:12rpx;color:#fff;font-size:26rpx}.hero button{margin-top:16rpx;font-size:26rpx}.range-row{display:flex;gap:10rpx;margin-top:20rpx}.range-row text{flex:1;padding:14rpx 4rpx;text-align:center;font-size:22rpx;border:1rpx solid #555;border-radius:12rpx}.range-row .selected{color:#cf0;border-color:#cf0}.more{padding-bottom:28rpx}
.page { min-height: 100vh; background: #121212; color: #FFFFFF; padding-bottom: calc(24rpx + env(safe-area-inset-bottom)); }
.content { height: calc(100vh - env(safe-area-inset-bottom)); padding: 0 24rpx; box-sizing: border-box; }
.hero, .court-card { margin-bottom: 22rpx; border-radius: 18rpx; background: #1E1E1E; border: 1rpx solid #2C2C2E; }
.hero { padding: 26rpx; }
.hero-title { display: block; color: #CCFF00; font-size: 34rpx; font-weight: 900; }
.hero-copy { display: block; margin-top: 10rpx; color: #D8D8D8; font-size: 24rpx; line-height: 1.55; }
.court-card { padding: 22rpx; }
.card-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16rpx; }
.court-main { flex: 1; min-width: 0; }
.court-name { display: block; font-size: 30rpx; font-weight: 900; line-height: 1.35; }
.court-address, .court-hours { display: block; margin-top: 8rpx; color: #A8A8AD; font-size: 23rpx; line-height: 1.45; }
.court-hours { margin-top: 18rpx; color: #D8D8D8; }
.distance-pill { flex: 0 0 auto; padding: 10rpx 14rpx; border-radius: 999rpx; background: rgba(204,255,0,.12); color: #CCFF00; font-size: 22rpx; font-weight: 900; }
.tag-row { margin-top: 18rpx; display: flex; flex-wrap: wrap; gap: 10rpx; }
.tag { padding: 8rpx 12rpx; border-radius: 999rpx; background: #242424; color: #D8D8D8; font-size: 21rpx; }
</style>
