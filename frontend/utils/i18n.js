import { getLanguage } from './store'
import { appLanguage, syncLanguage, translate } from './translate'
import pagesConfig from '../pages.json'

const zh = {
	tabBar: ['首页', 'AI训练', '找球友', '球圈', '我的'],
	pageTitle: {
		home: '羽迹 Track',
		coach: 'AI 智能私教',
		match: '积分匹配',
		feed: '球友圈',
		profile: '我的',
		settings: '设置'
	},
	profile: {
		title: '我的',
		editCover: '修改背景',
		following: '关注',
		followers: '粉丝',
		editProfile: '修改个人信息',
		trainingProfile: 'AI 训练画像',
		updatedAt: '更新至 2026-05-23',
		chatRequests: '聊天与请求',
		chatRequestsDesc: '查看申请、会话和已同意聊天',
		albumAvatar: '从相册选头像',
		libraryAvatar: '图片库头像',
		albumCover: '从相册选背景',
		libraryCover: '图片库背景',
		namePlaceholder: '昵称',
		cityPlaceholder: '所在城市',
		levelPlaceholder: '水平标签',
		clubPlaceholder: '俱乐部',
		bioPlaceholder: '个人简介',
		saveProfile: '保存资料',
		nameRequired: '昵称不能为空',
		saveToastPrefix: '昵称已改为',
		avatarFallback: '未选择图片，可使用图片库头像',
		coverFallback: '未选择图片，可使用图片库背景'
	},
	settings: {
		title: '设置',
		languageTitle: '语言',
		languageDesc: '切换后，页面、训练说明和操作提示会一起更新；选择会保留到下次打开',
		languageSaved: '语言已切换',
		sourceTitle: '内容来源',
		accountSettings: [
			{ label: '修改密码', desc: '用旧密码设置一个新密码', value: '去修改', url: '/pages/auth/change-password' }
		],
		settings: [
			{ label: '训练记录', desc: '查看已保存在账号中的训练与连续天数', value: '查看', url: '/pages/ai-coach/history' },
			{ label: '相册权限', desc: '发布帖子和头像编辑时使用系统相册', value: '按需调用' },
			{ label: '帖子编辑规则', desc: '自己发布的帖子 15 分钟内可修改', value: '已启用' },
			{ label: '图片库', desc: '可选用的羽毛球图片，使用时需要联网', value: '6 张' },
			{ label: '排名参考', desc: '球员榜单体验参考 Badminton4U', value: 'Badminton4U' }
		]
	},
	home: {
		searchPlaceholder: '搜索球星、国家、双打组合...',
		noPlayers: '没有找到相关球员',
		matchBrief: '赛况',
		matchBriefToast: '进入赛况',
		shortcuts: ['赛事签表', '球星排名', '智能器材库', '聊天中心'],
		soon: '即将开放',
		coachTitle: 'AI 私教',
		coachDesc: '学习动作要点、记录基础练习和训练视频；网页可按画面计数，手机相机仍在完善',
		recognition: '动作识别',
		trainingStreak: '连续训练',
		todayDiamonds: '今日钻石',
		taskLine: '今日任务：完成 3 个标准动作并保持识别率 90% 以上',
		routeLine: '学习路线：正手高远球 → 快速回中 → 网前准备',
		startTraining: '开始训练',
		chat: '聊天',
		open: '打开',
		nearbyCourts: '附近球场',
		view: '查看',
		chatMine: '今晚能练混双吗？',
		chatOther: '可以，先发时间',
		chatReady: '已建立聊天，可以直接发消息',
		chatRequests: '个聊天申请',
		chatRequestsDesc: '同意后会自动进入聊天窗口',
		noMessage: '还没有新消息',
		noMessageDesc: '找球友互相同意后，就能像微信一样聊天'
	},
	match: {
		title: '积分匹配',
		subtitle: '先申请，双方同意后才会进入聊天',
		message: '消息',
		yourPoints: '你的训练累计分',
		hero: '按训练累计分接近度推荐，仅供找球友参考，不代表竞技水平。点开看资料，双方同意后可聊天。',
		tabs: ['全部', '同城', '训练', '双打'],
		searchPlaceholder: '搜索球友、城市或打法',
		chatRule: '聊天需双方同意，已建立的会话会像微信一样直接出现在聊天页',
		nearbyCourts: '附近球场',
		view: '查看',
		chat: '聊天',
		requestPractice: '发起约练申请',
		acceptedChat: '同意后开始聊天',
		points: '积分',
		pointsGap: '积分差',
		pointsClose: '积分接近',
		goChat: '去聊天',
		acceptChat: '同意聊天',
		checkProgress: '查看进度',
		reapply: '重新申请',
		applyChat: '申请聊天',
		noMessage: '暂无新消息',
		noMessageDesc: '向球友发起申请，对方同意后就能聊天'
	},
	feed: {
		tabs: ['球友圈', '最新', '诊所'],
		publish: '发布',
		edited: '已编辑',
		edit: '编辑',
		sourceNote: '信息更新至 2026-05-23，来源：BWF 官方赛事页、BWF 世界排名入口与公开图片库。',
		reward: '悬赏',
		editPost: '编辑帖子',
		publishPost: '发布帖子',
		titlePlaceholder: '标题',
		contentPlaceholder: '分享训练、约球、器材或赛况想法...',
		album: '从相册选图',
		library: '图片库',
		editWindow: '帖子发布后 15 分钟内可编辑，当前剩余',
		minutes: '分钟。',
		save: '保存修改',
		submit: '发布',
		fillRequired: '请填写标题和内容',
		editExpired: '已超过 15 分钟编辑时间',
		saved: '已保存',
		published: '已发布',
		tooLate: '超过 15 分钟，不能再编辑',
		albumFallback: '未选择图片，可使用内置图片库'
	},
	coach: {
		title: 'AI 智能私教',
		streak: '连续训练天数',
		diamonds: '钻石',
		levelLeft: '下个学习目标还差',
		points: '积分',
		weeklyShots: '本周击球',
		aiCheckIn: '近七天训练天数',
		todayPlan: '今日训练计划',
		todayPlanSub: '热身、两组基础动作与放松 · 可暂停接着练',
		start: '开始',
		planBasket: '学习计划篮',
		allPlans: '全部训练计划',
		planDesc: '每个计划有 10 个阶段，每阶段 10 个部分，每部分 4 道题。',
		bigPlans: '大计划',
		completed: '已完成',
		wins: '连胜',
		specialTask: '每日特别任务',
		done: '已完成 · 做完后火力点亮',
		aiFeedback: 'AI 反馈',
		finishFeedback: '完成并生成反馈',
		startLesson: '开始这节课',
		history: '训练记录',
		report: '查看报告'
	}
}

