export const sources = [
	{
		title: 'Malaysia Masters 2026',
		url: 'https://bwfworldtour.bwfbadminton.com/tournament/5229/perodua-malaysia-masters-2026/overview',
		note: 'BWF 世界巡回赛赛事页，比赛日期为 2026年5月19日至24日。'
	},
	{
		title: '新华社 2026 马来西亚大师赛图片',
		url: 'https://english.news.cn/20260524/f52467c86d0e4056a768a46335f199bc/c.html',
		note: '2026年5月24日马来西亚大师赛决赛的现场图片与报道。'
	},
	{
		title: 'BadmintonPlanet 马来西亚大师赛回顾',
		url: 'https://www.badmintonplanet.com/badminton-news/ratchanok-intanon-li-shifeng-champions.html',
		note: '拉差诺·因达农和李诗沣夺冠的决赛回顾。'
	},
	{
		title: 'Badminton4U',
		url: 'https://play.google.com/store/apps/details?id=com.bwf.mobile.app',
		note: 'BWF 官方应用，可查看职业球员、排名与最新赛事。'
	},
	{
		title: 'BWF 世界排名',
		url: 'https://bwfbadminton.com/rankings/',
		note: 'BWF 官方排名入口，可查看单打与双打组合排名。'
	},
	{
		title: 'BWF TV',
		url: 'https://www.youtube.com/@bwftv',
		note: 'BWF 官方视频频道，提供直播、全场回放和精彩集锦。'
	},
	{
		title: 'Unsplash 羽毛球图片',
		url: 'https://unsplash.com/s/photos/badminton',
		note: '羽毛球场地和训练图片的公开来源。'
	}
]

export const dailyUpdate = {
	ranking: {
		title: '球星排名每日更新',
		cadence: '每天 08:00 自动检查',
		lastChecked: '2026-05-26',
		sourceName: 'BWF World Rankings / Badminton4U',
		sourceUrl: 'https://bwfbadminton.com/rankings/',
		note: '上架接入后端定时任务后，可每天拉取 BWF 官方排名并覆盖本地榜单。'
	},
	tournament: {
		title: '赛事与赛程每日更新',
		cadence: '每天 08:15 自动检查',
		lastChecked: '2026-05-26',
		sourceName: 'BWF World Tour / BWF TV',
		sourceUrl: 'https://bwfworldtour.bwfbadminton.com/calendar/',
		videoSourceUrl: 'https://www.youtube.com/@bwftv',
		note: '赛事结果、签表、比赛图片和全场回放入口每天跟随官方来源检查。'
	}
}

export const officialVideoHub = {
	title: 'BWF TV 官方全场回放',
	url: 'https://www.youtube.com/@bwftv',
	note: 'BWF TV 会在版权允许地区提供直播、全场回放或精彩集锦；如果某场暂未发布，应用会打开官方搜索结果。'
}

export const matchPhotos = {
	'li-shifeng-malaysia-2026': {
		url: 'https://english.news.cn/20260524/f52467c86d0e4056a768a46335f199bc/LC6areH6WbmncP1u.jpg',
		source: 'Xinhua: Li Shifeng during Malaysia Masters 2026 men singles final'
	},
	'ratchanok-malaysia-2026': {
		url: 'https://english.news.cn/20260524/f52467c86d0e4056a768a46335f199bc/kCTdB2jjlAz6bu3X.jpg',
		source: 'Xinhua: Ratchanok Intanon during Malaysia Masters 2026 women singles final'
	},
	'goh-izzuddin-malaysia-2026': {
		url: 'https://english.news.cn/20260524/f52467c86d0e4056a768a46335f199bc/8FaVnOvKRVLxcLdr.jpg',
		source: 'Xinhua: Li Shifeng and Panitchaphon awarding ceremony photo, used as tournament finals coverage image'
	},
	'chen-luo-malaysia-2026': {
		url: 'https://english.news.cn/20260524/f52467c86d0e4056a768a46335f199bc/dWsCX3O5vRIWzj1P.jpg',
		source: 'Xinhua: Chen Fanshutian / Luo Xumin during Malaysia Masters 2026 women doubles final'
	},
	'gao-wei-malaysia-2026': {
		url: 'https://english.news.cn/20260524/f52467c86d0e4056a768a46335f199bc/Tmi9Gs6wOJTfceJs.jpg',
		source: 'Xinhua: Gao Jiaxuan / Wei Yaxin Malaysia Masters 2026 mixed doubles podium photo'
	}
}

