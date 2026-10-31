<template>
	<view class="page" :style="{ paddingTop: statusBarHeight + 'px', '--top-safe-height': statusBarHeight + 'px' }">
		<view class="nav-bar">
			<view>
				<text class="nav-title">{{ $tr(copy.title) }}</text>
				<text class="nav-sub">{{ $tr(copy.subtitle) }}</text>
			</view>
		</view>

		<button style="margin:16rpx 24rpx;background:#CCFF00;color:#121212;font-size:26rpx" @click="goGames">{{ $tr("约球报名 · 发起球局") }}</button>
		<view class="hero-card">
			<view class="hero-left">
					<text class="hero-value">{{ $tr(referencePoints ?? '—') }}</text>
				<text class="hero-label">{{ $tr(copy.yourPoints) }}</text>
			</view>
			<view class="hero-right">
				<text class="hero-copy">{{ $tr(copy.hero) }}</text>
			</view>
		</view>

		<view class="tab-row">
			<text v-for="tab in tabs" :key="tab.key" class="tab" :class="{ active: activeKey === tab.key }" @click="activeKey = tab.key">{{ $tr(tab.label) }}</text>
		</view>

		<view class="search-box">
			<text class="search-icon">{{ $tr("⌕") }}</text>
			<input
				class="search-input"
				:value="searchText"
				:placeholder="$tr(copy.searchPlaceholder)"
				placeholder-class="search-placeholder"
				confirm-type="search"
				@input="handleSearchInput"
			/>
			<text v-if="searchText" class="clear-search" @click="searchText = ''">{{ $tr("×") }}</text>
		</view>

		<scroll-view class="content" scroll-y>
            <view class="list-status"><text v-if="listChanged">{{ $tr("球友名单或训练累计分有变化，请刷新后继续翻看。") }}</text><button :disabled="loading||Boolean(applyingPlayerId)" @click="syncState">{{ $tr("刷新球友名单") }}</button></view>
			<view v-if="!visiblePlayers.length" style="padding: 32rpx; color: #999">{{ $tr(loading ? '正在查找球友…' : (loadError || (activeKey==='near'&&!getUser().city ? '请先在个人资料填写城市' : '暂无符合条件的球友，试试其他筛选'))) }}<button v-if="!loading" @click="syncState">{{ $tr("重新加载") }}</button></view>
            <view class="podium">
				<view v-for="player in visiblePlayers.slice(0, 3)" :key="player.id" class="podium-card" @click="openPlayer(player)" :hover-class="'click-feedback'">
					<image v-if="!failedPhotos[player.id]" class="podium-photo" :src="player.avatar" mode="aspectFill" @error="markPhotoFailed(player)" />
					<view v-else class="fallback">{{ getInitials(player.name) }}</view>
					<text class="podium-rank">{{ player.level }}</text>
					<text class="podium-name">{{ player.name }}</text>
					<text class="podium-meta">{{ player.points + ' ' + $tr(copy.points) + ' · ' + (player.role === '羽毛球爱好者' ? $tr('羽毛球爱好者') : player.role) }}</text>
				</view>
			</view>

			<view class="list">
				<view v-for="player in visiblePlayers" :key="player.id" class="row" @click="openPlayer(player)" :hover-class="'click-feedback'">
					<text class="rank">{{ player.level }}</text>
					<image v-if="!failedPhotos[player.id]" class="photo" :src="player.avatar" mode="aspectFill" @error="markPhotoFailed(player)" />
					<view v-else class="fallback-row">{{ getInitials(player.name) }}</view>
					<view class="main">
						<text class="name">{{ player.name }}</text>
						<text class="meta">{{ player.city === '未设置城市' ? $tr('未设置城市') : player.city }} · {{ player.role === '羽毛球爱好者' ? $tr('羽毛球爱好者') : player.role }} · {{ $tr(player.points) }} {{ $tr(copy.points) }}</text>
						<text class="meta soft">{{ $tr("{0} · {1}", [player.online, gapLabel(player.points)]) }}</text>
					</view>
					<button class="chat-btn" :disabled="listChanged || Boolean(applyingPlayerId) || player.chat_state==='waiting'" @click.stop="applyChat(player)">{{ $tr(applyingPlayerId === player.id ? '发送中' : chatLabel(player)) }}</button>
				</view>
			</view>
			<view v-if="visiblePlayers.length" class="list-footer"><text>{{ $tr("已显示 {0} / {1} 位球友", [players.length, total]) }}</text><text v-if="loadError">{{ $tr(loadError) }}</text><button v-if="!listChanged && (hasMore || loadError)" :disabled="loading" @click="loadMore">{{ $tr(loading?'正在加载…':'继续加载') }}</button></view>
		</scroll-view>
	</view>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { onShow, onHide, onUnload } from '@dcloudio/uni-app'
