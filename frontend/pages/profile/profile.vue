<template>
	<view class="page" :style="{ paddingTop: statusBarHeight + 'px', '--top-safe-height': statusBarHeight + 'px' }">
		<view class="nav-bar">
			<text class="nav-title">{{ $tr(copy.title) }}</text>
			<button class="setting icon-setting" @click="goSettings" :aria-label='$tr("设置")'>{{ $tr("⚙️") }}</button>
		</view>

		<scroll-view class="content" scroll-y>
            <view v-if="profileLoading || profileError" class="state-note"><text>{{ $tr(profileLoading?'正在读取本人资料…':profileError) }}</text><button v-if="profileError" :disabled="profileLoading||saving" @click="loadProfile">{{ $tr("重新读取资料") }}</button></view>
			<view class="profile-card">
				<image class="cover" :src="userInfo.cover || imageLibrary[0].url" mode="aspectFill" />
				<button class="cover-edit" :disabled="saving||profileLoading||!profileReady" @click="openEditor">{{ $tr(copy.editCover) }}</button>
				<view class="identity-row">
					<image class="avatar" :src="userInfo.avatar" mode="aspectFill" />
					<view class="identity-main">
						<text class="name">{{ userInfo.name }}</text>
						<text class="bio">{{ userInfo.bio }}</text>
						<view class="chips">
							<text class="chip">{{ userInfo.city === '未设置城市' ? $tr('未设置城市') : userInfo.city }}</text>
							<text class="chip">{{ userInfo.levelTag === '羽毛球爱好者' ? $tr('羽毛球爱好者') : userInfo.levelTag }}</text>
							<text class="chip">{{ $tr(userInfo.hand) }}</text>
						</view>
					</view>
				</view>
				<view class="asset-row">
					<view class="asset" @click="goMenu({url: '/pages/profile/people?kind=following'})">
						<text class="asset-value">{{ $tr(userInfo.following) }}</text>
						<text class="asset-label">{{ $tr(copy.following) }}</text>
					</view>
					<view class="asset" @click="goMenu({url: '/pages/profile/people?kind=followers'})">
						<text class="asset-value">{{ $tr(userInfo.followers) }}</text>
						<text class="asset-label">{{ $tr(copy.followers) }}</text>
					</view>
				</view>
				<button class="primary-btn" :disabled="saving||profileLoading||!profileReady" @click="openEditor">{{ $tr(copy.editProfile) }}</button>
			</view>

			<view class="radar-card">
				<view class="section-head">
					<text class="section-title">{{ $tr(copy.trainingProfile) }}</text>
					<text class="section-sub">{{ $tr(trainingProfileUpdatedText) }}</text>
				</view>
				<text v-if="trainingSummary" class="bio">{{ $tr("累计 {0} 次训练 · {1} 分钟；连续 {2} 天。动作能力需要实际评估，暂不显示虚构能力分。", [trainingSummary.sessions, trainingSummary.total_minutes, trainingSummary.streak]) }}</text>
                <view v-else class="state-note"><text>{{ $tr(trainingLoading?'正在读取训练统计…':trainingError||'训练统计尚未读取') }}</text><button :disabled="trainingLoading" @click="loadTraining">{{ $tr("重新读取训练统计") }}</button></view>
                <button class="primary-btn" @click="goMenu({url: '/pages/ai-coach/history'})">{{ $tr("我的训练记录") }}</button>
                <button class="primary-btn" @click="goMenu({url: '/pages/video-feed/video-feed?mine=1'})">{{ $tr("我的动态") }}</button>
			</view>

			<view class="menu-group">
				<view v-for="item in menus" :key="item.titleKey" class="menu-cell" @click="goMenu(item)" :hover-class="'click-feedback'">
					<view class="menu-left">
						<text class="menu-icon">{{ $tr(item.icon) }}</text>
						<view>
							<text class="menu-title">{{ $tr(copy[item.titleKey]) }}</text>
							<text class="menu-desc">{{ $tr(copy[item.descKey]) }}</text>
						</view>
					</view>
					<text class="arrow">{{ $tr("›") }}</text>
				</view>
			</view>
		</scroll-view>

		<view v-if="editorVisible" class="mask" @click="closeEditor">
			<view class="editor" @click.stop>
				<view class="editor-head">
					<text class="editor-title">{{ $tr(copy.editProfile) }}</text>
					<text class="close-btn" @click="closeEditor">{{ $tr("×") }}</text>
				</view>
                <text v-if="saveError" class="state-note">{{ $tr(saveError) }}</text>
				<view class="avatar-picker">
					<image class="edit-avatar" :src="absoluteUrl(draft.avatar)" mode="aspectFill" />
					<view class="avatar-actions">
						<button class="small-btn" :disabled="saving" @click="chooseAvatarFromAlbum">{{ $tr(copy.albumAvatar) }}</button>
						<button class="small-btn" :disabled="saving" @click="avatarLibraryVisible = !avatarLibraryVisible">{{ $tr(copy.libraryAvatar) }}</button>
					</view>
				</view>
				<view class="cover-picker">
					<image class="edit-cover" :src="absoluteUrl(draft.cover || imageLibrary[0].url)" mode="aspectFill" />
					<view class="avatar-actions">
						<button class="small-btn" :disabled="saving" @click="chooseCoverFromAlbum">{{ $tr(copy.albumCover) }}</button>
						<button class="small-btn" :disabled="saving" @click="coverLibraryVisible = !coverLibraryVisible">{{ $tr(copy.libraryCover) }}</button>
					</view>
				</view>
				<view v-if="avatarLibraryVisible" class="library-grid">
					<image v-for="image in imageLibrary" :key="image.id" class="library-image" :class="{ picked: draft.avatar === image.url }" :src="image.url" mode="aspectFill" @click="!saving && (draft.avatar = image.url)" />
				</view>
				<view v-if="coverLibraryVisible" class="library-grid">
					<image v-for="image in imageLibrary" :key="'cover-' + image.id" class="library-image" :class="{ picked: draft.cover === image.url }" :src="image.url" mode="aspectFill" @click="!saving && (draft.cover = image.url)" />
				</view>
				<input class="input" :disabled="saving" maxlength="50" v-model="draft.name" :placeholder="$tr(copy.namePlaceholder)" placeholder-class="placeholder" />
				<input class="input" :disabled="saving" maxlength="80" v-model="draft.city" :placeholder="$tr(copy.cityPlaceholder)" placeholder-class="placeholder" />
				<input class="input" :disabled="saving" maxlength="80" v-model="draft.levelTag" :placeholder="$tr(copy.levelPlaceholder)" placeholder-class="placeholder" />
				<input class="input" :disabled="saving" maxlength="80" v-model="draft.club" :placeholder="$tr(copy.clubPlaceholder)" placeholder-class="placeholder" />
				<picker :disabled="saving" :range="[$tr('右手持拍'), $tr('左手持拍')]" @change="!saving && (draft.hand = ['右手持拍', '左手持拍'][$event.detail.value])"><view class="input">{{ $tr("持拍手：{0}", [draft.hand]) }}</view></picker>
                <textarea :disabled="saving" maxlength="500" class="textarea" v-model="draft.bio" :placeholder="$tr(copy.bioPlaceholder)" placeholder-class="placeholder" />
				<button class="save-btn" :disabled="saving" @click="saveProfile">{{ $tr(saving?'正在保存…':copy.saveProfile) }}</button>
			</view>
		</view>
	</view>