export const imageLibrary = [
	{
		id: 'lib-1',
		title: '训练场灯光',
		url: 'https://images.unsplash.com/photo-1626224583764-f87db24ac4ea?auto=format&fit=crop&w=900&q=80'
	},
	{
		id: 'lib-2',
		title: '球拍特写',
		url: 'https://images.unsplash.com/photo-1599474924187-334a4ae5bd3c?auto=format&fit=crop&w=900&q=80'
	},
	{
		id: 'lib-3',
		title: '室内球馆',
		url: 'https://images.unsplash.com/photo-1613918431703-aa50889e3be8?auto=format&fit=crop&w=900&q=80'
	},
	{
		id: 'lib-4',
		title: '比赛瞬间',
		url: 'https://images.unsplash.com/photo-1617696618050-b0fef0c666af?auto=format&fit=crop&w=900&q=80'
	},
	{
		id: 'lib-5',
		title: '羽毛球装备',
		url: 'https://images.unsplash.com/photo-1622279457486-62dcc4a431d6?auto=format&fit=crop&w=900&q=80'
	},
	{
		id: 'lib-6',
		title: '热身拉伸',
		url: 'https://images.unsplash.com/photo-1518611012118-696072aa579a?auto=format&fit=crop&w=900&q=80'
	}
]

export const playerPhotos = {
	'石宇奇': {
		url: 'https://commons.wikimedia.org/wiki/Special:FilePath/Shi%20Yuqi%20-%20Indonesia%20Open%202018.jpg?width=600',
		source: 'Wikimedia Commons: Shi Yuqi - Indonesia Open 2018.jpg'
	},
	'昆拉武特': {
		url: 'https://commons.wikimedia.org/wiki/Special:FilePath/Kunlavut%20Vitidsarn%20Indonesia%20Masters%202025.jpg?width=600',
		source: 'Wikimedia Commons: Kunlavut Vitidsarn Indonesia Masters 2025.jpg'
	},
	'安东森': {
		url: 'https://dkjulgymkya8y.cloudfront.net/images/c863306f-5745-4937-987b-d1c3e7f66c2a.webp',
		source: 'Victor Sport: Anders Antonsen player page'
	},
	'克里斯托·波波夫': {
		url: 'https://equipe-france.s3.linked.fr/img/personne/badminton-christo-popov-1.jpg',
		source: 'Equipe France: badminton-christo-popov-1.jpg'
	},
	'乔纳坦': {
		url: 'https://commons.wikimedia.org/wiki/Special:FilePath/Jonatan%20Christie%20(INA)%202023.jpg?width=600',
		source: 'Wikimedia Commons: Jonatan Christie (INA) 2023.jpg'
	},
	'安洗莹': {
		url: 'https://commons.wikimedia.org/wiki/Special:FilePath/An%20Se-young.jpg?width=600',
		source: 'Wikimedia Commons: An Se-young.jpg'
	},
	'王祉怡': {
		url: 'https://commons.wikimedia.org/wiki/Special:FilePath/Wang%20Zhi%20Yi%20(CHN)%202023.jpg?width=600',
		source: 'Wikimedia Commons: Wang Zhi Yi (CHN) 2023.jpg'
	},
	'山口茜': {
		url: 'https://www.jsports.co.jp/bad/img/player/yamaguchi.jpg',
		source: 'J Sports: Akane Yamaguchi player profile'
	},
	'陈雨菲': {
		url: 'https://alishuttler.com/wp-content/uploads/2024/01/Chen-Yufei-Best-Badminton-Player-in-China-2025.png',
		source: 'AliShuttler: Chen Yufei profile photo'
	},
	'韩悦': {
		url: 'https://dsg-images.com/players/150x150/3195215.png',
		source: 'Global Sports Archive / DSG Images: Han Yue player profile'
	},
	'金元昊 / 徐承宰': {
		url: 'https://commons.wikimedia.org/wiki/Special:FilePath/Seo%20Seung-jae%20(KOR)%202024.jpg?width=600',
		source: 'Wikimedia Commons: Seo Seung-jae (KOR) 2024.jpg'
	},
	'谢定峰 / 苏伟译': {
		url: 'https://commons.wikimedia.org/wiki/Special:FilePath/Aaron%20Chia%20PMO2025.jpg?width=600',
		source: 'Wikimedia Commons: Aaron Chia PMO2025.jpg'
	},
	'阿尔菲安 / 阿迪安托': {
		url: 'https://dsg-images.com/players/150x150/7874600.png',
		source: 'Global Sports Archive / DSG Images: Fajar Alfian player profile'
	},
	'兰基雷迪 / 谢提': {
		url: 'https://commons.wikimedia.org/wiki/Special:FilePath/Satwiksairaj%20Rankireddy%20(IND)%202022.jpg?width=600',
		source: 'Wikimedia Commons: Satwiksairaj Rankireddy (IND) 2022.jpg'
	},
	'梁伟铿 / 王昶': {
		url: 'https://commons.wikimedia.org/wiki/Special:FilePath/Liang%20Weikeng%20(CHN)%202023.jpg?width=600',
		source: 'Wikimedia Commons: Liang Weikeng (CHN) 2023.jpg'
	},
	'刘圣书 / 谭宁': {
		url: 'https://img.olympics.com/images/image/private/t_s_w960/t_s_16_9_g_auto/f_auto/primary/qdelqlqhteuomjj6gbon',
		source: 'Olympics.com: Liu Shengshu / Tan Ning profile imagery'
	},
	'白荷娜 / 李绍希': {
		url: 'https://img.olympics.com/images/image/private/t_s_w960/t_s_16_9_g_auto/f_auto/primary/cv4oohggdoifjz4ncnca',
		source: 'Olympics.com: Baek Ha Na / Lee So Hee profile imagery'
	},
	'陈清晨 / 贾一凡': {
		url: 'https://commons.wikimedia.org/wiki/Special:FilePath/Chen%20Qingchen%20and%20Jia%20Yifan%20at%20the%202024%20Indonesia%20Open.jpg?width=600',
		source: 'Wikimedia Commons: Chen Qingchen and Jia Yifan'
	},
	'松山奈未 / 志田千阳': {
		url: 'https://img.olympics.com/images/image/private/t_s_w960/t_s_16_9_g_auto/f_auto/primary/dfq7mprte1rbsnlmjxcn',
		source: 'Olympics.com: Nami Matsuyama / Chiharu Shida profile imagery'
	},
	'江振邦 / 魏雅欣': {
		url: 'https://img.olympics.com/images/image/private/t_s_w960/t_s_16_9_g_auto/f_auto/primary/kjzjbn7v5wwcn1nxmlgn',
		source: 'Olympics.com: Jiang Zhenbang / Wei Yaxin profile imagery'
	},
	'冯彦哲 / 黄东萍': {
		url: 'https://commons.wikimedia.org/wiki/Special:FilePath/Huang%20Dongping%20and%20Feng%20Yanzhe%20PMO2025.jpg?width=600',
		source: 'Wikimedia Commons: Huang Dongping and Feng Yanzhe PMO2025.jpg'
	},
	'德差波 / 苏皮萨拉': {
		url: 'https://commons.wikimedia.org/wiki/Special:FilePath/Dechapol%20Puavaranukroh%20PMO2025.jpg?width=600',
		source: 'Wikimedia Commons: Dechapol Puavaranukroh PMO2025.jpg'
	},
	'渡边勇大 / 田口真彩': {
		url: 'https://commons.wikimedia.org/wiki/Special:FilePath/Yuta%20Watanabe%20at%20the%202024%20Indonesia%20Open.jpg?width=600',
		source: 'Wikimedia Commons: Yuta Watanabe at the 2024 Indonesia Open.jpg'
	}
}