import { request, absoluteUrl } from '../../utils/request'
import { getUser } from '../../utils/store'
import { getAuthToken } from '../../utils/auth'
import { applyAppLanguage, getAppLanguage, getCopy, setPageTitle } from '../../utils/i18n'
import { getTopSafeAreaHeight } from '../../utils/safe-area'
import { applyChatRequest } from '../../utils/chat-api'

function goGames(){if(pageActive)uni.navigateTo({url:'/pages/match-making/games'})}
const statusBarHeight = getTopSafeAreaHeight()
const activeKey = ref('all')
const searchText = ref('')
const language = ref(getAppLanguage())
const copy = computed(() => getCopy('match', language.value))
const referencePoints = ref(null)
const players = ref([])
const loadError = ref('')
const loading = ref(false), hasMore = ref(false), total = ref(0)
const nextCursor=ref(''),revision=ref(''),listChanged=ref(false)
let loadTicket=0,searchTimer=null,pageActive=false,pageGeneration=0,applyTicket=0,owner='',token='',poll=null,statusBusy=false,statusTicket=0,statusOffset=0
function context(){return {owner,token,page:pageGeneration,filter:JSON.stringify([activeKey.value,searchText.value.trim()])}}
function current(c){return pageActive&&c.page===pageGeneration&&c.owner===String(getUser()?.id||'')&&c.owner===owner&&c.token===getAuthToken()}
const failedPhotos = ref({})
const applyingPlayerId = ref('')

const tabs = computed(() => [
	{ key: 'all', label: copy.value.tabs[0] },
	{ key: 'near', label: copy.value.tabs[1] },
	{ key: 'training', label: copy.value.tabs[2] },
	{ key: 'doubles', label: copy.value.tabs[3] }
])

const visiblePlayers = computed(() => players.value)

onShow(() => {
	const next=String(getUser()?.id||''),nextToken=getAuthToken()
    if(owner!==next||token!==nextToken){players.value=[];referencePoints.value=null;failedPhotos.value={};applyingPlayerId.value='';owner=next;token=nextToken;searchText.value='';activeKey.value='all'}
	pageActive = true
	pageGeneration++
	language.value = getAppLanguage()
	applyAppLanguage(language.value)
	setPageTitle('match', language.value)
	syncState()
    clearInterval(poll);poll=setInterval(checkStatus,5000)
})
function pauseLoads(){pageActive=false;pageGeneration++;loadTicket++;applyTicket++;statusTicket++;statusBusy=false;clearInterval(poll);clearTimeout(searchTimer);loading.value=false;applyingPlayerId.value=''}
onHide(pauseLoads);onUnload(pauseLoads)
watch([activeKey, searchText], () => {
    clearTimeout(searchTimer);loadTicket++;statusTicket++;statusBusy=false;players.value=[];hasMore.value=false;nextCursor.value='';revision.value='';listChanged.value=false;total.value=0;loadError.value='';loading.value=true
    searchTimer=setTimeout(()=>{if(pageActive)syncState()},300)
})

