import { request, uploadImage, absoluteUrl } from './request'
import { defaultUser } from '../data/app-data'
import { getUser,saveUser } from './store'
import { getAuthToken } from './auth'

function text(value, fallback = '') {
	return String(value ?? fallback).trim()
}


function toLocalProfile(profile) {
	const nickname = text(profile.nickname || profile.name || profile.username, defaultUser.name)
	const levelTag = text(profile.levelTag || profile.level_tag || profile.level, defaultUser.levelTag)
	return {
		...defaultUser,
		id: profile.id,
        canReviewReports: profile.can_review_reports === true,
		username: profile.username,
		phone: profile.phone,
		name: nickname,
		nickname,
		bio: text(profile.bio),
		city: text(profile.city),
		levelTag,
		avatar: absoluteUrl(profile.avatar || defaultUser.avatar),
		cover: absoluteUrl(profile.cover || defaultUser.cover),
		club: text(profile.club),
		hand: text(profile.hand, defaultUser.hand),
		followers: Number(profile.followers || 0),
		following: Number(profile.following || 0)
	}
}

const states=new Map()
function has(source,field){return Object.prototype.hasOwnProperty.call(source,field)}
function operation(options={}){
    const owner=String(getUser()?.id||''),token=getAuthToken(),key=owner+':'+token
    if(!states.has(key))states.set(key,{epoch:0,read:0,writing:false})
    const state=states.get(key)
    function check(page=true){if(!owner||!token||owner!==String(getUser()?.id||'')||token!==getAuthToken()||(page&&options.isCurrent&&!options.isCurrent()))throw new Error('页面或登录账号已变化，请重新打开资料')}
    check();return {owner,token,state,check}
}
function cacheProfile(profile,c){
    c.check(false)
    if(String(profile.id)!==c.owner)throw new Error('资料所属账号不一致，请重新登录')
    const local=toLocalProfile(profile)
    try{return saveUser(local)}catch{return {...local,localCacheError:true}}
}
export async function fetchMyProfile(options={}){
    const c=operation(options),epoch=c.state.epoch,read=++c.state.read
    const profile=await request('/profile/me');c.check()
    if(c.state.writing||epoch!==c.state.epoch||read!==c.state.read)throw Object.assign(new Error('资料正在更新，请稍候刷新'),{stale:true})
    return cacheProfile(profile,c)
}
export async function saveMyProfile(profile,options={}){
    const c=operation(options),source={...profile},data={}
    if(c.state.writing)throw new Error('资料正在保存，请稍候重试')
    c.state.writing=true;c.state.epoch++
    try{
        if(has(source,'nickname')||has(source,'name'))data.nickname=text(source.nickname??source.name)
        for(const field of ['club','hand','city','bio'])if(has(source,field))data[field]=text(source[field])
        if(has(source,'levelTag')||has(source,'level_tag'))data.level_tag=text(source.levelTag??source.level_tag)
        for(const field of ['avatar','cover'])if(has(source,field)){
            c.check();data[field]=await uploadImage(text(source[field]));c.check()
            if(options.onImageReady)options.onImageReady(field,data[field])
        }
        c.check()
        const updated=await request('/profile/me',{method:'PATCH',data})
        // A confirmed save belongs to its account even if its page has since closed.
        return cacheProfile(updated,c)
    }finally{c.state.writing=false;c.state.epoch++}
}
