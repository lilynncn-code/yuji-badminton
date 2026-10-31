<template>
	<view class="page">
		<scroll-view class="content" scroll-y :scroll-into-view="scrollTarget">
            <view v-if="loadError" class="source-note"><text>{{ $tr(loadError) }}</text><button v-if="postId" :disabled="busy||loading" @click="loadPost(postId)">{{ $tr("重新加载") }}</button><button v-if="focusCommentId" :disabled="busy||loading" @click="showLatest">{{ $tr("查看最新留言") }}</button></view>
            <view v-else-if="loading" class="source-note">{{ $tr("正在读取内容…") }}</view>
			<view v-if="detail.id || isNewsDetail" class="article">
				<view class="author-row">
					<image class="avatar" :src="detail.authorAvatar" mode="aspectFill" />
					<view class="author-main">
						<text class="author">{{ (isNewsDetail || detail.authorNameIsDefault) ? $tr(detail.authorName) : detail.authorName }}</text>
						<text class="meta">{{ $tr(detail.meta) }}</text>
					</view>
				</view>
				<text class="title">{{ (isNewsDetail || detail.titleIsDefault) ? $tr(detail.title) : detail.title }}</text>
                <video v-if="detail.videoUrl" id="post-detail-video" :src="detail.videoUrl" controls style="width:100%;margin-top:24rpx" />
				<scroll-view v-if="detail.images.length" class="image-list" scroll-x>
					<image v-for="image in detail.images" :key="image" class="image" :src="image" mode="aspectFill" @click="previewImage(image)" />
				</scroll-view>
				<text class="body">{{ isNewsDetail ? $tr(detail.content) : detail.content }}</text>
                <button v-if="detail.isMine" :disabled="busy||loading" @click="removePost">{{ $tr("删除这条动态") }}</button>
                <button v-else-if="!isNewsDetail && detail.id"  :disabled="busy" @click="reportItem('post', detail.id)">{{ $tr("举报这条动态") }}</button>
                <button v-if="!isNewsDetail && !detail.isMine && detail.authorId" @click="openAuthor">{{ $tr("查看球友 · 关注与屏蔽") }}</button>
				<view class="tag-row">
					<text v-for="tag in detail.tags" :key="tag" class="tag">#{{ (isNewsDetail || detail.tagsAreDefault) ? $tr(tag) : tag }}</text>
				</view>
			</view>
			<view v-if="!isNewsDetail && detail.id" class="discussion">
				<view class="discussion-head">
					<text class="discussion-title">{{ $tr("讨论 {0}", [detail.commentsCount]) }}</text>
					<text class="discussion-sub">{{ $tr("把想法接上，球友才聊得起来") }}</text>
				</view>
                <view v-if="focusCommentId || focusNote" class="source-note"><text>{{ $tr(focusNote || '正在查看提醒对应的留言') }}</text></view>
                <button class="earlier-btn" :disabled="loading||busy" @click="showLatest">{{ $tr("刷新最新留言") }}</button>
                <button v-if="detail.commentsHasMore" class="earlier-btn" :disabled="loadingEarlier||loading||busy" @click="loadEarlier">{{ $tr(loadingEarlier?'正在读取…':'查看更早留言') }}</button>
                <view v-if="earlierError" class="source-note"><text>{{ $tr(earlierError) }}</text><button :disabled="loadingEarlier||loading||busy" @click="loadEarlier">{{ $tr("重试读取更早留言") }}</button></view>
				<scroll-view class="prompt-row" scroll-x show-scrollbar="false">
					<text v-for="prompt in prompts" :key="prompt" class="prompt" @click="usePrompt(prompt)">{{ $tr(prompt) }}</text>
				</scroll-view>
				<view v-if="detail.comments.length" class="comment-list">
					<view v-for="comment in detail.comments" :id="`comment-${comment.id}`" :key="comment.id" class="comment" :class="{'focused-comment':comment.id===focusCommentId}">
						<image class="comment-avatar" :src="comment.authorAvatar" mode="aspectFill" />
						<view class="comment-main">
							<view class="comment-top">
								<text class="comment-name">{{ comment.authorNameIsDefault ? $tr(comment.authorName) : comment.authorName }}</text>
								<text class="comment-time">{{ $tr(formatTimeLabel(comment.createdAt)) }}</text>
							</view>
                            <view v-if="comment.replyToId" class="reply-quote"><text v-if="comment.replyTo">{{ $tr('回复') + ' ' + comment.replyTo.authorName + ': ' + comment.replyTo.content }}</text><text v-else>{{ $tr("原留言已删除或暂时无法查看") }}</text></view>
							<text class="comment-content">{{ comment.content }}</text>
                            <view class="comment-actions"><text @click="chooseReply(comment)">{{ $tr("回复") }}</text><text v-if="comment.isMine" @click="removeComment(comment)">{{ $tr("删除留言") }}</text><text v-else @click="reportItem('comment', comment.id)">{{ $tr("举报留言") }}</text></view>
						</view>
					</view>
				</view>
				<view v-else class="empty-discussion">
					<text>{{ $tr("还没人开聊。问一个细节、约一场练习，或者补一句经验都可以。") }}</text>
				</view>
			</view>
		</scroll-view>
		<view v-if="!isNewsDetail && detail.id" class="reply-bar">
            <text v-if="draftError || sendError" class="draft-note">{{ $tr(draftError || sendError) }}</text>
            <view v-if="replyTo" class="reply-target"><text>{{ $tr('回复') + ' ' + replyTo.authorName }}</text><text @click="cancelReply">{{ $tr("取消回复") }}</text></view>
            <view class="reply-compose">
			<textarea
				class="reply-input"
				v-model="commentText"
                :disabled="busy"
                :focus="replyFocus"
				:placeholder="replyTo ? $tr('回复') + ' ' + replyTo.authorName : $tr('说说你的看法，或问一句想练什么')"
				placeholder-class="placeholder"
				auto-height
				maxlength="500"
			/>
			<button class="reply-btn" :disabled="busy||loading||loadingEarlier" @click="submitComment">{{ $tr(commentSending ? '发送中' : '发送') }}</button>
            </view>
		</view>
	</view>
