<template><view><image v-if="src" :src="src" mode="aspectFill" class="chat-image" @click="preview"/><button v-else-if="error" class="retry" @click="load">{{ $tr("图片读取失败，点此重试") }}</button><text v-else class="retry">{{ $tr("正在读取图片…") }}</text></view></template>
<script setup>
import { ref, watch, onUnmounted } from 'vue'
import { API_BASE_URL, getAuthToken } from '../utils/auth'
import { handleStatus } from '../utils/request'
const props=defineProps({path:String,active:{type:Boolean,default:true}})
const src=ref(''),error=ref(false)
let generation=0
function release(){generation++
    // #ifdef H5
    if(src.value.startsWith('blob:'))URL.revokeObjectURL(src.value)
    // #endif
    src.value=''
}
async function load(){
    release();if(!props.active||!props.path)return
    const ticket=generation;error.value=false
    if(!/^\/chat\/chats\/\d+\/images\/\d+$/.test(props.path)){src.value=props.path;return}
    const token=getAuthToken()
    const current=()=>ticket===generation&&props.active&&token===getAuthToken()
    try{
        let url
        // #ifdef H5
        let result
        for(let attempt=0;attempt<2;attempt++){
            try{result=await fetch(API_BASE_URL+props.path,{headers:{Authorization:`Bearer ${token}`},cache:'no-store'});break}
            catch(e){
                if(attempt||!current())throw e
                await new Promise(resolve=>setTimeout(resolve,250))
                if(!current())return
            }
        }
        if(!current())return
        if(!result.ok)throw handleStatus(result.status,{})
        const blob=await result.blob()
        if(!current())return
        url=URL.createObjectURL(blob)
        // #endif
        // #ifndef H5
        url=await new Promise((resolve,reject)=>uni.downloadFile({url:API_BASE_URL+props.path,header:{Authorization:`Bearer ${token}`},success:r=>{if(!current()){reject(Error('登录情况已变化'));return}r.statusCode===200?resolve(r.tempFilePath):reject(handleStatus(r.statusCode,{}))},fail:reject}))
        // #endif
        if(current())src.value=url
        else{
            // #ifdef H5
            URL.revokeObjectURL(url)
            // #endif
        }
    }catch(e){if(current())error.value=true}
}
function preview(){if(src.value)uni.previewImage({current:src.value,urls:[src.value]})}
watch(()=>[props.path,props.active],load,{immediate:true})
onUnmounted(release)
</script>
<style scoped>.chat-image{width:360rpx;height:240rpx;border-radius:12rpx}.retry{display:block;color:#bbb;font-size:24rpx;line-height:1.6}</style>
