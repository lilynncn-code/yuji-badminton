<template>
	<view class="page">
		<view class="header">
			<view class="header-left" @click="goBack" :hover-class="'click-feedback'">
				<text class="back">{{ $tr("‹") }}</text>
			</view>
			<view class="header-main">
				<text class="name">{{ thread?.otherName ? (thread.otherNameIsDefault ? $tr(thread.otherName) : thread.otherName) : $tr('聊天') }}</text>
				<text class="status">{{ $tr(thread ? '已同意后可聊天' : '暂无会话') }}</text>
			</view>
			<button class="header-btn" @click="goInbox">{{ $tr("消息") }}</button>
			<button class="header-btn" :disabled="managing || sending" @click="manageChat">{{ $tr("管理") }}</button>
		</view>

		<scroll-view class="messages" scroll-y :scroll-top="scrollTop">
            <view v-if="loadError" class="chat-note"><text>{{ $tr(loadError) }}</text><button :disabled="loading||managing" @click="refresh()">{{ $tr("重新读取") }}</button></view>
            <text v-if="loading" class="chat-note">{{ $tr("正在读取聊天…") }}</text>
			<view v-if="thread" class="message-list">
                <button v-if="thread.hasMore" :disabled="loadingEarlier" @click="loadEarlier">{{ $tr(loadingEarlier ? '加载中' : '查看更早的消息') }}</button>
                <text v-if="earlierError" class="chat-note">{{ $tr("{0}，可点击上方按钮重试。", [earlierError]) }}</text>
				<view v-for="message in thread.messages" :key="message.id" class="message-row" :class="messageClass(message)">
					<view v-if="message.type === 'system'" class="system-pill">{{ $tr(message.text) }}</view>
					<view v-else class="bubble">
						<image v-if="message.senderId !== selfId" class="bubble-avatar" :src="thread.otherAvatar" mode="aspectFill" />
						<view class="bubble-main">
							<view class="bubble-card">
								<ChatImage v-if="message.image" :path="message.image" :active="imagesActive" />
								<view v-if="message.type === 'voice'" class="voice-line" @click="playLastVoice(message)">
									<text class="voice-dot"></text>
									<text class="voice-text">{{ $tr(message.text || '语音消息') }}</text>
								</view>
								<text v-if="message.text && message.type !== 'voice'" class="bubble-text">{{ message.text }}</text>
							</view>
							<view class="message-meta"><text class="bubble-time">{{ $tr("{0}{1}", [formatTimeLabel(message.createdAt), message.senderId===selfId ? (Number(message.id)<=thread.otherReadId?' · 对方已读':' · 未读') : '']) }}</text><text v-if="canRecall(message)" class="recall" @click="recall(message)">{{ $tr("撤回") }}</text></view>
						</view>
						<image v-if="message.senderId === selfId" class="bubble-avatar" :src="user.avatar" mode="aspectFill" />
					</view>
				</view>
			</view>
			<view v-else-if="loadError" class="empty"><text class="empty-sub">{{ $tr(loadError) }}</text><button @click="refresh()">{{ $tr("重新加载") }}</button></view>
			<view v-else class="empty">
				<text class="empty-title">{{ $tr("还没有可聊的会话") }}</text>
				<text class="empty-sub">{{ $tr("去积分匹配页发出申请，等对方同意后再回来。") }}</text>
				<button class="empty-btn" @click="goMatch">{{ $tr("去匹配") }}</button>
			</view>
		</scroll-view>

		<view v-if="thread" class="composer">
            <text v-if="draftError||sendError||voiceError" class="chat-note">{{ $tr([draftError,sendError,voiceError].filter(Boolean).join('；')) }}</text>
            <view v-if="pendingVoice" class="pending-voice"><text>{{ $tr("{0}{1}", [sending?'正在发送录音…':'有一条录音等待确认发送，可重试或放弃。', pendingVoice.saved?'':'临时录音可能在关闭应用后失效。']) }}</text><view class="pending-voice-actions"><button :disabled="sending||recording" @click="previewPendingVoice">{{ $tr("试听") }}</button><button :disabled="sending||recording||managing" @click="retryVoice">{{ $tr("重试发送") }}</button><button :disabled="sending||recording" @click="discardVoice">{{ $tr("放弃") }}</button></view></view>
			<view v-if="selectedImage" class="draft-image">
				<ChatImage v-if="selectedImage.startsWith('/chat/chats/')" :path="selectedImage" :active="imagesActive"/><image v-else :src="selectedImage" mode="aspectFill" />
				<text class="remove" @click="removeImage">{{ $tr("×") }}</text>
			</view>
			<text v-if="!recorder" class="voice-note">{{ $tr("录音请用手机版") }}</text>
			<view class="tool-row" :class="{'without-recorder':!recorder}">
				<view class="media-tools">
					<button class="tool-btn" :disabled="sending||managing" @click="chooseAlbum">{{ $tr("相册") }}</button>
					<button class="tool-btn" :disabled="sending||managing" @click="toggleLibrary">{{ $tr("图库") }}</button>
					<button v-if="recorder" class="tool-btn voice-btn" :class="{ recording: recording }" @touchstart="startRecord" @touchend="stopRecord" @touchcancel="cancelMouseRecord" @mousedown="startRecord" @mouseup="stopRecord" @mouseleave="cancelMouseRecord">{{ $tr(recording ? '松开发' : '按住说') }}</button>
				</view>
				<input class="input" :disabled="sending||managing" v-model="draftText" :placeholder='$tr("输入消息")' placeholder-class="placeholder" confirm-type="send" @confirm="sendMessage" />
				<button class="send-btn" :disabled="sending||managing" @click="sendMessage">{{ $tr(sending?'发送中':'发送') }}</button>
			</view>
			<view v-if="libraryVisible" class="library">
				<image v-for="image in imageLibrary" :key="image.id" class="library-image" :class="{ picked: selectedImage === image.url }" :src="image.url" mode="aspectFill" @click="pickLibrary(image)" />
			</view>
		</view>
	</view>
