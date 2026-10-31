import { API_BASE_URL, getAuthToken, clearAuthSession } from './auth'
let redirecting = false
export function errorMessage(data, fallback = '操作未完成，请重试') {
    if (typeof data?.detail === 'string') return data.detail
    if (Array.isArray(data?.detail)) return '填写内容不符合要求，请检查字数和格式'
    return fallback
}
export function handleStatus(status, data) {
    if (status === 401) {
        clearAuthSession()
        if (!redirecting) {
            redirecting = true
            uni.reLaunch({ url: '/pages/auth/login', complete: () => { redirecting = false } })
        }
    }
    const error = new Error(errorMessage(data, status === 401 ? '请重新登录' : undefined))
    error.status = status
    return error
}
export function request(path, options = {}) {
    return new Promise((resolve, reject) => {
        const token = getAuthToken()
        if (!token) { reject(handleStatus(401, {})); return }
        const method=String(options.method||'GET').toUpperCase()
        function send(attempt){
        if(getAuthToken()!==token){reject(new Error('登录账号已变化，请重新打开页面'));return}
        uni.request({ url: `${API_BASE_URL}${path}`, method, data: options.data,
            timeout: 20000, header: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
            success(response) {
                if(getAuthToken()!==token){reject(new Error('登录账号已变化，请重新打开页面'));return}
                if (response.statusCode >= 200 && response.statusCode < 300) resolve(response.data)
                else reject(handleStatus(response.statusCode, response.data))
            }, fail() {
                if(method==='GET'&&attempt===0){setTimeout(()=>send(1),250);return}
                reject(new Error('连接失败，请检查网络后重试'))
            }
        })
        }
        send(0)
    })
}
export function absoluteUrl(value = '') { return value.startsWith('/uploads/') ? API_BASE_URL + value : value }
export function utcTime(value) { return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T/.test(value) && !/(Z|[+-]\d{2}:\d{2})$/.test(value) ? value + 'Z' : value }
export function accountKey(name) { return `${name}-${uni.getStorageSync('track-user')?.id || 'guest'}` }
export function upload(filePath, path = '/media/upload', name = 'file', formData = {}) {
    return new Promise((resolve, reject) => {
        const token=getAuthToken()
        uni.uploadFile({ url: API_BASE_URL + path, filePath, name, formData, timeout: 30000,
            header: { Authorization: `Bearer ${token}` },
            success(response) {
                if(getAuthToken()!==token){reject(new Error('登录账号已变化，请重新打开页面'));return}
                let data = {}
                try { data = JSON.parse(response.data) } catch { reject(new Error('保存结果无法读取，请重试')); return }
                if (response.statusCode >= 200 && response.statusCode < 300) resolve(data)
                else reject(handleStatus(response.statusCode, data))
            }, fail() { reject(new Error('文件没有上传成功，请检查网络后重试')) }
        })
    })
}
export async function uploadImage(value) {
    // Save an address independent of the phone/host used to view the image.
    if (value?.startsWith(API_BASE_URL + '/uploads/images/')) return value.slice(API_BASE_URL.length)
    if (!value || value.startsWith('https://') || value.startsWith('/uploads/images/')) return value || ''
    const saved = await upload(value)
    return saved.url
}
export async function uploadVideo(value) {
    if (value?.startsWith(API_BASE_URL + '/uploads/videos/')) return value.slice(API_BASE_URL.length)
    if (!value || value.startsWith('/uploads/videos/')) return value || ''
    return (await upload(value, '/media/upload-video')).url
}