</template>

<script setup>
import { computed,ref } from 'vue'
import { onShow,onHide,onUnload } from '@dcloudio/uni-app'
import { imageLibrary } from '../../data/app-data'
import { getUser } from '../../utils/store'
import { getAuthToken } from '../../utils/auth'
import { applyAppLanguage,getAppLanguage,getCopy,setPageTitle } from '../../utils/i18n'
import { fetchMyProfile,saveMyProfile } from '../../utils/profile-api'
import { accountKey,absoluteUrl } from '../../utils/request'
import { fetchTrainingSummary } from '../../utils/training-api'
import { getTopSafeAreaHeight } from '../../utils/safe-area'
const statusBarHeight=getTopSafeAreaHeight(),userInfo=ref({...getUser()}),editorVisible=ref(false),avatarLibraryVisible=ref(false),coverLibraryVisible=ref(false),saving=ref(false),draft=ref({...userInfo.value})
const language=ref(getAppLanguage()),copy=computed(()=>getCopy('profile',language.value))
const trainingSummary=ref(null),trainingLoading=ref(false),trainingError=ref(''),profileLoading=ref(false),profileReady=ref(false),profileError=ref(''),saveError=ref('')
const trainingProfileUpdatedText=computed(()=>{const date=trainingSummary.value?.last_date;if(!date)return trainingSummary.value?'暂无训练记录':'暂未读取';return language.value==='en'?`Updated ${date}`:`更新至 ${date}`})
const menus=[{titleKey:'chatRequests',descKey:'chatRequestsDesc',icon:'◌',url:'/pages/chat/inbox'}]
let active=false,owner='',pageGeneration=0,profileRead=0,trainingRead=0,editorGeneration=0,pendingSave=null
function context(){return {owner,token:getAuthToken(),page:pageGeneration,editor:editorGeneration}}
function sameOwner(c){return c.owner===owner&&owner===String(getUser()?.id||'')&&c.token===getAuthToken()}
function current(c){return active&&c.page===pageGeneration&&sameOwner(c)}
function editorCurrent(c){return active&&sameOwner(c)&&c.editor===editorGeneration&&editorVisible.value}
onShow(()=>{
    const next=String(getUser()?.id||'')
    if(next!==owner){owner=next;editorGeneration++;editorVisible.value=false;avatarLibraryVisible.value=false;coverLibraryVisible.value=false;userInfo.value={...getUser()};draft.value={...userInfo.value};trainingSummary.value=null;profileReady.value=false;profileError.value='';saveError.value='';trainingError.value='';uni.showTabBar()}
    active=true;pageGeneration++;saving.value=Boolean(pendingSave&&sameOwner(pendingSave))
    language.value=getAppLanguage();applyAppLanguage(language.value);setPageTitle('profile',language.value)
    if(editorVisible.value)uni.hideTabBar()
    if(!saving.value)loadProfile();loadTraining()
})
function leave(){active=false;pageGeneration++;profileRead++;trainingRead++;profileLoading.value=false;trainingLoading.value=false}
onHide(leave);onUnload(()=>{leave();editorGeneration++})
async function loadProfile(){
    if(!active||saving.value)return
    const c=context(),generation=++profileRead;profileLoading.value=true;profileError.value=''
    try{
        const profile=await fetchMyProfile({isCurrent:()=>current(c)&&generation===profileRead})
        if(!current(c)||generation!==profileRead)return
        userInfo.value={...profile};profileReady.value=true;if(!editorVisible.value)draft.value={...profile}
        if(profile.localCacheError)profileError.value='资料已读取，但本机同步失败，请检查存储空间'
    }catch(e){if(current(c)&&generation===profileRead){profileReady.value=false;profileError.value=e.message||'资料读取失败，请重试'}}
    finally{if(current(c)&&generation===profileRead)profileLoading.value=false}
}
async function loadTraining(){
    if(!active)return
    const c=context(),generation=++trainingRead;trainingLoading.value=true;trainingError.value=''
    try{const summary=await fetchTrainingSummary();if(current(c)&&generation===trainingRead)trainingSummary.value=summary}
    catch(e){if(current(c)&&generation===trainingRead){trainingSummary.value=null;trainingError.value=e.message||'训练统计读取失败，请重试'}}
    finally{if(current(c)&&generation===trainingRead)trainingLoading.value=false}
}
function openEditor(){
    if(!active||saving.value||profileLoading.value||!profileReady.value||owner!==String(getUser()?.id||''))return
    if(editorVisible.value)return
    editorGeneration++;draft.value={...userInfo.value};saveError.value='';editorVisible.value=true;uni.hideTabBar()
}
function closeEditor(){
    if(!active||saving.value)return
    editorGeneration++;editorVisible.value=false;avatarLibraryVisible.value=false;coverLibraryVisible.value=false;draft.value={...userInfo.value};uni.showTabBar()
}
function choosePicture(field){
    if(!active||saving.value||!editorVisible.value)return
    const c=context()
    uni.chooseImage({count:1,sourceType:['album'],success(result){if(editorCurrent(c)&&!saving.value&&result.tempFilePaths?.[0])draft.value[field]=result.tempFilePaths[0]},fail(){if(editorCurrent(c))uni.showToast({title:field==='avatar'?copy.value.avatarFallback:copy.value.coverFallback,icon:'none'})}})
}
function chooseAvatarFromAlbum(){choosePicture('avatar')}
function chooseCoverFromAlbum(){choosePicture('cover')}
async function saveProfile(){
    if(!active||saving.value||!editorVisible.value||owner!==String(getUser()?.id||''))return
    const next={nickname:String(draft.value.name||'').trim(),city:String(draft.value.city||'').trim(),levelTag:String(draft.value.levelTag||'').trim(),bio:String(draft.value.bio||'').trim(),avatar:draft.value.avatar||userInfo.value.avatar,cover:draft.value.cover||userInfo.value.cover||imageLibrary[0].url,club:String(draft.value.club||'').trim(),hand:draft.value.hand||'右手持拍'}
    if(!next.nickname){saveError.value=copy.value.nameRequired;return}
    if(next.nickname.length>50||next.city.length>80||next.levelTag.length>80||next.club.length>80||next.bio.length>500){saveError.value='昵称最多50字，城市、等级和俱乐部最多80字，简介最多500字';return}
    const c=context();pendingSave=c;saving.value=true;saveError.value='';profileRead++;profileLoading.value=false
    try{
        const profile=await saveMyProfile(next,{isCurrent:()=>current(c)&&editorCurrent(c),onImageReady:(field,url)=>{if(editorCurrent(c))draft.value[field]=absoluteUrl(url)}})
        if(!active||!sameOwner(c))return
        userInfo.value={...profile};profileReady.value=true
        if(c.editor===editorGeneration){draft.value={...profile};saving.value=false;closeEditor()}
        profileError.value=profile.localCacheError?'资料已保存，但本机同步失败，请检查存储空间后刷新':''
        if(current(c))uni.showToast({title:profile.localCacheError?'资料已保存，本机同步待重试':'资料已保存',icon:'none'})
    }catch(e){if(active&&sameOwner(c)&&c.editor===editorGeneration)saveError.value=e.message||'资料尚未保存，请重试'}
    finally{if(pendingSave===c)pendingSave=null;if(active&&sameOwner(c))saving.value=false}
}
function goMenu(item){
    if(!active||saving.value)return
    if(item.url.startsWith('/pages/video-feed/video-feed')){uni.setStorageSync(accountKey('feed-filter'),'mine');uni.switchTab({url:'/pages/video-feed/video-feed'});return}
    uni.navigateTo({url:item.url})
}
function goSettings(){if(active&&!saving.value)uni.navigateTo({url:'/pages/settings/settings'})}
</script>