</template>

<script setup>
import { ref,nextTick,watch } from 'vue'
import { onLoad,onShow,onHide,onUnload } from '@dcloudio/uni-app'
import { latestNews } from '../../data/app-data'
import { formatTimeLabel,getUser } from '../../utils/store'
import { getAuthToken } from '../../utils/auth'
import { fetchPost,fetchPostComments,publishComment,deletePost,deleteComment } from '../../utils/posts-api'
import { reportContent } from '../../utils/social-api'
import { commentDraftSignature,restoreCommentDraft,persistCommentDraft,prepareCommentSend,clearCommentDraft } from '../../utils/comment-draft'
function emptyDetail(){return {id:'',title:'',content:'',images:[],tags:[],authorName:'',authorAvatar:'',meta:'',comments:[],commentsCount:0,commentsHasMore:false}}
const detail=ref(emptyDetail()),postId=ref(''),focusCommentId=ref(''),focusNote=ref(''),scrollTarget=ref(''),replyTo=ref(null),replyFocus=ref(false)
const loading=ref(false),loadingEarlier=ref(false),loadError=ref(''),earlierError=ref(''),draftError=ref(''),sendError=ref(''),busy=ref(false)
const isNewsDetail=ref(false),commentText=ref(''),commentSending=ref(false),draftRequestKey=ref('')
const prompts=['你是怎么练的？','周末一起打一场？','这个装备手感如何？','能补个细节吗？']
let owner='',active=false,pageGeneration=0,loadGeneration=0,writeGeneration=0,suppressDraft=false
const memoryDrafts=new Map()
function memoryKey(uid=owner,id=postId.value){return `${id}:${uid}`}
function draftData(){return {content:commentText.value,replyTo:replyTo.value?{...replyTo.value}:null}}
function context(){return {page:pageGeneration,owner,token:getAuthToken(),postId:postId.value}}
function sameOwner(c){return c.owner===String(getUser()?.id||'')&&c.owner===owner&&c.token===getAuthToken()&&c.postId===postId.value}
function current(c){return active&&c.page===pageGeneration&&sameOwner(c)}
function setDraft(data){suppressDraft=true;commentText.value=data.content||'';replyTo.value=data.replyTo||null;draftRequestKey.value=data.requestKey||'';suppressDraft=false}
function persistDraft(){
    if(suppressDraft||!active||isNewsDetail.value||owner!==String(getUser()?.id||'')||!postId.value)return
    const data=draftData(),prior=memoryDrafts.get(memoryKey())
    try{
        const saved=persistCommentDraft(owner,postId.value,data,prior)
        memoryDrafts.set(memoryKey(),saved);draftRequestKey.value=saved.requestKey||'';draftError.value=''
    }catch{
        const saved={...data,...(prior?.requestKey&&commentDraftSignature(prior)===commentDraftSignature(data)?{requestKey:prior.requestKey}:{})}
        memoryDrafts.set(memoryKey(),saved);draftRequestKey.value=saved.requestKey||''
        draftError.value='留言未能保存在本机，请检查存储空间；离开应用后可能无法找回'
    }
}
watch([commentText,replyTo],persistDraft,{deep:true,flush:'sync'})
function restoreDraft(){
    draftError.value='';sendError.value=''
    try{const saved=memoryDrafts.get(memoryKey())||restoreCommentDraft(owner,postId.value);memoryDrafts.set(memoryKey(),saved);setDraft(saved)}
    catch{setDraft({});draftError.value='本机留言无法读取，请检查存储空间后重试'}
}
onLoad(query=>{
    isNewsDetail.value=query.type==='news'
    if(isNewsDetail.value){
        const news=latestNews.find(item=>String(item.id)===String(query.id))
        if(!news){isNewsDetail.value=false;loadError.value='这条资讯不存在';return}
        detail.value={...emptyDetail(),title:news.title,content:news.summary,images:[news.image],tags:[news.tag],authorName:news.tag,authorAvatar:news.image,meta:news.date}
        return
    }
    postId.value=/^[1-9][0-9]*$/.test(String(query.id||''))?String(query.id):''
    focusCommentId.value=/^[1-9][0-9]*$/.test(String(query.comment||''))?String(query.comment):''
})
onShow(()=>{
    const next=String(getUser()?.id||'')
    if(owner!==next){owner=next;if(!isNewsDetail.value)detail.value=emptyDetail();setDraft({});focusNote.value='';scrollTarget.value=''}
    active=true;pageGeneration++;busy.value=false;commentSending.value=false
    if(!isNewsDetail.value){restoreDraft();if(postId.value)loadPost(postId.value);else loadError.value='请从球圈选择一条动态'}
})
function leave(){active=false;pageGeneration++;loadGeneration++;writeGeneration++;loading.value=false;loadingEarlier.value=false;busy.value=false;commentSending.value=false;replyFocus.value=false;uni.createVideoContext('post-detail-video').pause()}
onHide(leave);onUnload(leave)
function applyPost(post){
    detail.value={...post,images:post.images||[],tags:post.tags||[],comments:post.comments||[],commentsHasMore:post.commentsHasMore,
        meta:`${formatTimeLabel(post.createdAt)}${post.updatedAt?' · 已编辑':''} · ♡ ${post.likes} · ${post.commentsCount||0} 条讨论`}
}
async function loadPost(id=postId.value){
    if(!active||busy.value||isNewsDetail.value||String(id)!==postId.value)return
    const c=context(),generation=++loadGeneration,target=focusCommentId.value
    loading.value=true;loadingEarlier.value=false;loadError.value='';earlierError.value=''
    try{
        let post
        try{post=await fetchPost(c.postId,target)}catch(e){
            if(e.status!==404||!target)throw e
            if(!current(c)||generation!==loadGeneration)return
            post=await fetchPost(c.postId)
            if(!current(c)||generation!==loadGeneration)return
            focusCommentId.value='';focusNote.value='提醒对应的留言已删除或暂时无法查看，以下显示最新留言。'
        }
        if(!current(c)||generation!==loadGeneration)return
        applyPost(post)
        if(focusCommentId.value){await nextTick();if(current(c)&&generation===loadGeneration)scrollTarget.value=`comment-${focusCommentId.value}`}
    }catch(e){
        if(!current(c)||generation!==loadGeneration)return
        loadError.value=e.message||'动态加载失败，请重试'
        if([403,404].includes(e.status))detail.value=emptyDetail()
    }finally{if(current(c)&&generation===loadGeneration)loading.value=false}
}
async function loadEarlier(){
    if(!active||loadingEarlier.value||loading.value||busy.value||!detail.value.commentsHasMore)return
    const c=context(),generation=loadGeneration;loadingEarlier.value=true;earlierError.value=''
    try{
        const data=await fetchPostComments(c.postId,detail.value.comments[0]?.id)
        if(!current(c)||generation!==loadGeneration)return
        const ids=new Set(detail.value.comments.map(item=>item.id))
        detail.value.comments=[...data.items.filter(item=>!ids.has(item.id)),...detail.value.comments];detail.value.commentsHasMore=data.hasMore
    }catch(e){if(current(c)&&generation===loadGeneration){earlierError.value=e.message||'较早留言读取失败';if([403,404].includes(e.status))detail.value=emptyDetail()}}
    finally{if(current(c)&&generation===loadGeneration)loadingEarlier.value=false}
}
function showLatest(){if(busy.value||loading.value)return;focusCommentId.value='';focusNote.value='';scrollTarget.value='';loadPost()}
async function chooseReply(comment){
    if(!active||busy.value||!detail.value.comments.some(item=>item.id===comment.id))return
    const c=context();replyTo.value={id:comment.id,authorName:comment.authorName};replyFocus.value=false
    await nextTick();if(current(c)&&!busy.value)replyFocus.value=true
}
function cancelReply(){if(active&&!busy.value)replyTo.value=null}
function beginWrite(){loadGeneration++;loading.value=false;loadingEarlier.value=false;earlierError.value='';busy.value=true;return ++writeGeneration}
function endWrite(c,ticket){if(current(c)&&ticket===writeGeneration){busy.value=false;commentSending.value=false}}
function removePost(){
    if(!active||busy.value||loading.value||!detail.value.id||!detail.value.isMine)return
    const c=context(),target=detail.value.id
    uni.showModal({title:'删除动态',content:'删除后无法恢复，确定删除吗？',success:async r=>{
        if(!r.confirm||!current(c)||busy.value||detail.value.id!==target||!detail.value.isMine)return
        const ticket=beginWrite()
        try{await deletePost(target);if(current(c))uni.navigateBack()}
        catch(e){if(current(c))loadError.value=e.message||'动态尚未删除，请重试'}
        finally{endWrite(c,ticket)}
    }})
}
function removeComment(comment){
    if(!active||busy.value||loading.value||!comment.isMine)return
    const c=context(),target=detail.value.id,id=comment.id
    uni.showModal({title:'删除留言',content:'确定删除这条留言吗？',success:async r=>{
        if(!r.confirm||!current(c)||busy.value||detail.value.id!==target||!detail.value.comments.some(item=>item.id===id&&item.isMine))return
        const ticket=beginWrite()
        try{
            await deleteComment(target,id)
            if(!current(c))return
            detail.value.comments=detail.value.comments.filter(item=>item.id!==id).map(item=>item.replyToId===id?{...item,replyTo:null}:item)
            detail.value.commentsCount=Math.max(0,detail.value.commentsCount-1)
            if(replyTo.value?.id===id){replyTo.value=null;sendError.value='要回复的留言已删除，输入仍保留，可以重新选择回复对象'}
            endWrite(c,ticket);await loadPost()
        }catch(e){if(current(c))loadError.value=e.message||'留言尚未删除，请重试'}
        finally{endWrite(c,ticket)}
    }})
}
function reportItem(type,id){if(!active||busy.value)return;const c=context();reportContent(type,id,()=>current(c))}
function openAuthor(){if(active&&detail.value.authorId)uni.navigateTo({url:`/pages/match-making/group-detail?id=${detail.value.authorId}`})}
function previewImage(image){if(active)uni.previewImage({current:image,urls:detail.value.images})}
function usePrompt(prompt){if(active&&!busy.value)commentText.value=commentText.value?`${commentText.value} ${prompt}`:prompt}
async function submitComment(){
    if(!active||busy.value||loading.value||loadingEarlier.value||!detail.value.id||owner!==String(getUser()?.id||''))return
    const data=draftData(),content=data.content.trim()
    if(!content){sendError.value='先写一句再发送';return}
    if(content.length>500){sendError.value='留言最多500字，请缩短后再发送';return}
    const c=context(),scope=memoryKey(c.owner,c.postId)
    let saved
    try{saved=prepareCommentSend(c.owner,c.postId,data,memoryDrafts.get(scope));memoryDrafts.set(scope,saved);draftRequestKey.value=saved.requestKey;draftError.value=''}
    catch{draftError.value='发送前未能保存本机留言，请检查存储空间后重试';return}
    const ticket=beginWrite();commentSending.value=true;sendError.value=''
    try{
        const comment=await publishComment(c.postId,content,{replyToId:saved.replyTo?.id||'',requestKey:saved.requestKey})
        // An acknowledgement can clear only this exact send, including after leaving.
        let clearFailed=false
        try{clearCommentDraft(c.owner,c.postId,saved.requestKey)}catch{clearFailed=true}
        if(memoryDrafts.get(scope)?.requestKey===saved.requestKey)memoryDrafts.set(scope,{content:'',replyTo:null})
        if(!active||!sameOwner(c))return
        if(draftRequestKey.value===saved.requestKey)setDraft({})
        if(clearFailed)draftError.value='留言已发送，但本机草稿未能清理；重新打开后可以继续确认原结果'
        if(detail.value.id===c.postId&&!detail.value.comments.some(item=>item.id===comment.id)){
            detail.value.comments.push(comment);detail.value.commentsCount++
        }
        if(current(c))uni.showToast({title:'已加入讨论',icon:'none'})
        // Refresh only when this is still the active send; never unlock a newer one.
        if(ticket===writeGeneration){busy.value=false;commentSending.value=false;focusCommentId.value='';focusNote.value='';await loadPost()}
        else if(!busy.value)await loadPost()
    }catch(e){if(current(c)&&ticket===writeGeneration)sendError.value=e.message||'发送尚未确认，请重试'}
    finally{endWrite(c,ticket)}
}
</script>

