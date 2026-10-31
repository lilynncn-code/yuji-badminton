export function openExternal(url) {
    if (!/^https:\/\//.test(url || '')) { uni.showToast({ title: '暂无来源地址', icon: 'none' }); return }
    // #ifdef H5
    window.open(url, '_blank', 'noopener,noreferrer')
    return
    // #endif
    // #ifdef APP-PLUS
    plus.runtime.openURL(url)
    return
    // #endif
    uni.setClipboardData({ data: url })
}
