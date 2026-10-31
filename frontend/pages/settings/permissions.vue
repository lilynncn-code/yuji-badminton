<template><view class="page"><text class="title">{{ $tr("手机权限") }}</text><text class="note">{{ $tr("只会在你使用相关功能时申请。拒绝后仍可使用其他功能；定位也可用手动填写城市代替。") }}</text><view v-for="item in items" :key="item.key" class="card"><text class="name">{{ $tr("{0} · {1}", [item.name, states[item.key]||(loading?'正在读取…':'暂时无法读取')]) }}</text><text class="note">{{ $tr(item.use) }}</text></view><button :disabled="loading" @click="load">{{ $tr(loading?'正在读取…':'刷新权限情况') }}</button><button :disabled="opening" @click="openSettings">{{ $tr(opening?'正在打开…':settingsLabel) }}</button><text class="note">{{ $tr(help) }}</text></view></template>
<script setup>
import { ref } from 'vue'
import { onShow, onHide, onUnload } from '@dcloudio/uni-app'
const states=ref({}),help=ref(''),loading=ref(false),opening=ref(false),settingsLabel=ref('查看设置方法')
const items=[{key:'cameraAuthorized',name:'相机',use:'训练时显示画面；网页可选择保存无声录像。'},
{key:'microphoneAuthorized',name:'麦克风',use:'主动录制聊天语音。训练录像不需要麦克风。'},
{key:'albumAuthorized',name:'相册',use:'主动选择头像、背景、聊天图片、动态图片和视频，以及训练视频。'},
{key:'locationAuthorized',name:'定位',use:'主动查找附近球馆，不需要时可按城市查找。'}]
let generation=0,visit=0,active=false
const waiting=new Set()
const names={authorized:'已允许',denied:'未允许','not determined':'使用时询问',unknown:'暂时无法读取',granted:'已允许',prompt:'使用时询问',limited:'仅允许所选照片','config error':'暂时无法使用，请检查应用安装'}
onShow(()=>{active=true;visit++;load()})
function leave(){active=false;visit++;generation++;loading.value=false;opening.value=false;for(const cancel of [...waiting])cancel();states.value={};help.value=''}
onHide(leave);onUnload(leave)
function readBrowserPermission(name){
    return new Promise(resolve=>{
        let finished=false,timer
        const finish=value=>{if(finished)return;finished=true;clearTimeout(timer);waiting.delete(cancel);resolve(value)}
        const cancel=()=>finish('请查看网站设置')
        waiting.add(cancel);timer=setTimeout(cancel,4000)
        try{Promise.resolve(navigator.permissions.query({name})).then(result=>finish(names[result?.state]||'请查看网站设置'),cancel)}catch(e){cancel()}
    })
}
async function load(){
    if(!active||loading.value)return
    const ticket=++generation
    states.value={};help.value='';loading.value=true
    try{
    // #ifdef APP-PLUS
    settingsLabel.value='前往手机设置'
    try{const result=uni.getAppAuthorizeSetting();states.value=Object.fromEntries(items.map(item=>[item.key,names[result[item.key]]||'暂时无法读取']));help.value='从手机设置返回后，会重新读取。不同手机显示的项目可能不同；实际使用时仍由手机确认。'}
    catch(e){help.value='无法直接读取，请前往手机设置查看好羽的权限。'}
    return
    // #endif
    // #ifdef H5
    help.value='当前使用浏览器。点击网址旁的网站设置可管理相机、麦克风和定位；相册每次由你主动选择。'
    const entries=await Promise.all([['cameraAuthorized','camera'],['microphoneAuthorized','microphone'],['locationAuthorized','geolocation']].map(async([key,name])=>[key,await readBrowserPermission(name)]))
    if(active&&ticket===generation)states.value={albumAuthorized:'每次由你选择',...Object.fromEntries(entries)}
    return
    // #endif
    help.value='请在当前平台的设置中查看好羽的权限。'
    }finally{if(ticket===generation)loading.value=false}
}
function openSettings(){
    if(!active||opening.value)return
    const ticket=visit
    opening.value=true
    const current=()=>active&&ticket===visit
    // #ifdef APP-PLUS
    try{uni.openAppAuthorizeSetting({success:()=>{if(current())opening.value=false},fail:()=>{if(current()){opening.value=false;help.value='未能打开。请在手机“设置”中找到好羽，再查看权限。'}}})}
    catch(e){if(current()){opening.value=false;help.value='请在手机“设置”中找到好羽，再查看权限。'}}
    return
    // #endif
    uni.showModal({title:'查看权限',content:'浏览器请点击网址旁的网站设置；手机请在系统“设置”中找到好羽。你可以分别允许或关闭相机、麦克风、相册和定位。',showCancel:false,complete:()=>{if(current())opening.value=false}})
}
</script>
<style scoped>.page{min-height:100vh;padding:30rpx;background:#121212;color:#fff;box-sizing:border-box}.title{display:block;color:#cf0;font-size:38rpx;font-weight:bold}.card{background:#222;padding:24rpx;border-radius:18rpx;margin:22rpx 0}.name{display:block;font-size:29rpx;font-weight:bold}.note{display:block;color:#aaa;font-size:25rpx;line-height:1.7;margin:16rpx 0}button{background:#303030;color:#fff;margin:18rpx 0;font-size:27rpx}</style>
