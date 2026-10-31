<script>
import { getTheme, isOnboardingComplete } from './utils/store'

export default {
	onLaunch(options) {
		getTheme()
		console.log('Track App Launch')
		const launchPath = options?.path || ''
		if (isOnboardingComplete() && (!launchPath || launchPath === 'pages/onboarding/onboarding')) {
			setTimeout(() => {
				uni.switchTab({ url: '/pages/index/index' })
			}, 0)
		}
	},
	onShow() {
		getTheme()
	}
}
</script>

<style lang="scss">
page {
	min-height: 100%;
	background: #121212;
	color: #FFFFFF;
	font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Helvetica, Arial, sans-serif;
}

view,
text,
scroll-view,
swiper,
swiper-item,
image,
button,
input,
canvas {
	box-sizing: border-box;
}

button {
	margin: 0;
	padding: 0;
	border: 0;
	background: transparent;
	line-height: 1;
}

button::after {
	border: 0;
}

.click-feedback {
	opacity: 0.65;
	transform: scale(0.97);
	transition: all 0.1s ease;
}

html.track-theme-light,
body.track-theme-light,
html.track-theme-light page,
body.track-theme-light page,
body.track-theme-light .page {
	background: #FFFFFF !important;
	color: #111111 !important;
}

body.track-theme-light view,
body.track-theme-light uni-view,
body.track-theme-light scroll-view,
body.track-theme-light uni-scroll-view,
body.track-theme-light swiper,
body.track-theme-light uni-swiper,
body.track-theme-light swiper-item,
body.track-theme-light uni-swiper-item {
	background-color: #FFFFFF !important;
	border-color: #D6E0D4 !important;
	color: #111111 !important;
}

body.track-theme-light text,
body.track-theme-light input,
body.track-theme-light textarea,
body.track-theme-light uni-input,
body.track-theme-light uni-textarea {
	color: #111111 !important;
}

body.track-theme-light button,
body.track-theme-light uni-button,
body.track-theme-light .primary-btn,
body.track-theme-light .save-btn,
body.track-theme-light .publish-btn,
body.track-theme-light .submit-btn,
body.track-theme-light .refresh-btn,
body.track-theme-light .follow-btn,
body.track-theme-light .daily-btn,
body.track-theme-light .challenge-btn,
body.track-theme-light .start-btn,
body.track-theme-light .allow-btn,
body.track-theme-light .camera-permission,
body.track-theme-light .active,
body.track-theme-light .current,
body.track-theme-light .done {
	background: #1F6B3A !important;
	border-color: #1F6B3A !important;
	color: #FFFFFF !important;
}

body.track-theme-light .chip,
body.track-theme-light .tag,
body.track-theme-light .rank,
body.track-theme-light .value,
body.track-theme-light .search-icon,
body.track-theme-light .favorite,
body.track-theme-light .trend,
body.track-theme-light .time,
body.track-theme-light .live,
body.track-theme-light .brand,
body.track-theme-light .title,
body.track-theme-light .eyebrow,
body.track-theme-light .map-value,
body.track-theme-light .record-score,
body.track-theme-light .feedback-title,
body.track-theme-light .result-title,
body.track-theme-light .menu-icon {
	background: #FFFFFF !important;
	border-color: rgba(31, 107, 58, .36) !important;
	color: #1F6B3A !important;
}

body.track-theme-light .progress-fill,
body.track-theme-light .fill,
body.track-theme-light .scan-line,
body.track-theme-light .limb,
body.track-theme-light .joint,
body.track-theme-light .segment-line {
	background: #1F6B3A !important;
	box-shadow: 0 0 16rpx rgba(31, 107, 58, .28) !important;
}

