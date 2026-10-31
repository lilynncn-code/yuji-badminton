<template>
	<view class="page">
        <view v-if="loadError" class="panel"><text class="panel-text">{{ $tr(loadError) }}</text><button class="ghost-btn" :disabled="loading||busy" @click="refresh">{{ $tr("重新读取") }}</button></view>
		<view v-if="player" class="hero">
			<view class="photo"><image class="cover" :src="player.avatar" mode="aspectFill" @error="markPhotoFailed" />
			<view v-if="photoFailed || !player.avatar" class="fallback">{{ getInitials(player.name) }}</view></view>
			<view class="hero-body">
				<text class="rank">{{ player.level + ' · ' + (player.role === '羽毛球爱好者' ? $tr('羽毛球爱好者') : player.role) }}</text>
				<text class="name">{{ player.name }}</text>
				<text class="meta">{{ player.city === '未设置城市' ? $tr('未设置城市') : player.city }} · {{ $tr(player.points) }}{{ $tr("训练累计分 ·") }}{{ $tr(player.online) }}</text>
				<text class="bio">{{ player.bio }}</text>
				<text class="status" :class="chatState.status">{{ $tr(statusLabel) }}</text>
			</view>
		</view>

		<view v-if="player" class="panel">
			<text class="panel-title">{{ $tr("聊天状态") }}</text>
			<text class="panel-text">{{ $tr(statusDescription) }}</text>
			<view class="button-row">
				<button class="ghost-btn" @click="goBack">{{ $tr("返回") }}</button>
				<button class="ghost-btn" @click="goInbox">{{ $tr("消息") }}</button>
			</view>
            <button class="ghost-btn" v-if="!isSelf" :disabled="busy||loading||!canInteract" @click="toggleFollow">{{ $tr(relation.following ? '取消关注' : '关注这位球友') }}</button>
            <button class="ghost-btn" v-if="!isSelf" :disabled="busy||loading||!relationReady" @click="toggleBlock">{{ $tr(relation.blocked ? '取消屏蔽' : '屏蔽这位球友') }}</button>
            <button v-if="!isSelf" class="ghost-btn" :disabled="busy||loading" @click="reportPlayer">{{ $tr("举报这位球友") }}</button>
			<button class="ghost-btn" :disabled="loading||busy" @click="refresh">{{ $tr(loading?'正在读取状态…':'刷新状态') }}</button>
			<button v-if="canInteract" class="primary-btn" :disabled="busy||loading" @click="primaryAction">{{ $tr(primaryLabel) }}</button>
		</view>

		<view v-if="player" class="panel">
			<text class="panel-title">{{ $tr("资料") }}</text>
			<view class="line"><text>{{ $tr("位置") }}</text><text>{{ player.role === '羽毛球爱好者' ? $tr('羽毛球爱好者') : player.role }}</text></view>
			<view class="line"><text>{{ $tr("训练累计分") }}</text><text>{{ $tr(player.points) }}</text></view>
			<view class="line"><text>{{ $tr("城市") }}</text><text>{{ player.city === '未设置城市' ? $tr('未设置城市') : player.city }}</text></view>
			<view class="line"><text>{{ $tr("标签") }}</text><text>{{ player.tags.join(' / ') }}</text></view>
			<view class="line"><text>{{ $tr("头像") }}</text><text>{{ $tr("用户头像") }}</text></view>
		</view>

		<view v-else class="empty">
			<text class="empty-title">{{ $tr(loading?'正在读取球友资料…':loadError?'暂时无法查看这位球友':'没有找到这个球友') }}</text>
			<text class="empty-sub">{{ $tr(loading?'请稍等':'可以重新读取，或返回重新选择。') }}</text>
			<button class="primary-btn" @click="goBack">{{ $tr("返回") }}</button>
		</view>
	</view>
</template>

