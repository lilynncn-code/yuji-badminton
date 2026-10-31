<template>
    <view class="page">
        <view v-if="!detailId">
            <text class="title">{{ $tr("一起约球") }}</text>
            <text class="note">{{ $tr("报名仅确认参与意向。请发起人提前联系球馆确认场地，费用由参与者自行商量。") }}</text>
            <view class="row"><button :class="{active:!mine}" @click="changeFilter(false)">{{ $tr("可报名") }}</button><button :class="{active:mine}" @click="changeFilter(true)">{{ $tr("我参与的") }}</button><button class="active" :disabled="busy" @click="creating=!creating">{{ $tr(creating?'收起':'发起球局') }}</button></view>
            <view v-if="creating" class="card form">
                <input :disabled="busy" v-model="draft.title" maxlength="80" :placeholder='$tr("球局名称")' />
                <input :disabled="busy" v-model="draft.city" maxlength="80" :placeholder='$tr("城市")' />
                <input :disabled="busy" v-model="draft.venue" maxlength="200" :placeholder='$tr("场地名称和详细地址")' />
                <picker :disabled="busy" mode="date" :value="draft.date" @change="draft.date=$event.detail.value"><view class="field">{{ $tr("日期：{0}", [draft.date || '请选择']) }}</view></picker>
                <picker :disabled="busy" mode="time" :value="draft.time" @change="draft.time=$event.detail.value"><view class="field">{{ $tr("时间：{0}", [draft.time || '请选择']) }}</view></picker>
                <text class="note">{{ $tr("人数包含发起人（2至40人）") }}</text><input type="number" :disabled="busy" v-model="draft.capacity" />
                <text class="note">{{ $tr("时长（30至480分钟）") }}</text><input type="number" :disabled="busy" v-model="draft.duration" />
                <input :disabled="busy" v-model="draft.cost" maxlength="200" :placeholder='$tr("费用说明，例如每人分摊；无需在这里付款")' />
                <textarea :disabled="busy" v-model="draft.note" maxlength="1000" :placeholder='$tr("水平要求、集合方式、场地是否已预订")' />
                <text class="note">{{ $tr("日期和时间按手机当前时区显示。未发出的内容会按账号保存在本机。") }}</text>
                <text v-if="draftError" class="error">{{ $tr(draftError) }}</text><text v-if="saveError" class="error">{{ $tr(saveError) }}</text>
                <button class="active" :disabled="busy" @click="create">{{ $tr(busy?'保存中':'确认发起') }}</button>
            </view>
            <view v-if="!mine" class="row"><input class="city-input" v-model="city" maxlength="80" :placeholder='$tr("输入城市；留空看全部")' @confirm="load()"/><button @click="load()">{{ $tr("查找") }}</button></view>
            <text class="note">{{ $tr("{0} · {1}。刷新列表可查看新球局。", [mine?'我参与的':(listCity||'全部城市'), loaded?`已显示 ${items.length} 场`:'正在读取']) }}</text>
            <button :disabled="loading || busy" @click="load()">{{ $tr("刷新列表") }}</button>
            <text v-if="loading" class="note">{{ $tr("正在读取球局…") }}</text><text v-if="error" class="error">{{ $tr(error) }}</text><button v-if="error" :disabled="loading" @click="retryList">{{ $tr(positionExpired?'刷新列表':'重试读取') }}</button>
            <text v-if="loaded && !loading && !items.length && !error" class="note">{{ $tr("暂无球局，可以发起一场。") }}</text>
            <view v-for="game in items" :key="game.id" class="card" @click="open(game.id)">
                <text class="name">{{game.title}}</text><text class="note">{{ $tr(when(game.starts_at)) }} · {{game.city}}</text><text class="note">{{game.venue}}</text><text class="accent">{{ $tr("{0} · {1} / {2} 人 {3}", [statusText(game), game.count, game.capacity, game.joined?'· 已报名':'']) }}</text>
            </view>
            <button v-if="hasMore && !positionExpired" :disabled="loading || busy" @click="load(true)">{{ $tr("继续读取球局") }}</button>
        </view>
        <view v-else>
            <button :disabled="busy" @click="backToList">{{ $tr("返回球局列表") }}</button>
            <text v-if="opening" class="note">{{ $tr("正在读取最新状态…") }}</text><text v-if="detailError" class="error">{{ $tr(detailError) }}</text><button v-if="detailError" :disabled="busy || opening" @click="refreshDetail()">{{ $tr("重新读取状态") }}</button>
            <template v-if="selected">
            <view class="card"><text class="title">{{ selected.title }}</text><text class="accent">{{ $tr(statusText(selected)) }}</text><text class="note">{{ $tr('发起人：') + selected.host_name }}</text><text class="note">{{ $tr("{0} · {1} 分钟", [when(selected.starts_at), selected.duration_minutes]) }}</text><text class="note">{{ selected.city + ' · ' + selected.venue }}</text><text class="note">{{ $tr('费用：') + (selected.cost_note || $tr('请与发起人确认')) }}</text><text class="note">{{ selected.note }}</text></view>
            <view class="card"><text class="name">{{ $tr("参与名单 {0} / {1}", [selected.count, selected.capacity]) }}</text><view v-for="person in selected.members" :key="person.id" class="member" @click="openPerson(person)"><image :src="absoluteUrl(person.avatar)||'/static/logo.png'" mode="aspectFill"/><text>{{person.name}}{{ $tr(person.id===selected.host_id?' · 发起人':'') }}</text></view></view>
            <button :disabled="busy || opening" @click="refreshDetail()">{{ $tr("刷新状态") }}</button>
            <template v-if="selected.status==='open'">
                <button v-if="selected.host_id===selfId" class="danger" :disabled="busy" @click="confirmAction('cancel')">{{ $tr("取消这场球局") }}</button>
                <button v-else-if="selected.joined" :disabled="busy" @click="confirmAction('leave')">{{ $tr("退出报名") }}</button>
                <button v-else class="active" :disabled="busy || selected.count>=selected.capacity" @click="act('join')">{{ $tr(selected.count>=selected.capacity?'人数已满':'报名参加') }}</button>
            </template>
            </template>
        </view>
    </view>