function syncState(){clearTimeout(searchTimer);return loadPlayers(true)}
function loadMore(){if(!loading.value&&!listChanged.value)return loadPlayers(!revision.value)}
async function loadPlayers(reset) {
    if(!pageActive||owner!==String(getUser()?.id||''))return
    if(!reset&&(!hasMore.value||!nextCursor.value||listChanged.value))return
    const c=context(),ticket=++loadTicket,cursor=reset?'':nextCursor.value;loading.value=true;loadError.value=''
    if(reset){statusTicket++;statusBusy=false;players.value=[];hasMore.value=false;total.value=0;nextCursor.value='';revision.value='';listChanged.value=false;statusOffset=0}
    try {
        const data=await request(`/discovery/players?mode=${activeKey.value}&keyword=${encodeURIComponent(searchText.value.trim())}${cursor?'&cursor='+encodeURIComponent(cursor):''}`)
        if(ticket!==loadTicket||!current(c))return
        const items=data.items.map(player=>({...player,avatar:absoluteUrl(player.avatar)}))
        players.value=reset?items:[...players.value,...items.filter(p=>!players.value.some(old=>old.id===p.id))]
        nextCursor.value=data.next_cursor||'';revision.value=data.revision;hasMore.value=data.has_more;total.value=data.total;referencePoints.value=data.my_points;loadError.value=''
    }
    catch(error){if(ticket===loadTicket&&current(c)){loadError.value=error.message;if(reset)referencePoints.value=null;if(error.status===400){listChanged.value=true;hasMore.value=false;nextCursor.value=''}}}
    finally{if(ticket===loadTicket&&current(c))loading.value=false}
}
async function checkStatus(){
    if(!pageActive||loading.value||statusBusy||listChanged.value||!revision.value||applyingPlayerId.value)return
    const c=context(),ticket=loadTicket,status=++statusTicket,applied=applyTicket
    const shown=players.value.slice(statusOffset,statusOffset+100);statusBusy=true
    try{
        const data=await request(`/discovery/players/status?mode=${activeKey.value}&keyword=${encodeURIComponent(searchText.value.trim())}&revision=${revision.value}${shown.map(p=>'&ids='+p.id).join('')}`)
        if(!current(c)||ticket!==loadTicket||status!==statusTicket||applied!==applyTicket)return
        if(data.changed||data.revision!==revision.value){listChanged.value=true;hasMore.value=false;nextCursor.value='';return}
        const updated=new Map(data.items.map(p=>[p.id,{...p,avatar:absoluteUrl(p.avatar)}]))
        players.value=players.value.map(p=>updated.get(p.id)||p);statusOffset=statusOffset+100>=players.value.length?0:statusOffset+100
    }catch(e){/* Keep the confirmed list; an explicit refresh or further read can retry. */}
    finally{if(current(c)&&status===statusTicket)statusBusy=false}
}

function chatLabel(player){return {waiting:'等待同意',review:'查看申请',accepted:'去聊天',rejected:'重新申请'}[player.chat_state]||'申请聊天'}

function gapLabel(points) {
	if(referencePoints.value===null)return '本人训练累计分暂未读取'
	const diff = Math.abs(points - referencePoints.value)
	return diff ? `${copy.value.pointsGap} ${diff}` : copy.value.pointsClose
}

function openPlayer(player) {
	if(!pageActive||owner!==String(getUser()?.id||''))return
	uni.navigateTo({ url: `/pages/match-making/group-detail?id=${encodeURIComponent(player.id)}` })
}

