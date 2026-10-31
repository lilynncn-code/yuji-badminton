<template>
<view class="page"><button @click="back">{{ $tr("返回球圈") }}</button><text v-if="loading" class="note">{{ $tr("正在读取视频…") }}</text><text v-if="error" class="note">{{ $tr(error) }}</text><button v-if="error" :disabled="loading||busy" @click="load">{{ $tr("重新加载") }}</button><view v-if="post"><video v-if="post.videoUrl" id="post-video" :src="post.videoUrl" controls @error="videoError=true"/><text v-else class="note">{{ $tr("这条动态没有附带视频。") }}</text><text v-if="videoError" class="note">{{ $tr("视频无法播放，请检查网络或视频格式。") }}</text><text class="title">{{ post.titleIsDefault ? $tr(post.title) : post.title }}</text><text class="note" @click="author">{{ post.authorNameIsDefault ? $tr(post.authorName) : post.authorName }}{{ $tr("· 查看资料") }}</text><text class="body">{{post.content}}</text><view class="row"><button :disabled="busy||loading" @click="like">{{ $tr("{0} {1}", [post.likedByMe?'♥ 已点赞':'♡ 点赞', post.likes]) }}</button><button @click="comments">{{ $tr("评论 {0}", [post.commentsCount]) }}</button><button @click="share">{{ $tr("复制分享文字") }}</button></view></view></view>
</template>
<script setup>
import { translate } from '../../utils/translate'
import {ref} from 'vue'
import {onLoad,onShow,onHide,onUnload} from '@dcloudio/uni-app'
import {fetchPost,setPostLike} from '../../utils/posts-api'
import {getAuthToken} from '../../utils/auth'
import {getUser} from '../../utils/store'
const post=ref(null),id=ref(''),error=ref(''),videoError=ref(false),busy=ref(false),loading=ref(false)
let active=false,owner='',pageGeneration=0,readGeneration=0,writeGeneration=0
function context(){return {owner,token:getAuthToken(),page:pageGeneration}}
function current(c){return active&&c.owner===owner&&owner===String(getUser()?.id||'')&&c.token===getAuthToken()&&c.page===pageGeneration}
onLoad(q=>{id.value=/^[1-9][0-9]*$/.test(String(q.id||''))?String(q.id):''})
onShow(()=>{const next=String(getUser()?.id||'');if(next!==owner){owner=next;post.value=null}active=true;pageGeneration++;busy.value=false;load()})
function leave(){active=false;pageGeneration++;readGeneration++;writeGeneration++;busy.value=false;loading.value=false;uni.createVideoContext('post-video').pause()}
onHide(leave);onUnload(leave)
async function load(){
    if(!active||busy.value)return
    const c=context(),generation=++readGeneration;loading.value=true;error.value='';videoError.value=false
    try{if(!id.value)throw new Error('请从球圈选择一条视频');const result=await fetchPost(id.value);if(current(c)&&generation===readGeneration)post.value=result}
    catch(e){if(current(c)&&generation===readGeneration){post.value=null;error.value=e.message||'视频读取失败，请重试'}}
    finally{if(current(c)&&generation===readGeneration)loading.value=false}
}
async function like(){
    if(!active||busy.value||loading.value||!post.value)return
    const c=context(),ticket=++writeGeneration;readGeneration++;busy.value=true
    try{const data=await setPostLike(id.value,!post.value.likedByMe);if(current(c)&&ticket===writeGeneration)post.value={...post.value,likedByMe:data.liked,likes:data.likes}}
    catch(e){if(current(c))uni.showToast({title:e.message,icon:'none'})}
    finally{if(current(c)&&ticket===writeGeneration)busy.value=false}
}
function comments(){if(active&&post.value)uni.navigateTo({url:`/pages/community/post-detail?id=${id.value}`})}
function author(){if(active&&post.value)uni.navigateTo({url:`/pages/match-making/group-detail?id=${post.value.authorId}`})}
function share(){if(!active||!post.value)return;let text=`${post.value.authorName}：${post.value.title}\n${translate('在好羽查看动态，编号 {0}', [id.value])}`;if(typeof window!=='undefined')text+='\n'+window.location.origin+window.location.pathname+'#/pages/community/post-detail?id='+id.value;uni.setClipboardData({data:text})}
function back(){if(active)uni.switchTab({url:'/pages/video-feed/video-feed'})}
</script>
<style scoped>.page{min-height:100vh;padding:28rpx;background:#121212;color:white;box-sizing:border-box}video{width:100%;height:60vh;background:#050505}.title{display:block;font-size:38rpx;line-height:1.4;font-weight:bold;margin-top:24rpx}.note{display:block;color:#aaa;font-size:25rpx;line-height:1.7;margin:16rpx 0}.body{display:block;font-size:28rpx;white-space:pre-wrap;line-height:1.7}.row{display:flex;gap:10rpx;margin-top:24rpx}.row button{flex:1;font-size:24rpx;padding:12rpx}button{background:#292929;color:#ccff00;font-size:26rpx;margin:20rpx 0}</style>
