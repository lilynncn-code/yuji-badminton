<template>
	<view class="page" :style="{ paddingTop: statusBarHeight + 'px', '--top-safe-height': statusBarHeight + 'px' }">
		<view class="nav-bar">
			<view class="segment">
				<view v-for="tab in tabs" :key="tab.key" class="segment-item" :class="{ active: activeTab === tab.key }" @click="activeTab = tab.key" :hover-class="'click-feedback'">
					<text>{{ $tr(tab.label) }}</text>
					<view class="segment-line"></view>
				</view>
			</view>
			<button class="publish-btn" @click="openComposer()">{{ $tr(copy.publish) }}</button>
		</view>

		<scroll-view class="content" scroll-y>
			<view v-if="activeTab === 'feed'" class="post-list">
                <button @click="onlyMine = !onlyMine; loadPosts()">{{ $tr(onlyMine ? '显示所有动态' : '只看我的动态') }}</button>
                <button :disabled="onlyMine" @click="onlyFollowing=!onlyFollowing;loadPosts()">{{ $tr(onlyFollowing?'查看所有球友':'只看关注的球友') }}</button>
                <view style="display:flex;gap:12rpx;margin:18rpx 0"><input style="flex:1;color:white;background:#282828;padding:18rpx;border-radius:12rpx" v-model="searchText" maxlength="100" :placeholder='$tr("搜索动态")' @confirm="loadPosts()"/><button @click="loadPosts()">{{ $tr("搜索") }}</button></view>
				<view v-if="postsError" class="source-note"><text>{{ $tr(postsError) }}</text><button :disabled="loadingPosts" @click="retryPosts">{{ $tr("重试读取") }}</button></view>
                <view v-else-if="loadingPosts" class="source-note">
					<text>{{ $tr("正在加载动态...") }}</text>
				</view>
				<view v-else-if="usingBackupPosts" class="source-note">
					<text>{{ $tr("后端暂时连不上，正在显示本地备用动态。") }}</text>
				</view>
				<view v-else-if="!posts.length" class="source-note">
					<text>{{ $tr("还没有动态，来发第一条吧。") }}</text>
				</view>
				<view v-for="post in posts" :key="post.id" class="post-card" @click="openPostDetail(post)" :hover-class="'click-feedback'">
					<view class="post-head">
						<image class="avatar" :src="post.authorAvatar" mode="aspectFill" />
						<view class="author-main">
							<text class="author">{{ post.authorNameIsDefault ? $tr(post.authorName) : post.authorName }}</text>
							<text class="time">{{ $tr("{0}{1}", [formatTimeLabel(post.createdAt), post.updatedAt ? ` · ${copy.edited}` : '']) }}</text>
						</view>
						<button v-if="canEditPost(post)" class="edit-btn" @click.stop="openComposer(post)">{{ $tr("{0} {1}m", [copy.edit, editMinutesLeft(post)]) }}</button>
					</view>
					<text class="post-title">{{ post.titleIsDefault ? $tr(post.title) : post.title }}</text>
					<text class="post-content">{{ post.content }}</text>
                    <button v-if="post.videoUrl" @click.stop="openVideo(post)">{{ $tr("播放这条视频 ▶") }}</button>
					<scroll-view v-if="post.images.length" class="image-strip" scroll-x>
						<image v-for="image in post.images" :key="image" class="post-image" :src="image" mode="aspectFill" @click.stop="previewImage(image, post.images)" />
					</scroll-view>
					<view class="post-foot">
						<view class="tag-row">
							<text v-for="tag in post.tags" :key="tag" class="tag">#{{ post.tagsAreDefault ? $tr(tag) : tag }}</text>
						</view>
						<view class="action-row">
							<view class="comment-action" @click.stop="openPostDetail(post)">
								<text>{{ $tr("聊") }}</text>
								<text>{{ $tr(post.commentsCount || 0) }}</text>
							</view>
							<view class="like-action" :class="{ active: likedPosts[post.id] }" @click.stop="toggleLike(post)">
								<text class="heart">{{ $tr(likedPosts[post.id] ? '♥' : '♡') }}</text>
								<text>{{ $tr(post.likes) }}</text>
							</view>
						</view>
					</view>
				</view>
                <button v-if="postsHasMore" :disabled="loadingPosts" @click="loadPosts(true)">{{ $tr("加载更多") }}</button>
			</view>

			<view v-else-if="activeTab === 'news'" class="news-list">
				<view class="source-note">
					<text>{{ $tr(copy.sourceNote) }}</text>
				</view>
				<view v-for="item in latestNews" :key="item.id" class="news-card" @click="openNews(item)" :hover-class="'click-feedback'">
					<image class="news-image" :src="item.image" mode="aspectFill" />
					<view class="news-body">
						<text class="news-tag">{{ $tr(item.tag) }} · {{ $tr(item.date) }}</text>
						<text class="news-title">{{ $tr(item.title) }}</text>
						<text class="news-summary">{{ $tr(item.summary) }}</text>
					</view>
				</view>
			</view>

            <view v-else class="clinic-list">
                <button @click="goClinic()">{{ $tr("提出训练问题") }}</button>
                <button @click="clinicSaved=!clinicSaved;loadClinic()">{{ $tr(clinicSaved?'查看所有问题':'我的收藏') }}</button>
                <view v-if="clinicError" class="source-note"><text>{{ $tr(clinicError) }}</text><button :disabled="clinicLoading" @click="retryClinic">{{ $tr("重试读取") }}</button></view>
                <button @click="loadClinic()">{{ $tr("刷新问题") }}</button>
                <text v-if="!clinicPosts.length" class="source-note">{{ $tr("暂无问题，可以分享你的训练疑问。") }}</text>
                <view v-for="post in clinicPosts" :key="post.id" class="clinic-card" @click="goClinic(post.id)">
                    <text class="author">{{ post.author.name }}</text><text class="post-title">{{ post.titleIsDefault ? $tr(post.title) : post.title }}</text>
                    <text class="post-content">{{post.content}}</text><text class="time">{{ $tr("{0} 条回答 · {1}", [post.answer_count, post.accepted_answer_id?'已选择有帮助的回答':'交流中']) }}</text>
                </view>
                <button v-if="clinicHasMore" :disabled="clinicLoading" @click="loadClinic(true)">{{ $tr("加载更多") }}</button>
            </view>
		</scroll-view>

		<view v-if="composerVisible" class="mask" @click="closeComposer">
			<view class="composer" @click.stop>
				<view class="composer-head">
					<text class="composer-title">{{ $tr(editingPost ? copy.editPost : copy.publishPost) }}</text>
					<button class="close-btn" @click="closeComposer">{{ $tr("×") }}</button>
				</view>
				<text v-if="draftError || publishError" class="source-note">{{ $tr(draftError || publishError) }}</text>
                <input :disabled="submitting" maxlength="100" class="title-input" v-model="draft.title" :placeholder="$tr(copy.titlePlaceholder)" placeholder-class="placeholder" />
				<textarea :disabled="submitting" maxlength="1900" class="content-input" v-model="draft.content" :placeholder="$tr(copy.contentPlaceholder)" placeholder-class="placeholder" />
				<view class="picker-row">
					<button :disabled="submitting" class="picker-btn" @click="chooseVideo">{{ $tr("选择视频") }}</button>
					<button :disabled="submitting" class="picker-btn" @click="chooseFromAlbum">{{ $tr(copy.album) }}</button>
					<button :disabled="submitting" class="picker-btn" @click="libraryVisible = !libraryVisible">{{ $tr(copy.library) }}</button>
				</view>
				<view v-if="libraryVisible" class="library-grid">
					<image v-for="image in imageLibrary" :key="image.id" class="library-image" :class="{ picked: draft.images.includes(image.url) }" :src="image.url" mode="aspectFill" @click="toggleLibraryImage(image.url)" />
				</view>
				<scroll-view v-if="draft.images.length" class="image-strip draft-strip" scroll-x>
					<view v-for="image in draft.images" :key="image" class="draft-image-wrap">
						<image class="post-image" :src="absoluteUrl(image)" mode="aspectFill" />
						<text class="remove-image" @click="removeImage(image)">{{ $tr("×") }}</text>
					</view>
				</scroll-view>
                <text style="display:block;color:#aaa;font-size:24rpx;line-height:1.6">{{ $tr("图片和视频选择后会上传，获得文件地址的人可以查看。请勿上传私人内容；仅供自己重看的录像请保存到训练记录。") }}</text>
                <view v-if="draft.videoUrl"><video id="draft-video" :src="absoluteUrl(draft.videoUrl)" controls style="width:100%"/><button class="picker-btn" :disabled="submitting" @click="draft.videoUrl=''">{{ $tr("移除视频") }}</button></view>
				<text v-if="editingPost" class="edit-window">{{ $tr("{0} {1} {2}", [copy.editWindow, editMinutesLeft(editingPost), copy.minutes]) }}</text>
				<button class="submit-btn" :disabled="submitting" @click="submitPost">{{ $tr(editingPost ? copy.save : copy.submit) }}</button>
			</view>
		</view>

	</view>
