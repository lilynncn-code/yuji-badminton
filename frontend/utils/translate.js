import { ref } from 'vue'
import messages from './messages-en.json'

export const appLanguage = ref('zh-Hans')
const cache = new Map()
const escapePattern = value => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
const patterns = Object.entries(messages)
	.filter(([key]) => /\{\d+\}/.test(key))
	.sort(([a], [b]) => b.replace(/\{\d+\}/g, '').length - a.replace(/\{\d+\}/g, '').length)
	.map(([key, english]) => {
		const slots = [...key.matchAll(/\{(\d+)\}/g)].map(match => Number(match[1]))
		const parts = key.split(/\{\d+\}/).map(escapePattern)
		return { expressions: ['([\\s\\S]*)', '([\\s\\S]*?)'].map(slot => new RegExp('^' + parts.join(slot) + '$')), slots, english }
	})

export function syncLanguage(language) {
	appLanguage.value = language === 'en' ? 'en' : 'zh-Hans'
	if (typeof document !== 'undefined') document.documentElement.lang = appLanguage.value === 'en' ? 'en' : 'zh-CN'
	return appLanguage.value
}

function format(value, params, render) {
	return value.replace(/\{(\d+)\}/g, (slot, index) => params[index] === undefined ? slot : render(params[index]))
}

function english(value, depth = 0) {
	if (value === null || value === undefined) return ''
	const source = String(value)
	if (!/[\u3400-\u9fff]/u.test(source) || depth > 12) return source
	if (cache.has(source)) return cache.get(source)
	const trimmed = source.trim()
	let result = messages[trimmed]
	if (result === undefined) {
		for (const pattern of patterns) {
			for (const expression of pattern.expressions) {
				const match = trimmed.match(expression)
				if (!match) continue
				const values = []
				pattern.slots.forEach((slot, index) => { values[slot] = match[index + 1] })
				const candidate = format(pattern.english, values, item => english(item, depth + 1))
				if (result === undefined || (candidate.match(/[\u3400-\u9fff]/gu) || []).length < (result.match(/[\u3400-\u9fff]/gu) || []).length) result = candidate
				if (!/[\u3400-\u9fff]/u.test(result)) break
			}
			if (result !== undefined && !/[\u3400-\u9fff]/u.test(result)) break
		}
	}
	// Generated summaries can join several separately translated sentences.
	if (result === undefined) {
		const pieces = trimmed.split(/([；。\n]| · | → | \/ )/)
		if (pieces.length > 1) {
			result = pieces.map(piece => piece === '；' ? '; ' : piece === '。' ? '. ' : english(piece, depth + 1)).join('').trim()
		}
	}
	result = result === undefined ? source : source.replace(trimmed, () => result)
	if (cache.size > 4000) cache.clear()
	cache.set(source, result)
	return result
}

// Call only for application copy. Names, posts and messages entered by people stay unchanged.
export function translate(value, params) {
	const language = appLanguage.value
	if (value === null || value === undefined) return ''
	if (Array.isArray(value)) return value.map(item => translate(item)).join(', ')
	const source = String(value)
	if (params) {
		return format(language === 'en' ? messages[source] || source : source, params,
			item => language === 'en' ? english(item) : String(item ?? ''))
	}
	return language === 'en' ? english(source) : source
}