const en = {
	tabBar: ['Home', 'AI Coach', 'Players', 'Circle', 'Me'],
	pageTitle: {
		home: 'Track',
		coach: 'AI Coach',
		match: 'Point Match',
		feed: 'Badminton Circle',
		profile: 'Me',
		settings: 'Settings'
	},
	profile: {
		title: 'Me',
		editCover: 'Change cover',
		following: 'Following',
		followers: 'Followers',
		editProfile: 'Edit profile',
		trainingProfile: 'AI Training Profile',
		updatedAt: 'Updated May 23, 2026',
		chatRequests: 'Chats and Requests',
		chatRequestsDesc: 'View requests, conversations, and approved chats',
		albumAvatar: 'Album avatar',
		libraryAvatar: 'Library avatar',
		albumCover: 'Album cover',
		libraryCover: 'Library cover',
		namePlaceholder: 'Name',
		cityPlaceholder: 'City',
		levelPlaceholder: 'Level tag',
		clubPlaceholder: 'Club',
		bioPlaceholder: 'Bio',
		saveProfile: 'Save profile',
		nameRequired: 'Name is required',
		saveToastPrefix: 'Name updated to',
		avatarFallback: 'No image selected. You can use the avatar library.',
		coverFallback: 'No image selected. You can use the cover library.'
	},
	settings: {
		title: 'Settings',
		languageTitle: 'Language',
		languageDesc: 'Pages, practice instructions and prompts follow your language choice. Your choice is saved for next launch.',
		languageSaved: 'Language updated',
		sourceTitle: 'Content Sources',
		accountSettings: [
			{ label: 'Change password', desc: 'Use your old password to set a new one', value: 'Open', url: '/pages/auth/change-password' }
		],
		settings: [
			{ label: 'Training records', desc: 'View your saved training and practice streak', value: 'Open', url: '/pages/ai-coach/history' },
			{ label: 'Photo access', desc: 'Used only when posting or editing your avatar', value: 'On demand' },
			{ label: 'Post editing', desc: 'Your own posts can be edited within 15 minutes', value: 'Enabled' },
			{ label: 'Image library', desc: 'Choose badminton photos; internet access is needed', value: '6 images' },
			{ label: 'Ranking reference', desc: 'Player ranking experience references Badminton4U', value: 'Badminton4U' }
		]
	},
	home: {
		searchPlaceholder: 'Search players, countries, doubles pairs...',
		noPlayers: 'No matching players',
		matchBrief: 'Details',
		matchBriefToast: 'Opening match details',
		shortcuts: ['Draws', 'Rankings', 'Gear Library', 'Chat Center'],
		soon: 'Coming soon',
		coachTitle: 'AI Coach',
		coachDesc: 'Learn practice tips and save practice counts and videos. The web version can count movement; phone camera support is still being improved.',
		recognition: 'Recognition',
		trainingStreak: 'Train streak',
		todayDiamonds: 'Today diamonds',
		taskLine: 'Today: complete 3 standard moves and keep recognition above 90%',
		routeLine: 'Path: forehand clear -> fast recovery -> net readiness',
		startTraining: 'Start training',
		chat: 'Chat',
		open: 'Open',
		nearbyCourts: 'Nearby courts',
		view: 'View',
		chatMine: 'Can we practice mixed doubles tonight?',
		chatOther: 'Sure, send the time first',
		chatReady: 'Chat is ready. You can message directly.',
		chatRequests: 'chat requests',
		chatRequestsDesc: 'Accept to enter the chat',
		noMessage: 'No new messages',
		noMessageDesc: 'Mutual approval with a player unlocks WeChat-style chat.'
	},
	match: {
		title: 'Point Match',
		subtitle: 'Apply first. Chat opens only after both sides agree.',
		message: 'Messages',
		yourPoints: 'Your accumulated training points',
		hero: 'Recommends nearby players by point distance. Open profiles, apply, or enter approved chats.',
		tabs: ['All', 'Local', 'Training', 'Doubles'],
		searchPlaceholder: 'Search players, city, or style',
		chatRule: 'Chat requires mutual approval. Approved conversations appear in the chat page.',
		nearbyCourts: 'Nearby courts',
		view: 'View',
		chat: 'Chat',
		requestPractice: 'Send practice request',
		acceptedChat: 'Start after approval',
		points: 'pts',
		pointsGap: 'Gap',
		pointsClose: 'Close points',
		goChat: 'Chat',
		acceptChat: 'Accept',
		checkProgress: 'Pending',
		reapply: 'Apply again',
		applyChat: 'Apply',
		noMessage: 'No new messages',
		noMessageDesc: 'Send a request. Chat opens after approval.'
	},
	feed: {
		tabs: ['Circle', 'Latest', 'Clinic'],
		publish: 'Post',
		edited: 'Edited',
		edit: 'Edit',
		sourceNote: 'Updated May 23, 2026. Sources: BWF tournament pages, BWF rankings, and public image libraries.',
		reward: 'Reward',
		editPost: 'Edit post',
		publishPost: 'New post',
		titlePlaceholder: 'Title',
		contentPlaceholder: 'Share training, games, gear, or match thoughts...',
		album: 'Album',
		library: 'Library',
		editWindow: 'Posts can be edited for 15 minutes. Remaining',
		minutes: 'minutes.',
		save: 'Save',
		submit: 'Post',
		fillRequired: 'Please enter a title and content',
		editExpired: 'Edit time has expired',
		saved: 'Saved',
		published: 'Posted',
		tooLate: 'Past 15 minutes. Editing is closed.',
		albumFallback: 'No image selected. You can use the built-in library.'
	},
	coach: {
		title: 'AI Coach',
		streak: 'Streak',
		diamonds: 'Diamonds',
		levelLeft: 'Next learning goal',
		points: 'points',
		weeklyShots: 'Weekly shots',
		aiCheckIn: 'Training days this week',
		todayPlan: 'Today training plan',
		todayPlanSub: 'Warm up, two basic drills and cool down · pause and resume',
		start: 'Start',
		planBasket: 'Plan basket',
		allPlans: 'All training plans',
		planDesc: 'Each plan has 10 stages, 10 parts per stage, and 4 questions per part.',
		bigPlans: 'Plans',
		completed: 'Completed',
		wins: 'Streak',
		specialTask: 'Daily special task',
		done: 'done · flame lights up after completion',
		aiFeedback: 'AI Feedback',
		finishFeedback: 'Finish and create feedback',
		startLesson: 'Start lesson',
		history: 'Training history',
		report: 'Report'
	}
}