export const defaultUser = {
	name: '李大羽',
	nickname: 'Track特约特工',
	bio: '顺义夜场固定搭子，喜欢双打轮转和赛后复盘。',
	city: '北京·顺义区',
	levelTag: '顺义第 12 俱乐部主力',
	avatar: imageLibrary[1].url,
	cover: imageLibrary[0].url,
	followers: 12860,
	following: 56,
	matchesCount: 24,
	club: '羽动空间 VIP 联盟',
	hand: '右手持拍'
}

export const equipmentCategories = ['球拍', '球鞋', '球线', '球', '球服', '球包', '护具', '其他']

export const equipmentFallbackImages = {
	hero: '/static/badminton/racket-card-1.svg',
	球拍: '/static/badminton/racket-card-1.svg',
	球鞋: '/static/badminton/racket-card-2.svg',
	球线: '/static/badminton/racket-card-3.svg',
	球: '/static/badminton/racket-card-3.svg',
	球服: '/static/badminton/racket-card-2.svg',
	球包: '/static/badminton/racket-card-1.svg',
	护具: '/static/badminton/racket-card-2.svg',
	其他: '/static/badminton/racket-card-3.svg'
}

export const badmintonEquipment = [
	{
		id: 'yonex-astrox-100zz',
		brand: '尤尼克斯',
		category: '球拍',
		name: 'ASTROX 100 ZZ',
		desc: '高端进攻型球拍，拍头借力明显，适合后场重杀和连续进攻。',
		price: '约 1,599 元',
		weight: '约 83 克（4U）',
		spec: '拍头偏重；建议中等偏高磅数',
		suitable: '有一定基础、以后场进攻为主的人',
		usage: '第一次使用先从较低磅数开始，训练前检查手腕和肩部状态。',
		image: 'https://cdn.shopify.com/s/files/1/0710/8457/2893/files/astrox100zz_kurenai.png?v=1769128443&width=1200'
	},
	{
		id: 'lining-halbertec-9000',
		brand: '李宁',
		category: '球拍',
		name: '锋影 HALBERTEC 9000',
		desc: '控制和连贯兼顾，适合拉吊、突击和多拍节奏变化。',
		price: '约 1,299 元',
		weight: '约 83 克（4U）',
		spec: '中等偏头重；适合多种打法',
		suitable: '想兼顾控制和进攻的进阶球友',
		usage: '先用多球练习熟悉出球节奏，再逐步增加对抗强度。',
		image: 'https://www.li-ning.se/cdn/shop/files/Li-Ning-Halbertec-9000.png?v=1770822152&width=1200'
	},
	{
		id: 'kumpoo-power-shot',
		brand: '熏风',
		category: '球拍',
		name: 'POWER SHOT NANO',
		desc: '轻量化进阶球拍，适合业余训练和双打快速衔接。',
		price: '约 399 元',
		weight: '约 78 克（5U）',
		spec: '轻量；挥拍速度快',
		suitable: '入门到进阶、偏好快速衔接的人',
		usage: '适合双打平抽挡和网前练习，注意不要为追求速度而过度发力。',
		image: 'https://product.statnano.com/resource/pr_brand/files/images/21/2/main_c4ca4238a0b923820dcc509a6f75849b920389.jpg'
	},
	{
		id: 'victor-a970ace',
		brand: '胜利',
		category: '球鞋',
		name: 'A970 ACE',
		desc: '稳定支撑型羽毛球鞋，适合启动急停和多方向防守。',
		price: '约 699 元',
		weight: '单只约 360 克（参考）',
		spec: '橡胶场地底；包裹和支撑优先',
		suitable: '需要频繁启动、急停的人',
		usage: '穿与比赛相同的袜子试鞋，脚趾前留出约一指宽空间。',
		image: 'https://dkjulgymkya8y.cloudfront.net/images/a3d4856d-b7f4-4fd1-b195-78da895180c4.webp'
	},
	{
		id: 'kawasaki-k063',
		brand: '川崎',
		category: '球鞋',
		name: 'K-063',
		desc: '训练型羽毛球鞋，强调包裹、缓震和入门友好。',
		price: '约 299 元',
		weight: '单只约 330 克（参考）',
		spec: '橡胶场地底；缓震取向',
		suitable: '刚开始固定打球、以训练为主的人',
		usage: '先在短时间训练中磨合，确认脚跟和脚趾没有摩擦再参加长时间对抗。',
		image: 'https://cdn.shopify.com/s/files/1/0770/0450/5420/files/I4.png?v=1769180817'
	},
	{
		id: 'yonex-bg-80',
		brand: '尤尼克斯',
		category: '球线',
		name: 'BG80',
		desc: '硬弹手感，击球反馈清晰，常用于进攻和控球兼顾的穿线方案。',
		price: '约 80 元 / 条',
		weight: '线径约 0.68 毫米',
		spec: '手感偏硬；耐用和弹性平衡',
		suitable: '喜欢清脆反馈、已有穿线习惯的人',
		usage: '穿线磅数先按球拍和个人习惯选择，换线后先打几次再调整。',
		image: 'https://www.yonex.com/media/catalog/product/b/g/bg80yx_004-1.png?quality=80&bg-color=248,248,248,0.75&fit=bounds&height=1200&width=1200&canvas=1200:1200'
	},
	{
		id: 'lining-no1',
		brand: '李宁',
		category: '球线',
		name: 'No.1',
		desc: '细线径高弹球线，出球速度快，适合追求清脆手感。',
		price: '约 75 元 / 条',
		weight: '线径约 0.65 毫米',
		spec: '弹性明显；手感偏脆',
		suitable: '喜欢快速出球、能接受较频繁换线的人',
		usage: '新手不要一开始就拉太高磅，先以不伤手为标准慢慢调整。',
		image: 'https://cdn.shopify.com/s/files/1/0975/5210/5818/files/AXJJ018-1.jpg?crop=center&height=1200&v=1765137648&width=1200'
	},
	{
		id: 'victor-master-ace',
		brand: '胜利',
		category: '球',
		name: 'MASTER ACE',
		desc: '比赛级羽毛球，飞行稳定，适合俱乐部训练和正式对抗。',
		price: '约 180 元 / 筒',
		weight: '每球约 5 克',
		spec: '鸭毛球；速度按当地温度选择',
		suitable: '俱乐部训练和正式对抗',
		usage: '开打前轻轻蒸球或润球，按当天温度和湿度调整保存方式。',
		image: 'https://dkjulgymkya8y.cloudfront.net/victor/en_us/product-1451_0_20230419163841.webp'
	},
	{
		id: 'kawasaki-shuttle',
		brand: '川崎',
		category: '球',
		name: 'TRAINING Shuttle',
		desc: '训练耐打型羽毛球，适合多球训练和日常约球。',
		price: '约 90 元 / 筒',
		weight: '每球约 5 克',
		spec: '耐打取向；适合反复练习',
		suitable: '日常约球和多球训练',
		usage: '把比赛球和训练球分开使用，能减少不必要的损耗。',
		image: equipmentFallbackImages.球
	},
	{
		id: 'yonex-shirt',
		brand: '尤尼克斯',
		category: '球服',
		name: 'Tournament Shirt',
		desc: '速干比赛服，适合高强度训练和赛事穿着。',
		price: '约 299 元',
		weight: '轻薄面料（以尺码实物为准）',
		spec: '速干；短袖比赛版型',
		suitable: '训练和比赛都需要快干衣物的人',
		usage: '按胸围和肩宽选码，运动后尽快清洗并晾干。',
		image: 'https://www.yonex.com/media/catalog/product/cache/7f7f3a1e1b7a3d5f6f9e8b6f1f2b0d68/1/0/10564_019_1.png'
	},
	{
		id: 'lining-bag',
		brand: '李宁',
		category: '球包',
		name: '六支装球包',
		desc: '可放多支球拍、球鞋和训练衣物，适合日常通勤到球馆。',
		price: '约 399 元',
		weight: '空包约 1.2 千克',
		spec: '六支容量；含独立鞋袋',
		suitable: '需要带多支球拍和训练用品的人',
		usage: '球鞋和湿衣物单独放置，装满后双肩背负更省力。',
		image: 'https://cdn.shopify.com/s/files/1/0881/8724/0787/files/Template-01_1024x1024.webp?v=1732647861'
	},
	{
		id: 'victor-grip',
		brand: '胜利',
		category: '护具',
		name: 'GR233 手胶',
		desc: '吸汗防滑手胶，适合夏季训练和高频换拍。',
		price: '约 25 元 / 条',
		weight: '每条约 25 克',
		spec: '吸汗；表面偏黏',
		suitable: '手汗较多或经常换手胶的人',
		usage: '缠绕时保持轻微拉力，重叠约一半宽度，末端固定牢。',
		image: 'https://dkjulgymkya8y.cloudfront.net/victor/en_us/product-2016122913020936279.webp'
	},
	{
		id: 'kumpoo-wrist',
		brand: '熏风',
		category: '护具',
		name: '运动护腕',
		desc: '吸汗护腕，减少汗水影响握拍，适合训练和比赛。',
		price: '约 35 元 / 对',
		weight: '每只约 20 克',
		spec: '弹力针织；吸汗取向',
		suitable: '手腕附近容易出汗的人',
		usage: '戴上后应能放入一根手指，过紧时及时取下休息。',
		image: equipmentFallbackImages.护具
	},
	{
		id: 'kawasaki-towel',
		brand: '川崎',
		category: '其他',
		name: '运动毛巾',
		desc: '球场训练配件，适合间歇擦汗和赛后整理装备。',
		price: '约 39 元',
		weight: '约 100 克',
		spec: '吸水快干；便于携带',
		suitable: '训练和比赛中需要随手擦汗的人',
		usage: '准备两条轮换使用，使用后及时清洗并完全晾干。',
		image: equipmentFallbackImages.其他
	}
]

