<template>
	<view class="page" :style="{ paddingTop: statusBarHeight + 'px', '--top-safe-height': statusBarHeight + 'px' }">
		<view class="nav-bar">
			<view class="nav-left">
				<view class="back-btn" @click="goBack" :hover-class="'click-feedback'">
					<text class="back-icon">{{ $tr("‹") }}</text>
				</view>
				<view class="title-wrap">
					<text class="title">{{ $tr("聊天") }}</text>
					<text class="sub">{{ $tr("先申请，再开聊") }}</text>
				</view>
			</view>
			<button class="reminders" @click="openReminders">{{ $tr("提醒{0}", [reminderCount ? ` ${reminderCount > 99 ? '99+' : reminderCount}` : '']) }}</button>
			<button class="nav-btn" @click="goMatch">{{ $tr("找球友") }}</button>
		</view>

		<view class="summary">
			<view class="metric">
				<text class="metric-value">{{ $tr(summary ? summary.total_threads : '—') }}</text>
				<text class="metric-label">{{ $tr("会话") }}</text>
			</view>
			<view class="metric">
				<text class="metric-value">{{ $tr(summary ? pendingIncoming : '—') }}</text>
				<text class="metric-label">{{ $tr("待同意") }}</text>
			</view>
			<view class="metric">
				<text class="metric-value">{{ $tr(summary ? summary.total_requests : '—') }}</text>
				<text class="metric-label">{{ $tr("申请") }}</text>
			</view>
		</view>

		<view class="switcher">
			<view v-for="tab in tabs" :key="tab.key" class="switch-item" :class="{ active: activeTab === tab.key }" @click="selectTab(tab.key)">
				<text>{{ $tr(tab.label) }}</text>
				<text v-if="tab.key === 'requests' && pendingIncoming" class="dot">{{ $tr(pendingIncoming) }}</text>
			</view>
		</view>

		<scroll-view class="content" scroll-y>
            <view class="list-controls">
                <text v-if="current.stale">{{ $tr("聊天列表有更新，请刷新后继续翻看。") }}</text>
                <text v-if="current.error">{{ $tr(current.error) }}</text>
                <text v-if="current.statusError">{{ $tr(current.statusError) }}</text>
                <text v-if="loading">{{ $tr("正在读取…") }}</text>
                <button :disabled="loading || Boolean(busy)" @click="refresh">{{ $tr(current.error && !current.loaded ? '重试读取' : '刷新列表') }}</button>
            </view>
			<view v-if="activeTab === 'threads'">
				<view v-if="threads.length" class="list">
					<view v-for="thread in threads" :key="thread.id" class="row" @click="openThread(thread.id)" :hover-class="'click-feedback'">
						<image class="avatar" :src="thread.otherAvatar" mode="aspectFill" />
						<view class="main">
							<view class="row-head">
								<text class="name">{{ thread.otherNameIsDefault ? $tr(thread.otherName) : thread.otherName }}</text>
								<text class="time">{{ $tr(formatTimeLabel(thread.updatedAt)) }}</text>
							</view>
							<text class="last">{{ thread.lastMessageIsSystem ? $tr(thread.lastMessage || '已建立聊天') : thread.lastMessage }}</text>
						</view>
						<text v-if="thread.unreadCount" class="dot">{{ $tr(thread.unreadCount) }}</text><text class="arrow">{{ $tr("›") }}</text>
						<button class="remove-thread" :disabled="Boolean(busy)" @click.stop="removeThread(thread)">{{ $tr("删除") }}</button>
					</view>
				</view>
				<view v-else-if="current.loaded && !loading && !current.error && !current.stale" class="empty">
					<text class="empty-title">{{ $tr("暂无会话") }}</text>
					<text class="empty-sub">{{ $tr("先去找球友发起申请，等对方同意后这里会出现聊天。") }}</text>
				</view>
			</view>

			<view v-else>
				<view v-if="requests.length" class="list">
					<view v-for="request in requests" :key="request.id" class="request-card">
						<view class="row-head">
							<view class="request-title">
								<image class="avatar" :src="request.fromId === selfId ? request.toAvatar : request.fromAvatar" mode="aspectFill" />
								<view class="main">
									<text class="name">{{ request.fromId === selfId ? (request.toNameIsDefault ? $tr(request.toName) : request.toName) : (request.fromNameIsDefault ? $tr(request.fromName) : request.fromName) }}</text>
									<text class="time">{{ $tr(request.fromId === selfId ? '你发出的申请' : '对方发来的申请') }}</text>
								</view>
							</view>
							<text class="status" :class="request.status">{{ $tr(requestStatusLabel(request)) }}</text>
						</view>
						<text class="note">{{ request.noteIsDefault ? $tr(request.note) : request.note }}</text>
						<view class="action-row">
							<button :disabled="Boolean(busy)" class="ghost-btn" @click="handleRequest(request)">{{ $tr(requestActionLabel(request)) }}</button>
							<button :disabled="Boolean(busy)" v-if="request.status === 'pending' && request.fromId !== selfId" class="primary-btn" @click="acceptRequest(request)">{{ $tr("同意") }}</button>
							<button :disabled="Boolean(busy)" v-else-if="request.status === 'pending' && request.fromId === selfId" class="primary-btn" @click="cancelRequest(request)">{{ $tr("撤销申请") }}</button>
							<button :disabled="Boolean(busy)" v-else-if="request.status === 'rejected'" class="primary-btn" @click="retryRequest(request)">{{ $tr("重新申请") }}</button>
							<button :disabled="Boolean(busy)" v-else class="primary-btn" @click="openAccepted(request)">{{ $tr("去聊天") }}</button>
						</view>
					</view>
				</view>
				<view v-else-if="current.loaded && !loading && !current.error && !current.stale" class="empty">
					<text class="empty-title">{{ $tr("暂无申请") }}</text>
					<text class="empty-sub">{{ $tr("去找球友发起聊天申请，或者等待别人来找你。") }}</text>
				</view>
			</view>
            <view class="list-controls" v-if="current.loaded && !current.stale && current.hasMore">
                <button :disabled="loading || Boolean(busy)" @click="loadMore">{{ $tr(loading ? '正在读取…' : current.error ? '重试继续读取' : '继续读取') }}</button>
            </view>
        </scroll-view>

		<view class="bottom-tabs">
			<view v-for="item in bottomTabs" :key="item.url" class="bottom-tab" @click="goTab(item.url)" :hover-class="'click-feedback'">
				<image class="bottom-icon" :src="item.icon" mode="aspectFit" />
				<text>{{ $tr(item.label) }}</text>
			</view>
		</view>
	</view>