async function applyChat(player) {
	if(!pageActive||listChanged.value||applyingPlayerId.value||owner!==String(getUser()?.id||'')||!players.value.some(p=>p.id===player.id))return
	if(player.chat_state==='waiting')return
	if(player.chat_state==='review'){openPlayer(player);return}
	if(player.chat_state==='accepted'){uni.navigateTo({url:`/pages/chat/thread?id=${player.chat_id}`});return}
	const c=context(),ticket=++applyTicket
    applyingPlayerId.value=player.id
	try {
		const result = await applyChatRequest({
			id: player.id,
			name: player.name,
			avatar: player.avatar,
			note: `想和你聊聊 ${player.role}，看能不能一起约练。`
		})
		if(!current(c)||ticket!==applyTicket||c.filter!==context().filter)return
        const shown=players.value.find(p=>p.id===player.id)
        if(!shown)return
        shown.chat_id=result.chat.id
		shown.chat_state=result.chat.status==='pending'?(result.request.fromId===String(getUser().id)?'waiting':'review'):result.chat.status
		if (result.chat.status === 'accepted') {
			uni.navigateTo({ url: `/pages/chat/thread?id=${encodeURIComponent(result.chat.id)}` })
			return
		}
		uni.showToast({ title: shown.chat_state==='review'?'对方已向你申请，请查看':'申请已发出', icon: 'none' })
	} catch (error) {
		if(current(c)&&ticket===applyTicket)uni.showToast({title:error.message||'申请失败',icon:'none'})
	} finally {
		if(current(c)&&ticket===applyTicket)applyingPlayerId.value=''
	}
}

function handleSearchInput(event) {
	searchText.value = event.detail.value
}

function getInitials(name) {
	return name
		.split(' / ')[0]
		.slice(0, 2)
}

function markPhotoFailed(player) {
	failedPhotos.value = { ...failedPhotos.value, [player.id]: true }
}
</script>

