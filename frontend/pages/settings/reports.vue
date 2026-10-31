<template><view class="page"><text class="title">{{ $tr("我的举报记录") }}</text><text class="note">{{ $tr("提交后会保存原因和当时的内容；只有处理完成才会显示处理结果。") }}</text><button :disabled="loading" @click="load()">{{ $tr("刷新记录") }}</button><view v-if="error"><text class="note">{{ $tr(error) }}</text><button :disabled="loading" @click="load(failedMore)">{{ $tr("重试") }}</button></view><text v-if="loading&&!items.length" class="note">{{ $tr("正在读取记录…") }}</text><text v-else-if="!items.length&&!error" class="note">{{ $tr("暂无举报记录。") }}</text><view v-for="item in items" :key="item.id" class="card"><text>{{ $tr("{0} · 编号 {1}", [item.status==='resolved'?'已处理':'等待处理', item.id]) }}</text><text class="note">{{ item.reason }}</text><text class="note">{{ $tr(formatTimeLabel(utcTime(item.created_at))) }}</text><text v-if="item.result" class="note">{{ $tr('处理结果：') + item.result }}</text></view><button v-if="hasMore" :disabled="loading" @click="load(true)">{{ $tr(loading?'正在读取…':'更早的记录') }}</button><text v-else-if="items.length" class="note">{{ $tr("已显示全部记录") }}</text></view></template>
<script setup>
import {ref} from 'vue'
import {onShow,onHide,onUnload} from '@dcloudio/uni-app'
import {request,utcTime} from '../../utils/request'
import {formatTimeLabel,getUser} from '../../utils/store'
import {getAuthToken} from '../../utils/auth'
const items=ref([]),error=ref(''),loading=ref(false),hasMore=ref(false),failedMore=ref(false)
let generation=0,owner='',active=false
const account=()=>`${getUser().id||''}:${getAuthToken()}`
const current=ticket=>active&&ticket===generation&&owner===account()
async function load(more=false){
    if(!active||owner!==account()||loading.value)return
    const ticket=++generation;loading.value=true;error.value='';failedMore.value=more
    try{
        const before=more?items.value[items.value.length-1]?.id:0
        const data=await request('/social/reports'+(before?'?before_id='+before:''))
        if(!current(ticket))return
        const known=new Set(items.value.map(r=>r.id))
        items.value=more?[...items.value,...data.items.filter(r=>!known.has(r.id))]:data.items
        hasMore.value=data.has_more
    }catch(e){if(current(ticket))error.value=e.message}finally{if(current(ticket))loading.value=false}
}
function leave(){active=false;generation++;loading.value=false}
onShow(()=>{
    active=true;generation++;loading.value=false
    if(owner!==account()){items.value=[];hasMore.value=false;error.value='';failedMore.value=false}
    owner=account()
    if(!getAuthToken()){uni.reLaunch({url:'/pages/auth/login'});return}
    load()
});onHide(leave);onUnload(leave)
</script>
<style scoped>.page{min-height:100vh;padding:28rpx;background:#121212;color:white;box-sizing:border-box}.title{display:block;font-size:36rpx;font-weight:bold;color:#ccff00}.note{display:block;font-size:26rpx;line-height:1.7;color:#aaa;margin-top:16rpx;white-space:pre-wrap;word-break:break-word}.card{padding:24rpx;background:#222;border-radius:16rpx;margin-top:24rpx}button{margin-top:24rpx;background:#333;color:white;font-size:26rpx}</style>
