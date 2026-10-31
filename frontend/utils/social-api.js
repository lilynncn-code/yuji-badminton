import { request } from './request'
import { getAuthToken } from './auth'
export function getRelation(id) { return request(`/social/users/${id}`) }
export function setFollow(id, value) { return request(`/social/users/${id}/follow`, {method: value ? 'PUT' : 'DELETE'}) }
export function setBlock(id, value) { return request(`/social/users/${id}/block`, {method: value ? 'PUT' : 'DELETE'}) }
export function getFavorites(kind) { return request(`/social/favorites/${kind}`) }
export function setFavorite(kind, key, value) { return request(`/social/favorites/${kind}/${encodeURIComponent(key)}`, {method: value ? 'PUT' : 'DELETE'}) }
export function reportContent(target_type, target_id, isCurrent = () => true) {
    const token=getAuthToken()
    const current=()=>getAuthToken()===token&&isCurrent()
    uni.showModal({ title: '举报原因', editable: true, placeholderText: '请说明问题，最多500字', success: async result => {
        if (!result.confirm||!current()) return
        const reason = String(result.content || '').trim()
        if (reason.length < 2 || reason.length > 500) { uni.showToast({title:'请填写2至500字的原因',icon:'none'}); return }
        try { const data = await request('/social/reports', {method:'POST', data:{target_type, target_id:Number(target_id), reason}}); if(!current())return; uni.showModal({title:'举报记录已保存',content:data.message,showCancel:false}) }
        catch(e) { if(current())uni.showToast({title:e.message,icon:'none'}) }
    }})
}
