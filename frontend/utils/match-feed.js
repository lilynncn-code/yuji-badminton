import { ref } from 'vue'
import { fetchMatches, historicalMatches, readMatchCache } from './match-api'

// Each page keeps its last confirmed content and invalidates reads when it leaves.
export function useMatchFeed(kind = 'events') {
    const initial = readMatchCache(kind) || historicalMatches()
    const data = ref(initial), loading = ref(false), error = ref('')
    let generation = 0
    async function load() {
        const read = ++generation
        const current = () => read === generation
        // Another page may have confirmed a deletion or a newer score meanwhile.
        const saved = readMatchCache(kind)
        const stamp = value => Date.parse(value?.sync?.last_attempt_at || value?.sync?.latest_updated_at || '') || 0
        if (saved && stamp(saved) >= stamp(data.value)) data.value = saved
        loading.value = true; error.value = ''
        try {
            const result = await fetchMatches(kind, { isCurrent: current })
            if (current()) data.value = result
        } catch (e) {
            if (!current() || e.stale) return
            error.value = e.message || '比赛读取失败'
            data.value = { ...data.value, fromCache: !data.value.historical }
        } finally { if (current()) loading.value = false }
    }
    function leave() { generation++; loading.value = false }
    return { data, loading, error, load, leave }
}