body.track-theme-light .hero::after,
body.track-theme-light .shade {
	background: linear-gradient(180deg, rgba(255,255,255,.08), rgba(255,255,255,.72) 48%, #FFFFFF 100%) !important;
}

body.track-theme-light .mask {
	background: rgba(17, 17, 17, .28) !important;
}

body.track-theme-light .path-card {
	background: linear-gradient(180deg, #202122 0%, #151616 100%) !important;
	background-color: #151616 !important;
	border-color: rgba(204, 255, 0, .18) !important;
	color: #FFFFFF !important;
}

body.track-theme-light .path-card .stage-main,
body.track-theme-light .path-card .node-path,
body.track-theme-light .path-card .unit,
body.track-theme-light .path-card .island,
body.track-theme-light .path-card .mini-unit,
body.track-theme-light .path-card .shuttle-body {
	background: transparent !important;
	background-color: transparent !important;
}

body.track-theme-light .path-card .practice-route-bar {
	background: rgba(255, 255, 255, .05) !important;
	background-color: rgba(255, 255, 255, .05) !important;
	border-color: rgba(255, 255, 255, .08) !important;
}

body.track-theme-light .path-card .route-metric {
	background: rgba(255, 255, 255, .04) !important;
	background-color: rgba(255, 255, 255, .04) !important;
}

body.track-theme-light .path-card .route-metric.highlight {
	background: rgba(204, 255, 0, .12) !important;
	background-color: rgba(204, 255, 0, .12) !important;
}

body.track-theme-light .path-card .stage-card {
	background: linear-gradient(135deg, rgba(204, 255, 0, .24), rgba(34, 34, 34, .98)) !important;
	background-color: #222222 !important;
	border-color: rgba(204, 255, 0, .2) !important;
	color: #FFFFFF !important;
}

body.track-theme-light .path-card .stage-menu {
	background: rgba(204, 255, 0, .08) !important;
	background-color: rgba(204, 255, 0, .08) !important;
	border-color: rgba(204, 255, 0, .2) !important;
}

body.track-theme-light .path-card .lesson-node {
	background: #2C2C2E !important;
	background-color: #2C2C2E !important;
	border-color: rgba(255, 255, 255, .08) !important;
	color: #8E8E93 !important;
	box-shadow: 0 12rpx 0 #151515 !important;
}

body.track-theme-light .path-card .lesson-node.done {
	background: rgba(204, 255, 0, .14) !important;
	background-color: rgba(204, 255, 0, .14) !important;
	border-color: rgba(204, 255, 0, .32) !important;
	color: #CCFF00 !important;
	box-shadow: 0 12rpx 0 rgba(108, 136, 0, .42) !important;
}

body.track-theme-light .path-card .lesson-node.current {
	background: #CCFF00 !important;
	background-color: #CCFF00 !important;
	border-color: #1C1C1E !important;
	color: #121212 !important;
	box-shadow: 0 12rpx 0 #7A9900 !important;
}

body.track-theme-light .path-card .node-face {
	background: rgba(255, 255, 255, .08) !important;
	background-color: rgba(255, 255, 255, .08) !important;
}

body.track-theme-light .path-card .lesson-node.current .node-face {
	background: rgba(18, 18, 18, .12) !important;
	background-color: rgba(18, 18, 18, .12) !important;
}

body.track-theme-light .path-card text {
	color: inherit !important;
}

body.track-theme-light .path-card .stage-kicker,
body.track-theme-light .path-card .route-metric.highlight .route-value,
body.track-theme-light .path-card .lesson-node.current .node-title {
	color: #CCFF00 !important;
}

body.track-theme-light .path-card .stage-copy {
	color: #D8D8D8 !important;
}

body.track-theme-light .path-card .route-label,
body.track-theme-light .path-card .node-title {
	color: #8E8E93 !important;
}

body.track-theme-light .path-card .shuttle-feather,
body.track-theme-light .path-card .shuttle-cork,
body.track-theme-light .path-card .shuttle-shadow,
body.track-theme-light .path-card .guide-racket {
	border-color: rgba(204, 255, 0, .55) !important;
}

body.track-theme-light .path-card .shuttle-guide {
	background: transparent !important;
	background-color: transparent !important;
}

body.track-theme-light .path-card .shuttle-feather {
	background: linear-gradient(180deg, rgba(255, 255, 255, .9), rgba(190, 196, 198, .65)) !important;
	background-color: rgba(255, 255, 255, .9) !important;
}

body.track-theme-light .path-card .shuttle-cork {
	background: linear-gradient(180deg, #F8F1D5, #C2A26E) !important;
	background-color: #C2A26E !important;
}

body.track-theme-light .path-card .shuttle-shadow {
	background: rgba(0, 0, 0, .28) !important;
	background-color: rgba(0, 0, 0, .28) !important;
}

body.track-theme-light .path-card .guide-racket {
	background: rgba(204, 255, 0, .55) !important;
	background-color: rgba(204, 255, 0, .55) !important;
}
</style>
