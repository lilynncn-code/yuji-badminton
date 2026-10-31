<script>
import { getTheme, isOnboardingComplete } from './utils/store'
import { isLoggedIn } from './utils/auth'
import { applyAppLanguage } from './utils/i18n'

export default {
	onLaunch(options) {
		getTheme()
		applyAppLanguage()
		const launchPath = options?.path || ''
		const authPages = ['pages/auth/login', 'pages/auth/register', 'pages/auth/forgot']
        const publicPages = [...authPages, 'pages/agreement/agreement', 'pages/privacy/privacy']
		if (!isLoggedIn() && !publicPages.includes(launchPath)) {
			setTimeout(() => {
				uni.redirectTo({ url: '/pages/auth/login' })
			}, 0)
			return
		}
		if (isLoggedIn() && authPages.includes(launchPath)) {
			setTimeout(() => {
				if (isOnboardingComplete()) {
					uni.switchTab({ url: '/pages/index/index' })
				} else {
					uni.redirectTo({ url: '/pages/onboarding/onboarding' })
				}
			}, 0)
			return
		}
		if (isLoggedIn() && isOnboardingComplete() && (!launchPath || launchPath === 'pages/onboarding/onboarding')) {
			setTimeout(() => {
				uni.switchTab({ url: '/pages/index/index' })
			}, 0)
		}
	},
	onShow() {
		getTheme()
		applyAppLanguage()
	}
}
</script>

<style lang="scss">
/* #ifdef H5 */
html[lang="en"] .uni-modal__bd {
	word-break: normal;
	overflow-wrap: break-word;
}
/* #endif */
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
	display: flex;
	align-items: center;
	justify-content: center;
	box-sizing: border-box;
	min-width: 0;
	min-height: 1.4em;
	margin: 0;
	padding: 8rpx 16rpx;
	border: 0;
	background: transparent;
	line-height: 1.25;
	text-align: center;
	white-space: normal;
	word-break: break-word;
	overflow: visible;
}

button::after {
	border: 0;
}

.click-feedback {
	opacity: 0.65;
	transform: scale(0.97);
	transition: all 0.1s ease;
}
</style>