</template>

<script setup>
import { nextTick, onUnmounted, ref, watch } from 'vue'
import { onLoad, onShow, onHide } from '@dcloudio/uni-app'
import { imageLibrary } from '../../data/app-data'
import { formatTimeLabel, getUser } from '../../utils/store'
import { getAuthToken } from '../../utils/auth'
import { fetchChatThread, getChatSelfId, sendChatMessageRemote, sendChatVoiceRemote, markChatRead, downloadVoice, recallChatMessage, clearChatHistory, removeChatConversation, openChatConversation } from '../../utils/chat-api'
import ChatImage from '../../components/ChatImage.vue'
import { readVoiceDraft,keepVoiceDraft,forgetVoiceDraft } from '../../utils/voice-draft'
import { chatDraftSignature,readChatDraft,saveChatDraft,prepareChatSend,saveChatUpload,clearChatDraft } from '../../utils/chat-draft'
const selfId=ref(''),user=ref({}),threadId=ref(''),thread=ref(null)
const imagesActive=ref(false),managing=ref(false),loadError=ref(''),earlierError=ref(''),draftError=ref(''),sendError=ref(''),voiceError=ref('')
const draftText=ref(''),selectedImage=ref(''),libraryVisible=ref(false),scrollTop=ref(0)
const sending=ref(false),pendingVoice=ref(null),loadingEarlier=ref(false),loading=ref(false),recording=ref(false)
let active=false,pageGeneration=0,loadGeneration=0,refreshing=false,poll=null,sessionToken='',pendingSend=null,suppressDraft=false
let sendOperation=null,manageOperation=null,recordAttempt=null,recordPreparing=false,voicePlayGeneration=0,recorder=null
const memoryDrafts=new Map()
// #ifndef H5
recorder=uni.getRecorderManager?uni.getRecorderManager():null
// #endif
const audioPlayer=uni.createInnerAudioContext?uni.createInnerAudioContext():null
audioPlayer?.onError?.(()=>{if(active)voiceError.value='录音无法播放，文件可能已失效，请重试或重新录制'})
function context(){return {owner:selfId.value,token:sessionToken,chat:threadId.value,page:pageGeneration}}
function sameLogin(c){return c.owner===getChatSelfId()&&c.owner===selfId.value&&c.token===getAuthToken()&&c.token===sessionToken&&c.chat===threadId.value}
function current(c){return active&&sameLogin(c)&&c.page===pageGeneration}
function ready(){return active&&sameLogin(context())&&Boolean(threadId.value)}
function memoryKey(owner=selfId.value,chat=threadId.value){return `${chat}:${owner}`}
function data(){return {text:draftText.value,image:selectedImage.value}}
function setDraft(saved){suppressDraft=true;pendingSend={...saved};draftText.value=saved.text||'';selectedImage.value=saved.image||'';suppressDraft=false}
function persistDraft(){
    if(suppressDraft||!ready())return
    const value=data()
    try{pendingSend=saveChatDraft(selfId.value,threadId.value,value,pendingSend);memoryDrafts.set(memoryKey(),{...pendingSend});draftError.value=''}
    catch{pendingSend={...value,...(chatDraftSignature(value)===chatDraftSignature(pendingSend||{})?{requestKey:pendingSend?.requestKey,uploadedImage:pendingSend?.uploadedImage}:{})};memoryDrafts.set(memoryKey(),{...pendingSend});draftError.value='聊天草稿未能保存在本机，请检查存储空间；关闭应用可能丢失'}
}
watch([draftText,selectedImage],persistDraft,{flush:'sync'})
function restoreDraft(){
    try{setDraft(memoryDrafts.get(memoryKey())||readChatDraft(selfId.value,threadId.value));draftError.value=''}
    catch{setDraft({});draftError.value='本机聊天草稿无法读取，请检查存储空间后重试'}
    try{pendingVoice.value=readVoiceDraft(threadId.value,selfId.value);voiceError.value=''}catch{pendingVoice.value=null;voiceError.value='待发录音无法读取，请检查存储空间'}
}
onLoad(query=>{threadId.value=/^[1-9][0-9]*$/.test(String(query.id||''))?String(query.id):''})
onShow(()=>{
    const next=getChatSelfId(),token=getAuthToken(),changed=next!==selfId.value||token!==sessionToken
    pageGeneration++;loadGeneration++;active=true;refreshing=false;loading.value=false;loadingEarlier.value=false
    if(changed){thread.value=null;setDraft({});pendingVoice.value=null;libraryVisible.value=false;scrollTop.value=0;voicePlayGeneration++;audioPlayer?.stop()}
    selfId.value=next;sessionToken=token;user.value={...getUser()};imagesActive.value=true
    loadError.value='';earlierError.value='';sendError.value='';restoreDraft();syncBusy()
    if(threadId.value){if(!managing.value)enterChat()}else loadError.value='请从消息列表选择一个聊天'
    clearInterval(poll);poll=setInterval(()=>refresh(true),4000)
})
function cleanup(){
    persistDraft();active=false;pageGeneration++;loadGeneration++;refreshing=false;loading.value=false;loadingEarlier.value=false;imagesActive.value=false
    clearInterval(poll);voicePlayGeneration++;audioPlayer?.stop()
    if(recordAttempt){recordAttempt.canceled=true;if(recording.value){recording.value=false;try{recorder?.stop()}catch{recordAttempt=null}}}
}
onHide(cleanup)
onUnmounted(()=>{cleanup();recorder?.offStop?.(onRecordStop);recorder?.offError?.(onRecordError);audioPlayer?.destroy()})
function syncBusy(){sending.value=Boolean(sendOperation&&sameLogin(sendOperation.c));managing.value=Boolean(manageOperation&&sameLogin(manageOperation.c))}
async function enterChat(){
    const c=context()
    try{await openChatConversation(c.chat);if(current(c))await refresh()}
    catch(e){if(current(c)){loadError.value=e.message||'聊天打开失败';thread.value=null}}
}
async function refresh(silent=false){
    if(active&&!sameLogin(context())){cleanup();thread.value=null;setDraft({});pendingVoice.value=null;loadError.value='登录情况已变化，请返回消息列表重新打开聊天';return}
    if(!ready()||refreshing||loadingEarlier.value||managing.value)return
    const c=context(),ticket=++loadGeneration,lastId=thread.value?.messages.at(-1)?.id
    refreshing=true;loading.value=!thread.value
    try{
        const next=await fetchChatThread(c.chat,lastId?{after_id:lastId,after_change_id:thread.value.changeCursor||0}:{})
        if(!current(c)||ticket!==loadGeneration)return
        if(lastId&&thread.value){const known=new Set(thread.value.messages.map(m=>m.id));next.messages=[...thread.value.messages,...next.messages.filter(m=>!known.has(m.id))];next.hasMore=thread.value.hasMore}
        const updates=new Map((next.messageUpdates||[]).map(m=>[m.id,m]));next.messages=next.messages.map(m=>updates.get(m.id)||m)
        const changed=next.messages.at(-1)?.id!==thread.value?.messages.at(-1)?.id
        thread.value=next;loadError.value=''
        if(changed)scrollToBottom(c)
        const latest=next.messages.at(-1)?.id
        if(latest&&current(c))await markChatRead(c.chat,latest)
    }catch(e){if(current(c)&&ticket===loadGeneration){loadError.value=e.message||'聊天读取失败，请重试';if([401,403,404].includes(e.status))thread.value=null}}
    finally{if(current(c)&&ticket===loadGeneration){refreshing=false;loading.value=false}}
}
async function loadEarlier(){
    if(!ready()||loadingEarlier.value||refreshing||managing.value||!thread.value?.hasMore)return
    const c=context(),ticket=++loadGeneration,before=thread.value.messages[0]?.id
    if(!before)return
    loadingEarlier.value=true;earlierError.value=''
    try{
        const earlier=await fetchChatThread(c.chat,{before_id:before})
        if(!current(c)||ticket!==loadGeneration||!thread.value)return
        const known=new Set(thread.value.messages.map(m=>m.id));thread.value.messages=[...earlier.messages.filter(m=>!known.has(m.id)),...thread.value.messages]
        thread.value.hasMore=earlier.hasMore
    }catch(e){if(current(c)&&ticket===loadGeneration){earlierError.value=e.message||'更早消息读取失败，请重试';if([401,403,404].includes(e.status))thread.value=null}}
    finally{if(current(c)&&ticket===loadGeneration)loadingEarlier.value=false}
}
function scrollToBottom(c=context()){nextTick(()=>{if(current(c))scrollTop.value=999999})}
function goBack(){uni.navigateBack()}
function goInbox(){uni.navigateTo({url:'/pages/chat/inbox'})}
function goMatch(){uni.switchTab({url:'/pages/match-making/match-making'})}
function messageClass(message){return message.type==='system'?'system-row':message.senderId===selfId.value?'me-row':'other-row'}
function canRecall(message){return ready()&&message.senderId===selfId.value&&!message.recalled&&Date.now()-new Date(message.createdAt).getTime()<=120000}
function beginManage(c){const op={c};manageOperation=op;loadGeneration++;refreshing=false;loading.value=false;loadingEarlier.value=false;syncBusy();return op}
function endManage(op){if(manageOperation===op){manageOperation=null;syncBusy();if(active&&sameLogin(op.c)&&!current(op.c))refresh()}}
function recall(message){
    if(!ready()||managing.value||sending.value||recording.value||!canRecall(message))return
    const c=context(),id=message.id
    uni.showModal({title:'撤回这条消息',content:'发送后2分钟内可以撤回。无法收回对方已经保存的内容。',success:async r=>{
        if(!r.confirm||!current(c)||managing.value||sending.value||!thread.value?.messages.some(m=>m.id===id&&canRecall(m)))return
        const op=beginManage(c)
        try{const updated=await recallChatMessage(c.chat,id);if(current(c)&&thread.value){thread.value.messages=thread.value.messages.map(m=>m.id===updated.id?updated:m);voicePlayGeneration++;audioPlayer?.stop()}}
        catch(e){if(current(c))loadError.value=e.message||'撤回尚未确认，请刷新后重试'}finally{endManage(op)}
    }})
}
function manageChat(){
    if(!ready()||!thread.value||managing.value||sending.value||recording.value)return
    const c=context()
    uni.showActionSheet({itemList:['清空我这边的聊天记录','删除我这边的会话'],success:choice=>{
        if(!current(c)||managing.value||sending.value||![0,1].includes(choice.tapIndex))return
        const removing=choice.tapIndex===1
        uni.showModal({title:removing?'删除会话':'清空聊天记录',content:removing?'会清空你这边的历史并移出会话列表，对方的记录保留。收到新消息或主动打开聊天时会重新出现，旧记录不会恢复。':'只清空你这边的聊天记录，无法恢复；对方的记录保留。',success:async r=>{
            if(!r.confirm||!current(c)||managing.value||sending.value)return
            const op=beginManage(c)
            try{
                await(removing?removeChatConversation(c.chat):clearChatHistory(c.chat))
                if(!current(c))return
                thread.value=null;voicePlayGeneration++;audioPlayer?.stop();endManage(op)
                if(removing)uni.redirectTo({url:'/pages/chat/inbox'});else{await refresh();if(current(c))uni.showToast({title:'已清空',icon:'none'})}
            }catch(e){if(current(c))loadError.value=e.message||'操作尚未确认，请刷新后重试'}finally{endManage(op)}
        }})
    }})
}
function endSend(op){if(sendOperation===op){sendOperation=null;syncBusy()}}
async function sendMessage(){
    if(!ready()||!thread.value||sending.value||managing.value||recording.value)return
    if(!draftText.value.trim()&&!selectedImage.value){sendError.value='先输入消息或选一张图';return}
    const c=context(),value=data()
    let sent
    try{sent=prepareChatSend(c.owner,c.chat,value,pendingSend);pendingSend={...sent};memoryDrafts.set(memoryKey(),{...sent});draftError.value=''}
    catch{draftError.value='发送前未能保留草稿和发送编号，请检查存储空间后重试';return}
    const op={c,sent,kind:'text'};sendOperation=op;syncBusy();sendError.value=''
    const payload={...sent,isCurrent:()=>current(c),onUploaded:()=>{
        if(!sameLogin(c))return
        sent.uploadedImage=payload.uploadedImage
        const mk=memoryKey(c.owner,c.chat),remembered=memoryDrafts.get(mk)
        if(remembered?.requestKey===sent.requestKey&&chatDraftSignature(remembered)===chatDraftSignature(sent))memoryDrafts.set(mk,{...sent})
        if(pendingSend?.requestKey===sent.requestKey)pendingSend={...sent}
        saveChatUpload(c.owner,c.chat,sent)
    }}
    try{
        await sendChatMessageRemote(c.chat,payload)
        if(!sameLogin(c))return
        let cleared=false
        try{cleared=clearChatDraft(c.owner,c.chat,sent)}catch{if(active)draftError.value='消息已发送，本机待发项未能清理；可重试确认，不会重复发送'}
        const mk=memoryKey(c.owner,c.chat),remembered=memoryDrafts.get(mk)
        if(cleared&&remembered?.requestKey===sent.requestKey&&chatDraftSignature(remembered)===chatDraftSignature(sent))memoryDrafts.delete(mk)
        if(cleared&&pendingSend?.requestKey===sent.requestKey&&chatDraftSignature(data())===chatDraftSignature(sent))setDraft({})
        if(current(c)){await refresh();if(current(c))uni.showToast({title:'发送已确认',icon:'none'})}
    }catch(e){if(current(c))sendError.value=e.message||'发送未确认，内容保留，可重试'}finally{endSend(op)}
}
function chooseAlbum(){
    if(!ready()||sending.value||managing.value||recording.value)return
    const c=context()
    uni.chooseImage({count:1,sizeType:['compressed'],sourceType:['album'],success:r=>{if(current(c)&&!sending.value&&!managing.value){selectedImage.value=r.tempFilePaths?.[0]||'';libraryVisible.value=false}},fail:()=>{if(current(c))sendError.value='未选择图片，可使用图片库'}})
}
function toggleLibrary(){if(ready()&&!sending.value&&!managing.value&&!recording.value)libraryVisible.value=!libraryVisible.value}
function pickLibrary(image){if(ready()&&!sending.value&&!managing.value&&!recording.value)selectedImage.value=image.url}
function removeImage(){if(ready()&&!sending.value&&!managing.value)selectedImage.value=''}
function startRecord(){
    if(!ready()||!thread.value||recordAttempt||recordPreparing||sending.value||managing.value)return
    if(pendingVoice.value){voiceError.value='先重试或放弃上一条录音';return}
    if(!recorder){voiceError.value='录音请用手机版';return}
    const attempt={c:context(),started:Date.now(),canceled:false};recordAttempt=attempt;recording.value=true;voiceError.value=''
    try{recorder.start({duration:60000,sampleRate:16000,numberOfChannels:1,encodeBitRate:48000,format:'wav'})}
    catch{onRecordError()}
}
function stopRecord(){if(!recording.value||!recorder)return;recording.value=false;try{recorder.stop()}catch{onRecordError()}}
function cancelMouseRecord(){if(recordAttempt)recordAttempt.canceled=true;stopRecord()}
async function onRecordStop(result){
    const attempt=recordAttempt;recordAttempt=null;recording.value=false
    if(!attempt||attempt.canceled||!current(attempt.c))return
    if(Date.now()-attempt.started<600){voiceError.value='说话时间太短，请重新录制';return}
    if(!result.tempFilePath||sending.value||pendingVoice.value)return
    const op={c:attempt.c,kind:'keepVoice'};sendOperation=op;recordPreparing=true;syncBusy()
    try{
        const saved=await keepVoiceDraft(result.tempFilePath,attempt.c.chat,attempt.c.owner,{isCurrent:()=>sameLogin(attempt.c)})
        if(sameLogin(attempt.c))pendingVoice.value=saved
    }catch(e){if(current(attempt.c))voiceError.value=e.message||'录音未能保留，请重新录制'}
    finally{recordPreparing=false;endSend(op)}
    if(current(attempt.c)&&pendingVoice.value)await retryVoice()
}
function onRecordError(){const attempt=recordAttempt;recordAttempt=null;recording.value=false;if(attempt&&!attempt.canceled&&current(attempt.c))voiceError.value='录音失败，请检查麦克风权限'}
recorder?.onStop(onRecordStop);recorder?.onError(onRecordError)
async function retryVoice(){
    if(!ready()||!pendingVoice.value||sending.value||managing.value||recordAttempt||recordPreparing)return
    const c=context(),draft={...pendingVoice.value},op={c,kind:'voice'};sendOperation=op;syncBusy();voiceError.value=''
    try{
        await sendChatVoiceRemote(c.chat,draft.path,draft.requestKey)
        if(!sameLogin(c))return
        try{if(forgetVoiceDraft(c.chat,c.owner,draft)&&pendingVoice.value?.requestKey===draft.requestKey)pendingVoice.value=null}
        catch{if(active)voiceError.value='录音已发送，本机待发项未能清理；可重试确认'}
        if(current(c)){await refresh();if(current(c))uni.showToast({title:'录音发送已确认',icon:'none'})}
    }catch(e){if(current(c))voiceError.value=e.message||'录音发送未确认，可重试'}finally{endSend(op)}
}
function previewPendingVoice(){if(ready()&&audioPlayer&&pendingVoice.value&&!sending.value){voicePlayGeneration++;audioPlayer.stop();audioPlayer.src=pendingVoice.value.path;audioPlayer.play()}}
function discardVoice(){
    if(!ready()||sending.value||!pendingVoice.value)return
    const c=context(),draft={...pendingVoice.value}
    uni.showModal({title:'放弃待发录音',content:'会清除本机这份录音。如果之前已经送达，对方收到的录音仍会保留，可在聊天中查看。',success:r=>{
        if(!r.confirm||!current(c)||sending.value||pendingVoice.value?.requestKey!==draft.requestKey)return
        try{if(forgetVoiceDraft(c.chat,c.owner,draft)){voicePlayGeneration++;audioPlayer?.stop();pendingVoice.value=null;voiceError.value=''}}catch{voiceError.value='本机录音未能移除，请检查存储空间后重试'}
    }})
}
async function playLastVoice(message){
    if(!ready()||!audioPlayer||!message.audioPath)return
    const c=context(),play=++voicePlayGeneration
    try{const file=await downloadVoice(message.audioPath);if(current(c)&&play===voicePlayGeneration){audioPlayer.stop();audioPlayer.src=file;audioPlayer.play()}}
    catch(e){if(current(c)&&play===voicePlayGeneration)voiceError.value=e.message||'录音无法播放'}
}
</script>