export const latestNews = [
	{
		id: 1,
		title: 'Malaysia Masters 2026 正在吉隆坡进行',
		date: '2026-05-23',
		tag: 'BWF 世界巡回赛',
		summary: 'PERODUA Malaysia Masters 2026 于 2026-05-19 至 2026-05-24 举行，适合作为本周赛事签表与赛况内容来源。',
		image: imageLibrary[3].url
	},
	{
		id: 2,
		title: 'BWF 世界排名持续更新',
		date: '2026-05-23',
		tag: '世界排名',
		summary: '应用使用 BWF 官方排名入口作为球员积分、近期状态和榜单内容的参考源。',
		image: imageLibrary[0].url
	},
	{
		id: 3,
		title: '业余训练关注步伐覆盖和中前场衔接',
		date: '2026-05-23',
		tag: 'AI 教练',
		summary: 'AI 训练页聚焦杀球速度、米字步覆盖、多拍防守和网前反应等可量化指标。',
		image: imageLibrary[5].url
	}
]

export const rankingGroups = [
	{
		key: 'ms',
		label: '男单',
		players: [
			{ rank: 1, name: '石宇奇', country: '中国', points: 105967, trend: 'Week 18 第一', bio: '中国男单核心，进攻连贯和中后场突击能力突出。' },
			{ rank: 2, name: '昆拉武特', country: '泰国', points: 97179, trend: '稳定前三', bio: '节奏控制细腻，防守和多拍耐心是标志。' },
			{ rank: 3, name: '安东森', country: '丹麦', points: 93829, trend: '欧洲强势', bio: '欧洲男单代表，拉吊组织和反击质量稳定。' },
			{ rank: 4, name: '克里斯托·波波夫', country: '法国', points: 84705, trend: '上升明显', bio: '法国新生代主力，速度和冲击力提升明显。' },
			{ rank: 5, name: '乔纳坦', country: '印尼', points: 84174, trend: '经验优势', bio: '印尼男单名将，大赛经验和关键分处理成熟。' }
		]
	},
	{
		key: 'ws',
		label: '女单',
		players: [
			{ rank: 1, name: '安洗莹', country: '韩国', points: 117270, trend: 'Week 18 第一', bio: '韩国女单领军人物，攻防转换和落点控制极强。' },
			{ rank: 2, name: '王祉怡', country: '中国', points: 106012, trend: '连续深轮次', bio: '中国女单主力，近期深轮次表现稳定。' },
			{ rank: 3, name: '山口茜', country: '日本', points: 93764, trend: '防守韧性', bio: '日本女单名将，移动覆盖和防守韧性出众。' },
			{ rank: 4, name: '陈雨菲', country: '中国', points: 91035, trend: '回合质量高', bio: '中国奥运冠军，回合质量和控场能力扎实。' },
			{ rank: 5, name: '韩悦', country: '中国', points: 85050, trend: '稳步上升', bio: '中国女单主力之一，连续作战稳定性提升。' }
		]
	},
	{
		key: 'md',
		label: '男双',
		players: [
			{ rank: 1, name: '金元昊 / 徐承宰', country: '韩国', points: 123905, trend: 'Week 18 第一', bio: '韩国男双组合，前后场衔接和防反质量突出。' },
			{ rank: 2, name: '谢定峰 / 苏伟译', country: '马来西亚', points: 93150, trend: '主场关注', bio: '马来西亚王牌男双，防守反击和连续平抽挡强。' },
			{ rank: 3, name: '阿尔菲安 / 阿迪安托', country: '印尼', points: 86150, trend: '轮转成熟', bio: '印尼男双强档，轮转默契和网前压迫成熟。' },
			{ rank: 4, name: '兰基雷迪 / 谢提', country: '印度', points: 84518, trend: '进攻强势', bio: '印度男双代表，后场重杀和速度压迫鲜明。' },
			{ rank: 5, name: '梁伟铿 / 王昶', country: '中国', points: 83576, trend: '速度压迫', bio: '中国男双主力，连贯进攻和节奏变化很有威胁。' }
		]
	},
	{
		key: 'wd',
		label: '女双',
		players: [
			{ rank: 1, name: '刘圣书 / 谭宁', country: '中国', points: 108650, trend: '年轻冲击', bio: '中国女双新锐组合，连贯速度和后场下压能力突出。' },
			{ rank: 2, name: '白荷娜 / 李绍希', country: '韩国', points: 103240, trend: '稳定前三', bio: '韩国女双强档，防守弹性和多拍相持质量很高。' },
			{ rank: 3, name: '陈清晨 / 贾一凡', country: '中国', points: 97880, trend: '冠军底蕴', bio: '中国女双名将，网前控制和攻防转换经验丰富。' },
			{ rank: 4, name: '松山奈未 / 志田千阳', country: '日本', points: 92610, trend: '节奏细腻', bio: '日本女双代表，轮转细腻、防守反击质量稳定。' }
		]
	},
	{
		key: 'xd',
		label: '混双',
		players: [
			{ rank: 1, name: '江振邦 / 魏雅欣', country: '中国', points: 107920, trend: '冲击榜首', bio: '中国混双组合，男后女前衔接速度和中前场压迫突出。' },
			{ rank: 2, name: '冯彦哲 / 黄东萍', country: '中国', points: 103400, trend: '经验强档', bio: '中国混双强档，前三拍处理和关键分经验成熟。' },
			{ rank: 3, name: '德差波 / 苏皮萨拉', country: '泰国', points: 94320, trend: '配合上升', bio: '泰国混双组合，网前变化和防反衔接很有威胁。' },
			{ rank: 4, name: '渡边勇大 / 田口真彩', country: '日本', points: 88210, trend: '速度打法', bio: '日本混双组合，平抽挡速度和中前场反应快。' }
		]
	}
]

