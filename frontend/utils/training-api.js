import { request, upload, handleStatus } from './request'
import { API_BASE_URL, getAuthToken } from './auth'
export function fetchTrainingProgress() { return request('/training/progress') }
export function fetchTrainingSummary() { return request('/training/summary') }
export function fetchTrainingHistory(beforeId) { return request('/training?limit=30' + (beforeId ? `&before_id=${encodeURIComponent(beforeId)}` : '')) }
export function saveTrainingRecord(data) { return request('/training', { method: 'POST', data }) }
export function uploadTrainingVideo(path, requestKey) { return upload(path, '/media/upload-training-video', 'file', requestKey ? {request_key:requestKey} : {}) }
export function findTrainingVideoUpload(key) { return request(`/media/training-uploads/${encodeURIComponent(key)}`) }
export function abandonTrainingVideoUpload(key) { return request(`/media/training-uploads/${encodeURIComponent(key)}`,{method:'DELETE'}) }
export function attachTrainingVideo(id, mediaId) { return request(`/training/${id}/media`, {method:'PATCH',data:{media_id:mediaId}}) }
export async function loadTrainingVideo(path) {
    if (!/^\/media\/\d+\/file$/.test(path || '')) throw new Error('旧训练视频没有保存，请重新上传。')
    const token=getAuthToken()
    function ensureAccount(){if(getAuthToken()!==token)throw new Error('登录账号已变化，请重新打开页面')}
    if(!token)throw handleStatus(401,{})
    // #ifdef H5
    const response = await fetch(API_BASE_URL + path, {headers:{Authorization:`Bearer ${token}`},cache:'no-store'})
    ensureAccount()
    if (!response.ok) throw handleStatus(response.status, {})
    const blob=await response.blob()
    ensureAccount()
    return URL.createObjectURL(blob)
    // #endif
    // #ifndef H5
    return new Promise((resolve,reject)=>uni.downloadFile({url:API_BASE_URL+path,header:{Authorization:`Bearer ${token}`},success:r=>{try{ensureAccount();r.statusCode===200?resolve(r.tempFilePath):reject(handleStatus(r.statusCode,{}))}catch(e){reject(e)}},fail:()=>reject(new Error('视频读取失败，请检查网络后重试'))}))
    // #endif
}
