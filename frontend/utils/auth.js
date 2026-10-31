import { defaultUser } from '../data/app-data'

const BACKEND_ENV = 'test'
const LOCAL_BACKEND_HOST = '192.168.0.104'
const BACKEND_URLS = {
	test: '',
	prod: 'https://这里填写正式后端网址'
}

function getTestBackendUrl() {
	const envUrl = import.meta.env?.VITE_API_BASE_URL
	if (envUrl) return envUrl

	if (typeof window !== 'undefined' && window.location?.hostname) {
		const host = window.location.hostname
		return `http://${host}:8000`
	}

	return `http://${LOCAL_BACKEND_HOST}:8000`
}

export const API_BASE_URL = (BACKEND_ENV === 'test' ? getTestBackendUrl() : BACKEND_URLS[BACKEND_ENV]).replace(/\/$/, '')
export const TOKEN_KEY = 'track-auth-token'
const AUTH_USER_KEY = 'track-auth-user'
let authAttempt = 0
let sessionRevision = 0

function staleAuth() {
    const error = new Error('登录情况或页面已变化，请重新操作')
    error.stale = true
    return error
}

function request(path, data, options = {}) {
	return new Promise((resolve, reject) => {
		uni.request({
			url: `${API_BASE_URL}${path}`,
			method: 'POST',
			timeout: 20000,
			data,
			header: {
				'Content-Type': 'application/json',
				...(options.header || {})
			},
			success(response) {
				if (response.statusCode >= 200 && response.statusCode < 300) {
					resolve(response.data)
					return
				}
				const detail=response.data?.detail
				const error=new Error(typeof detail==='string'?detail:(Array.isArray(detail)?'填写内容不符合要求，请检查字数和格式':'操作没有完成，请重试'))
                error.status=response.statusCode
                reject(error)
			},
			fail() {
				reject(new Error('连接失败，请检查网络后重试'))
			}
		})
	})
}

function toLocalUser(user) {
	const image=value=>typeof value==='string'&&value.startsWith('/uploads/')?API_BASE_URL+value:value
	return {
		...defaultUser,
		id: user.id,
		username: user.username,
		phone: user.phone,
		name: user.name || user.nickname || user.username,
		nickname: user.name || user.nickname || user.username,
		city: user.city || '未设置城市',
		levelTag: user.level_tag || '羽毛球爱好者',
		bio: user.bio || '',
		avatar: image(user.avatar || defaultUser.avatar),
		cover: image(user.cover || defaultUser.cover),
		club: user.club || '',
		hand: user.hand || '右手持拍',
		followers: user.followers || 0,
		following: user.following || 0
	}
}

export function saveAuthSession(data) {
    if(!data?.token || typeof data.token!=='string' || !data.user?.id)throw new Error('登录结果没有读完整，请重新登录')
    const previous = uni.getStorageSync('track-user')
	const localUser = toLocalUser(data.user)
	const keys=[AUTH_USER_KEY,'track-user',TOKEN_KEY]
    const before=keys.map(key=>uni.getStorageSync(key))
    try{
        uni.setStorageSync(AUTH_USER_KEY,data.user)
        uni.setStorageSync('track-user',localUser)
        uni.setStorageSync(TOKEN_KEY,data.token)
    }catch(e){
        let restored=true
        keys.forEach((key,index)=>{try{before[index]?uni.setStorageSync(key,before[index]):uni.removeStorageSync(key)}catch(ignore){restored=false}})
        if(!restored)keys.forEach(key=>{try{uni.removeStorageSync(key)}catch(ignore){}})
        sessionRevision++;authAttempt++
        const error=new Error('本机未能保存登录信息，请检查可用空间后重新登录。注册或密码修改可能已完成，请使用新资料登录确认。')
        error.localSessionError=true
        throw error
    }
    sessionRevision++;authAttempt++
    if(previous?.id&&previous.id!==data.user.id){
        for(const key of ['track-posts','track-chat','track-chat-contact-meta','ai-coach-training-day','ai-coach-streak','track-onboarding']){
            try{uni.removeStorageSync(key)}catch(ignore){}
        }
    }
	return localUser
}