<script setup>
import { computed, ref } from 'vue'
import { onLoad, onShow, onHide, onUnload } from '@dcloudio/uni-app'
import { request, absoluteUrl } from '../../utils/request'
import { getAuthToken } from '../../utils/auth'
import { getRelation, setFollow, setBlock, reportContent } from '../../utils/social-api'
import { applyChatRequest, acceptChatRequestRemote, getChatSelfId } from '../../utils/chat-api'
const playerName=ref(''),player=ref(null),relation=ref({following:false,blocked:false,can_interact:false}),relationReady=ref(false)
const busy=ref(false),loading=ref(true),photoFailed=ref(false),loadError=ref(''),chatState=ref({status:'none'})
let active=false,owner='',viewGeneration=0,readGeneration=0
const isSelf=computed(()=>player.value&&String(player.value.id)===getChatSelfId())
const canInteract=computed(()=>Boolean(relationReady.value&&relation.value.can_interact&&!isSelf.value))
function context(){return {page:viewGeneration,owner,token:getAuthToken(),id:playerName.value}}
function current(c){return active&&c.page===viewGeneration&&c.owner===getChatSelfId()&&c.token===getAuthToken()&&c.id===playerName.value}
function leave(){active=false;viewGeneration++;readGeneration++;loading.value=false;busy.value=false}
onHide(leave);onUnload(leave)
onLoad(query=>{playerName.value=/^[1-9][0-9]*$/.test(String(query.id||''))?String(query.id):''})
onShow(()=>{
    if(owner!==getChatSelfId()){owner=getChatSelfId();player.value=null;relationReady.value=false;relation.value={following:false,blocked:false,can_interact:false};chatState.value={status:'none'};photoFailed.value=false}
    active=true;viewGeneration++;refresh()
})
async function refresh(){
    if(!active)return
    const c=context(),generation=++readGeneration
    loading.value=true;loadError.value='';relationReady.value=false
    if(!playerName.value){player.value=null;loadError.value='没有找到这个球友，请返回后重新选择';loading.value=false;return}
    try{
        const [item,state]=await Promise.all([request(`/discovery/players/${encodeURIComponent(c.id)}`),getRelation(c.id)])
        if(!current(c)||generation!==readGeneration)return
        player.value={...item,avatar:absoluteUrl(item.avatar)};relation.value=state;relationReady.value=true;photoFailed.value=false
        const status=item.chat_state
        chatState.value={status:['waiting','review'].includes(status)?'pending':status,
            thread:status==='accepted'?{id:String(item.chat_id)}:null,
            request:item.chat_id?{id:String(item.chat_id),fromId:status==='waiting'?getChatSelfId():String(item.id)}:null}
    }catch(e){
        if(!current(c)||generation!==readGeneration)return
        loadError.value=e.message||'球友状态暂时无法读取，请重试'
        if(e.status===404||e.status===403){player.value=null;chatState.value={status:'none'}}
    }finally{if(current(c)&&generation===readGeneration)loading.value=false}
}
const primaryLabel=computed(()=>{
    if(chatState.value.status==='accepted')return '去聊天'
    if(chatState.value.status==='pending'&&chatState.value.request?.fromId!==getChatSelfId())return '同意聊天'
    if(chatState.value.status==='pending')return '查看进度'
    if(chatState.value.status==='rejected')return '重新申请'
    return '申请聊天'
})
const statusLabel=computed(()=>{
    if(isSelf.value)return '这是你自己的资料'
    if(!relationReady.value)return '互动状态尚未读取'
    if(relation.value.blocked)return '已屏蔽'
    if(!canInteract.value)return '暂时无法互动'
    return {accepted:'已同意',pending:'待同意',rejected:'已拒绝'}[chatState.value.status]||'可申请'
})
const statusDescription=computed(()=>{
    if(isSelf.value)return '返回个人页可以修改资料。训练累计分不代表比赛水平。'
    if(!relationReady.value)return '请重新读取状态后再操作。'
    if(relation.value.blocked)return '已停止互动。取消屏蔽后可以重新查看状态，之前的关注不会恢复。'
    if(!canInteract.value)return '当前不能与这位球友互动，可以稍后刷新查看。'
    if(chatState.value.status==='accepted')return '你们已经建立会话，可以直接聊天。'
    if(chatState.value.status==='pending'&&chatState.value.request?.fromId!==getChatSelfId())return '对方发来申请，同意后即可聊天。'
    if(chatState.value.status==='pending')return '申请已发出，等对方同意后会出现在聊天页。'
    if(chatState.value.status==='rejected')return '上一次申请被拒绝，可以重新发起。'
    return '先发起聊天申请，对方同意后才会开聊。'
})
async function toggleFollow(){
    if(busy.value||loading.value||!canInteract.value||!player.value)return
    const c=context(),id=player.value.id,wanted=!relation.value.following
    busy.value=true;readGeneration++
    try{const result=await setFollow(id,wanted);if(current(c))relation.value={...relation.value,following:result.following}}
    catch(e){if(current(c)){await refresh();if(current(c))loadError.value=e.message}}
    finally{if(current(c))busy.value=false}
}
function toggleBlock(){
    if(busy.value||loading.value||!relationReady.value||!player.value||isSelf.value)return
    const c=context(),id=player.value.id,wasBlocked=relation.value.blocked
    uni.showModal({title:wasBlocked?'取消屏蔽':'屏蔽球友',content:wasBlocked?'取消后可以重新查看互动状态，之前的关注不会恢复。':'屏蔽后停止聊天，并隐藏对方动态；双方的关注关系会取消。',success:async r=>{
        if(!r.confirm||!current(c)||busy.value||loading.value||!relationReady.value||relation.value.blocked!==wasBlocked)return
        busy.value=true;readGeneration++
        try{
            await setBlock(id,!wasBlocked)
            if(!current(c))return
            relation.value={...relation.value,blocked:!wasBlocked,following:false,can_interact:false}
            await refresh()
        }catch(e){if(current(c))loadError.value=e.message}
        finally{if(current(c))busy.value=false}
    }})
}
function reportPlayer(){
    if(!player.value||isSelf.value||busy.value||loading.value)return
    const c=context();reportContent('user',player.value.id,()=>current(c))
}
function getInitials(name){return String(name||'球友').split(' / ')[0].slice(0,2)}
function markPhotoFailed(){photoFailed.value=true}
function goBack(){uni.navigateBack()}
function goInbox(){uni.navigateTo({url:'/pages/chat/inbox'})}
async function primaryAction(){
    if(!player.value||busy.value||loading.value||!canInteract.value)return
    if(chatState.value.thread){uni.navigateTo({url:`/pages/chat/thread?id=${chatState.value.thread.id}`});return}
    if(chatState.value.status==='pending'&&chatState.value.request?.fromId===getChatSelfId()){goInbox();return}
    const c=context(),contact={...player.value},state=chatState.value
    busy.value=true;readGeneration++
    try{
        if(state.status==='pending'){
            const result=await acceptChatRequestRemote(state.request.id)
            if(current(c))uni.navigateTo({url:`/pages/chat/thread?id=${result.chat.id}`})
        }else{
            const result=await applyChatRequest(contact)
            if(!current(c))return
            uni.showToast({title:result.message,icon:'none'});await refresh()
        }
    }catch(e){if(current(c)){await refresh();if(current(c))loadError.value=e.message}}
    finally{if(current(c))busy.value=false}
}
</script>

