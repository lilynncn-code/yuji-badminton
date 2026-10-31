export function todayDate() { const date = new Date(); return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}` }
export function getDailyTournamentUpdate(tournament) {
    return { date: tournament?.date || '2026-05', title: '赛事资料', eventName: tournament?.name || 'BWF 赛事', eventDate: tournament?.date || '', source: 'BWF World Tour', sourceUrl: tournament?.source || 'https://bwfworldtour.bwfbadminton.com/calendar/', status: '历史资料，最新结果请查看官方来源', summary: '当前展示历史赛事，尚未自动获取最新结果' }
}
export function getDailyRankingUpdate() {
    return { date: '2026-05-23', title: '排名资料', source: 'BWF World Rankings', sourceUrl: 'https://bwfbadminton.com/rankings/', status: '历史资料', summary: '资料日期：2026-05-23，最新完整排名请查看官方来源' }
}
