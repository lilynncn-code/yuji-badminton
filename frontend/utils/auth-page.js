import { computed, ref, reactive } from 'vue'
import { onShow, onHide, onUnload } from '@dcloudio/uni-app'
import { getAuthToken } from './auth'

// One visible form owns each pending operation and every resulting navigation.
export function useAuthPage({clearSecrets=()=>{},onAccountChange=()=>{},requireLogin=false}={}) {
    const working=ref(''),notice=ref('')
    const loading=computed(()=>Boolean(working.value))
    let active=false,visit=0,operation=0,seenToken=getAuthToken()
    onShow(()=>{
        active=true;visit++
        if(seenToken!==getAuthToken()){
            seenToken=getAuthToken();operation++;working.value='';notice.value=''
            clearSecrets();onAccountChange()
        }
        if(requireLogin&&!seenToken)uni.reLaunch({url:'/pages/auth/login'})
    })
    function hide(){active=false;visit++;clearSecrets()}
    onHide(hide);onUnload(hide)
    const canAct=()=>active&&seenToken===getAuthToken()&&!loading.value
    function explain(message){
        if(!active||seenToken!==getAuthToken())return
        notice.value=message
        uni.showToast({title:message,icon:'none'})
    }
    async function run(kind,action,{message='',success=()=>{},clearOnSuccess=false}={}){
        if(!canAct())return
        const ticket=++operation,pageVisit=visit
        let expectedToken=getAuthToken()
        const sameAccount=()=>ticket===operation&&expectedToken===getAuthToken()
        const current=()=>active&&pageVisit===visit&&sameAccount()
        working.value=kind;notice.value=''
        const options={isCurrent:current,onSaved:token=>{
            expectedToken=token
            if(ticket===operation)seenToken=token
        }}
        try{
            const result=await action(options)
            if(!sameAccount())return
            if(clearOnSuccess)clearSecrets()
            // An already submitted password change can finish while hidden.
            // Its result stays available without navigating a different page.
            if(message)notice.value=message
            if(current()){
                if(message)uni.showToast({title:message,icon:'none'})
                success(result)
            }
            return result
        }catch(error){
            if(current()&&!error.stale){
                explain(error.message||'操作没有完成，请重试')
                if(error.authExpired&&requireLogin)uni.reLaunch({url:'/pages/auth/login'})
            }
        }finally{if(ticket===operation)working.value=''}
    }
    return {working,loading,notice,canAct,explain,run}
}

const smsDeadlines=reactive(new Map())
export function useSmsCooldown(phone,scene){
    const now=ref(Date.now())
    let timer=null
    const key=value=>`${scene}:${value.trim()}`
    const smsSeconds=computed(()=>Math.max(0,Math.ceil(((smsDeadlines.get(key(phone.value))||0)-now.value)/1000)))
    function stop(){clearInterval(timer);timer=null}
    onShow(()=>{stop();now.value=Date.now();timer=setInterval(()=>now.value=Date.now(),1000)})
    onHide(stop);onUnload(stop)
    function remember(value){smsDeadlines.set(key(value),Date.now()+60000);now.value=Date.now()}
    return {smsSeconds,remember}
}

export function validatePhone(value){return /^1[3-9][0-9]{9}$/.test(value)?'':'请填写正确的11位手机号'}
export function validatePassword(value,label='密码'){
    if(!value)return `请填写${label}`
    if(value.length<6)return `${label}至少6位`
    if(value.length>50)return `${label}不能超过50位`
    if(/\s/.test(value))return `${label}不能包含空格`
    return ''
}