<style lang="scss" scoped>
.page {
	min-height: 100vh;
	background: #121212;
	color: #FFFFFF;
	padding: 24rpx 24rpx calc(28rpx + env(safe-area-inset-bottom));
	box-sizing: border-box;
}

.hero,
.panel,
.empty {
	margin-bottom: 18rpx;
	border-radius: 18rpx;
	background: #1E1E1E;
	border: 1rpx solid #2C2C2E;
	overflow: hidden;
}

.hero {
	position: relative;
}

.photo { position: relative; }

.cover {
	display: block;
	width: 100%;
	height: 420rpx;
	background: #2C2C2E;
}

.fallback {
	position: absolute;
	inset: 0;
	display: flex;
	align-items: center;
	justify-content: center;
	background: #2C2C2E;
	color: #CCFF00;
	font-size: 42rpx;
	font-weight: 900;
}

.hero-body {
	padding: 22rpx 22rpx 24rpx;
}

.rank {
	display: block;
	color: #CCFF00;
	font-size: 24rpx;
	font-weight: 900;
}

.name {
	display: block;
	margin-top: 8rpx;
	font-size: 40rpx;
	font-weight: 900;
}

.meta,
.bio,
.status,
.panel-text {
	display: block;
	margin-top: 12rpx;
	font-size: 24rpx;
	line-height: 1.6;
	color: #D8D8D8;
}

.meta {
	color: #8E8E93;
}

.status.accepted {
	color: #4CD964;
}

.status.pending {
	color: #CCFF00;
}

.status.rejected {
	color: #8E8E93;
}

.panel {
	padding: 22rpx;
}

.panel-title {
	display: block;
	font-size: 30rpx;
	font-weight: 900;
}

.button-row {
	margin-top: 16rpx;
	display: grid;
	grid-template-columns: repeat(2, 1fr);
	gap: 12rpx;
}

.primary-btn,
.ghost-btn {
	height: 74rpx;
	border-radius: 14rpx;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 26rpx;
	font-weight: 900;
}

.primary-btn {
	margin-top: 12rpx;
	background: #CCFF00;
	color: #121212;
}

.ghost-btn {
	background: #2C2C2E;
	color: #FFFFFF;
}

.line {
	min-height: 64rpx;
	display: flex;
	align-items: center;
	justify-content: space-between;
	border-bottom: 1rpx solid #2C2C2E;
	color: #8E8E93;
	font-size: 24rpx;
}

.line:last-child {
	border-bottom: 0;
}

.empty {
	padding: 120rpx 24rpx;
	text-align: center;
}

.empty-title {
	display: block;
	font-size: 36rpx;
	font-weight: 900;
}

.empty-sub {
	display: block;
	margin-top: 10rpx;
	color: #8E8E93;
	font-size: 24rpx;
}
</style>
