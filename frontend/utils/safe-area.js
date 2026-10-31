export function getTopSafeAreaHeight() {
	const systemInfo = uni.getSystemInfoSync?.() || {}
	const heights = [
		systemInfo.statusBarHeight,
		systemInfo.safeAreaInsets?.top,
		systemInfo.safeArea?.top
	]
		.map((height) => Number(height || 0))
		.filter((height) => Number.isFinite(height) && height > 0)

	return heights.length ? Math.max(...heights) : 0
}