export const tournaments = [
	{
		id: 'malaysia-masters-2026',
		name: 'PERODUA Malaysia Masters 2026',
		date: '2026-05-19 至 2026-05-24',
		location: '吉隆坡 · Axiata Arena',
		status: '已完赛',
		image: matchPhotos['li-shifeng-malaysia-2026'].url,
		source: sources[0].url,
		sourceTitle: 'BWF World Tour / Xinhua / BadmintonPlanet',
		updatedAt: '2026-05-26',
		updateStatus: '今日已检查官方赛程、结果与视频入口',
		videoUrl: 'https://www.youtube.com/results?search_query=PERODUA+Malaysia+Masters+2026+Finals+BWF+TV+full+match',
		videoSource: 'BWF TV official YouTube search',
		summary: 'PERODUA Malaysia Masters 2026 于 2026-05-19 至 2026-05-24 在吉隆坡 Axiata Arena 举行。决赛日冠军包括李诗沣、拉差诺·因达农，以及马来西亚男双吴世飞 / 努伊祖丁。',
		matches: [
			{
				id: 1,
				round: '决赛',
				category: '男单',
				court: 'Axiata Arena',
				time: '2026-05-24',
				p1: '李诗沣',
				p2: '潘尼查蓬·提拉拉萨库尔',
				s1: '17 21 23',
				s2: '21 12 21',
				scoreText: '17-21, 21-12, 23-21',
				winner: '李诗沣',
				image: matchPhotos['li-shifeng-malaysia-2026'].url,
				imageSource: matchPhotos['li-shifeng-malaysia-2026'].source,
				videoUrl: 'https://www.youtube.com/results?search_query=Li+Shifeng+Panitchaphon+Teeraratsakul+Malaysia+Masters+2026+full+match+BWF+TV',
				videoTitle: '李诗沣 vs 潘尼查蓬 全场回放',
				report: '李诗沣在男单决赛中逆转潘尼查蓬·提拉拉萨库尔，卫冕 Malaysia Masters 男单冠军。'
			},
			{
				id: 2,
				round: '决赛',
				category: '女单',
				court: 'Axiata Arena',
				time: '2026-05-24',
				p1: '拉差诺·因达农',
				p2: '陈雨菲',
				s1: '21 21',
				s2: '18 12',
				scoreText: '21-18, 21-12',
				winner: '拉差诺·因达农',
				image: matchPhotos['ratchanok-malaysia-2026'].url,
				imageSource: matchPhotos['ratchanok-malaysia-2026'].source,
				videoUrl: 'https://www.youtube.com/results?search_query=Ratchanok+Intanon+Chen+Yufei+Malaysia+Masters+2026+full+match+BWF+TV',
				videoTitle: '拉差诺 vs 陈雨菲 全场回放',
				report: '拉差诺·因达农击败陈雨菲，拿到个人第三个 Malaysia Masters 女单冠军。'
			},
			{
				id: 3,
				round: '决赛',
				category: '男双',
				court: 'Axiata Arena',
				time: '2026-05-24',
				p1: '吴世飞 / 努伊祖丁',
				p2: '拉斯姆森 / 阿斯特鲁普',
				s1: '21 21',
				s2: '18 19',
				scoreText: '21-18, 21-19',
				winner: '吴世飞 / 努伊祖丁',
				image: matchPhotos['goh-izzuddin-malaysia-2026'].url,
				imageSource: matchPhotos['goh-izzuddin-malaysia-2026'].source,
				videoUrl: 'https://www.youtube.com/results?search_query=Goh+Sze+Fei+Nur+Izzuddin+Malaysia+Masters+2026+full+match+BWF+TV',
				videoTitle: '吴世飞 / 努伊祖丁 男双全场回放',
				report: '吴世飞 / 努伊祖丁在主场夺得男双冠军，帮助马来西亚队在决赛日收获本土冠军。'
			},
			{
				id: 4,
				round: '决赛',
				category: '女双',
				court: 'Axiata Arena',
				time: '2026-05-24',
				p1: '陈芳卉 / 田箐',
				p2: '罗徐敏 / 吴梦莹',
				s1: '21 21',
				s2: '14 18',
				scoreText: '21-14, 21-18',
				winner: '陈芳卉 / 田箐',
				image: matchPhotos['chen-luo-malaysia-2026'].url,
				imageSource: matchPhotos['chen-luo-malaysia-2026'].source,
				videoUrl: 'https://www.youtube.com/results?search_query=Chen+Fanshutian+Luo+Xumin+Malaysia+Masters+2026+full+match+BWF+TV',
				videoTitle: '陈芳卉 / 田箐 女双全场回放',
				report: '中国组合陈芳卉 / 田箐赢下女双决赛。'
			},
			{
				id: 5,
				round: '决赛',
				category: '混双',
				court: 'Axiata Arena',
				time: '2026-05-24',
				p1: '高家炫 / 魏雅欣',
				p2: '德扬 / 格洛丽亚',
				s1: '21 21',
				s2: '16 19',
				scoreText: '21-16, 21-19',
				winner: '高家炫 / 魏雅欣',
				image: matchPhotos['gao-wei-malaysia-2026'].url,
				imageSource: matchPhotos['gao-wei-malaysia-2026'].source,
				videoUrl: 'https://www.youtube.com/results?search_query=Gao+Jiaxuan+Wei+Yaxin+Malaysia+Masters+2026+full+match+BWF+TV',
				videoTitle: '高家炫 / 魏雅欣 混双全场回放',
				report: '中国组合高家炫 / 魏雅欣夺得混双冠军。'
			}
		]
	}
]