<style lang="scss" scoped>
.list-status{margin:0 24rpx 20rpx;color:#ccc;font-size:24rpx;line-height:1.6}.list-status button{background:#292929;color:#ccff00;font-size:24rpx;margin-top:12rpx}
.list-footer{padding:24rpx;color:#aaa;text-align:center;font-size:24rpx}.list-footer text{display:block;margin-bottom:16rpx}
.page {
	min-height: 100vh;
	background: #121212;
	color: #FFFFFF;
	padding-bottom: calc(24rpx + env(safe-area-inset-bottom));
}

.nav-bar {
	height: 96rpx;
	padding: 0 24rpx;
	display: flex;
	align-items: center;
	justify-content: space-between;
}

.nav-title {
	display: block;
	font-size: 40rpx;
	font-weight: 900;
}

.nav-sub {
	display: block;
	margin-top: 6rpx;
	color: #8E8E93;
	font-size: 22rpx;
}

.hero-card {
	margin: 0 24rpx 16rpx;
	padding: 20rpx;
	border-radius: 18rpx;
	background: #1E1E1E;
	border: 1rpx solid #2C2C2E;
	display: flex;
	gap: 18rpx;
}

.hero-left {
	width: 184rpx;
	padding: 14rpx;
	border-radius: 14rpx;
	background: rgba(204, 255, 0, 0.1);
}

.hero-value {
	display: block;
	color: #CCFF00;
	font-size: 40rpx;
	font-weight: 900;
}

.hero-label {
	display: block;
	margin-top: 8rpx;
	color: #8E8E93;
	font-size: 22rpx;
}

.hero-right {
	flex: 1;
	min-width: 0;
	display: flex;
	align-items: center;
}

.hero-copy {
	color: #D8D8D8;
	font-size: 24rpx;
	line-height: 1.55;
}

.tab-row {
	padding: 0 24rpx;
	display: flex;
	gap: 12rpx;
	margin-bottom: 16rpx;
}

.tab {
	flex: 1;
	height: 62rpx;
	border-radius: 999rpx;
	background: #1E1E1E;
	border: 1rpx solid #2C2C2E;
	color: #8E8E93;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 24rpx;
	font-weight: 800;
}

.tab.active {
	background: rgba(204, 255, 0, 0.12);
	border-color: rgba(204, 255, 0, 0.3);
	color: #CCFF00;
}

.search-box {
	margin: 0 24rpx 16rpx;
	height: 74rpx;
	border-radius: 16rpx;
	background: #1E1E1E;
	border: 1rpx solid #2C2C2E;
	display: flex;
	align-items: center;
	padding: 0 22rpx;
	color: #8E8E93;
}

.search-icon {
	color: #CCFF00;
	font-size: 30rpx;
	margin-right: 12rpx;
}

.search-input { flex: 1; height: 74rpx; color: #FFFFFF; font-size: 24rpx; }
.search-placeholder { color: #8E8E93; font-size: 24rpx; }
.clear-search { width: 46rpx; height: 46rpx; border-radius: 50%; background: #2C2C2E; color: #FFFFFF; display: flex; align-items: center; justify-content: center; text-align: center; line-height: 46rpx; font-size: 30rpx; }

.content {
	height: auto;
	max-height: calc(100vh - 348rpx - var(--top-safe-height));
	padding-bottom: calc(28rpx + env(safe-area-inset-bottom));
}

.podium {
	padding: 0 24rpx;
	display: grid;
	grid-template-columns: repeat(3, 1fr);
	gap: 12rpx;
	align-items: end;
	margin-bottom: 18rpx;
}

.podium-card {
	position: relative;
	min-height: 300rpx;
	padding: 16rpx 10rpx;
	border-radius: 16rpx;
	background: #1E1E1E;
	border: 1rpx solid #2C2C2E;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: flex-start;
	box-sizing: border-box;
}

.podium-card:first-child {
	min-height: 340rpx;
	border-color: rgba(204, 255, 0, 0.45);
}

.podium-photo,
.fallback {
	display: flex;
	flex: 0 0 112rpx;
	width: 112rpx;
	height: 112rpx;
	border-radius: 50%;
	background: #2C2C2E;
}

.fallback {
	align-items: center;
	justify-content: center;
	color: #CCFF00;
	font-size: 30rpx;
	font-weight: 900;
}

.podium-rank {
	display: block;
	width: 100%;
	margin-top: 12rpx;
	color: #CCFF00;
	font-size: 26rpx;
	font-weight: 900;
	text-align: center;
}

.podium-name {
	display: block;
	width: 100%;
	margin-top: 10rpx;
	font-size: 24rpx;
	font-weight: 800;
	text-align: center;
	line-height: 1.35;
}

.podium-meta {
	display: block;
	width: 100%;
	margin-top: 8rpx;
	color: #8E8E93;
	font-size: 20rpx;
	text-align: center;
	line-height: 1.4;
}

.list {
	margin: 0 24rpx 22rpx;
	border-radius: 18rpx;
	overflow: hidden;
	background: #1E1E1E;
	border: 1rpx solid #2C2C2E;
}

.row {
	position: relative;
	min-height: 104rpx;
	padding: 16rpx 20rpx;
	display: flex;
	align-items: center;
	border-bottom: 1rpx solid #2C2C2E;
}

.row:last-child {
	border-bottom: 0;
}

.rank {
	width: 54rpx;
	color: #8E8E93;
	font-size: 26rpx;
	font-weight: 800;
}

.photo,
.fallback-row {
	width: 72rpx;
	height: 72rpx;
	border-radius: 50%;
	background: #2C2C2E;
	flex: 0 0 auto;
}

.fallback-row {
	display: flex;
	align-items: center;
	justify-content: center;
	color: #CCFF00;
	font-size: 22rpx;
	font-weight: 900;
}

.main {
	flex: 1;
	min-width: 0;
	margin-left: 16rpx;
}

.chat-btn {
	min-width: 154rpx;
	min-height: 62rpx;
	margin-left: 14rpx;
	padding: 8rpx 16rpx;
	border-radius: 14rpx;
	background: #CCFF00;
	color: #121212;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 22rpx;
	line-height: 1.2;
	font-weight: 900;
	white-space: nowrap;
}

.name {
	display: block;
	font-size: 28rpx;
	font-weight: 800;
}

.meta {
	display: block;
	margin-top: 6rpx;
	color: #8E8E93;
	font-size: 22rpx;
	line-height: 1.35;
}

.soft {
	color: #D8D8D8;
}

</style>