<style lang="scss" scoped>
.page { min-height: 100vh; background: #121212; color: #FFFFFF; }
.content { height: 100vh; }
.article { padding: 32rpx 24rpx 28rpx; box-sizing: border-box; }
.article button{margin-top:20rpx;background:#292929;color:#ddd;font-size:25rpx}
.source-note { margin: 24rpx 24rpx 0; padding: 20rpx 24rpx; border-radius: 16rpx; background: #1E1E1E; border: 1rpx solid #2C2C2E; color: #8E8E93; font-size: 22rpx; line-height: 1.5; }
.author-row { display: flex; align-items: center; margin-bottom: 26rpx; }
.avatar { width: 78rpx; height: 78rpx; border-radius: 50%; background: #2C2C2E; }
.author-main { flex: 1; min-width: 0; margin-left: 16rpx; }
.author { display: block; font-size: 28rpx; font-weight: 900; }
.meta { display: block; margin-top: 8rpx; color: #8E8E93; font-size: 22rpx; }
.title { display: block; font-size: 42rpx; font-weight: 900; line-height: 1.28; }
.image-list { width: 100%; margin-top: 24rpx; white-space: nowrap; }
.image { display: inline-block; width: 640rpx; height: 430rpx; margin-right: 18rpx; border-radius: 16rpx; background: #2C2C2E; }
.body { display: block; margin-top: 26rpx; color: #E8E8E8; font-size: 30rpx; line-height: 1.72; white-space: pre-wrap; }
.tag-row { margin-top: 26rpx; display: flex; flex-wrap: wrap; gap: 12rpx; }
.tag { padding: 10rpx 14rpx; border-radius: 999rpx; background: rgba(204,255,0,.1); color: #CCFF00; font-size: 23rpx; }
.discussion { padding: 0 24rpx 420rpx; box-sizing: border-box; }
.discussion-head { padding-top: 10rpx; display: flex; align-items: flex-end; justify-content: space-between; gap: 18rpx; }
.discussion-title { color: #FFFFFF; font-size: 32rpx; font-weight: 900; }
.discussion-sub { flex: 1; text-align: right; color: #8E8E93; font-size: 22rpx; line-height: 1.4; }
.prompt-row { width: 100%; margin: 20rpx 0 8rpx; white-space: nowrap; }
.prompt { display: inline-flex; align-items: center; height: 54rpx; margin-right: 12rpx; padding: 0 18rpx; border-radius: 999rpx; background: #242424; color: #D8D8D8; font-size: 24rpx; }
.comment-list { margin-top: 8rpx; }
.comment { display: flex; gap: 16rpx; padding: 22rpx 0; border-bottom: 1rpx solid #242424; }
.comment-avatar { width: 58rpx; height: 58rpx; border-radius: 50%; background: #2C2C2E; }
.comment-main { flex: 1; min-width: 0; }
.comment-top { display: flex; align-items: center; justify-content: space-between; gap: 16rpx; }
.comment-name { color: #FFFFFF; font-size: 25rpx; font-weight: 800; }
.comment-time { color: #8E8E93; font-size: 21rpx; }
.comment-content { display: block; margin-top: 8rpx; color: #E8E8E8; font-size: 27rpx; line-height: 1.55; white-space: pre-wrap; }
.empty-discussion { margin-top: 18rpx; padding: 24rpx; border-radius: 16rpx; background: #1E1E1E; border: 1rpx solid #2C2C2E; color: #8E8E93; font-size: 25rpx; line-height: 1.5; }
.reply-bar { position: fixed; left: 0; right: 0; bottom: 0; z-index: 20; padding: 18rpx 24rpx calc(18rpx + env(safe-area-inset-bottom)); background: rgba(18,18,18,.96); border-top: 1rpx solid #2C2C2E; box-sizing: border-box; }
.draft-note{display:block;color:#ffbf8a;font-size:23rpx;line-height:1.5;margin-bottom:12rpx}.reply-compose{display:flex;align-items:flex-end;gap:14rpx}.reply-target{display:flex;justify-content:space-between;color:#cf0;font-size:24rpx;margin-bottom:16rpx;gap:16rpx}.reply-quote{border-left:4rpx solid #777;background:#242424;margin-top:12rpx;padding:14rpx;font-size:24rpx;color:#bbb;white-space:pre-wrap;word-break:break-word}.comment-actions{display:flex;gap:28rpx;color:#aaa;margin-top:12rpx;font-size:23rpx}.comment-actions text:first-child{color:#cf0}.focused-comment{background:rgba(204,255,0,.06)}.earlier-btn,.source-note button{background:#333;color:#cf0;font-size:25rpx;margin:18rpx 0}
.reply-input { flex: 1; min-height: 68rpx; max-height: 168rpx; padding: 16rpx 20rpx; border-radius: 18rpx; background: #242424; color: #FFFFFF; font-size: 26rpx; line-height: 1.45; box-sizing: border-box; }
.placeholder { color: #777; }
.reply-btn { width: 128rpx; height: 68rpx; border-radius: 999rpx; background: #CCFF00; color: #121212; font-size: 26rpx; font-weight: 900; }
.reply-btn[disabled] { opacity: .6; }
</style>
