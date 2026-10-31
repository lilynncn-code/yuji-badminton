import { request } from './request'
export function fetchNotifications(beforeId,onlyUnread=false){return request(`/notifications?only_unread=${onlyUnread}${beforeId?'&before_id='+encodeURIComponent(beforeId):''}`)}
export function fetchNotificationCount(ids=[]){return request('/notifications/unread'+(ids.length?'?'+ids.map(id=>'ids='+encodeURIComponent(id)).join('&'):''))}
export function readNotifications(data){return request('/notifications/read',{method:'POST',data})}
