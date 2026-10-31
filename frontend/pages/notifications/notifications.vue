<template><view class="page"><text class="title">{{ $tr("站内提醒") }}</text><text class="note">{{ $tr("{0}打开应用可查看；手机后台弹出的通知暂未完成。", [countKnown?unreadCount+' 条未读。':'未读数量暂未读取。']) }}</text>
<view class="actions"><button :disabled="marking" :class="{selected:!onlyUnread}" @click="changeFilter(false)">{{ $tr("全部") }}</button><button :disabled="marking" :class="{selected:onlyUnread}" @click="changeFilter(true)">{{ $tr("未读") }}</button><button :disabled="loading||marking||!ready||!items.length||!unreadCount" @click="readThrough">{{ $tr("全部已读") }}</button></view>
<text v-if="actionError" class="note">{{ $tr(actionError) }}</text><view v-if="pollError" class="message"><text>{{ $tr(pollError) }}</text><button :disabled="loading||marking" @click="load">{{ $tr("重新读取提醒") }}</button></view>
<button v-if="hasNew" :disabled="loading||marking" class="selected" @click="load">{{ $tr("有新提醒，点击查看") }}</button>
<view v-if="error" class="message"><text>{{ $tr(error) }}</text><button :disabled="loading" @click="failedMore?loadMore():load()">{{ $tr("重试") }}</button></view>
<text v-if="loading&&!items.length" class="note">{{ $tr("正在读取提醒…") }}</text><text v-else-if="!items.length&&!error" class="note">{{ $tr(onlyUnread?'没有未读提醒':'还没有站内提醒') }}</text>
<view v-for="item in items" :key="item.id" class="card" :class="{unread:!item.read_at}" @click="open(item)"><view class="heading"><text class="name">{{ item.actor_name !== undefined ? (item.actor_name_is_default ? $tr(item.actor_name) : item.actor_name) + ' ' + $tr(notificationText[item.kind] || '有了新动态') : $tr(item.title) }}</text><text v-if="!item.read_at" class="dot">{{ $tr("未读") }}</text></view><text v-if="item.excerpt" class="excerpt">{{ item.excerpt }}</text><text class="note">{{ $tr("{0} · 点击查看", [formatTimeLabel(utcTime(item.created_at))]) }}</text></view>
<button v-if="hasMore" :disabled="loading||marking||!ready" @click="loadMore">{{ $tr(loading?'正在读取…':'更早的提醒') }}</button><text v-else-if="items.length" class="end">{{ $tr("已显示全部提醒") }}</text>
</view></template>
<script setup>
import { ref } from 'vue'
import { onShow,onHide,onUnload } from '@dcloudio/uni-app'
import { fetchNotifications,fetchNotificationCount,readNotifications } from '../../utils/notifications-api'
import { utcTime } from '../../utils/request'
import { formatTimeLabel } from '../../utils/store'
import { getUser } from '../../utils/store'
import { getAuthToken } from '../../utils/auth'
const notificationText={post_comment:'在你的动态下留言',comment_reply:'回复了你的留言',chat_request:'申请与你聊天',chat_accepted:'同意了你的聊天申请',chat_rejected:'暂未同意你的聊天申请',game_joined:'报名了你的球局',game_left:'退出了你的球局',game_cancelled:'取消了你参加的球局',clinic_answer:'回答了你的问题'}
const items=ref([]),loading=ref(false),marking=ref(false),unreadCount=ref(0),hasMore=ref(false),onlyUnread=ref(false),hasNew=ref(false),error=ref(''),failedMore=ref(false)
const countKnown=ref(false),ready=ref(false),actionError=ref(''),pollError=ref('')
let generation=0,poll=null,newest=0,oldest=0,active=false,checking=false,owner='',markOperation=0,pollOperation=0
const account=()=>`${getUser().id||''}:${getAuthToken()}`
const sameAccount=()=>active&&Boolean(getAuthToken())&&owner===account()
const current=ticket=>sameAccount()&&ticket===generation
onShow(()=>{
    active=true;generation++;markOperation++;pollOperation++;marking.value=false;checking=false;loading.value=false
    if(owner!==account()){
        items.value=[];unreadCount.value=0;hasMore.value=false;onlyUnread.value=false;hasNew.value=false;countKnown.value=false;newest=0;oldest=0
    }
    owner=account();error.value='';actionError.value='';pollError.value='';ready.value=false
    if(!getAuthToken()){uni.reLaunch({url:'/pages/auth/login'});return}
    load();clearInterval(poll);poll=setInterval(checkNew,15000)
})
function leave(){active=false;generation++;markOperation++;pollOperation++;clearInterval(poll);poll=null;loading.value=false;marking.value=false;checking=false;ready.value=false}
onHide(leave);onUnload(leave)
async function load(){
    if(!sameAccount()||loading.value||marking.value)return
    const ticket=++generation;loading.value=true;ready.value=false;error.value='';actionError.value='';failedMore.value=false
    try{const data=await fetchNotifications(null,onlyUnread.value);if(!current(ticket))return;items.value=data.items;hasMore.value=data.has_more;unreadCount.value=data.unread_count;countKnown.value=true;newest=data.latest_id||data.items[0]?.id||0;oldest=data.items[data.items.length-1]?.id||0;hasNew.value=false;ready.value=true;pollError.value=''}
    catch(e){if(current(ticket)){error.value=e.message;countKnown.value=false}}finally{if(current(ticket))loading.value=false}
}
async function loadMore(){
    if(!sameAccount()||loading.value||marking.value||!ready.value||!hasMore.value)return
    const ticket=++generation;loading.value=true;error.value='';failedMore.value=true
    try{const data=await fetchNotifications(oldest||null,onlyUnread.value);if(!current(ticket))return;const ids=new Set(items.value.map(n=>n.id));items.value.push(...data.items.filter(n=>!ids.has(n.id)));hasMore.value=data.has_more;unreadCount.value=data.unread_count;countKnown.value=true;oldest=data.items[data.items.length-1]?.id||oldest}
    catch(e){if(current(ticket))error.value=e.message}finally{if(current(ticket))loading.value=false}
}
async function checkNew(){
    if(!sameAccount()||checking||loading.value||marking.value||!ready.value)return
    const ticket=generation,operation=++pollOperation;checking=true
    const ids=items.value.map(item=>item.id),batches=[]
    for(let i=0;i<ids.length;i+=100)batches.push(ids.slice(i,i+100))
    if(!batches.length)batches.push([])
    try{
        const results=await Promise.all(batches.map(batch=>fetchNotificationCount(batch)))
        if(!current(ticket)||loading.value||marking.value)return
        const visible=new Map(results.flatMap(data=>data.items||[]).map(item=>[item.id,item]))
        items.value=items.value.map(item=>visible.get(item.id)).filter(item=>item&&(!onlyUnread.value||!item.read_at))
        unreadCount.value=results[0].unread_count;countKnown.value=true;hasNew.value=results[0].latest_id>newest;pollError.value=''
    }catch(e){if(current(ticket))pollError.value='提醒暂未更新，请检查网络后重新读取'}finally{if(operation===pollOperation)checking=false}
}
function changeFilter(value){if(!sameAccount()||marking.value||value===onlyUnread.value)return;generation++;loading.value=false;onlyUnread.value=value;items.value=[];hasMore.value=false;ready.value=false;load()}
async function open(item){
    if(!sameAccount()||marking.value||loading.value||!ready.value)return
    const target=items.value.find(row=>row.id===item.id)
    if(!target)return
    const ticket=++generation,operation=++markOperation,url=target.url
    marking.value=true;actionError.value=''
    try{const data=await readNotifications({ids:[target.id]});if(!current(ticket))return;unreadCount.value=data.unread_count;countKnown.value=true;target.read_at=new Date().toISOString();if(onlyUnread.value)items.value=items.value.filter(row=>row.id!==target.id);if(url)uni.navigateTo({url})}
    catch(e){if(current(ticket)){actionError.value=e.message;uni.showToast({title:e.message,icon:'none'})}}finally{if(operation===markOperation)marking.value=false}
}
async function readThrough(){
    if(!sameAccount()||marking.value||loading.value||!ready.value||!items.value.length)return
    const through=items.value[0].id,ticket=++generation,operation=++markOperation;marking.value=true;actionError.value=''
    try{const data=await readNotifications({through_id:through});if(!current(ticket))return;unreadCount.value=data.unread_count;countKnown.value=true;items.value.forEach(item=>{if(item.id<=through)item.read_at=new Date().toISOString()});if(onlyUnread.value){marking.value=false;await load()}}
    catch(e){if(current(ticket)){actionError.value=e.message;uni.showToast({title:e.message,icon:'none'})}}finally{if(operation===markOperation)marking.value=false}
}
</script>
<style scoped>.page{min-height:100vh;padding:28rpx;background:#121212;color:#fff;box-sizing:border-box}.title{font-size:38rpx;color:#cf0;font-weight:bold;display:block}.note{font-size:24rpx;color:#aaa;line-height:1.7;display:block;margin:16rpx 0}.actions{display:flex;gap:12rpx;margin:20rpx 0}.actions button{flex:1;padding:8rpx;font-size:24rpx}.card,.message{background:#222;border:1rpx solid #333;border-radius:18rpx;padding:24rpx;margin:22rpx 0}.unread{border-color:#566c00}.heading{display:flex;gap:14rpx;justify-content:space-between}.name{font-size:28rpx;font-weight:bold;word-break:break-word}.dot{font-size:22rpx;color:#cf0;white-space:nowrap}.excerpt{font-size:26rpx;color:#ddd;line-height:1.6;display:block;margin-top:14rpx;white-space:pre-wrap;word-break:break-word}button{background:#333;color:#fff;font-size:26rpx;white-space:normal}.selected{background:#cf0;color:#121212}.end{text-align:center;display:block;color:#888;font-size:24rpx;margin:24rpx 0}</style>