</template>

<script setup>
import { computed, onUnmounted, ref } from 'vue'
import { onShow, onHide } from '@dcloudio/uni-app'
import { formatTimeLabel } from '../../utils/store'
import { acceptChatRequestRemote, applyChatRequest, fetchChatInbox, fetchChatInboxStatus, getChatSelfId, rejectChatRequestRemote, cancelChatRequest, removeChatConversation } from '../../utils/chat-api'
import { getTopSafeAreaHeight } from '../../utils/safe-area'
import { fetchNotificationCount } from '../../utils/notifications-api'

const statusBarHeight = getTopSafeAreaHeight()
const selfId = ref(getChatSelfId())
const reminderCount = ref(0)
const activeTab = ref('threads')
const blankPage = () => ({items:[],loaded:false,hasMore:false,cursor:'',revision:null,stale:false,error:'',statusError:''})
const pages = ref({threads:blankPage(),requests:blankPage()})
const current = computed(() => pages.value[activeTab.value])
const threads = computed(() => pages.value.threads.items)
const requests = computed(() => pages.value.requests.items)
const summary = ref(null)
const pendingIncoming = computed(() => summary.value?.pending_incoming || 0)
const loading = ref(false)
const busy = ref('')
const tabs = [{key:'threads',label:'会话'},{key:'requests',label:'请求'}]
const bottomTabs = [
 {label:'首页',icon:'/static/tab/home.svg',url:'/pages/index/index'},
 {label:'训练',icon:'/static/tab/coach.svg',url:'/pages/ai-coach/ai-coach'},
 {label:'找球友',icon:'/static/tab/match.svg',url:'/pages/match-making/match-making'},
 {label:'球圈',icon:'/static/tab/video.svg',url:'/pages/video-feed/video-feed'},
 {label:'我的',icon:'/static/tab/profile.svg',url:'/pages/profile/profile'}
]
let poll=null, visible=false, generation=0, readGeneration=0, checking=false, checkOffset=0
function context(){return {generation,uid:selfId.value}}
function live(ticket){return visible && ticket.generation===generation && ticket.uid===getChatSelfId()}
function stopReads(){readGeneration++;loading.value=false;checking=false}
function leave(){visible=false;generation++;stopReads();busy.value='';clearInterval(poll)}
onHide(leave);onUnmounted(leave)
onShow(() => {
 generation++;visible=true;stopReads();busy.value='';selfId.value=getChatSelfId();reminderCount.value=0
 pages.value={threads:blankPage(),requests:blankPage()};summary.value=null;checkOffset=0
 loadPage();clearInterval(poll);poll=setInterval(checkStatus,5000)
})
function selectTab(kind){
 if(kind===activeTab.value)return
 generation++;stopReads();busy.value='';activeTab.value=kind;checkOffset=0
 if(!current.value.loaded)loadPage();else checkStatus()
}
async function loadPage(more=false,fromAction=false){
 if(!visible||loading.value||(busy.value&&!fromAction))return
 const page=current.value,kind=activeTab.value
 if(more&&(!page.loaded||!page.hasMore||page.stale))return
 const ticket=context(),read=++readGeneration;checking=false;loading.value=true;page.error=''
 try{
  const data=await fetchChatInbox({kind,cursor:more?page.cursor:''})
  if(!live(ticket)||read!==readGeneration)return
  const found=new Set(more?page.items.map(item=>item.id):[])
  const additions=data[kind].filter(item=>!found.has(item.id))
  page.items=more?[...page.items,...additions]:additions
  page.loaded=true;page.hasMore=data.hasMore;page.cursor=data.nextCursor;page.revision=data.revision;page.stale=false;page.statusError=''
  summary.value=data.summary
  for(const key of ['threads','requests'])if(key!==kind&&pages.value[key].loaded&&pages.value[key].revision!==data.revision)pages.value[key].stale=true
 }catch(error){
  if(!live(ticket)||read!==readGeneration)return
  page.error=error.message||'聊天读取失败，请重试'
  if(more&&(error.status===409||error.status===400))page.stale=true
 }finally{if(live(ticket)&&read===readGeneration)loading.value=false}
}
async function checkStatus(){
 if(!visible||checking||loading.value||busy.value)return
 const ticket=context(),read=readGeneration,kind=activeTab.value,page=current.value
 const ids=page.items.map(item=>item.id)
 if(checkOffset>=ids.length)checkOffset=0
 const selected=ids.slice(checkOffset,checkOffset+100);checkOffset+=selected.length
 checking=true
 try{
  const [data,notice]=await Promise.allSettled([fetchChatInboxStatus(selected),fetchNotificationCount()])
  if(!live(ticket)||read!==readGeneration)return
  if(notice.status==='fulfilled')reminderCount.value=notice.value.unread_count
  if(data.status==='rejected'){page.statusError=data.reason.message||'新消息暂未更新';return}
  const latest=data.value;summary.value=latest.summary;page.statusError=''
  for(const key of ['threads','requests'])if(pages.value[key].loaded&&pages.value[key].revision!==latest.revision)pages.value[key].stale=true
  const checked=new Set(selected),updates=new Map(latest[kind].map(item=>[item.id,item]))
  // Update content in place; a changed ordering requires an explicit refresh.
  page.items=page.items.filter(item=>!checked.has(item.id)||updates.has(item.id)).map(item=>updates.get(item.id)||item)
 }finally{if(live(ticket)&&read===readGeneration)checking=false}
}
function refresh(){return loadPage(false)}
function loadMore(){return loadPage(true)}
async function act(id,work,after){
 if(busy.value||!visible)return
 const ticket=context();stopReads();busy.value=id
 try{
  const result=await work()
  if(!live(ticket))return
  pages.value={threads:blankPage(),requests:blankPage()};summary.value=null;checkOffset=0
  await loadPage(false,true)
  if(live(ticket)){busy.value='';if(after)after(result)}
 }catch(error){if(live(ticket))uni.showToast({title:error.message||'操作未完成，请重试',icon:'none'})}
 finally{if(live(ticket))busy.value=''}
}
function removeThread(thread){
 if(busy.value)return
 const ticket=context()
 uni.showModal({title:'删除会话',content:'清空你这边的历史并移出列表，无法恢复；对方的记录保留，收到新消息时会重新出现。',success:r=>{
  if(r.confirm&&live(ticket))act(thread.id,()=>removeChatConversation(thread.id))
 }})
}
function cancelRequest(item){return act(item.id,()=>cancelChatRequest(item.id))}
function acceptRequest(item){return act(item.id,()=>acceptChatRequestRemote(item.id),result=>openThread(result.chat.id))}
function retryRequest(item){
 const outgoing=item.fromId===selfId.value
 return act(item.id,()=>applyChatRequest({id:outgoing?item.toId:item.fromId,name:outgoing?item.toName:item.fromName,note:item.note}),result=>{
  if(result.chat.status==='accepted')openThread(result.chat.id)
  else uni.showToast({title:'已重新发出申请',icon:'none'})
 })
}
function handleReject(item){return act(item.id,()=>rejectChatRequestRemote(item.id),()=>uni.showToast({title:'已拒绝',icon:'none'}))}
function requestStatusLabel(item){return item.status==='accepted'?'已同意':item.status==='rejected'?'已拒绝':'待同意'}
function requestActionLabel(item){return item.status==='accepted'?'打开':item.status==='rejected'?'可重发':item.fromId===selfId.value?'查看进度':'拒绝'}
function handleRequest(item){
 if(busy.value)return
 if(item.status==='accepted')openAccepted(item)
 else if(item.status==='rejected')retryRequest(item)
 else if(item.fromId===selfId.value)goMatch()
 else handleReject(item)
}
function openAccepted(item){if(!busy.value)openThread(item.threadId||item.id)}
function openThread(id){if(!busy.value)uni.navigateTo({url:`/pages/chat/thread?id=${encodeURIComponent(id)}`})}
function openReminders(){uni.navigateTo({url:'/pages/notifications/notifications'})}
function goMatch(){uni.switchTab({url:'/pages/match-making/match-making'})}
function goTab(url){uni.switchTab({url})}
function goBack(){if(getCurrentPages().length>1)uni.navigateBack();else uni.switchTab({url:'/pages/index/index'})}
</script>

