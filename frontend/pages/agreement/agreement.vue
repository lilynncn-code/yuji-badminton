<template>
	<view class="page">
		<text class="title">{{ $tr("用户协议") }}</text>
		<text class="updated">{{ $tr("更新时间：2026年6月30日") }}</text>
		<view class="section" v-for="item in sections" :key="item.title">
			<text class="section-title">{{ $tr(item.title) }}</text>
			<text class="section-text">{{ $tr(item.text) }}</text>
		</view>
	</view>
</template>

<script setup>
const sections = [
	{
		title: '一、服务说明',
		text: '好羽提供羽毛球训练、球友匹配、内容浏览、发帖、聊天等服务。你使用本应用，即表示你已阅读并同意本协议。'
	},
	{
		title: '二、账号使用',
		text: '请使用真实、有效的信息注册和使用账号。你需要妥善保管账号和密码，因你主动泄露或保管不当造成的损失，由你自行承担。'
	},
	{
		title: '三、内容规则',
		text: '你发布的头像、图片、文字、聊天内容应合法、友善，不得侵犯他人权益，不得发布违法、欺诈、骚扰、低俗或无关广告内容。'
	},
	{
		title: '四、功能权限',
		text: '训练识别需要使用相机；设置头像、背景、聊天图片和动态图片需要访问相册。相关权限仅在你使用对应功能时申请。'
	},
	{
		title: '五、服务调整',
		text: '我们可能根据产品需要调整、暂停或升级部分服务，并会尽量减少对正常使用的影响。'
	},
	{
		title: '六、联系我们',
		text: '如你对本协议或应用服务有疑问，请通过应用发布平台填写的客服邮箱或联系方式联系我们。'
	}
]
</script>

<style lang="scss" scoped>
.page { min-height: 100vh; padding: 44rpx 28rpx 64rpx; background: #121212; color: #FFFFFF; box-sizing: border-box; }
.title { display: block; color: #CCFF00; font-size: 44rpx; font-weight: 900; }
.updated { display: block; margin: 12rpx 0 30rpx; color: #8E8E93; font-size: 24rpx; }
.section { margin-bottom: 28rpx; padding-bottom: 28rpx; border-bottom: 1rpx solid #2C2C2E; }
.section:last-child { border-bottom: 0; }
.section-title { display: block; margin-bottom: 12rpx; font-size: 30rpx; font-weight: 900; }
.section-text { display: block; color: #D7D7DC; font-size: 26rpx; line-height: 1.75; }
</style>