</template>

<script setup>
import { computed,ref,watch } from 'vue'
import { onShow,onLoad,onHide,onUnload } from '@dcloudio/uni-app'
import { imageLibrary,latestNews } from '../../data/app-data'
import { canEditPost,editMinutesLeft,formatTimeLabel,getUser } from '../../utils/store'
import { getAuthToken } from '../../utils/auth'
import { applyAppLanguage,getAppLanguage,getCopy,setPageTitle } from '../../utils/i18n'
import { fetchPosts,publishPost,savePost,setPostLike } from '../../utils/posts-api'
import { accountKey,request,uploadImage,uploadVideo,absoluteUrl } from '../../utils/request'
import { restorePostDraft,persistPostDraft,preparePostSend,clearPostDraft,postRequestSnapshot } from '../../utils/post-draft'
import { getTopSafeAreaHeight } from '../../utils/safe-area'
const statusBarHeight=getTopSafeAreaHeight(),activeTab=ref('feed'),language=ref(getAppLanguage()),copy=computed(()=>getCopy('feed',language.value))
const posts=ref([]),likedPosts=ref({}),likeBusy=ref({}),loadingPosts=ref(false),usingBackupPosts=ref(false),postsError=ref('')
const composerVisible=ref(false),submitting=ref(false),postCursor=ref(''),postsHasMore=ref(false),totalPosts=ref(0),onlyMine=ref(false),onlyFollowing=ref(false),searchText=ref('')
const libraryVisible=ref(false),editingPost=ref(null),draft=ref(emptyDraft()),draftError=ref(''),publishError=ref('')
const clinicPosts=ref([]),clinicError=ref(''),clinicSaved=ref(false),clinicTotal=ref(0),clinicCursor=ref(''),clinicHasMore=ref(false),clinicLoading=ref(false)
const tabs=computed(()=>[{key:'feed',label:copy.value.tabs[0]},{key:'news',label:copy.value.tabs[1]},{key:'clinic',label:copy.value.tabs[2]}])
let active=false,owner='',pageGeneration=0,composerGeneration=0,postRead=0,clinicRead=0,writeGeneration=0,suppressDraft=false,lastPostMore=false,lastClinicMore=false,postFilter='',clinicFilter=''
const memoryDrafts=new Map()
function emptyDraft(){return {title:'',content:'',images:[],videoUrl:'',tags:['我的发布']}}
function context(){return {owner,token:getAuthToken(),page:pageGeneration,composer:composerGeneration}}
function sameOwner(c){return c.owner===owner&&owner===String(getUser()?.id||'')&&c.token===getAuthToken()}
function current(c){return active&&c.page===pageGeneration&&sameOwner(c)}
function composerCurrent(c){return active&&sameOwner(c)&&c.composer===composerGeneration&&composerVisible.value}
function setDraft(value){suppressDraft=true;draft.value=value;suppressDraft=false}
function persistDraft(){
    if(suppressDraft||!active||owner!==String(getUser()?.id||'')||!composerVisible.value||editingPost.value)return
    const data=JSON.parse(JSON.stringify(draft.value)),known=memoryDrafts.get(owner)
    try{const saved=persistPostDraft(owner,data,known);memoryDrafts.set(owner,saved);setDraft(saved);draftError.value=''}
    catch{if(known?.requestSnapshot!==postRequestSnapshot(data)){delete data.requestKey;delete data.requestSnapshot}memoryDrafts.set(owner,data);setDraft(data);draftError.value='草稿未能保存在本机，请检查存储空间；退出应用后可能无法找回'}
}
watch(draft,persistDraft,{deep:true,flush:'sync'})
onLoad(q=>{onlyMine.value=q.mine==='1'})
onShow(()=>{
    const next=String(getUser()?.id||'')
    if(next!==owner){
        owner=next;posts.value=[];likedPosts.value={};likeBusy.value={};clinicPosts.value=[];totalPosts.value=0;clinicTotal.value=0;postsHasMore.value=false;clinicHasMore.value=false;postCursor.value='';clinicCursor.value=''
        composerGeneration++;composerVisible.value=false;editingPost.value=null;libraryVisible.value=false;setDraft(emptyDraft());draftError.value='';publishError.value=''
        onlyFollowing.value=false;searchText.value='';clinicSaved.value=false;uni.showTabBar({animation:true})
    }
    active=true;pageGeneration++;writeGeneration++;submitting.value=false;likeBusy.value={}
    language.value=getAppLanguage();applyAppLanguage(language.value);setPageTitle('feed',language.value)
    if(uni.getStorageSync(accountKey('feed-filter'))==='mine'){onlyMine.value=true;activeTab.value='feed';uni.removeStorageSync(accountKey('feed-filter'))}
    if(composerVisible.value)uni.hideTabBar({animation:true})
    loadPosts();if(activeTab.value==='clinic')loadClinic()
})
function leave(){active=false;pageGeneration++;postRead++;clinicRead++;writeGeneration++;loadingPosts.value=false;clinicLoading.value=false;submitting.value=false;uni.createVideoContext('draft-video').pause()}
onHide(leave);onUnload(leave)
watch(activeTab,value=>{if(!active)return;if(value==='clinic')loadClinic();else if(value==='feed')loadPosts()})
function filters(){return JSON.stringify([onlyMine.value,!onlyMine.value&&onlyFollowing.value,searchText.value.trim()])}
function retryPosts(){return loadPosts(lastPostMore)}
async function loadPosts(more=false){
    if(!active||owner!==String(getUser()?.id||''))return
    const filter=filters()
    if(more&&(loadingPosts.value||filter!==postFilter||!postsHasMore.value||!postCursor.value))return
    const c=context(),generation=++postRead,next=more?postCursor.value:''
    if(!more&&filter!==postFilter){posts.value=[];likedPosts.value={};totalPosts.value=0;postCursor.value='';postsHasMore.value=false}
    postFilter=filter;loadingPosts.value=true;postsError.value='';lastPostMore=more
    const [mine,following,keyword]=JSON.parse(filter)
    try{
        const data=await fetchPosts(next,mine,following,keyword)
        if(!current(c)||generation!==postRead||filter!==filters())return
        const ids=new Set(posts.value.map(p=>p.id));posts.value=more?[...posts.value,...data.items.filter(p=>!ids.has(p.id))]:data.items
        totalPosts.value=data.total;postCursor.value=data.nextCursor;postsHasMore.value=data.hasMore;usingBackupPosts.value=false
        likedPosts.value=Object.fromEntries(posts.value.filter(p=>p.likedByMe).map(p=>[p.id,true]))
    }catch(e){if(current(c)&&generation===postRead){postsError.value=e.message||'动态读取失败，请重试';if(e.status===400){lastPostMore=false;postsHasMore.value=false;postCursor.value=''}}}
    finally{if(current(c)&&generation===postRead)loadingPosts.value=false}
}
function retryClinic(){return loadClinic(lastClinicMore)}
async function loadClinic(more=false){
    if(!active||owner!==String(getUser()?.id||''))return
    const filter=String(clinicSaved.value)
    if(more&&(clinicLoading.value||filter!==clinicFilter||!clinicHasMore.value||!clinicCursor.value))return
    const c=context(),generation=++clinicRead,next=more?clinicCursor.value:''
    if(!more&&filter!==clinicFilter){clinicPosts.value=[];clinicTotal.value=0;clinicCursor.value='';clinicHasMore.value=false}
    clinicFilter=filter;clinicLoading.value=true;clinicError.value='';lastClinicMore=more
    try{
        const data=await request(`/clinic?saved=${filter}${next?'&cursor='+encodeURIComponent(next):''}`)
        if(!current(c)||generation!==clinicRead||filter!==String(clinicSaved.value))return
        const ids=new Set(clinicPosts.value.map(p=>p.id));clinicPosts.value=more?[...clinicPosts.value,...data.items.filter(p=>!ids.has(p.id))]:data.items
        clinicTotal.value=data.total;clinicCursor.value=data.next_cursor||'';clinicHasMore.value=Boolean(data.has_more)
    }catch(e){if(current(c)&&generation===clinicRead){clinicError.value=e.message||'问题读取失败，请重试';if(e.status===400){lastClinicMore=false;clinicHasMore.value=false;clinicCursor.value=''}}}
    finally{if(current(c)&&generation===clinicRead)clinicLoading.value=false}
}
function openComposer(post){
    if(!active||submitting.value||owner!==String(getUser()?.id||''))return
    if(post&&!canEditPost(post)){uni.showToast({title:copy.value.tooLate,icon:'none'});return}
    composerGeneration++;editingPost.value=post||null;draftError.value='';publishError.value=''
    if(post)setDraft({title:post.title,content:post.content,images:[...post.images],videoUrl:post.videoUrl||'',tags:[...post.tags]})
    else try{const saved=memoryDrafts.get(owner)||restorePostDraft(owner);memoryDrafts.set(owner,saved);setDraft(saved)}catch{setDraft(emptyDraft());draftError.value='本机草稿无法读取，请检查存储空间后重试'}
    libraryVisible.value=!post;composerVisible.value=true;uni.hideTabBar({animation:true})
}
function closeComposer(){
    if(!active||submitting.value)return
    persistDraft();composerGeneration++;composerVisible.value=false;libraryVisible.value=false;editingPost.value=null;uni.createVideoContext('draft-video').pause();uni.showTabBar({animation:true})
}
function chooseFromAlbum(){
    if(!active||!composerVisible.value||submitting.value)return
    const c=context()
    uni.chooseImage({count:Math.max(1,6-draft.value.images.length),sizeType:['compressed'],sourceType:['album'],success:async result=>{
        if(!composerCurrent(c)||submitting.value)return
        const ticket=++writeGeneration;submitting.value=true
        try{
            const images=await Promise.all(result.tempFilePaths.map(value=>{if(!composerCurrent(c))throw Error('页面已变化');return uploadImage(value)}))
            if(composerCurrent(c)&&ticket===writeGeneration)draft.value.images=[...draft.value.images,...images].slice(0,6)
        }catch(e){if(composerCurrent(c))publishError.value=e.message||'图片未能保存，请重新选择'}
        finally{if(composerCurrent(c)&&ticket===writeGeneration)submitting.value=false}
    },fail(){if(composerCurrent(c))uni.showToast({title:copy.value.albumFallback,icon:'none'})}})
}
function chooseVideo(){
    if(!active||!composerVisible.value||submitting.value)return
    const c=context()
    uni.chooseVideo({sourceType:['album'],maxDuration:120,success:async result=>{
        if(!composerCurrent(c)||submitting.value)return
        if(result.size>32*1024*1024){publishError.value='请选择不超过32MB的视频';return}
        const ticket=++writeGeneration;submitting.value=true
        try{const url=await uploadVideo(result.tempFilePath);if(composerCurrent(c)&&ticket===writeGeneration)draft.value.videoUrl=url}
        catch(e){if(composerCurrent(c))publishError.value=e.message||'视频未能保存，请重新选择'}
        finally{if(composerCurrent(c)&&ticket===writeGeneration)submitting.value=false}
    }})
}
function toggleLibraryImage(url){if(!active||submitting.value)return;if(draft.value.images.includes(url))removeImage(url);else draft.value.images=[...draft.value.images,url].slice(0,6)}
function removeImage(url){if(active&&!submitting.value)draft.value.images=draft.value.images.filter(image=>image!==url)}
async function submitPost(){
    if(!active||submitting.value||!composerVisible.value||owner!==String(getUser()?.id||''))return
    if((draft.value.title+'\n'+draft.value.content).length>2000){publishError.value='标题和正文合计不能超过2000字';return}
    if(!draft.value.title.trim()||!draft.value.content.trim()){publishError.value=copy.value.fillRequired;return}
    const c=context(),post=editingPost.value,ticket=++writeGeneration,payload=JSON.parse(JSON.stringify(draft.value))
    let sentKey='';submitting.value=true;publishError.value=''
    try{
        if(post)await savePost(post.id,payload,{isCurrent:()=>current(c)&&composerCurrent(c)})
        else await publishPost(payload,{isCurrent:()=>current(c)&&composerCurrent(c),savePrepared:prepared=>{
            if(!current(c)||!composerCurrent(c))throw Error('页面已变化，请重新打开动态')
            const saved=preparePostSend(c.owner,prepared,memoryDrafts.get(c.owner));sentKey=saved.requestKey
            memoryDrafts.set(c.owner,saved);setDraft(saved);draftError.value='';return saved
        }})
        let clearFailed=false
        if(!post){
            try{clearPostDraft(c.owner,sentKey)}catch{clearFailed=true}
            if(memoryDrafts.get(c.owner)?.requestKey===sentKey)memoryDrafts.set(c.owner,emptyDraft())
        }
        if(!active||!sameOwner(c))return
        if(!post&&draft.value.requestKey===sentKey){setDraft(emptyDraft());if(clearFailed)draftError.value='动态已发布，但本机草稿未能清理；重开后可继续确认原结果'}
        if(current(c)&&composerCurrent(c)&&ticket===writeGeneration){
            submitting.value=false;composerVisible.value=false;libraryVisible.value=false;editingPost.value=null;composerGeneration++;uni.showTabBar({animation:true})
            uni.showToast({title:post?copy.value.saved:copy.value.published,icon:'none'})
        }
        if(!submitting.value)await loadPosts()
    }catch(e){if(current(c)&&composerCurrent(c)&&ticket===writeGeneration)publishError.value=e.message||'发布尚未确认，请重试'}
    finally{if(current(c)&&c.composer===composerGeneration&&ticket===writeGeneration)submitting.value=false}
}
async function toggleLike(post){
    if(!active||loadingPosts.value||likeBusy.value[post.id]||owner!==String(getUser()?.id||''))return
    const c=context(),filter=postFilter;postRead++;likeBusy.value={...likeBusy.value,[post.id]:true}
    try{
        const result=await setPostLike(post.id,!likedPosts.value[post.id])
        if(!current(c)||postFilter!==filter)return
        const interrupted=loadingPosts.value;postRead++;loadingPosts.value=false
        likedPosts.value={...likedPosts.value,[post.id]:result.liked};posts.value=posts.value.map(item=>item.id===post.id?{...item,likes:result.likes,likedByMe:result.liked}:item)
        if(interrupted)await loadPosts()
    }catch(e){if(current(c))uni.showToast({title:e.message||'点赞尚未确认，请重试',icon:'none'})}
    finally{if(current(c))likeBusy.value={...likeBusy.value,[post.id]:false}}
}
function goClinic(id){if(active)uni.navigateTo({url:'/pages/video-feed/clinic-detail'+(id?'?id='+id:'?new=1')})}
function openVideo(post){if(active)uni.navigateTo({url:`/pages/video-feed/player?id=${post.id}`})}
function openPostDetail(post){if(active)uni.navigateTo({url:`/pages/community/post-detail?id=${encodeURIComponent(post.id)}`})}
function openNews(item){if(active)uni.navigateTo({url:`/pages/community/post-detail?type=news&id=${encodeURIComponent(item.id)}`})}
function previewImage(current,urls){if(active)uni.previewImage({current,urls})}
</script>