<style lang="scss" scoped>
.list-controls{padding:20rpx 24rpx;display:flex;flex-direction:column;gap:12rpx;color:#ddd;font-size:25rpx}
.list-controls button{margin:0;padding:0 24rpx;background:#292929;color:#cf0;font-size:26rpx;align-self:flex-start}

.reminders{margin:0 12rpx 0 auto;padding:0 14rpx;background:#242424;color:#cf0;font-size:24rpx;line-height:60rpx;border-radius:24rpx;white-space:nowrap;flex-shrink:0}
.remove-thread{margin-left:12rpx;padding:0 12rpx;font-size:22rpx;color:#aaa;background:#292929;flex-shrink:0}
.page {
	min-height: 100vh;
	background: #121212;
	color: #FFFFFF;
	padding-bottom: calc(120rpx + env(safe-area-inset-bottom));
}

.nav-bar {
	height: 92rpx;
	padding: 0 24rpx;
	display: flex;
	align-items: center;
	justify-content: space-between;
}

.nav-left {
	display: flex;
	align-items: center;
	min-width: 0;
}

.back-btn {
	width: 68rpx;
	height: 68rpx;
	margin-right: 14rpx;
	border-radius: 14rpx;
	background: #1E1E1E;
	display: flex;
	align-items: center;
	justify-content: center;
	flex: 0 0 auto;
}

.back-icon {
	font-size: 44rpx;
	line-height: 1;
}

.title-wrap {
	min-width: 0;
}

.title {
	display: block;
	font-size: 40rpx;
	font-weight: 900;
}

.sub {
	display: block;
	margin-top: 6rpx;
	color: #8E8E93;
	font-size: 22rpx;
}

.nav-btn,
.primary-btn,
.ghost-btn {
	height: 68rpx;
	padding: 0 24rpx;
	border-radius: 14rpx;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 26rpx;
	font-weight: 900;
}

.nav-btn {
	background: #1E1E1E;
	color: #CCFF00;
}

.summary {
	margin: 0 24rpx 18rpx;
	padding: 18rpx 14rpx;
	border-radius: 18rpx;
	background: #1E1E1E;
	border: 1rpx solid #2C2C2E;
	display: grid;
	grid-template-columns: repeat(3, 1fr);
	gap: 10rpx;
}

.metric {
	padding: 16rpx 0;
	text-align: center;
}

.metric-value {
	display: block;
	color: #CCFF00;
	font-size: 34rpx;
	font-weight: 900;
}

.metric-label {
	display: block;
	margin-top: 6rpx;
	color: #8E8E93;
	font-size: 20rpx;
}

.switcher {
	margin: 0 24rpx 12rpx;
	display: flex;
	gap: 12rpx;
}

.switch-item {
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

.switch-item.active {
	background: rgba(204, 255, 0, 0.12);
	color: #CCFF00;
	border-color: rgba(204, 255, 0, 0.3);
}

.dot {
	margin-left: 10rpx;
	padding: 0 10rpx;
	height: 32rpx;
	border-radius: 999rpx;
	background: #FF5722;
	color: #FFFFFF;
	font-size: 20rpx;
	line-height: 32rpx;
}

.content {
	height: calc(100vh - 380rpx - var(--top-safe-height) - env(safe-area-inset-bottom));
}

.list {
	padding: 0 24rpx 28rpx;
}

.row,
.request-card {
	margin-bottom: 16rpx;
	padding: 20rpx;
	border-radius: 18rpx;
	background: #1E1E1E;
	border: 1rpx solid #2C2C2E;
}

.row {
	display: flex;
	align-items: center;
}

.avatar {
	width: 80rpx;
	height: 80rpx;
	border-radius: 50%;
	background: #2C2C2E;
	flex: 0 0 auto;
}

.main {
	flex: 1;
	min-width: 0;
	margin-left: 16rpx;
}

.row-head,
.request-title {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 16rpx;
}

.request-title {
	flex: 1;
	min-width: 0;
	justify-content: flex-start;
}

.name {
	display: block;
	font-size: 28rpx;
	font-weight: 900;
}

.time,
.note {
	display: block;
	margin-top: 8rpx;
	color: #8E8E93;
	font-size: 22rpx;
	line-height: 1.5;
}

.last {
	display: block;
	margin-top: 10rpx;
	color: #D8D8D8;
	font-size: 24rpx;
	line-height: 1.45;
}

.arrow {
	color: #8E8E93;
	font-size: 42rpx;
	margin-left: 10rpx;
}

.status {
	font-size: 22rpx;
	font-weight: 900;
}

.status.pending {
	color: #CCFF00;
}

.status.accepted {
	color: #4CD964;
}

.status.rejected {
	color: #8E8E93;
}

.action-row {
	margin-top: 18rpx;
	display: grid;
	grid-template-columns: 1fr 1fr;
	gap: 12rpx;
}

.primary-btn {
	background: #CCFF00;
	color: #121212;
}

.ghost-btn {
	background: #2C2C2E;
	color: #FFFFFF;
}

.empty {
	padding: 120rpx 24rpx 0;
	text-align: center;
}

.empty-title {
	display: block;
	font-size: 34rpx;
	font-weight: 900;
}

.empty-sub {
	display: block;
	margin-top: 12rpx;
	color: #8E8E93;
	font-size: 24rpx;
	line-height: 1.6;
}

.bottom-tabs {
	position: fixed;
	left: 0;
	right: 0;
	bottom: 0;
	height: calc(104rpx + env(safe-area-inset-bottom));
	padding: 10rpx 10rpx calc(10rpx + env(safe-area-inset-bottom));
	background: #121212;
	border-top: 1rpx solid #2C2C2E;
	display: grid;
	grid-template-columns: repeat(5, 1fr);
	z-index: 10;
}

.bottom-tab {
	min-width: 0;
	height: 84rpx;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	color: #8E8E93;
	font-size: 20rpx;
	font-weight: 800;
}

.bottom-icon {
	width: 40rpx;
	height: 40rpx;
	margin-bottom: 6rpx;
}
</style>
