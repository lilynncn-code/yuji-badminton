import { request } from './request'
import { saveAuthSession, clearAuthSession, getAuthToken } from './auth'
export function sendOldPhoneCode(){return request('/auth/change-phone/code',{method:'POST'})}
export function startPhoneChange(data){return request('/auth/change-phone/start',{method:'POST',data})}
export function resendNewPhoneCode(change_id){return request('/auth/change-phone/resend',{method:'POST',data:{change_id}})}
export function cancelPhoneChange(change_id){return request('/auth/change-phone/cancel',{method:'POST',data:{change_id}})}
export async function finishPhoneChange(change_id,new_code){
    const token=getAuthToken()
    const data=await request('/auth/change-phone/finish',{method:'POST',data:{change_id,new_code}})
    if(getAuthToken()!==token)throw new Error('登录账号已变化，请重新打开页面')
    saveAuthSession(data)
    return data
}
export function sendDeletionCode(){return request('/account/deletion/code',{method:'POST'})}
export async function deleteAccount(data){
    const token=getAuthToken(),id=uni.getStorageSync('track-user')?.id
    const result=await request('/account/deletion',{method:'POST',data})
    if(getAuthToken()!==token)throw new Error('登录账号已变化，请重新打开页面')
    if(id){
        for(const key of uni.getStorageInfoSync().keys){
            if(key.endsWith(`-${id}`))uni.removeStorageSync(key)
        }
    }
    clearAuthSession()
    return result
}