<style lang="scss" scoped>
.chat-note{display:block;color:#ddd;font-size:24rpx;line-height:1.6;padding:12rpx;overflow-wrap:anywhere}.chat-note button{font-size:24rpx;margin:8rpx 0;background:#303030;color:#fff}
.pending-voice{font-size:24rpx;color:#cf0;background:#242424;padding:16rpx;margin-bottom:16rpx;border-radius:14rpx;line-height:1.5}.pending-voice-actions{display:flex;gap:12rpx;margin-top:12rpx}.pending-voice-actions button{flex:1;font-size:24rpx;padding:0 8rpx;background:#333;color:#fff}
.message-meta{display:flex;gap:18rpx;align-items:center;flex-wrap:wrap}.recall{color:#aaa;font-size:22rpx;margin-top:8rpx;padding:4rpx 8rpx}
.page {
	height: calc(100vh - var(--window-top, 0px));
	box-sizing: border-box;
	background: #121212;
	color: #FFFFFF;
	display: flex;
	flex-direction: column;
}

.header {
	flex-shrink:0;
	height: 96rpx;
	padding: 0 20rpx;
	display: flex;
	align-items: center;
	gap: 14rpx;
	border-bottom: 1rpx solid #2C2C2E;
}

.header-left,
.header-btn,
.tool-btn,
.send-btn,
.empty-btn {
	height: 68rpx;
	border-radius: 14rpx;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 24rpx;
	font-weight: 900;
	line-height: 1.2;
	text-align: center;
	box-sizing: border-box;
	white-space: normal;
}

.header-left {
	width: 68rpx;
	background: #1E1E1E;
}

.back {
	font-size: 44rpx;
	line-height: 1;
}

.header-main {
	flex: 1;
	min-width: 0;
}

.name {
	display: block;
	font-size: 32rpx;
	font-weight: 900;
}

.status {
	display: block;
	margin-top: 4rpx;
	color: #8E8E93;
	font-size: 20rpx;
}

.header-btn {
	min-width: 76rpx;
	padding: 0 22rpx;
	background: #1E1E1E;
	color: #CCFF00;
	flex: 0 0 auto;
}

.messages {
	flex: 1;
	height: 0;
}

.message-list {
	padding: 24rpx 18rpx;
}

.message-row {
	margin-bottom: 16rpx;
}

.system-row {
	display: flex;
	justify-content: center;
}

.system-pill {
	max-width: 88%;
	padding: 12rpx 18rpx;
	border-radius: 999rpx;
	background: rgba(255, 255, 255, 0.06);
	color: #8E8E93;
	font-size: 22rpx;
	line-height: 1.4;
	text-align: center;
}

.bubble {
	display: flex;
	align-items: flex-end;
}

.me-row .bubble {
	justify-content: flex-end;
}

.bubble-avatar {
	width: 64rpx;
	height: 64rpx;
	border-radius: 50%;
	background: #2C2C2E;
	flex: 0 0 auto;
}

.bubble-main {
	max-width: 74%;
	margin: 0 12rpx;
}

.bubble-card {
	padding: 16rpx 18rpx;
	border-radius: 18rpx;
	background: #1E1E1E;
	border: 1rpx solid #2C2C2E;
}

.me-row .bubble-card {
	background: rgba(204, 255, 0, 0.14);
	border-color: rgba(204, 255, 0, 0.28);
}

.bubble-image {
	width: 100%;
	height: 220rpx;
	border-radius: 14rpx;
	background: #2C2C2E;
	margin-bottom: 10rpx;
}

.bubble-text {
	display: block;
	font-size: 28rpx;
	line-height: 1.6;
	word-break: break-word;
}

.bubble-time {
	display: block;
	margin-top: 6rpx;
	color: #8E8E93;
	font-size: 20rpx;
}

.composer {
	position: relative;
	flex-shrink:0;
	z-index: 5;
	padding: 14rpx 16rpx calc(20rpx + env(safe-area-inset-bottom));
	border-top: 1rpx solid #2C2C2E;
	background: #151515;
	box-shadow: 0 -10rpx 30rpx rgba(0, 0, 0, 0.28);
}

.draft-image {
	position: relative;
	width: 180rpx;
	height: 180rpx;
	margin-bottom: 14rpx;
	border-radius: 16rpx;
	overflow: hidden;
}

.draft-image image {
	width: 100%;
	height: 100%;
}

.remove {
	position: absolute;
	right: 8rpx;
	top: 8rpx;
	width: 34rpx;
	height: 34rpx;
	border-radius: 50%;
	background: rgba(0, 0, 0, 0.6);
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 30rpx;
	line-height: 1;
}

.tool-row {
	display: grid;
	grid-template-columns: 268rpx minmax(0, 1fr) 96rpx;
	gap: 10rpx;
	align-items: center;
}

.media-tools {
	display: grid;
	grid-template-columns: repeat(3, minmax(0, 1fr));
	gap: 8rpx;
	min-width: 0;
}
.voice-note {display:block;color:#aaa;font-size:22rpx;line-height:1.4;margin-bottom:12rpx;}
.without-recorder{grid-template-columns:176rpx minmax(0,1fr) 96rpx}.without-recorder .media-tools{grid-template-columns:repeat(2,minmax(0,1fr))}

.tool-btn {
	width: 100%;
	min-height: 68rpx;
	padding: 6rpx 8rpx;
	background: #1E1E1E;
	color: #FFFFFF;
	font-size: 23rpx;
	line-height: 1.2;
	word-break: break-word;
}

.input {
	height: 68rpx;
	padding: 0 18rpx;
	border-radius: 14rpx;
	background: #1E1E1E;
	color: #FFFFFF;
	font-size: 26rpx;
	box-sizing: border-box;
}

.placeholder {
	color: #8E8E93;
}

.send-btn {
	width: 96rpx;
	min-height: 68rpx;
	padding: 6rpx 10rpx;
	background: #CCFF00;
	color: #121212;
	font-size: 24rpx;
	line-height: 1.2;
	word-break: keep-all;
}

.voice-btn.recording {
	background: #CCFF00;
	color: #121212;
}

.voice-line {
	display: flex;
	align-items: center;
	gap: 12rpx;
	min-width: 180rpx;
}

.voice-dot {
	width: 18rpx;
	height: 18rpx;
	border-radius: 50%;
	background: #CCFF00;
	flex: 0 0 auto;
}

.voice-text {
	display: block;
	font-size: 26rpx;
	line-height: 1.5;
	word-break: break-word;
}

.library {
	margin-top: 14rpx;
	display: grid;
	grid-template-columns: repeat(3, 1fr);
	gap: 10rpx;
}

.library-image {
	width: 100%;
	height: 120rpx;
	border-radius: 12rpx;
	background: #2C2C2E;
	box-sizing: border-box;
	border: 2rpx solid transparent;
}

.library-image.picked {
	border-color: #CCFF00;
}

@media screen and (max-width: 430px) {
	.tool-row {
		grid-template-columns: 1fr 96rpx;
		grid-template-areas:
			"tools tools"
			"input send";
		gap: 10rpx;
	}

	.media-tools {
		grid-area: tools;
		grid-template-columns: repeat(3, minmax(0, 1fr));
	}

	.input {
		grid-area: input;
	}

	.send-btn {
		grid-area: send;
	}
}

.empty {
	padding: 180rpx 28rpx 0;
	text-align: center;
}

.empty-title {
	display: block;
	font-size: 36rpx;
	font-weight: 900;
}

.empty-sub {
	display: block;
	margin-top: 12rpx;
	color: #8E8E93;
	font-size: 24rpx;
	line-height: 1.6;
}

.empty-btn {
	width: 220rpx;
	min-height: 72rpx;
	margin: 24rpx auto 0;
	padding: 8rpx 18rpx;
	background: #CCFF00;
	color: #121212;
}
</style>
