<template>
	<view class="page">
		<text class="title">{{ $tr("隐私政策") }}</text>
		<text class="updated">{{ $tr("更新时间：2026年10月17日") }}</text>
		<view class="section" v-for="item in sections" :key="item.title">
			<text class="section-title">{{ $tr(item.title) }}</text>
			<text class="section-text">{{ $tr(item.text) }}</text>
		</view>
	</view>
</template>

<script setup>
const sections = [
	{
		title: '一、我们收集的信息',
		text: '为提供登录、个人资料、发帖、聊天、训练识别等服务，我们可能收集你主动填写的账号信息、昵称、头像、城市、训练记录、发布内容和聊天内容。'
	},
	{
		title: '二、权限使用说明',
		text: '网络权限用于连接服务；相机用于你主动开始的训练，动作计数在本设备计算。训练录像默认关闭，只有你打开保存录像或主动附上视频，才会上传视频。相册用于你选择头像、背景、动态及训练视频；麦克风用于你主动录制聊天语音，训练录像不录声音；定位用于你主动查找附近球馆。你可以拒绝这些权限，相关功能将无法使用，其他功能不受影响。离开训练页会停止相机并丢弃未保存录像，离开聊天页会取消正在录制的内容；已录好但发送失败的语音按账号和会话保留在本机，供试听、重试或放弃。空间不足时临时录音可能失效。'
	},
	{
		title: '三、信息使用方式',
		text: '我们会将信息用于账号识别、内容展示、训练记录、消息收发、问题处理和安全保护，不会将你的个人信息用于与好羽服务无关的用途。'
	},
	{
		title: '四、信息保存和保护',
		text: '账号资料、动态、训练结果和聊天内容保存在应用服务中。头像、背景，以及动态和技术诊所选择上传的图片和视频，可由获得文件地址的人查看；请选择适合公开的内容。新选择的聊天图片仅会话双方登录后可读取；旧版已经上传为公开地址的聊天图片不会自动变为私有，仍需后续清理。仅供本人重看的训练录像请放在训练记录。聊天语音只供该会话双方读取。训练录像单独保存，仅本人登录后可重看，可以在训练记录中删除视频，次数和时长仍保留。换账号时会按账号区分学习和草稿等记录。退出不会自动删除已发布的内容。提交举报时会保存原因和当时的文字，供获准的处理人员核查；你可在设置查看自己的处理结果。移除动态或留言后不再在应用中展示，旧公开文件的已知地址不因此自动失效。账号注销会清除相关举报中保留的本人文字和内部身份记录。'
	},
	{
		title: '五、信息共享',
		text: '你请求短信验证码时，手机号和验证码用途会交给阿里云短信服务处理；查找附近球馆时，位置或手动填写的城市、搜索词会交给高德地图处理；启用智能训练建议并主动请求时，训练名称、次数、时长和反馈文字会交给豆包服务处理。当前训练记录不需要上传画面，球友语音不会交给自动回复服务，也不会冒充其他球友回复。公开图片和官方内容链接由相应网站提供，打开链接后适用对方规则。'
	},
	{
		title: '六、你的权利',
		text: '你可以在应用内查看和修改资料、更换手机号、删除本人动态和留言、删除训练视频。设置中的“注销账号与删除资料”会核对密码及手机验证码，然后永久删除账号和相关资料，包括双方聊天会话、训练记录、发布内容和你发起的球局。具体范围在注销页逐项列出，注销后无法恢复，其他人已经另行保存的副本无法收回。文件清理失败时会保留待清理记录以便继续处理。当前尚未提供人工客服入口。'
	},
	{
		title: '七、政策更新',
		text: '如隐私政策发生变化，我们会在应用内或发布平台要求的位置展示更新后的内容。'
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
