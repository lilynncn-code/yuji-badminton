import { defaultUser } from '../data/app-data'

const USER_KEY = 'track-user'
const LANGUAGE_KEY = 'track-language'
const THEME_KEY = 'track-theme'
const ONBOARDING_KEY = 'track-onboarding-complete'
const EDIT_WINDOW_MS = 15 * 60 * 1000
const DEFAULT_LANGUAGE = 'zh-Hans'
const DEFAULT_THEME = 'dark'
let activeLanguage = DEFAULT_LANGUAGE
let activeTheme = DEFAULT_THEME

function applyThemeClass(theme) {
	const nextTheme = DEFAULT_THEME
	if (typeof document !== 'undefined') {
		const root = document.documentElement
		const body = document.body
		root?.classList.remove('track-theme-light', 'track-theme-dark')
		body?.classList.remove('track-theme-light', 'track-theme-dark')
		root?.classList.add(`track-theme-${nextTheme}`)
		body?.classList.add(`track-theme-${nextTheme}`)
	}
	if (typeof uni !== 'undefined' && uni.setNavigationBarColor) {
		uni.setNavigationBarColor({
			frontColor: '#ffffff',
			backgroundColor: '#121212'
		})
	}
}

export function getUser() {
	return uni.getStorageSync(USER_KEY) || defaultUser
}

export function saveUser(user) {
	const nickname = user?.nickname || user?.name
	const nextUser = { ...getUser(), ...user }
	if (nickname) {
		nextUser.name = nickname
		nextUser.nickname = nickname
	}
	uni.setStorageSync(USER_KEY, nextUser)
	return nextUser
}

export function getLanguage() {
	const storedLanguage = uni.getStorageSync(LANGUAGE_KEY)
	activeLanguage = storedLanguage || activeLanguage || DEFAULT_LANGUAGE
	return activeLanguage
}

export function saveLanguage(language) {
	const nextLanguage = language === 'en' ? 'en' : DEFAULT_LANGUAGE
	uni.setStorageSync(LANGUAGE_KEY, nextLanguage)
	activeLanguage = nextLanguage
	uni.$emit?.('track-language-changed', nextLanguage)
	return activeLanguage
}

export function getTheme() {
	activeTheme = DEFAULT_THEME
	uni.setStorageSync(THEME_KEY, activeTheme)
	applyThemeClass(activeTheme)
	return activeTheme
}

export function saveTheme() {
	activeTheme = DEFAULT_THEME
	uni.setStorageSync(THEME_KEY, activeTheme)
	applyThemeClass(activeTheme)
	return activeTheme
}

export function isOnboardingComplete() {
	return uni.getStorageSync(`${ONBOARDING_KEY}-${getUser().id || 'guest'}`) === true
}

export function completeOnboarding(language = getLanguage()) {
	const owner = getUser().id
	if (!owner) throw new Error('请先登录后再保存首次设置')
	const key = `${ONBOARDING_KEY}-${owner}`
	const beforeLanguage = uni.getStorageSync(LANGUAGE_KEY), beforeFlag = uni.getStorageSync(key), beforeActive = activeLanguage
	try {
		saveLanguage(language)
		uni.setStorageSync(key, true)
	} catch (error) {
		for (const [name, value] of [[LANGUAGE_KEY, beforeLanguage], [key, beforeFlag]]) {
			try { if (value === '' || value === undefined || value === null) uni.removeStorageSync(name); else uni.setStorageSync(name, value) } catch {}
		}
		activeLanguage = beforeActive
		uni.$emit?.('track-language-changed', beforeActive)
		throw error
	}
	return true
}

export function canEditPost(post) {
	if (!post?.isMine || post.canEdit === false) return false
	return Date.now() - new Date(post.createdAt).getTime() <= EDIT_WINDOW_MS
}

export function formatTimeLabel(value) {
    if (!value || !Number.isFinite(new Date(value).getTime())) return ''
	const diff = Date.now() - new Date(value).getTime()
	const minutes = Math.max(0, Math.floor(diff / 60000))
	if (minutes < 1) return '刚刚'
	if (minutes < 60) return `${minutes} 分钟前`
	const hours = Math.floor(minutes / 60)
	if (hours < 24) return `${hours} 小时前`
	return typeof value === 'string' ? value.slice(0, 10) : ''
}

export function editMinutesLeft(post) {
	const left = EDIT_WINDOW_MS - (Date.now() - new Date(post.createdAt).getTime())
	return Math.max(0, Math.ceil(left / 60000))
}