export function isLoggedIn() {
	return Boolean(uni.getStorageSync(TOKEN_KEY))
}

export function getAuthToken() {
	return uni.getStorageSync(TOKEN_KEY) || ''
}

export function clearAuthSession() {
	sessionRevision++;authAttempt++
	uni.removeStorageSync(TOKEN_KEY)
	uni.removeStorageSync(AUTH_USER_KEY)
	uni.removeStorageSync('track-user')
    for (const key of ['track-posts', 'track-chat', 'track-chat-contact-meta', 'ai-coach-training-day', 'ai-coach-streak', 'track-onboarding']) uni.removeStorageSync(key)
}

async function authenticate(path,payload,options={}) {
    const ticket=++authAttempt,token=getAuthToken(),revision=sessionRevision
    const current=()=>ticket===authAttempt&&token===getAuthToken()&&revision===sessionRevision&&(!options.isCurrent||options.isCurrent())
    if(!current())throw staleAuth()
    const data=await request(path,{...payload})
    if(!current())throw staleAuth()
    const user=saveAuthSession(data)
    options.onSaved?.(data.token)
    return user
}

export function login(account, password,options={}) {
    return authenticate('/auth/login',{account,password},options)
}

export function register(payload,options={}) {
    return authenticate('/auth/register',payload,options)
}

export function sendSms(phone, scene) {
	return request('/auth/send-sms', { phone, scene })
}

export function registerWithSms(data,options={}) {
    return register(data,options)
}

export async function resetPasswordBySms(phoneOrData, code, newPassword, account, options={}) {
	if(typeof phoneOrData==='object' && code && typeof code==='object')options=code
	const payload = typeof phoneOrData === 'object'
		? {
			account: phoneOrData.account || phoneOrData.phone,
			phone: phoneOrData.phone,
			new_password: phoneOrData.new_password || phoneOrData.newPassword,
			sms_code: phoneOrData.sms_code || phoneOrData.code
		}
		: {
			account: account || phoneOrData,
			phone: phoneOrData,
			new_password: newPassword,
			sms_code: code
		}
	return authenticate('/auth/forgot-password',payload,options)
}

export function resetPassword(payload,options={}) {
    return authenticate('/auth/forgot-password',payload,options)
}

export async function changePassword(payload,options={}) {
	const token = getAuthToken()
	if (!token) {
		return Promise.reject(new Error('请先登录'))
	}
    if(options.isCurrent&&!options.isCurrent())throw staleAuth()
    const revision=sessionRevision
    let data
    try{data = await request('/auth/change-password', {...payload}, {
		header: {
			Authorization: `Bearer ${token}`
		}
	})}catch(error){
        if(error.status===401&&getAuthToken()===token&&revision===sessionRevision){
            clearAuthSession();options.onSaved?.('');error.authExpired=true
        }
        throw error
    }
    if (getAuthToken() !== token||revision!==sessionRevision) throw new Error('登录账号已变化，请重新打开页面')
    try{saveAuthSession(data)}catch(error){
        if(error.localSessionError&&getAuthToken()===token){
            clearAuthSession();options.onSaved?.('');error.authExpired=true
        }
        throw error
    }
    options.onSaved?.(data.token)
    return data
}

export async function logoutRemote() {
    const token = getAuthToken(),revision=sessionRevision
    try{await request('/auth/logout', {}, { header: { Authorization: `Bearer ${token}` } })}
    catch(error){
        if(error.status!==401||getAuthToken()!==token||revision!==sessionRevision)throw error
    }
    if (getAuthToken() !== token||revision!==sessionRevision) throw new Error('登录账号已变化，请重新打开页面')
    clearAuthSession()
}