<style lang="scss" scoped>
.state-note{display:block;padding:20rpx;color:#ccc;background:#242424;border-radius:12rpx;font-size:24rpx;line-height:1.6;margin:16rpx 0}.state-note button{margin-top:12rpx;background:#333;color:#ccff00;font-size:24rpx}
.page { min-height: 100vh; background: #121212; color: #FFFFFF; padding-bottom: calc(24rpx + env(safe-area-inset-bottom)); }
.nav-bar { height: 88rpx; padding: 0 24rpx; display: flex; align-items: center; justify-content: space-between; box-sizing: border-box; }
.nav-title { font-size: 36rpx; font-weight: 900; }
.setting { width: 58rpx; height: 58rpx; margin: 0 0 0 auto; padding: 0; border-radius: 999rpx; background: #1E1E1E; color: #FFFFFF; font-size: 28rpx; line-height: 58rpx; display: flex; align-items: center; justify-content: center; text-align: center; }
.setting::after { border: 0; }
.content { height: calc(100vh - 88rpx - var(--top-safe-height) - env(safe-area-inset-bottom)); padding: 0 24rpx; box-sizing: border-box; }
.profile-card, .radar-card, .menu-group { margin-bottom: 22rpx; border-radius: 18rpx; background: #1E1E1E; border: 1rpx solid #2C2C2E; overflow: hidden; }
.profile-card { position: relative; }
.cover { width: 100%; height: 210rpx; background: #2C2C2E; }
.cover-edit { position: absolute; right: 18rpx; top: 18rpx; z-index: 2; height: 54rpx; padding: 0 18rpx; border-radius: 999rpx; background: rgba(18,18,18,.72); color: #FFFFFF; font-size: 22rpx; }
.identity-row { padding: 0 24rpx 22rpx; display: flex; align-items: flex-start; }
.avatar { width: 132rpx; height: 132rpx; margin-top: -54rpx; border-radius: 50%; border: 6rpx solid #1E1E1E; background: #2C2C2E; flex: 0 0 auto; }
.identity-main { flex: 1; min-width: 0; margin-left: 18rpx; padding-top: 16rpx; }
.name { display: block; min-height: 54rpx; font-size: 38rpx; font-weight: 900; line-height: 1.28; white-space: normal; overflow: visible; word-break: break-word; }
.bio { display: block; margin-top: 8rpx; color: #D8D8D8; font-size: 24rpx; line-height: 1.45; }
.chips { margin-top: 12rpx; display: flex; flex-wrap: wrap; gap: 10rpx; }
.chip { padding: 8rpx 12rpx; border-radius: 999rpx; background: rgba(204,255,0,.1); color: #CCFF00; font-size: 20rpx; }
.asset-row { padding: 8rpx 24rpx 24rpx; display: grid; grid-template-columns: repeat(2, 1fr); gap: 14rpx; }
.asset { padding: 18rpx 12rpx; border-radius: 12rpx; background: #242424; text-align: center; }
.asset-value { display: block; font-size: 30rpx; font-weight: 900; }
.asset-label { display: block; margin-top: 6rpx; color: #8E8E93; font-size: 22rpx; }
.primary-btn, .save-btn { width: calc(100% - 48rpx); min-height: 74rpx; margin: 0 24rpx 24rpx; padding: 10rpx 24rpx; border-radius: 999rpx; background: #CCFF00; color: #121212; font-size: 28rpx; line-height: 1.25; font-weight: 900; }
.radar-card { padding: 24rpx; }
.section-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14rpx; }
.section-title { font-size: 30rpx; font-weight: 900; }
.section-sub, .menu-desc { color: #8E8E93; font-size: 22rpx; }
.radar-canvas { display: block; width: 100%; height: 280rpx; }
.menu-cell { min-height: 112rpx; padding: 20rpx 24rpx; display: flex; align-items: center; justify-content: space-between; border-bottom: 1rpx solid #2C2C2E; }
.menu-cell:last-child { border-bottom: 0; }
.menu-left { display: flex; align-items: center; min-width: 0; }
.menu-icon { width: 64rpx; height: 64rpx; margin-right: 18rpx; border-radius: 16rpx; background: rgba(204,255,0,.1); color: #CCFF00; display: flex; align-items: center; justify-content: center; text-align: center; line-height: 64rpx; }
.menu-title { display: block; font-size: 28rpx; font-weight: 900; }
.arrow { color: #8E8E93; font-size: 40rpx; }
.mask { position: fixed; inset: 0; z-index: 9999; display: flex; align-items: flex-end; background: rgba(0,0,0,.58); }
.editor { width: 100%; max-height: calc(100vh - var(--top-safe-height) - 40rpx); padding: 24rpx 24rpx calc(40rpx + env(safe-area-inset-bottom)); border-radius: 26rpx 26rpx 0 0; background: #181818; overflow: auto; box-sizing: border-box; }
.editor-head { display: flex; align-items: center; justify-content: space-between; }
.editor-title { font-size: 34rpx; font-weight: 900; }
.close-btn { width: 64rpx; height: 64rpx; color: #FFFFFF; background: transparent; font-size: 52rpx; display: flex; align-items: center; justify-content: center; text-align: center; }
.avatar-picker, .cover-picker { margin-top: 18rpx; display: flex; align-items: center; gap: 18rpx; }
.edit-avatar { width: 112rpx; height: 112rpx; border-radius: 50%; background: #2C2C2E; }
.edit-cover { width: 150rpx; height: 92rpx; border-radius: 14rpx; background: #2C2C2E; }
.avatar-actions { flex: 1; display: grid; grid-template-columns: repeat(2, 1fr); gap: 12rpx; }
.small-btn { min-height: 68rpx; padding: 8rpx 14rpx; border-radius: 12rpx; background: #2C2C2E; color: #FFFFFF; font-size: 24rpx; line-height: 1.25; }
.library-grid { margin-top: 18rpx; display: grid; grid-template-columns: repeat(3, 1fr); gap: 12rpx; }
.library-image { width: 100%; height: 130rpx; border-radius: 10rpx; border: 3rpx solid transparent; background: #2C2C2E; box-sizing: border-box; }
.library-image.picked { border-color: #CCFF00; }
.input, .textarea { width: 100%; margin-top: 16rpx; padding: 0 20rpx; border-radius: 14rpx; background: #222; color: #FFFFFF; font-size: 28rpx; box-sizing: border-box; }
.input { height: 78rpx; line-height: 78rpx; }
.textarea { height: 150rpx; padding-top: 18rpx; padding-bottom: 18rpx; line-height: 1.5; }
:deep(.uni-input-wrapper),
:deep(.uni-input-input) { height: 78rpx; min-height: 78rpx; line-height: 78rpx; color: #FFFFFF; }
:deep(.uni-textarea-wrapper),
:deep(.uni-textarea-textarea) { min-height: 114rpx; color: #FFFFFF; }
.placeholder { color: #777; }
.save-btn { width: 100%; margin: 20rpx 0 0; }
</style>