const dictionaries = { 'zh-Hans': zh, en }

export function getAppLanguage() {
	return getLanguage() === 'en' ? 'en' : 'zh-Hans'
}

export function getCopy(namespace, language = getAppLanguage()) {
	appLanguage.value
	return dictionaries[language]?.[namespace] || dictionaries['zh-Hans'][namespace] || {}
}

export function applyAppLanguage(language = getAppLanguage()) {
	syncLanguage(language)
	const dict = dictionaries[language] || dictionaries['zh-Hans']
	if (typeof uni === 'undefined') return
	uni.setLocale?.(language === 'en' ? 'en' : 'zh-Hans')
	dict.tabBar.forEach((text, index) => {
		uni.setTabBarItem?.({ index, text })
	})
}

export function refreshPageLanguage() {
	applyAppLanguage()
	const pages = typeof getCurrentPages === 'function' ? getCurrentPages() : []
	const route = pages[pages.length - 1]?.route
	const page = pagesConfig.pages.find(item => item.path === route)
	if (page?.style?.navigationBarTitleText) uni.setNavigationBarTitle({ title: translate(page.style.navigationBarTitleText) })
}

let installed = false
export function installLanguage(app) {
	app.config.globalProperties.$tr = translate
	app.mixin({ onShow() { refreshPageLanguage() }, onReady() { refreshPageLanguage() } })
	if (installed || typeof uni === 'undefined') return
	installed = true
	syncLanguage(getAppLanguage())
	uni.$on?.('track-language-changed', () => refreshPageLanguage())
	for (const name of ['showToast', 'showLoading', 'showModal', 'showActionSheet', 'setNavigationBarTitle']) {
		uni.addInterceptor(name, { invoke(options) {
			for (const key of ['title', 'content', 'placeholderText', 'confirmText', 'cancelText']) {
				if (typeof options[key] === 'string') options[key] = translate(options[key])
			}
			if (options.itemList) options.itemList = options.itemList.map(item => translate(item))
			if (name === 'showModal') {
				options.confirmText ||= translate('确定')
				options.cancelText ||= translate('取消')
			}
		} })
	}
}

export function setPageTitle(pageKey, language = getAppLanguage()) {
	const title = dictionaries[language]?.pageTitle?.[pageKey] || dictionaries['zh-Hans'].pageTitle[pageKey]
	if (title && typeof uni !== 'undefined') {
		uni.setNavigationBarTitle({ title })
	}
}
