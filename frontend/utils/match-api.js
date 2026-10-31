import { API_BASE_URL } from './auth'
import { tournaments } from '../data/app-data'

export const MATCH_FALLBACK_IMAGE = '/static/badminton/match-placeholder.svg'
const CACHE_KEY = 'track-match-data-v2'
const reads = new Map()

function cache() {
    try { return uni.getStorageSync(CACHE_KEY) || { feeds: {}, details: {} } }
    catch { return { feeds: {}, details: {} } }
}
function save(value) {
    try { uni.setStorageSync(CACHE_KEY, value) } catch { /* Keep displaying the confirmed response if storage is full. */ }
}
function version(data) { return Date.parse(data?.sync?.last_attempt_at || data?.sync?.latest_updated_at || '') || 0 }
function stale() { const error = new Error('页面已变化'); error.stale = true; return error }
function ticket(key, isCurrent) {
    const id = (reads.get(key) || 0) + 1
    reads.set(key, id)
    return () => reads.get(key) === id && (!isCurrent || isCurrent())
}
function request(path) {
    return new Promise((resolve, reject) => uni.request({
        url: `${API_BASE_URL}${path}${path.includes('?') ? '&' : '?'}_read=${Date.now()}`,
        method: 'GET', timeout: 15000,
        success(response) {
            if (response.statusCode >= 200 && response.statusCode < 300) { resolve(response.data); return }
            const error = new Error(response.statusCode === 404 ? '比赛不存在或已被来源移除，请返回赛事页查看' : '比赛暂时无法读取，请稍后重试')
            error.status = response.statusCode
            reject(error)
        },
        fail() { reject(new Error('连接失败，请检查网络后重新读取')) }
    }))
}
function image(value) { return /^https?:\/\//.test(value || '') || String(value || '').startsWith('/static/') ? value : MATCH_FALLBACK_IMAGE }
export function normaliseMatchData(data) {
    if (!data || !Array.isArray(data.items) || !Array.isArray(data.events) || !data.sync || data.items.some(item => !item?.id || !item.event_id)) throw new Error('比赛内容没有读完整，请重新读取')
    return { ...data, items: data.items.map(item => ({ ...item, displayImage: image(item.image_url) })) }
}
export function historicalMatches() {
    return {
        historical: true, sync: {},
        events: tournaments.map(event => ({ id: event.id, name: event.name, start_date: event.date?.slice(0, 10), end_date: event.date?.slice(-10), location: event.location, image_url: event.image, summary: event.summary, source_url: event.source })),
        items: tournaments.flatMap(event => event.matches.map(item => ({
            id: `history-${event.id}-${item.id}`, event_id: event.id, event_name: event.name,
            discipline: item.category, round: item.round, court: item.court, scheduled_at: item.time,
            player1: item.p1, player2: item.p2, score1: item.s1, score2: item.s2, score_text: item.scoreText,
            winner: item.winner, status: 'finished', image_url: item.image, displayImage: image(item.image),
            image_source: item.imageSource, replay_url: item.videoUrl, report: item.report, source_url: event.source,
            source_updated_at: event.updatedAt
        })))
    }
}
export function readMatchCache(kind = 'events') {
    const saved = cache()
    const result = saved.feeds?.[kind] || saved.feeds?.events || saved.feeds?.home
    if (!result?.data || !Array.isArray(result.data.items)) return null
    return { ...result.data, cacheSavedAt: result.savedAt, fromCache: true }
}
export function readCachedMatch(id) {
    const saved = cache()
    const candidates = [saved.details?.[id], ...Object.values(saved.feeds || {}).map(feed => ({ data: { item: feed.data?.items?.find(item => item.id === id), sync: feed.data?.sync }, savedAt: feed.savedAt }))]
        .filter(entry => entry?.data?.item?.id === id).sort((a, b) => version(b.data) - version(a.data))
    if (!candidates.length) return null
    return { ...candidates[0].data, cacheSavedAt: candidates[0].savedAt, fromCache: true }
}
function removeCachedMatch(id) {
    const saved = cache()
    delete saved.details?.[id]
    Object.values(saved.feeds || {}).forEach(feed => { if (feed.data?.items) feed.data.items = feed.data.items.filter(item => item.id !== id) })
    save(saved)
}
export async function fetchMatches(kind = 'events', { isCurrent } = {}) {
    const current = ticket(`feed:${kind}`, isCurrent)
    const data = normaliseMatchData(await request(`/content/matches${kind === 'home' ? '?limit=6' : ''}`))
    if (!current()) throw stale()
    if (!data.items.length && !data.sync.latest_updated_at) throw new Error(data.sync.last_error || '后台还没有比赛内容')
    const saved = cache()
    saved.feeds ||= {}; saved.details ||= {}
    if (version(data) >= version(saved.feeds[kind]?.data)) saved.feeds[kind] = { savedAt: new Date().toISOString(), data }
    save(saved)
    return data
}
export async function fetchMatch(id, { isCurrent } = {}) {
    const current = ticket(`detail:${id}`, isCurrent)
    let data
    try { data = await request(`/content/matches/${encodeURIComponent(id)}`) }
    catch (error) {
        if (!current()) throw stale()
        if (error.status === 404) removeCachedMatch(id)
        throw error
    }
    if (!current()) throw stale()
    if (!data?.item || data.item.id !== id || !data.sync) throw new Error('比赛内容没有读完整，请重新读取')
    data = { ...data, item: { ...data.item, displayImage: image(data.item.image_url) } }
    const saved = cache()
    saved.details ||= {}
    if (version(data) >= version(saved.details[id]?.data)) saved.details[id] = { savedAt: new Date().toISOString(), data }
    save(saved)
    return data
}
export function matchStatusLabel(value) {
    return ({ scheduled: '未开始', live: '比赛中', finished: '已完赛', cancelled: '已取消', postponed: '已延期', walkover: '退赛', retired: '中途退赛', upcoming: '即将开始', ongoing: '进行中' })[value] || '待确认'
}
export function formatMatchUpdated(value) {
    if (!value) return '暂无记录'
    const utc = /^\d{4}-\d{2}-\d{2}T/.test(value) && !/(Z|[+-]\d{2}:\d{2})$/.test(value) ? value + 'Z' : value
    const date = new Date(utc)
    if (!Number.isFinite(date.getTime())) return '暂无记录'
    const pad = n => String(n).padStart(2, '0')
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}