</template>
<script setup>
import {ref,watch,nextTick} from 'vue'
import {onLoad,onShow,onHide,onUnload} from '@dcloudio/uni-app'
import {request,absoluteUrl} from '../../utils/request'
import {getUser} from '../../utils/store'
import {restoreGameDraft,persistGameDraft,prepareGameSend,clearGameDraft} from '../../utils/game-draft'
const account=()=>String(getUser().id||'guest')
const selfId=ref(Number(getUser().id)),mine=ref(false),city=ref(getUser().city==='未设置城市'?'':getUser().city||'')
const defaults=()=>({title:'',city:city.value,venue:'',date:'',time:'',capacity:'4',duration:'60',cost:'',note:''})
const draft=ref(defaults()),creating=ref(false),draftError=ref(''),saveError=ref('')
const selected=ref(null),detailId=ref(''),detailError=ref(''),opening=ref(false)
const items=ref([]),total=ref(null),hasMore=ref(false),cursor=ref(''),loaded=ref(false),listCity=ref('')
const busy=ref(false),loading=ref(false),error=ref(''),retryMore=ref(false),positionExpired=ref(false)
let owner=account(),active=false,restoring=false,generation=0,view=0,listRead=0,detailRead=0,poll=null
onLoad(q=>{detailId.value=q.id?String(q.id):''})
function context(){return {owner,generation,view}}
function live(ticket){return active&&ticket.owner===account()&&ticket.generation===generation&&ticket.view===view}
function resetScroll(){const ticket=context();nextTick(()=>{if(live(ticket))uni.pageScrollTo({scrollTop:0,duration:0})})}
function resetReads(){listRead++;detailRead++;loading.value=false;opening.value=false}
function restoreDraft(){
 restoring=true
 try{draft.value=restoreGameDraft(owner,defaults());draftError.value=''}
 catch(e){draft.value=defaults();draftError.value='草稿暂时无法读取，请检查本机存储空间'}
 finally{restoring=false}
}
watch(draft,value=>{
 if(restoring||!active||owner!==account())return
 try{persistGameDraft(owner,value);draftError.value=''}catch(e){draftError.value='草稿没有保存，请检查本机存储空间；保存恢复前不会发起球局'}
},{deep:true,flush:'sync'})
onShow(()=>{
 generation++;active=true;resetReads();busy.value=false
 if(owner!==account()){
  owner=account();selfId.value=Number(getUser().id);selected.value=null;detailId.value='';creating.value=false
  items.value=[];total.value=null;cursor.value='';hasMore.value=false;loaded.value=false
  city.value=getUser().city==='未设置城市'?'':getUser().city||''
 }
 restoreDraft();saveError.value=''
 if(detailId.value)refreshDetail();else load()
 resetScroll()
 clearInterval(poll);poll=setInterval(()=>{if(detailId.value&&!busy.value&&!opening.value)refreshDetail(true)},5000)
})
function leave(){active=false;generation++;resetReads();busy.value=false;clearInterval(poll)}
onHide(leave);onUnload(leave)
function when(value){const d=new Date(value);return `${d.getFullYear()}年${d.getMonth()+1}月${d.getDate()}日 ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`}
function statusText(game){return {open:'报名中',cancelled:'已取消',ended:'已开始'}[game.status]||game.status}
function changeFilter(value){if(busy.value||mine.value===value)return;view++;resetReads();mine.value=value;items.value=[];total.value=null;loaded.value=false;hasMore.value=false;cursor.value='';load();resetScroll()}
async function load(more=false){
 if(!active||busy.value||(more&&(loading.value||!hasMore.value||positionExpired.value)))return
 const ticket=context(),read=++listRead,searchCity=mine.value?'':more?listCity.value:city.value.trim()
 if(!more&&searchCity!==listCity.value){items.value=[];loaded.value=false;cursor.value='';hasMore.value=false;total.value=null}
 loading.value=true;error.value='';retryMore.value=more
 try{
  const data=await request(`/games?mine=${mine.value}&city=${encodeURIComponent(searchCity)}${more?'&cursor='+encodeURIComponent(cursor.value):''}`)
  if(!live(ticket)||read!==listRead)return
  const ids=new Set(more?items.value.map(game=>game.id):[])
  const additions=data.items.filter(game=>!ids.has(game.id))
  items.value=more?[...items.value,...additions]:additions;total.value=data.total;loaded.value=true;listCity.value=searchCity
  hasMore.value=data.has_more;cursor.value=data.next_cursor||'';positionExpired.value=false
 }catch(e){
  if(!live(ticket)||read!==listRead)return
  error.value=e.message||'球局读取失败，请重试'
  if(more&&e.status===400)positionExpired.value=true
 }finally{if(live(ticket)&&read===listRead)loading.value=false}
}
function retryList(){return load(positionExpired.value?false:retryMore.value)}
function backToList(){if(busy.value)return;view++;resetReads();selected.value=null;detailId.value='';detailError.value='';load();resetScroll()}
function open(id){
 if(busy.value)return
 view++;resetReads();detailId.value=String(id);selected.value=null;detailError.value='';refreshDetail();resetScroll()
}
async function refreshDetail(silent=false){
 if(!active||!detailId.value||(!silent&&busy.value))return
 const id=detailId.value,ticket=context(),read=++detailRead;opening.value=true
 try{
  const game=await request(`/games/${encodeURIComponent(id)}`)
  if(live(ticket)&&read===detailRead){selected.value=game;detailError.value=''}
 }catch(e){
  if(!live(ticket)||read!==detailRead)return
  detailError.value=e.message||'球局状态暂未更新，请重试'
  if(e.status===403||e.status===404)selected.value=null
 }finally{if(live(ticket)&&read===detailRead)opening.value=false}
}
async function create(){
 if(!active||owner!==account()||busy.value)return
 const data={...draft.value},start=new Date(`${data.date}T${data.time}:00`)
 if(!data.date||!data.time||Number.isNaN(start.getTime())){saveError.value='请选择日期和时间';return}
 if(data.title.trim().length<2||!data.city.trim()||data.venue.trim().length<2){saveError.value='请填写至少2字的名称和场地，并填写城市';return}
 const duration=Number(data.duration),capacity=Number(data.capacity)
 if(!Number.isInteger(capacity)||capacity<2||capacity>40||!Number.isInteger(duration)||duration<30||duration>480){saveError.value='人数需要2至40人，时长需要30至480分钟，均填写整数';return}
 const payload={title:data.title.trim(),city:data.city.trim(),venue:data.venue.trim(),starts_at:start.toISOString(),duration_minutes:duration,capacity,cost_note:data.cost.trim(),note:data.note.trim()}
 let send
 try{send=prepareGameSend(owner,data,payload);draftError.value=''}catch(e){draftError.value='草稿没有保存，请检查本机存储空间后重试';return}
 const ticket=context();resetReads();busy.value=true;saveError.value=''
 try{
  const game=await request('/games',{method:'POST',data:send})
  let cleared=false
  try{cleared=clearGameDraft(ticket.owner,send.request_key)}catch(e){/* Retaining the matching key still makes a retry safe. */}
  if(!live(ticket))return
  busy.value=false;view++;resetReads();selected.value=game;detailId.value=String(game.id);creating.value=false;detailError.value='';resetScroll()
  if(cleared){restoring=true;draft.value=defaults();restoring=false}
  else draftError.value='球局已保存，本机草稿暂未清理；重复确认会返回同一场球局'
 }catch(e){if(live(ticket))saveError.value=e.message||'尚未确认保存成功，请保留内容后重试'}
 finally{if(live(ticket))busy.value=false}
}
function confirmAction(kind){
 if(!active||busy.value||!selected.value)return
 const ticket=context(),id=selected.value.id
 uni.showModal({title:kind==='cancel'?'取消球局':'退出报名',content:kind==='cancel'?'取消后会给当前参与者保存站内提醒；手机后台通知暂未完成，请另行告知已约好的球友。':'确认退出这场球局吗？',success:r=>{if(r.confirm&&live(ticket)&&selected.value?.id===id)act(kind,id)}})
}
async function act(kind,id=selected.value?.id){
 if(!active||owner!==account()||busy.value||!id||selected.value?.id!==id)return
 const ticket=context();resetReads();busy.value=true;detailError.value=''
 try{
  const game=await request(`/games/${id}/${kind==='cancel'?'cancel':'join'}`,{method:kind==='cancel'?'POST':kind==='leave'?'DELETE':'PUT'})
  if(live(ticket))selected.value=game
 }catch(e){
  if(!live(ticket))return
  uni.showToast({title:e.message||'操作未完成，请刷新状态后重试',icon:'none'})
  await refreshDetail(true)
 }finally{if(live(ticket))busy.value=false}
}
function openPerson(person){if(person.id!==selfId.value)uni.navigateTo({url:`/pages/match-making/group-detail?id=${person.id}`})}
</script>
<style scoped>
.error{display:block;color:#ffb1a9;font-size:26rpx;line-height:1.6;margin:16rpx 0}

.page{min-height:100vh;background:#121212;color:#fff;padding:28rpx;box-sizing:border-box}.title{display:block;font-size:38rpx;color:#ccff00;font-weight:bold}.note{display:block;color:#aaa;line-height:1.7;font-size:25rpx;margin:14rpx 0;white-space:pre-wrap}.row{display:flex;gap:12rpx;align-items:center;margin:24rpx 0}.row button{flex:1;padding:0 12rpx}.card{padding:26rpx;background:#222;border:1rpx solid #333;border-radius:20rpx;margin:24rpx 0}.name{display:block;font-size:32rpx;font-weight:bold}.accent{display:block;color:#ccff00;font-size:26rpx;margin-top:14rpx}button{background:#333;color:#fff;font-size:26rpx;border-radius:14rpx;margin:18rpx 0}.active{background:#ccff00;color:#121212}.danger{color:#ff8b8b}.form input,.form textarea,.field,.city-input{background:#303030;color:white;padding:20rpx;border-radius:12rpx;font-size:26rpx;margin-bottom:18rpx;box-sizing:border-box;width:100%}.form input{min-height:80rpx}.form textarea{height:160rpx}.city-input{flex:3;margin:0}.member{display:flex;align-items:center;gap:20rpx;margin-top:24rpx;font-size:28rpx}.member image{width:64rpx;height:64rpx;border-radius:50%}
</style>