export const localPlayers = [
	{
		id: 'user-linxiaokou',
		name: '林小扣',
		city: '北京·顺义',
		level: '黄金 V',
		points: 86280,
		role: '双打封网',
		online: '刚刚在线',
		avatar: imageLibrary[0].url,
		tags: ['混双', '晚场', '节奏快'],
		bio: '顺义固定晚场球友，喜欢前三拍抢节奏，正在练反手接杀。'
	},
	{
		id: 'user-zhou',
		name: '老周',
		city: '北京·朝阳',
		level: '白银 IV',
		points: 80560,
		role: '男双后场',
		online: '12 分钟前在线',
		avatar: imageLibrary[4].url,
		tags: ['男双', '后场', '稳定'],
		bio: '打球不挑场，后场高远和连续防守比较稳。'
	},
	{
		id: 'user-ayu',
		name: '阿羽教练',
		city: '北京·海淀',
		level: '钻石 II',
		points: 92340,
		role: '训练搭档',
		online: '在线',
		avatar: imageLibrary[5].url,
		tags: ['训练', '复盘', '步伐'],
		bio: '可以帮看步伐和挥拍节奏，偏技术复盘型交流。'
	},
	{
		id: 'user-xiaoman',
		name: '小满',
		city: '北京·昌平',
		level: '黄金 III',
		points: 87120,
		role: '女双前场',
		online: '30 分钟前在线',
		avatar: imageLibrary[2].url,
		tags: ['女双', '前场', '接发'],
		bio: '周末女双和混双都可，想找能一起练接发轮转的球友。'
	},
	{
		id: 'user-azhe',
		name: '后场阿哲',
		city: '北京·顺义',
		level: '铂金 I',
		points: 89520,
		role: '后场进攻',
		online: '今天在线',
		avatar: imageLibrary[3].url,
		tags: ['杀球', '男双', '周末'],
		bio: '喜欢后场进攻，但也想找人一起补防守和中前场衔接。'
	}
]