<style lang="scss" scoped>
.page { min-height: 100vh; background: #121212; color: #FFFFFF; padding-bottom: calc(24rpx + env(safe-area-inset-bottom)); }
.nav-bar { height: 96rpx; padding: 0 24rpx; display: flex; align-items: center; justify-content: space-between; background: #121212; }
.segment { display: flex; align-items: center; gap: 18rpx; }
.segment-item { position: relative; height: 88rpx; min-width: 112rpx; display: flex; align-items: center; justify-content: center; color: #8E8E93; font-size: 30rpx; }
.segment-item.active { color: #FFFFFF; font-weight: 900; }
.segment-line { position: absolute; left: 24rpx; right: 24rpx; bottom: 8rpx; height: 4rpx; border-radius: 999rpx; }
.segment-item.active .segment-line { background: #CCFF00; }
.publish-btn, .submit-btn { height: 64rpx; padding: 0 28rpx; border-radius: 999rpx; background: #CCFF00; color: #121212; font-size: 26rpx; font-weight: 900; }
.content { height: calc(100vh - 96rpx - var(--top-safe-height) - env(safe-area-inset-bottom)); }
.post-list, .news-list, .clinic-list { padding: 22rpx 24rpx 150rpx; }
.post-card, .news-card, .clinic-card, .source-note { margin-bottom: 22rpx; padding: 24rpx; border-radius: 16rpx; background: #1E1E1E; border: 1rpx solid #2C2C2E; }
.post-head, .clinic-head { display: flex; align-items: center; margin-bottom: 18rpx; }
.avatar { width: 72rpx; height: 72rpx; border-radius: 50%; background: #2C2C2E; }
.author-main { flex: 1; min-width: 0; margin-left: 16rpx; display: flex; flex-direction: column; }
.author { font-size: 28rpx; font-weight: 900; }
.time, .source-note { margin-top: 6rpx; color: #8E8E93; font-size: 22rpx; line-height: 1.5; }
.edit-btn { height: 52rpx; padding: 0 18rpx; border-radius: 999rpx; background: rgba(204,255,0,.12); color: #CCFF00; font-size: 22rpx; }
.post-title { display: block; margin-bottom: 10rpx; font-size: 32rpx; font-weight: 900; line-height: 1.35; }
.post-content, .news-summary, .answer { display: block; color: #D8D8D8; font-size: 26rpx; line-height: 1.6; }
.image-strip { margin-top: 18rpx; width: 100%; white-space: nowrap; }
.post-image { display: inline-block; width: 260rpx; height: 190rpx; margin-right: 14rpx; border-radius: 12rpx; background: #2C2C2E; }
.post-foot { margin-top: 18rpx; display: flex; align-items: center; justify-content: space-between; gap: 16rpx; }
.tag-row { flex: 1; display: flex; flex-wrap: wrap; gap: 10rpx; }
.tag { color: #CCFF00; font-size: 22rpx; }
.action-row { display: flex; align-items: center; gap: 10rpx; }
.like-action, .comment-action { min-width: 92rpx; height: 48rpx; padding: 0 14rpx; border-radius: 999rpx; background: #242424; color: #8E8E93; display: flex; align-items: center; justify-content: center; gap: 6rpx; font-size: 24rpx; }
.like-action.active { background: rgba(255,87,34,.16); color: #FF5722; }
.comment-action { color: #D8D8D8; }
.heart { color: #FF5722; font-size: 26rpx; }
.news-card { padding: 0; overflow: hidden; }
.news-image { width: 100%; height: 260rpx; background: #2C2C2E; }
.news-body { padding: 22rpx; }
.news-tag { color: #CCFF00; font-size: 22rpx; font-weight: 800; }
.news-title { display: block; margin: 10rpx 0; font-size: 32rpx; font-weight: 900; }
.clinic-thumb { width: 100%; height: 300rpx; margin: 18rpx 0; border-radius: 12rpx; background: #2C2C2E; }
.mask { position: fixed; inset: 0; z-index: 9999; display: flex; align-items: flex-end; background: rgba(0,0,0,.58); }
.composer { width: 100%; max-height: calc(100vh - var(--top-safe-height) - 40rpx); padding: 24rpx 24rpx calc(40rpx + env(safe-area-inset-bottom)); border-radius: 26rpx 26rpx 0 0; background: #181818; overflow-y: auto; box-sizing: border-box; }
.composer-head, .picker-row { display: flex; align-items: center; justify-content: space-between; gap: 18rpx; }
.composer-title { font-size: 34rpx; font-weight: 900; }
.close-btn { width: 64rpx; height: 64rpx; border-radius: 50%; color: #FFFFFF; background: #2C2C2E; font-size: 40rpx; }
.title-input, .content-input { width: 100%; margin-top: 18rpx; border-radius: 14rpx; background: #222; color: #FFFFFF; font-size: 28rpx; box-sizing: border-box; }
.title-input { height: 78rpx; padding: 0 20rpx; line-height: 78rpx; }
.content-input { height: 210rpx; padding: 20rpx; line-height: 1.5; }
:deep(.title-input .uni-input-wrapper),
:deep(.title-input .uni-input-input),
:deep(.title-input .uni-input-placeholder) { height: 78rpx; min-height: 78rpx; line-height: 78rpx; color: #FFFFFF; }
.placeholder { color: #777; }
.picker-row { margin-top: 18rpx; }
.picker-btn { flex: 1; height: 70rpx; border-radius: 12rpx; background: #2C2C2E; color: #FFFFFF; font-size: 26rpx; }
.library-grid { margin-top: 18rpx; display: grid; grid-template-columns: repeat(3, 1fr); gap: 12rpx; }
.library-image { width: 100%; height: 130rpx; border-radius: 10rpx; border: 3rpx solid transparent; background: #2C2C2E; box-sizing: border-box; }
.library-image.picked { border-color: #CCFF00; }
.draft-strip { margin-bottom: 18rpx; }
.draft-image-wrap { position: relative; display: inline-block; }
.remove-image { position: absolute; top: 8rpx; right: 20rpx; width: 40rpx; height: 40rpx; border-radius: 50%; background: rgba(0,0,0,.68); color: #FFFFFF; text-align: center; line-height: 40rpx; }
.edit-window { display: block; margin: 8rpx 0 18rpx; color: #8E8E93; font-size: 22rpx; }
.submit-btn { width: 100%; margin-top: 8rpx; }
</style>
