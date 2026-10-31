<template>
    <view class="page">
        <view class="tabs"><button v-for="tab in tabs" :key="tab.key" :class="{active:kind===tab.key}" :disabled="busy" @click="change(tab.key)">{{ $tr(tab.label) }}</button></view>
        <view class="list-head"><text class="note">{{ $tr(loading&&!loaded ? '正在读取…' : total===null ? '人数尚未读取' : `共 ${total} 人`) }}</text><button :disabled="loading||busy" @click="load()">{{ $tr("刷新列表") }}</button></view>
        <text class="note">{{ $tr(kind==='blocked'?'按最近屏蔽的时间排列。取消屏蔽不会恢复之前的关注。':'按最近关注的时间排列，新增球友请刷新查看。') }}</text>
        <view v-if="error" class="error"><text>{{ $tr(error) }}</text><button :disabled="loading||busy" @click="retryList">{{ $tr(positionExpired?'刷新后继续':'重新加载') }}</button></view>
        <view v-for="person in items" :key="person.id" class="card">
            <image :src="absoluteUrl(person.avatar) || '/static/logo.png'" mode="aspectFill" @click="openPerson(person)" />
            <view class="info" @click="openPerson(person)"><text class="name">{{ person.name }}</text><text class="note">{{ person.city || $tr('未设置城市') }} · {{ person.bio }}</text></view>
            <button v-if="kind==='blocked'" :disabled="busy||loading" @click="unblock(person)">{{ $tr(busyId===person.id?'正在取消…':'取消屏蔽') }}</button>
        </view>
        <text v-if="loaded && !loading && !error && !items.length" class="note">{{ $tr("这里还没有球友。") }}</text>
        <button v-if="hasMore&&!positionExpired" class="more" :disabled="loading||busy" @click="load(true)">{{ $tr(loading?'正在读取…':'加载更多') }}</button>
        <text v-else-if="loaded&&items.length&&!error" class="note end-note">{{ $tr("已显示本次列表，新的变化请刷新查看。") }}</text>
    </view>
</template>
<script setup>
import { ref } from 'vue'
import { onLoad, onShow, onHide, onUnload } from '@dcloudio/uni-app'
import { request, absoluteUrl } from '../../utils/request'
import { getAuthToken } from '../../utils/auth'
import { getUser } from '../../utils/store'
import { setBlock } from '../../utils/social-api'
const tabs=[{key:'following',label:'关注'},{key:'followers',label:'粉丝'},{key:'blocked',label:'已屏蔽'}]
const kind=ref('following'),items=ref([]),total=ref(null),loading=ref(false),loaded=ref(false),error=ref(''),busy=ref(false),busyId=ref(0),hasMore=ref(false),cursor=ref(''),positionExpired=ref(false),listRevision=ref(null)
let active=false,owner='',generation=0,pageGeneration=0,retryMore=false,pollTimer=null,checking=false
onLoad(q=>{kind.value=tabs.some(t=>t.key===q.kind)?q.kind:'following'})
function context(){return {page:pageGeneration,owner,token:getAuthToken(),kind:kind.value}}
function current(c){return active&&c.page===pageGeneration&&c.owner===String(getUser()?.id||'')&&c.token===getAuthToken()&&c.kind===kind.value}
function leave(){clearInterval(pollTimer);pollTimer=null;checking=false;active=false;pageGeneration++;generation++;loading.value=false;busy.value=false;busyId.value=0}
onHide(leave);onUnload(leave)
onShow(()=>{
    const next=String(getUser()?.id||'')
    if(owner!==next){owner=next;items.value=[];total.value=null;loaded.value=false;cursor.value='';hasMore.value=false;listRevision.value=null}
    active=true;pageGeneration++;load();clearInterval(pollTimer);pollTimer=setInterval(checkChanges,5000)
})
async function load(more=false){
    if(!active||more&&(loading.value||!hasMore.value||positionExpired.value))return
    const c=context(),readGeneration=++generation,position=more?cursor.value:''
    loading.value=true;error.value='';retryMore=more
    if(!more)positionExpired.value=false
    try{
        const data=await request(`/social/people?kind=${c.kind}&limit=30${position?`&cursor=${encodeURIComponent(position)}`:''}`)
        if(!current(c)||readGeneration!==generation)return
        if(more){const ids=new Set(items.value.map(p=>p.id));items.value.push(...data.items.filter(p=>!ids.has(p.id)))}
        else items.value=data.items
        total.value=data.total;listRevision.value=data.revision;hasMore.value=data.has_more;cursor.value=data.next_cursor||'';loaded.value=true
    }catch(e){if(current(c)&&readGeneration===generation){error.value=e.message||'球友列表读取失败，请重试';if(more&&e.status===400)positionExpired.value=true}}
    finally{if(current(c)&&readGeneration===generation)loading.value=false}
}
async function checkChanges(){
    if(!active||checking||loading.value||busy.value||!loaded.value||error.value||listRevision.value===null||positionExpired.value)return
    const c=context(),readGeneration=generation;checking=true
    try{
        const data=await request(`/social/people/status?kind=${c.kind}`)
        if(!current(c)||readGeneration!==generation||data.revision===listRevision.value)return
        generation++;positionExpired.value=true;items.value=[];total.value=data.total;hasMore.value=false;cursor.value=''
        error.value='名单有变化，请刷新后继续查看'
        uni.pageScrollTo({scrollTop:0,duration:0})
    }catch{}finally{if(current(c))checking=false}
}
function retryList(){return load(positionExpired.value?false:retryMore)}
function change(next){
    if(busy.value||kind.value===next)return
    generation++;kind.value=next;items.value=[];total.value=null;loaded.value=false;hasMore.value=false;cursor.value='';listRevision.value=null;load()
}
function openPerson(person){if(!active)return;uni.navigateTo({url:`/pages/match-making/group-detail?id=${person.id}`})}
async function unblock(person){
    if(busy.value||loading.value||kind.value!=='blocked')return
    const c=context();busy.value=true;busyId.value=person.id;error.value=''
    try{
        await setBlock(person.id,false)
        if(!current(c))return
        generation++;items.value=items.value.filter(p=>p.id!==person.id);total.value=Math.max(0,(total.value||0)-1)
        await load()
    }catch(e){if(current(c))error.value=e.message||'尚未取消屏蔽，请重试'}
    finally{if(current(c)){busy.value=false;busyId.value=0}}
}
</script>
<style scoped>
.page{min-height:100vh;background:#121212;color:white;padding:24rpx;box-sizing:border-box}.tabs{display:flex;gap:12rpx;margin-bottom:24rpx}.tabs button{flex:1;min-width:0;padding:0 12rpx}button{font-size:24rpx;background:#282828;color:white;border-radius:14rpx;margin:0}button[disabled]{color:#888}.active{background:#ccff00;color:#121212}.note{display:block;color:#aaa;font-size:24rpx;line-height:1.6}.list-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:16rpx}.card{display:flex;gap:20rpx;align-items:center;padding:24rpx 0;border-bottom:1rpx solid #333}.card image{width:80rpx;height:80rpx;flex-shrink:0;border-radius:50%}.card button{flex-shrink:0;padding:0 18rpx}.info{flex:1;min-width:0;word-break:break-word}.name{display:block;font-size:30rpx;font-weight:bold}.error{margin:20rpx 0;color:#ffb7a4;font-size:25rpx;line-height:1.6}.error button,.more{margin-top:20rpx}.end-note{margin:24rpx 0;text-align:center}
</style>