export const courtGames = [
	{
		id: 1,
		timeStr: '今天 19:30 - 21:30',
		statusText: '缺 1 人',
		locationName: '后沙峪羽动空间·VIP 1 号场',
		tags: ['AI 平均：黄金 V', '混双友好', '新球 AA'],
		joinedAvatars: [defaultUser.avatar, imageLibrary[4].url, imageLibrary[5].url],
		maxPlayers: 4,
		currentPlayers: 3,
		costPerPerson: 58
	},
	{
		id: 2,
		timeStr: '周日 10:00 - 12:00',
		statusText: '缺 3 人',
		locationName: '空港体育公园·7 号训练场',
		tags: ['AI 平均：青铜 I', '新手局', '教练带热身'],
		joinedAvatars: [imageLibrary[2].url],
		maxPlayers: 4,
		currentPlayers: 1,
		costPerPerson: 36
	},
	{
		id: 3,
		timeStr: '周六 14:00 - 16:00',
		statusText: '缺 2 人',
		locationName: '顺义奥体中心·3 号轻奢片区',
		tags: ['AI 平均：白银 IV', '男双中级', '提供三只羽毛球'],
		joinedAvatars: [imageLibrary[1].url, imageLibrary[0].url],
		maxPlayers: 4,
		currentPlayers: 2,
		costPerPerson: 45
	}
]

export const defaultPosts = [
	{
		id: 'seed-1',
		authorName: 'Track分析员',
		authorAvatar: imageLibrary[4].url,
		title: '第三拍抢网为什么总慢半拍？',
		content: '复盘今天双打，主要问题是接发后第一步没有压到中前场。下次先练启动步，再练封网。',
		images: [imageLibrary[0].url],
		createdAt: '2026-05-23T08:30:00+08:00',
		updatedAt: '',
		likes: 311,
		comments: [
			{
				id: 'comment-seed-1',
				authorName: '小满',
				authorAvatar: imageLibrary[1].url,
				content: '我也是慢在第一步，今晚试试你这个启动练法。',
				createdAt: '2026-05-23T09:02:00+08:00'
			},
			{
				id: 'comment-seed-2',
				authorName: '林小扣',
				authorAvatar: imageLibrary[2].url,
				content: '可以加一个两人轮转练习吗？我想周末找人一起练。',
				createdAt: '2026-05-23T09:18:00+08:00'
			}
		],
		tags: ['复盘', '双打']
	},
	{
		id: 'seed-2',
		authorName: '阿羽教练',
		authorAvatar: imageLibrary[5].url,
		title: '中前场封网练习，三组动作让节奏快起来',
		content: '今天的训练建议：小跳启动、拍头提前、封直线后立即补斜线。',
		images: [imageLibrary[3].url, imageLibrary[5].url],
		createdAt: '2026-05-23T07:50:00+08:00',
		updatedAt: '',
		likes: 472,
		comments: [
			{
				id: 'comment-seed-3',
				authorName: '后场阿哲',
				authorAvatar: imageLibrary[3].url,
				content: '拍头提前这句很有用，封网总慢的人一看就懂。',
				createdAt: '2026-05-23T08:08:00+08:00'
			}
		],
		tags: ['训练', '网前']
	}
]
