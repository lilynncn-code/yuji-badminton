<template>
	<view class="page" :style="{ paddingTop: statusBarHeight + 'px', '--top-safe-height': statusBarHeight + 'px' }">
		<view class="nav-bar">
			<text>{{ $tr(copy.title) }}</text>
		</view>

		<scroll-view class="content" scroll-y>
			<view v-if="progressLoading || summaryLoading || progressError || summaryError" class="load-notice">
                <text v-if="progressLoading || summaryLoading">{{ $tr("正在读取本人的学习进度和训练统计…") }}</text>
                <text v-if="progressError">{{ $tr(progressError) }}</text>
                <button v-if="progressError" @click="restoreProgress">{{ $tr("重试读取学习进度") }}</button>
                <text v-if="summaryError">{{ $tr(summaryError) }}</text>
                <button v-if="summaryError" @click="restoreSummary">{{ $tr("重试读取训练统计") }}</button>
            </view>
            <view class="learning-status">
				<view class="status-pill flame" :class="{ active: todayTrainingDone }">
					<text class="flame-emoji">{{ $tr("🔥") }}</text>
					<text class="status-value">{{ $tr(learningStats.streak ?? '—') }}</text>
					<text class="status-label">{{ $tr(copy.streak) }}</text>
				</view>
			</view>

			<view class="stats-card">
				<view class="level-block">
					<text class="level">{{ $tr(userStats.level) }}</text>
					<view v-if="progressReady" class="progress-track">
						<view class="progress-fill" :style="{ width: (learningStats.xp % 100) + '%' }"></view>
					</view>
					<text v-if="progressReady" class="progress-text">{{ $tr("{0} {1} {2}", [copy.levelLeft, userStats.nextLevelScore, copy.points]) }}</text>
				</view>
				<view class="stat-list">
					<view class="stat-item" @click="showStat(copy.weeklyShots, `${userStats.weeklyShots ?? '暂未读到'} 次已保存的训练`)">
						<text class="stat-value">{{ $tr(userStats.weeklyShots === null ? '—' : userStats.weeklyShots.toLocaleString()) }}</text>
						<text class="stat-label">{{ $tr("本周训练次数") }}</text>
					</view>
					<view class="stat-item" @click="showStat(copy.aiCheckIn, `最近七天有 ${userStats.activeDays ?? '暂未读到'} 天训练`)">
						<text class="stat-value">{{ $tr("{0} 天", [userStats.activeDays ?? '—']) }}</text>
						<text class="stat-label">{{ $tr(copy.aiCheckIn) }}</text>
					</view>
				</view>
			</view>

			<view class="daily-card">
				<view>
					<text class="daily-title">{{ $tr(copy.todayPlan) }}</text>
					<text class="daily-sub">{{ $tr(copy.todayPlanSub) }}</text>
				</view>
				<button class="daily-btn" @click="startDailyWorkout">{{ $tr(copy.start) }}</button>
			</view>

			<view class="plan-basket-card" @click="openPlanBasket" :hover-class="'click-feedback'">
				<view>
					<text class="basket-kicker">{{ $tr(copy.planBasket) }}</text>
					<text class="basket-title">{{ $tr(copy.allPlans) }}</text>
					<text class="basket-copy">{{ $tr(copy.planDesc) }}</text>
				</view>
				<view class="basket-badge">
					<text>{{ $tr("6 个计划") }}</text>
					<text>{{ $tr("分阶段练") }}</text>
				</view>
			</view>

			<view class="path-card">
				<view class="practice-route-bar">
					<view class="route-metric">
						<text class="route-value">{{ $tr(progressReady?'进行中':'等待读取') }}</text>
						<text class="route-label">{{ $tr("训练计划") }}</text>
					</view>
					<view class="route-metric">
						<text class="route-value">{{ $tr(displayedLearningUnits[0].kicker) }}</text>
						<text class="route-label">{{ $tr("阶段") }}</text>
					</view>
				</view>
				<view v-for="unit in displayedLearningUnits" :key="unit.id" class="unit island">
					<view v-for="miniUnit in visibleMiniUnits(unit)" :key="miniUnit.id" class="mini-unit">
						<view class="stage-card">
							<view class="stage-main">
								<text class="stage-kicker">{{ $tr("{0}，第 {1} 部分", [unit.kicker, miniUnit.order]) }}</text>
								<text class="stage-title">{{ $tr(miniUnit.title.replace('小单元 · ', '')) }}</text>
								<text class="stage-copy">{{ $tr(miniUnit.copy) }}</text>
							</view>
						</view>
						<view class="node-path">
							<view
								v-for="lesson in visibleMajorTasks(miniUnit)"
								:key="lesson.id"
								class="lesson-node"
								:class="[lesson.status, lesson.align]"
								@click="openLearningLesson(lesson)"
								:hover-class="'click-feedback'"
							>
								<view class="node-face">
									<text class="node-icon">{{ $tr(nodeIcon(lesson)) }}</text>
								</view>
								<text class="node-type">{{ $tr(lesson.type) }}</text>
								<text class="node-title">{{ $tr(majorTaskTitle(lesson)) }}</text>
								<view
									v-if="lesson.status === 'current'"
									class="shuttle-guide"
									:class="{ speaking: shuttleSpeaking }"
									@click.stop="playShuttleEncouragement"
									:hover-class="'click-feedback'"
								>
									<view class="shuttle-shadow"></view>
									<image class="shuttle-character" src="/static/ai-coach/shuttlecock-character.png" mode="aspectFit"></image>
								</view>
							</view>
						</view>
					</view>
				</view>
			</view>

		</scroll-view>

		<view v-if="planBasketVisible" class="modal-mask" @click="planBasketVisible = false">
			<view class="plan-basket-modal" @click.stop>
				<view class="modal-head">
					<view>
						<text class="practice-kicker">{{ $tr("学习计划篮") }}</text>
						<text class="practice-title">{{ $tr("选择一个大计划") }}</text>
					</view>
					<button class="close-btn" @click="planBasketVisible = false">{{ $tr("×") }}</button>
				</view>
				<scroll-view class="plan-list" scroll-y>
					<view v-for="unit in learningUnits" :key="unit.id" class="plan-card">
						<view class="plan-card-head">
							<view>
								<text class="unit-kicker">{{ $tr(unit.kicker) }}</text>
								<text class="plan-card-title">{{ $tr(unit.title) }}</text>
							</view>
							<text class="plan-progress">{{ $tr("10 阶段") }}</text>
						</view>
						<text class="plan-card-copy">{{ $tr(unit.subtitle) }}</text>
						<view class="plan-track">
							<view class="plan-fill" :style="{ width: unitProgress(unit) + '%' }"></view>
						</view>
						<view class="plan-meta-row">
							<text>{{ $tr("10 阶段 · 每阶段 10 部分") }}</text>
							<text>{{ $tr("每部分 4 道题") }}</text>
						</view>
						<view class="plan-actions">
							<button class="plan-secondary full" @click="startUnitFromBasket(unit)">{{ $tr("开始计划") }}</button>
						</view>
					</view>
				</scroll-view>
			</view>
		</view>

		<view v-if="practiceVisible" class="modal-mask" @click="practiceVisible = false">
			<view class="practice-modal" @click.stop>
				<text class="practice-kicker">{{ $tr(currentPractice.unit) }}</text>
				<text class="practice-title">{{ $tr(currentPractice.title) }}</text>
				<text class="practice-question">{{ $tr(currentPractice.question) }}</text>
				<view class="option-list">
					<button
						v-for="option in currentPractice.options"
						:key="option"
						class="option"
						:class="{ picked: selectedOption === option, correct: answerState === 'correct' && selectedOption === option, wrong: answerState === 'wrong' && selectedOption === option }"
						@click="chooseOption(option)"
					>
						{{ $tr(option) }}
					</button>
				</view>
				<view v-if="answerState" class="answer-box" :class="answerState">
					<text class="answer-title">{{ $tr(answerState === 'correct' ? '正确' : '再想一下') }}</text>
					<text class="answer-copy">{{ $tr(currentPractice.feedback) }}</text>
				</view>
				<button class="allow-btn" @click="continuePractice">{{ $tr(answerState === 'correct' ? '进入识别训练' : '继续') }}</button>
			</view>
		</view>

	</view>
</template>

<script setup>
import { computed, onUnmounted, ref } from 'vue'
import { onLoad, onShow, onHide, onUnload } from '@dcloudio/uni-app'
import { imageLibrary } from '../../data/app-data'
import { accountKey } from '../../utils/request'
import { getUser } from '../../utils/store'
import { getAuthToken } from '../../utils/auth'
import { fetchTrainingProgress, fetchTrainingSummary } from '../../utils/training-api'
import { applyAppLanguage, getAppLanguage, getCopy, setPageTitle } from '../../utils/i18n'
import { getTopSafeAreaHeight } from '../../utils/safe-area'

const statusBarHeight = getTopSafeAreaHeight()
const language = ref(getAppLanguage())
const copy = computed(() => getCopy('coach', language.value))
const activeStep = ref(0)
const trainingStarted = ref(false)
const feedbackVisible = ref(false)
const practiceVisible = ref(false)
const planBasketVisible = ref(false)
const selectedOption = ref('')
const answerState = ref('')
const activeUnitId = ref('unit-1')
const focusTaskId = ref('')
const progressReady=ref(false),progressLoading=ref(false),summaryLoading=ref(false),progressError=ref(''),summaryError=ref('')
let pageActive=false,owner='',progressTicket=0,summaryTicket=0
let requestedCourseTask=''
const account=()=>`${getUser().id||''}:${getAuthToken()}`
function available(){return pageActive&&owner===account()}
function selectPlan(value){
    if(!available())return
    activeUnitId.value=value
    try{uni.setStorageSync(accountKey('selected-learning-plan'),value)}catch(e){uni.showToast({title:'本机未能记住计划，账号学习进度仍会保留',icon:'none'})}
}
const shuttleSpeaking = ref(false)
const encouragementAudios = [
	'/static/ai-coach/encourage-1.m4a',
	'/static/ai-coach/encourage-2.m4a',
	'/static/ai-coach/encourage-3.m4a'
]
const englishEncouragementAudios = [
	'/static/ai-coach/encourage-en-1.m4a',
	'/static/ai-coach/encourage-en-2.m4a',
	'/static/ai-coach/encourage-en-3.m4a'
]
let encouragementAudio = null
let shuttleTimer = null
onLoad((query = {}) => {
    const unit = String(query.unit || '')
    const task = String(query.task || '')
    if (/^unit-[1-6]$/.test(unit)) activeUnitId.value = unit
    if (/^unit-[1-6]-m\d+-t[1-4]$/.test(task)) {
        requestedCourseTask = task
        focusTaskId.value = task
    }
    const storedTask = uni.getStorageSync(accountKey('pending-course-task'))
    if (!requestedCourseTask && /^unit-[1-6]-m\d+-t[1-4]$/.test(String(storedTask || ''))) {
        requestedCourseTask = String(storedTask)
        focusTaskId.value = requestedCourseTask
        try { uni.removeStorageSync(accountKey('pending-course-task')) } catch {}
    }
})
onShow(() => {
    pageActive=true
    const storedTask = uni.getStorageSync(accountKey('pending-course-task'))
    if (!requestedCourseTask && /^unit-[1-6]-m\d+-t[1-4]$/.test(String(storedTask || ''))) {
        requestedCourseTask = String(storedTask)
        focusTaskId.value = requestedCourseTask
        try { uni.removeStorageSync(accountKey('pending-course-task')) } catch {}
    }
    if(owner!==account()){
        owner=account();practiceVisible.value=false;planBasketVisible.value=false;selectedOption.value='';answerState.value=''
        activeUnitId.value=uni.getStorageSync(accountKey('selected-learning-plan'))||'unit-1'
    }
    language.value=getAppLanguage();applyAppLanguage(language.value);setPageTitle('coach',language.value)
    restoreProgress();restoreSummary()
})
function stopPage(){
    pageActive=false;progressTicket++;summaryTicket++;progressLoading.value=false;summaryLoading.value=false
    practiceVisible.value=false;planBasketVisible.value=false;selectedOption.value='';answerState.value=''
    if(shuttleTimer)clearTimeout(shuttleTimer)
    shuttleSpeaking.value=false
    if(encouragementAudio)encouragementAudio.stop()
}
onHide(stopPage);onUnload(stopPage)
onUnmounted(()=>{stopPage();if(encouragementAudio){encouragementAudio.destroy();encouragementAudio=null}})
const todayTrainingDone=ref(false)
const learningStats=ref({streak:null,xp:null})
const userStats=ref({level:'正在读取学习进度',nextLevelScore:null,weeklyShots:null,activeDays:null})

const coachLessons = [
	{
		id: 1,
		title: '正手高远球',
		accuracyRate: 98,
		difficulty: '基础强化',
		duration: '8 分钟',
		goal: '把击球点稳定在身体前上方，提升后场回球深度。',
		image: imageLibrary[3].url,
		steps: ['侧身架拍，非持拍手指向来球', '最后一步蹬转，击球点在头顶前方', '收拍到左髋，快速回中'],
		feedback: '本节课建议：击球点再前移 12cm，收拍后第一步回中速度可以再快一点。'
	},
	{
		id: 2,
		title: '反手被动过渡',
		accuracyRate: 94,
		difficulty: '中阶突破',
		duration: '10 分钟',
		goal: '在被压到底线时稳定过渡到中后场，避免只起半场球。',
		image: imageLibrary[0].url,
		steps: ['先撤髋再引拍，身体不要完全背对球网', '拍面微开，击球瞬间手指发力', '出球后小跳回中，准备下一拍防守'],
		feedback: 'AI 判断你的反手击球点偏后，建议先练撤髋启动，再练手指发力。'
	},
	{
		id: 3,
		title: '网前扑球',
		accuracyRate: 96,
		difficulty: '节奏训练',
		duration: '6 分钟',
		goal: '提高网前启动和拍头准备速度。',
		image: imageLibrary[5].url,
		steps: ['重心压低，拍头高于手腕', '小跳启动后一步到位', '扑球后拍面立刻回正'],
		feedback: '网前反应不错，但扑球后拍头下沉，容易被对手推后场。'
	},
	{
		id: 4,
		title: '起跳杀球',
		accuracyRate: 92,
		difficulty: '力量进阶',
		duration: '12 分钟',
		goal: '建立起跳、转体、鞭打的连续发力。',
		image: imageLibrary[2].url,
		steps: ['并步找球，起跳前肩髋侧向打开', '击球瞬间前臂内旋，手腕下压', '落地后右脚先缓冲，立刻准备封网'],
		feedback: '杀球速度达标，落地后重心偏右，下一拍衔接会慢。'
	}
]

const selectedLesson = ref(coachLessons[0])
const learningUnits = ref([
	{
		id: 'unit-1',
		kicker: '大单元 1',
		title: '新手起飞岛',
		subtitle: '先把正手、回中和网前准备练顺，像打小游戏一样一关一关点亮',
		miniUnits: [
			{
				id: 'u1-mini-1',
				title: '小单元 · 后场发射台',
				copy: '高远球和回中两件小事，练完就能少被吊着跑',
				tasks: [
					{ id: 'u1-1', type: '小任务', title: '正手高远', xp: 10, status: 'done', align: 'left', lessonIndex: 0, unit: '后场发射台', answer: '击球点在身体前上方', question: '正手高远球最关键的击球点在哪里？', options: ['身体正后方', '身体前上方', '膝盖旁边'], feedback: '正手高远球要在身体前上方击球，才能把球送到底线。' },
					{ id: 'u1-2', type: '小任务', title: '快速回中', xp: 15, status: 'current', align: 'center', lessonIndex: 0, unit: '后场发射台', answer: '击球后第一步回到中场', question: '打完高远球后，第一反应应该是什么？', options: ['站着看球', '击球后第一步回到中场', '立刻退到底线'], feedback: '击球后立刻回中，下一拍才不会被动。' }
				]
			},
			{
				id: 'u1-mini-2',
				title: '小单元 · 网前抢糖',
				copy: '拍头抬起来，抢网会像按了加速键',
				tasks: [
					{ id: 'u1-3', type: '小任务', title: '网前准备', xp: 15, status: 'locked', align: 'right', lessonIndex: 2, unit: '网前抢糖', answer: '拍头高于手腕', question: '网前扑球准备时拍头应该怎样？', options: ['拍头高于手腕', '拍头垂到膝盖', '拍面完全向下'], feedback: '拍头提前抬高，才能抢到网前第一时间。' }
				]
			}
		]
	},
	{
		id: 'unit-2',
		kicker: '大单元 2',
		title: '双打节奏岛',
		subtitle: '第三拍、封网、轮转，适合想把球打得更有戏的人',
		miniUnits: [
			{
				id: 'u2-mini-1',
				title: '小单元 · 前三拍抢拍',
				copy: '接发之后别发呆，抢到半拍就很香',
				tasks: [
					{ id: 'u2-1', type: '小任务', title: '第三拍抢网', xp: 20, status: 'locked', align: 'left', lessonIndex: 2, unit: '前三拍抢拍', answer: '接发后重心前压', question: '第三拍抢网前，身体重心更应该？', options: ['向后坐', '接发后重心前压', '完全站直'], feedback: '重心前压能让你更快抢到中前场。' }
				]
			},
			{
				id: 'u2-mini-2',
				title: '小单元 · 后场连招',
				copy: '杀完还要接下一拍，帅气不能只帅一秒',
				tasks: [
					{ id: 'u2-2', type: '小任务', title: '后场衔接', xp: 20, status: 'locked', align: 'center', lessonIndex: 3, unit: '后场连招', answer: '杀球后准备封网或补位', question: '杀球后下一拍应准备什么？', options: ['原地停住', '杀球后准备封网或补位', '转身背对球网'], feedback: '杀球不是结束，衔接才决定下一拍主动权。' }
				]
			}
		]
	},
	{
		id: 'unit-3',
		kicker: '大单元 3',
		title: '防守反击岛',
		subtitle: '从被动接杀到反手过渡，先稳住，再把球权抢回来',
		miniUnits: [
			{
				id: 'u3-mini-1',
				title: '小单元 · 接杀稳住',
				copy: '降低重心、拍面立住，把对手的重杀顶回去',
				tasks: [
					{ id: 'u3-1', type: '小任务', title: '接杀站位', xp: 25, status: 'locked', align: 'left', lessonIndex: 1, unit: '接杀稳住', answer: '重心降低，拍面提前立住', question: '面对杀球时，准备动作最重要的是什么？', options: ['重心降低，拍面提前立住', '身体完全站直', '球到身边再举拍'], feedback: '接杀要提前立拍，身体低一点，才有时间借力。' },
					{ id: 'u3-2', type: '小任务', title: '挡网反击', xp: 25, status: 'locked', align: 'center', lessonIndex: 2, unit: '接杀稳住', answer: '借力轻挡到网前', question: '对方重杀后，想反击网前应该怎样处理？', options: ['借力轻挡到网前', '大力抽到后场', '闭眼挥拍'], feedback: '借力挡网能让对手从进攻变成被动上网。' }
				]
			},
			{
				id: 'u3-mini-2',
				title: '小单元 · 反手逃生',
				copy: '被压到底线时，用反手过渡把回合续上',
				tasks: [
					{ id: 'u3-3', type: '小任务', title: '反手过渡', xp: 25, status: 'locked', align: 'right', lessonIndex: 1, unit: '反手逃生', answer: '先撤髋再引拍', question: '反手底线被动时第一步应该怎么做？', options: ['先撤髋再引拍', '只用手腕硬抬', '站在原地等球'], feedback: '先撤髋能让身体转开，反手才不会只靠手腕。' }
				]
			}
		]
	},
	{
		id: 'unit-4',
		kicker: '大单元 4',
		title: '进攻爆发岛',
		subtitle: '练起跳杀球、劈吊和连续下压，让进攻不只是一拍爽',
		miniUnits: [
			{
				id: 'u4-mini-1',
				title: '小单元 · 后场重炮',
				copy: '从侧身、起跳到落地衔接，把杀球连起来',
				tasks: [
					{ id: 'u4-1', type: '小任务', title: '起跳杀球', xp: 30, status: 'locked', align: 'left', lessonIndex: 3, unit: '后场重炮', answer: '落地后立刻准备下一拍', question: '起跳杀球后最关键的衔接是什么？', options: ['落地后立刻准备下一拍', '站着看球', '转身庆祝'], feedback: '杀球后下一拍才是真正决定得分的地方。' },
					{ id: 'u4-2', type: '小任务', title: '劈吊变化', xp: 30, status: 'locked', align: 'center', lessonIndex: 3, unit: '后场重炮', answer: '动作像杀球，出球变短', question: '劈吊最有欺骗性的地方是什么？', options: ['动作像杀球，出球变短', '动作完全停住', '拍面朝地面'], feedback: '劈吊要让对手以为你要杀，最后一刻变线路。' }
				]
			},
			{
				id: 'u4-mini-2',
				title: '小单元 · 连续下压',
				copy: '杀、封、补位一口气完成，别让进攻断掉',
				tasks: [
					{ id: 'u4-3', type: '小任务', title: '杀封衔接', xp: 30, status: 'locked', align: 'right', lessonIndex: 3, unit: '连续下压', answer: '同伴补网，自己准备后场下一拍', question: '双打后场杀球后，队友和自己应该怎样衔接？', options: ['同伴补网，自己准备后场下一拍', '两个人都后退', '两个人都站住'], feedback: '杀封衔接靠分工，前场封网，后场继续压。' }
				]
			}
		]
	},
	{
		id: 'unit-5',
		kicker: '大单元 5',
		title: '双打战术岛',
		subtitle: '练轮转、封网、补位和沟通，让两个人像一个系统在打球',
		miniUnits: [
			{
				id: 'u5-mini-1',
				title: '小单元 · 前后轮转',
				copy: '谁上网、谁补后场，跑位要有默契',
				tasks: [
					{ id: 'u5-1', type: '小任务', title: '前后轮转', xp: 35, status: 'locked', align: 'left', lessonIndex: 2, unit: '前后轮转', answer: '谁进攻谁上前封，队友补后场', question: '双打进攻时前后轮转的核心是什么？', options: ['谁进攻谁上前封，队友补后场', '两个人站一条线', '谁都不动'], feedback: '前后轮转要让网前和后场都有人接管。' },
					{ id: 'u5-2', type: '小任务', title: '封网预判', xp: 35, status: 'locked', align: 'center', lessonIndex: 2, unit: '前后轮转', answer: '拍头高，压住直线和中路', question: '封网时最应该提前准备哪里？', options: ['拍头高，压住直线和中路', '拍头放低', '退到底线'], feedback: '封网不是等球，是提前压住最危险的线路。' }
				]
			},
			{
				id: 'u5-mini-2',
				title: '小单元 · 沟通补位',
				copy: '喊球、让球、补空当，减少撞拍和空档',
				tasks: [
					{ id: 'u5-3', type: '小任务', title: '喊球补位', xp: 35, status: 'locked', align: 'right', lessonIndex: 0, unit: '沟通补位', answer: '提前喊球并补空当', question: '双打两人都能接到球时，最好怎么做？', options: ['提前喊球并补空当', '一起抢同一拍', '都让给对方'], feedback: '沟通越早，补位越顺，失误就越少。' }
				]
			}
		]
	},
	{
		id: 'unit-6',
		kicker: '大单元 6',
		title: '高手比赛岛',
		subtitle: '进入实战模式：节奏变化、体能分配、关键分和赛后复盘',
		miniUnits: [
			{
				id: 'u6-mini-1',
				title: '小单元 · 关键分处理',
				copy: '20 平之后不乱打，用最稳定的套路拿分',
				tasks: [
					{ id: 'u6-1', type: '小任务', title: '关键分选择', xp: 40, status: 'locked', align: 'left', lessonIndex: 0, unit: '关键分处理', answer: '用成功率最高的线路', question: '关键分时最应该优先选择什么？', options: ['用成功率最高的线路', '只追求最帅一拍', '完全随机'], feedback: '关键分拼的是成功率和执行力，不是炫技。' },
					{ id: 'u6-2', type: '小任务', title: '节奏变化', xp: 40, status: 'locked', align: 'center', lessonIndex: 3, unit: '关键分处理', answer: '快慢结合打乱对手启动', question: '高手局里节奏变化的目的是什么？', options: ['快慢结合打乱对手启动', '永远一个速度', '只打高远球'], feedback: '节奏变化能让对手启动慢半拍。' }
				]
			},
			{
				id: 'u6-mini-2',
				title: '小单元 · 赛后复盘',
				copy: '用 AI 报告看失分原因，下一次训练更准',
				tasks: [
					{ id: 'u6-3', type: '小任务', title: 'AI 复盘报告', xp: 40, status: 'locked', align: 'right', lessonIndex: 1, unit: '赛后复盘', answer: '看失分模式和动作稳定性', question: '赛后复盘最有价值的数据是什么？', options: ['看失分模式和动作稳定性', '只看总分', '只看球拍颜色'], feedback: '复盘要找到反复丢分的模式，下一次训练才有方向。' }
				]
			}
		]
	}
])
const alignOptions = ['left', 'center', 'right', 'center']
const roundMethods = ['慢速分解', '无球预演', '定点击球', '两点移动', '连续三拍', '变线练习', '压力计时', '左右交替', '实战还原', '收尾复盘']
const taskKinds = ['动作要点', '衔接练习', '自查标准', '避坑挑战']

// 每个阶段都有自己的重点、完成标准和易错点；100 个部分会按阶段和练法变化，不再复制同一套题。
const curriculumStageData = {
	'unit-1': [
		['握拍与准备', '先把拍子拿稳，再开始移动', '虎口放松，拍柄握在手指根部', '完成后回到准备位并保持拍头向上', '手臂夹紧、拍头下垂'],
		['侧身转体', '让身体转起来，给击球留出空间', '非持拍肩指向来球', '转体后用小步回到中场', '正面对网只用手臂挥拍'],
		['高远击球点', '把球送到后场，不靠蛮力', '在身体前上方击球', '收拍后第一步回中', '击球点落到身体后方'],
		['收拍回中', '打完球马上准备下一拍', '收拍到非持拍侧肩前', '回中时眼睛继续看球', '站在原地看球飞行'],
		['并步启动', '先动脚，再伸手击球', '启动时重心放在前脚掌', '两步内回到中线', '跨大步后身体失去平衡'],
		['前后步伐', '前后移动都能保持身体正面', '最后一步用小步刹住', '落地后拍头仍在身前', '冲过球后再急停'],
		['网前举拍', '提前准备，减少网前反应时间', '拍头高于手腕', '扑球后拍面立刻回正', '等球到身边才举拍'],
		['网前放网', '轻柔控球，让球贴网落下', '触球时手指短促发力', '出球后立即回到网前', '大幅挥臂把球挑高'],
		['接发准备', '接发前先读懂对手动作', '双脚分开并保持膝盖微屈', '接发后向空当补位', '脚跟落地、站得太直'],
		['基础连贯', '把准备、击球和回中连起来', '每拍结束都回到可启动姿势', '连续三拍保持节奏', '只练击球不练回位']
	],
	'unit-2': [
		['发球落点', '用稳定发球开始主动回合', '发球前固定站位和拍面', '发球后马上抬拍准备', '发球后低头看球'],
		['接发压迫', '接发第一拍就给对手压力', '接发时拍面朝前并向前迎球', '接发后向中前场移动', '只把球挡回去不跟进'],
		['第三拍抢网', '接发之后抢半拍上网', '击球前重心向前压', '上网后拍头保持在眼前', '击球后仍停在后场'],
		['推压中路', '把球打向两人之间制造犹豫', '推球时拍面稳定向前', '推完后封住中路', '只盯着边线追求角度'],
		['后场连杀', '连续下压时保持身体节奏', '杀球前先侧身找高点', '下一拍继续向前压迫', '第一拍杀完就停住'],
		['劈吊变化', '让同样的准备动作产生不同落点', '击球前保持杀球姿势', '出球后立刻观察对手', '提前露出吊球意图'],
		['平抽快挡', '中场对抗时缩短挥拍', '拍头在身体前方快速迎球', '挡完后向前一步', '用大幅度挥拍抢速度'],
		['封网压线', '网前守住最可能的回球线路', '拍头高并压住直线', '封网后随队友移动', '拍头放低等球落下'],
		['轮转时机', '前后站位随着球权改变', '队友进攻时自己补后场', '球权转换后及时换位', '两个人同时抢同一区域'],
		['双打连贯', '从发球到第三拍形成固定套路', '每次击球前先看队友位置', '一拍结束就说清下一步', '各打各的、不看队友']
	],
	'unit-3': [
		['接杀站位', '先稳住防守，再找反击机会', '重心降低，拍面提前立住', '接杀后向空当移动', '站得太高、拍面太晚'],
		['挡网反击', '借对手的力量把球挡短', '触球时手指轻轻收紧', '挡网后拍头继续向前', '大力抡拍把球挡高'],
		['防守平抽', '被压制时用平抽争取主动', '击球点保持在身体前侧', '平抽后立刻回到中线', '只用手腕向后甩'],
		['反手引拍', '反手被动时先让身体转开', '先撤髋再引拍', '击球后用小跳回中', '只用手腕硬抬球'],
		['反手过渡', '把被动球送到安全区域', '拍面微开并借力向上', '出球后观察对方站位', '为了发力把拍面压死'],
		['底线防守', '深球来时给自己留出时间', '提前向落点移动', '回球后不要贴着底线站', '等球落地后才启动'],
		['被动高远', '困难时先把球打深', '击球点前移并充分伸展', '打深后回到中后场', '只顾追求速度不顾高度'],
		['防守变线', '在合适时机把球打向空当', '变线前先看清对手位置', '变线后马上准备下一拍', '没有观察就盲目变线'],
		['救球落地', '救球后仍能保持下一拍准备', '最后一步用小碎步调整', '落地后先稳住重心', '扑完球直接坐在地上'],
		['防守反击', '防住一拍后把球权拿回来', '先保证回球过网且有深度', '看到短球再向前抢', '防守成功就马上冒险进攻']
	],
	'unit-4': [
		['起跳准备', '杀球前先完成侧身和蹬地', '起跳前肩髋侧向打开', '落地后两脚分开缓冲', '面对球网直直起跳'],
		['高点击球', '在最高点击球获得角度', '击球点在头顶前上方', '击球后立刻向前回收', '等球下降才挥拍'],
		['转体发力', '让身体带动手臂而不是反过来', '先转髋再转肩', '转体后保持身体平衡', '只靠手臂抡拍'],
		['杀球落点', '选择空当比只追求速度更重要', '击球前先看对手站位', '杀球后向下一拍落点移动', '每次都打同一条线'],
		['连续下压', '一拍杀球后继续保持压迫', '杀球后拍头马上回到身前', '下一拍准备封网或补位', '杀完球站着看结果'],
		['劈吊伪装', '用相同准备动作改变节奏', '出拍前保持杀球姿势', '出球后快速上网', '提前停拍暴露意图'],
		['点杀控制', '用较小动作打出落点变化', '击球时减少多余摆臂', '点杀后及时回中', '为了发力把身体甩出去'],
		['杀封配合', '后场进攻和网前封堵要连起来', '后场击球前先确认队友位置', '队友封网时自己准备补后场', '两个人都冲到网前'],
		['耐力下压', '连续进攻也要保留体力', '每拍结束用小步调整', '感觉失位时先回中', '只追求每拍全力杀球'],
		['进攻选择', '看清机会再选择杀、吊或推', '击球前判断来球高度', '选择后马上执行并回位', '没有机会也强行起跳']
	],
	'unit-5': [
		['前后轮转', '两人保持前后层次，不抢同一条线', '进攻方上前，队友补后场', '球权变化后一起换位', '两人站成一条横线'],
		['左右补位', '对角移动时守住空当', '队友出拍时先看自己负责区域', '补位后恢复基本站位', '只跟着球跑不看空当'],
		['封网预判', '提前压住最危险的回球线路', '拍头高并盯住对手拍面', '封网后顺着球路移动', '等球飞来才开始判断'],
		['沟通喊球', '一句清楚的喊声能减少撞拍', '来球前提前说“我”或“你”', '喊完后主动补空当', '球到眼前才开口'],
		['发接发分工', '发球方和接发方都知道下一步', '发球后守住直线', '接发后向前跟进', '发完球两人都退后'],
		['中路处理', '中路球先由更有利位置的人处理', '提前约定中路责任', '处理后马上补回自己的区域', '两个人同时抢中路'],
		['边线防守', '防守时两人覆盖整个半场', '根据球的位置缩小空档', '回球后一起向中间收', '只守自己脚下的边线'],
		['轮转复位', '一回合结束后快速恢复站位', '看见队友移动就跟着补位', '落位后拍头重新举起', '移动后忘记自己的区域'],
		['战术手势', '发球前用简单手势约定线路', '确认队友看懂手势', '发完球按约定执行', '临时改变却不告诉队友'],
		['双打实战', '把沟通、轮转和出球连在一起', '每拍前先看队友和对手', '失位后先补空再进攻', '只顾自己打得漂亮']
	],
	'unit-6': [
		['关键分心态', '比分紧张时仍按熟悉套路执行', '发球前做一次深呼吸', '得失分后快速回到准备位', '关键分突然改变所有习惯'],
		['节奏变化', '用快慢变化打乱对手启动', '先用稳定球建立节奏', '改变速度后立刻回位', '每拍都用同一个速度'],
		['体能分配', '把体力留给真正的得分机会', '准备阶段用小步移动', '长回合后主动放慢呼吸', '每一拍都全力冲刺'],
		['比分策略', '领先和落后时选择不同风险', '领先时优先打成功率高的线路', '落后时先减少无谓失误', '只看比分不看回合状态'],
		['对手观察', '从对手习惯找到可利用的空当', '观察对手回位方向', '发现规律后及时告诉队友', '只盯自己的动作'],
		['线路选择', '让出球方向服务于下一拍', '击球前先确认空当', '出球后向下一拍位置移动', '只追求边线不顾回位'],
		['连续得分', '得分后继续执行同一套准备', '得分后先整理呼吸', '下一分开始前重新确认计划', '得分后马上冒险炫技'],
		['逆风处理', '落后时一分一分追回来', '先把下一拍打过网', '连续两分后再调整战术', '一落后就急着一次扳回'],
		['赛中复盘', '利用短暂间歇修正一个重点', '只选一个最影响结果的问题', '下一分立刻验证修正', '一次改变太多动作'],
		['赛后总结', '把比赛变成下一次训练计划', '记录失分最多的场景', '为下次训练定一个可检查目标', '只看总分不看失分原因']
	]
}

function stageFromData(data) {
	return { title: data[0], copy: data[1], focus: data[0], cue: data[2], recovery: data[3], warning: data[4] }
}

function buildGeneratedTask(unit, stage, miniIndex, taskIndex, roundMethod) {
	const isFirstUnit = unit.id === 'unit-1'
	const status = isFirstUnit && miniIndex === 1 && taskIndex === 1 ? 'current' : 'locked'
	const facts = [
		{ question: `练习${stage.focus}时，最先要做到什么？`, answer: stage.cue, wrong: ['等球到身边再处理', '先站住不动'] },
		{ question: `完成${stage.focus}后，下一步应怎样？`, answer: stage.recovery, wrong: ['站着看球飞行', '立刻转身背对球网'] },
		{ question: `用${roundMethod}练${stage.focus}时，怎样算做对？`, answer: stage.cue, wrong: ['只追求速度不管落点', '动作越大越好'] },
		{ question: `${stage.focus}最需要避免哪种情况？`, answer: stage.warning, wrong: ['提前回到准备位', '看清来球再移动'] }
	][taskIndex - 1]
	return {
		id: `${unit.id}-m${miniIndex}-t${taskIndex}`,
		unitId: unit.id,
		type: '小任务',
		title: `${stage.title} · ${roundMethod} · ${taskKinds[taskIndex - 1]}`,
		xp: 10 + (Number(unit.id.slice(-1)) - 1) * 5 + Math.floor((miniIndex - 1) / 10) * 2 + taskIndex,
		status,
		align: alignOptions[(taskIndex - 1) % alignOptions.length],
		unit: `${unit.title} · 第 ${miniIndex} 部分`,
		question: facts.question,
		answer: facts.answer,
		options: rotateOptions([facts.answer, ...facts.wrong], miniIndex + taskIndex),
		feedback: `本轮采用${roundMethod}：${stage.focus}先抓住“${stage.cue}”，完成后${stage.recovery}。`
	}
}

function expandMiniUnits(unit) {
	const stages = (curriculumStageData[unit.id] || []).map(stageFromData)
	return Array.from({ length: 100 }, (_, index) => {
		const order = index + 1
		const stage = stages[index % stages.length]
		const roundMethod = roundMethods[Math.floor(index / stages.length) % roundMethods.length]
		return {
			id: `${unit.id}-mini-${order}`,
			order,
			title: `小单元 · ${stage.title} · ${roundMethod}`,
			copy: `${stage.copy}。本轮采用${roundMethod}，完成后再进入下一部分。`,
			tasks: Array.from({ length: 4 }, (_, taskIndex) => buildGeneratedTask(unit, stage, order, taskIndex + 1, roundMethod))
		}
	})
}

learningUnits.value = learningUnits.value.map((unit) => ({
	...unit,
	miniUnits: expandMiniUnits(unit)
}))
const currentPractice = ref(learningUnits.value[0].miniUnits[0].tasks[0])
const displayedLearningUnits = computed(() => {
	const activeUnit = learningUnits.value.find((unit) => unit.id === activeUnitId.value)
	if (activeUnit) return [activeUnit]
	const currentUnit = learningUnits.value.find((unit) => unitTasks(unit).some((task) => task.status === 'current'))
	return currentUnit ? [currentUnit] : [learningUnits.value[0]]
})

function selectLesson(lesson) {
	selectedLesson.value = lesson
	activeStep.value = 0
	trainingStarted.value = false
	feedbackVisible.value = false
	uni.showToast({ title: `已选择 ${lesson.title}`, icon: 'none' })
}

function openPlanBasket() {
    if(!available()||!progressReady.value)return
	planBasketVisible.value = true
}

function showStat(title, content) {
	uni.showModal({ title, content, showCancel: false })
}

function startDailyWorkout() {
    if(!available())return
	uni.navigateTo({url:'/pages/ai-coach/daily'})
}

function nodeIcon(lesson) {
	if (lesson.status === 'done') return '✓'
	if (lesson.status === 'current') return '羽'
	const lockedIcons = ['拍', '步', '挥', 'AI', '测']
	const code = lesson.id.split('').reduce((sum, char) => sum + char.charCodeAt(0), 0)
	return lockedIcons[code % lockedIcons.length]
}

function openLearningLesson(lesson) {
    if(!available()||!progressReady.value){if(available())uni.showToast({title:'请先读取学习进度',icon:'none'});return}
    if(!learningUnits.value.flatMap(unitTasks).includes(lesson))return
	if (lesson.status === 'locked') {
		uni.showToast({ title: '先完成前面的关卡', icon: 'none' })
		return
	}
	if (lesson.unitId) selectPlan(lesson.unitId)
	currentPractice.value = lesson
	selectedOption.value = ''
	answerState.value = ''
	practiceVisible.value = true
}

function chooseOption(option) {
    if(!available()||!progressReady.value||!practiceVisible.value)return
	if (answerState.value === 'correct') return
	selectedOption.value = option
	if (option === currentPractice.value.answer) {
		answerState.value = 'correct'
        // Answering prepares the exercise. Only a saved exercise completes a task.
		return
	}
	answerState.value = 'wrong'
	uni.showToast({ title: '答错了，再试一次', icon: 'none' })
}

function rotateOptions(values, offset) {
    const items = [...new Set(values)]
    const start = offset % items.length
    return [...items.slice(start), ...items.slice(0, start)]
}
async function restoreProgress() {
    if(!available()||progressLoading.value)return
    const ticket=++progressTicket,who=owner
    progressLoading.value=true;progressReady.value=false;progressError.value='';learningStats.value.xp=null
    userStats.value.level='正在读取学习进度';userStats.value.nextLevelScore=null
    practiceVisible.value=false;selectedOption.value='';answerState.value=''
    learningUnits.value.forEach(unit=>unitTasks(unit).forEach(task=>task.status='locked'))
    try{
        const progress=await fetchTrainingProgress()
        if(!available()||ticket!==progressTicket||who!==owner)return
        const done=new Set(progress.completed)
        let opened=false
        learningUnits.value.forEach(unit=>unitTasks(unit).forEach(task=>{
            if(done.has(task.id))task.status='done'
            else if(!opened){task.status='current';opened=true}
            else task.status='locked'
        }))
        const current=learningUnits.value.flatMap(unitTasks).find(t=>t.status==='current')
        const saved=uni.getStorageSync(accountKey('selected-learning-plan'))
        activeUnitId.value=learningUnits.value.some(u=>u.id===saved)?saved:(current?.unitId||'unit-1')
        focusRequestedCourseTask()
        learningStats.value.xp=progress.xp
        userStats.value.level=`已完成 ${progress.completed.length} 关`;userStats.value.nextLevelScore=100-progress.xp%100
        progressReady.value=true
    }catch(error){if(available()&&ticket===progressTicket&&who===owner){progressError.value=error.message||'学习进度暂时没有读到';userStats.value.level='暂未读到学习进度'}}
    finally{if(available()&&ticket===progressTicket&&who===owner)progressLoading.value=false}
}
async function restoreSummary(){
    if(!available()||summaryLoading.value)return
    const ticket=++summaryTicket,who=owner
    summaryLoading.value=true;summaryError.value='';learningStats.value.streak=null;todayTrainingDone.value=false
    userStats.value.weeklyShots=null;userStats.value.activeDays=null
    try{
        const summary=await fetchTrainingSummary()
        if(!available()||ticket!==summaryTicket||who!==owner)return
        learningStats.value.streak=summary.streak;todayTrainingDone.value=summary.today_done
        userStats.value.weeklyShots=summary.weekly_sessions;userStats.value.activeDays=summary.active_days
    }catch(error){if(available()&&ticket===summaryTicket&&who===owner)summaryError.value=error.message||'训练统计暂时没有读到'}
    finally{if(available()&&ticket===summaryTicket&&who===owner)summaryLoading.value=false}
}

function continuePractice() {
    if(!available()||!progressReady.value||!practiceVisible.value)return
	if (answerState.value !== 'correct') {
		selectedOption.value = ''
		answerState.value = ''
		return
	}
	practiceVisible.value = false
	const targetLesson = coachLessons[currentPractice.value.lessonIndex] || coachLessons[0]
	selectLesson(targetLesson)
	uni.navigateTo({ url: `/pages/ai-coach/camera-capture?lesson=${encodeURIComponent(targetLesson.title)}&task=${encodeURIComponent(currentPractice.value.id)}` })
}

function showLeague() {
	uni.showModal({
		title: '本周榜单',
		content: '每完成一个训练关卡获得20学习分，训练记录会保存在你的账号中。',
		showCancel: false
	})
}

function unitTasks(unit) {
	return unit.miniUnits.flatMap((miniUnit) => miniUnit.tasks)
}

function currentMiniUnit(unit) {
	const focused = unit.miniUnits.find((miniUnit) => miniUnit.tasks.some((task) => task.id === focusTaskId.value))
	if (focused) return focused
	return unit.miniUnits.find((miniUnit) => miniUnit.tasks.some((task) => task.status === 'current')) || unit.miniUnits[0]
}

function visibleMiniUnits(unit) {
	const miniUnit = currentMiniUnit(unit)
	if (!miniUnit) return []
	const startIndex = Math.max(0, unit.miniUnits.findIndex((item) => item.id === miniUnit.id))
	return unit.miniUnits.slice(startIndex, startIndex + 12)
}

function visibleMajorTasks(miniUnit) {
	return miniUnit.tasks
}

function majorTaskTitle(lesson) {
	return lesson.title.replace(/\s+(动作入门|连贯训练|AI 识别|阶段挑战)$/, '')
}

function completedTasks(unit) {
	return unitTasks(unit).filter((task) => task.status === 'done').length
}

function unitProgress(unit) {
	const tasks = unitTasks(unit)
	if (!tasks.length) return 0
	return Math.round((completedTasks(unit) / tasks.length) * 100)
}

function startUnitFromBasket(unit) {
    if(!available()||!progressReady.value)return
	const tasks = unitTasks(unit)
	const nextTask = tasks.find((task) => task.status === 'current') || tasks.find((task) => task.status !== 'locked')
	if (!tasks.length) {
		uni.showToast({ title: '这个计划没有可用内容', icon: 'none' })
		return
	}
	if (!nextTask) {
		uni.showToast({ title: '请先完成前面的计划', icon: 'none' })
		return
	}
	selectPlan(unit.id)
	planBasketVisible.value = false
	openLearningLesson(nextTask)
}

function focusRequestedCourseTask() {
    if (!requestedCourseTask) return
    const task = learningUnits.value.flatMap(unitTasks).find((item) => item.id === requestedCourseTask)
    if (!task) return
    focusTaskId.value = task.id
    activeUnitId.value = task.unitId
    currentPractice.value = task
    selectedOption.value = ''
    answerState.value = ''
    if (task.status !== 'locked') {
        practiceVisible.value = true
        requestedCourseTask = ''
    } else {
        uni.showToast({ title: '已定位到这部分课程', icon: 'none' })
    }
}

function startLesson() {
	if (!trainingStarted.value) {
		uni.navigateTo({ url: `/pages/ai-coach/camera-capture?lesson=${encodeURIComponent(selectedLesson.value.title)}` })
		return
	}
	trainingStarted.value = false
	feedbackVisible.value = true
	uni.showToast({ title: 'AI 反馈已生成', icon: 'none' })
}

function playShuttleEncouragement() {
    if(!available()||!progressReady.value)return
	const voices = getAppLanguage() === 'en' ? englishEncouragementAudios : encouragementAudios
	const index = Math.floor(Math.random() * voices.length)
	if (!encouragementAudio) {
		encouragementAudio = uni.createInnerAudioContext()
		encouragementAudio.onEnded(() => {
			shuttleSpeaking.value = false
		})
		encouragementAudio.onError(() => {
			shuttleSpeaking.value = false
			if(available())uni.showToast({ title: '继续加油，下一拍更稳！', icon: 'none' })
		})
	}
	if (shuttleTimer) clearTimeout(shuttleTimer)
	encouragementAudio.stop()
	encouragementAudio.src = voices[index]
	shuttleSpeaking.value = true
	encouragementAudio.play()
	shuttleTimer = setTimeout(() => {
		shuttleSpeaking.value = false
	}, 6000)
}

</script>

<style lang="scss" scoped>
.load-notice{margin:20rpx 0;padding:20rpx;background:#252525;border-radius:14rpx;color:#ddd;font-size:25rpx;line-height:1.6}.load-notice text{display:block}.load-notice button{margin-top:12rpx;font-size:25rpx;background:#353535;color:#cf0}
$bg-main: #121212;
$bg-card: #1E1E1E;
$brand-primary: #CCFF00;
$text-white: #FFFFFF;
$text-gray: #8E8E93;
$border-color: #2C2C2E;

.page { min-height: 100vh; background: $bg-main; padding-bottom: calc(24rpx + env(safe-area-inset-bottom)); }
.nav-bar { position: relative; height: 88rpx; display: flex; align-items: center; justify-content: center; background: $bg-main; color: $text-white; font-size: 32rpx; font-weight: 700; }
.content { height: auto; max-height: calc(100vh - 88rpx - var(--top-safe-height)); padding-bottom: calc(36rpx + env(safe-area-inset-bottom)); }
.learning-status { margin: 20rpx 24rpx 0; display: grid; grid-template-columns: repeat(2, 1fr); gap: 12rpx; }
.status-pill { min-height: 86rpx; border-radius: 16rpx; background: $bg-card; border: 1rpx solid $border-color; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.flame-emoji { margin-bottom: 6rpx; font-size: 46rpx; line-height: 1; }
.status-pill.flame { grid-column: 1 / -1; }
.status-pill.flame.active .status-value { color: #FF6A3D; }
.status-value { color: $brand-primary; font-size: 32rpx; font-weight: 900; }
.status-label { margin-top: 6rpx; color: $text-gray; font-size: 20rpx; }
.path-card { position: relative; margin: 20rpx 24rpx 0; padding: 22rpx 0 30rpx; border-radius: 22rpx; background: linear-gradient(180deg, #202122 0%, #151616 100%); border: 1rpx solid rgba(204,255,0,.18); overflow: hidden; }
.stats-card { margin: 24rpx; padding: 32rpx; border-radius: 18rpx; background: $bg-card; display: flex; justify-content: space-between; border: 1rpx solid $border-color; }
.level-block { width: 330rpx; }
.level { color: $brand-primary; font-size: 36rpx; font-weight: 900; }
.progress-track { margin: 24rpx 0 10rpx; width: 100%; height: 12rpx; border-radius: 20rpx; background: #303033; overflow: hidden; }
.progress-fill { width: 72%; height: 100%; border-radius: 20rpx; background: $brand-primary; box-shadow: 0 0 16rpx rgba(204,255,0,.36); }
.progress-text { color: $text-gray; font-size: 24rpx; }
.stat-list { display: flex; flex-direction: column; justify-content: space-between; text-align: right; }
.stat-item { display: flex; flex-direction: column; padding: 8rpx 0; }
.stat-value { color: $text-white; font-size: 30rpx; font-weight: 800; }
.stat-label { margin-top: 8rpx; color: $text-gray; font-size: 22rpx; }
.daily-card { margin: 0 24rpx 24rpx; padding: 24rpx; border-radius: 18rpx; background: linear-gradient(135deg, rgba(204,255,0,.16), rgba(30,30,30,1)); border: 1rpx solid rgba(204,255,0,.22); display: flex; align-items: center; justify-content: space-between; gap: 18rpx; }
.daily-card > view { flex: 1; min-width: 0; }
.daily-title { display: block; color: $text-white; font-size: 32rpx; font-weight: 900; }
.daily-sub { display: block; margin-top: 8rpx; color: $text-gray; font-size: 24rpx; }
.daily-btn { min-width: 150rpx; min-height: 66rpx; padding: 8rpx 20rpx; border-radius: 999rpx; background: $brand-primary; color: #121212; font-size: 26rpx; line-height: 1.2; font-weight: 900; flex: 0 0 auto; text-align: center; white-space: normal; word-break: break-word; }
.plan-basket-card { margin: 0 24rpx 24rpx; padding: 26rpx 24rpx; border-radius: 20rpx; background: linear-gradient(135deg, rgba(255,255,255,.08), rgba(204,255,0,.12)); border: 1rpx solid rgba(204,255,0,.22); display: flex; align-items: center; justify-content: space-between; gap: 20rpx; }
.plan-basket-card > view:first-child { flex: 1; min-width: 0; }
.basket-kicker { display: block; color: $brand-primary; font-size: 23rpx; font-weight: 900; }
.basket-title { display: block; margin-top: 8rpx; color: $text-white; font-size: 34rpx; font-weight: 900; }
.basket-copy { display: block; margin-top: 10rpx; color: #D8D8D8; font-size: 23rpx; line-height: 1.45; }
.basket-badge { width: 120rpx; height: 120rpx; border-radius: 24rpx; background: $brand-primary; color: #121212; display: flex; flex-direction: column; align-items: center; justify-content: center; flex: 0 0 auto; font-weight: 900; text-align: center; }
.basket-badge text:first-child { width: 100%; font-size: 28rpx; line-height: 1.15; text-align: center; }
.basket-badge text:last-child { width: 100%; margin-top: 8rpx; font-size: 24rpx; line-height: 1.1; text-align: center; }
.unit-kicker { display: block; margin-bottom: 6rpx; color: $text-gray; font-size: 21rpx; font-weight: 800; }
.practice-route-bar { margin: 0 20rpx 18rpx; padding: 16rpx; border-radius: 16rpx; background: rgba(255,255,255,.05); border: 1rpx solid rgba(255,255,255,.08); display: grid; grid-template-columns: repeat(2, 1fr); gap: 12rpx; box-sizing: border-box; }
.route-metric { min-height: 82rpx; border-radius: 14rpx; background: rgba(255,255,255,.04); display: flex; flex-direction: column; align-items: center; justify-content: center; }
.route-value { color: $text-white; font-size: 32rpx; font-weight: 900; line-height: 1; }
.route-label { margin-top: 8rpx; color: $text-gray; font-size: 20rpx; font-weight: 700; }
.unit { margin-top: 0; }
.unit:first-of-type { margin-top: 0; }
.island { padding: 0 20rpx 4rpx; }
.mini-unit { position: relative; min-height: 600rpx; padding: 0 0 34rpx; }
.mini-unit + .mini-unit { margin-top: 28rpx; }
.stage-card { position: relative; min-height: 190rpx; border-radius: 18rpx; background: linear-gradient(135deg, rgba(204,255,0,.24), rgba(34,34,34,.98)); color: #FFFFFF; box-shadow: inset 0 0 0 1rpx rgba(204,255,0,.2); display: flex; overflow: hidden; }
.stage-main { flex: 1; min-width: 0; padding: 24rpx 28rpx; box-sizing: border-box; }
.stage-kicker { display: block; color: $brand-primary; font-size: 24rpx; font-weight: 900; }
.stage-title { display: block; margin-top: 8rpx; font-size: 36rpx; font-weight: 900; line-height: 1.22; }
.stage-copy { display: block; margin-top: 8rpx; color: #D8D8D8; font-size: 21rpx; line-height: 1.35; }
.node-path { position: relative; min-height: 390rpx; padding: 44rpx 18rpx 0; display: flex; flex-direction: column; gap: 56rpx; overflow: hidden; }
.node-path::before { content: ''; position: absolute; left: 50%; top: 54rpx; bottom: 34rpx; width: 8rpx; border-radius: 999rpx; background: linear-gradient(180deg, rgba(204,255,0,.42), rgba(255,255,255,.1)); transform: translateX(-50%); pointer-events: none; }
.node-path::after { content: ''; position: absolute; left: 28rpx; right: 28rpx; bottom: 0; height: 2rpx; background: repeating-linear-gradient(90deg, rgba(204,255,0,.18) 0 34rpx, transparent 34rpx 66rpx); pointer-events: none; }
.lesson-node { position: relative; width: 156rpx; height: 156rpx; border-radius: 50%; background: #2C2C2E; display: flex; flex-direction: column; align-items: center; justify-content: center; box-sizing: border-box; box-shadow: 0 12rpx 0 #151515; color: $text-gray; border: 2rpx solid rgba(255,255,255,.08); z-index: 1; }
.lesson-node.left { align-self: flex-start; margin-left: 8%; }
.lesson-node.center { align-self: center; }
.lesson-node.right { align-self: flex-end; margin-right: 8%; }
.lesson-node.done { background: rgba(204,255,0,.14); color: $brand-primary; box-shadow: 0 12rpx 0 rgba(108,136,0,.42); border-color: rgba(204,255,0,.32); }
.lesson-node.current { width: 178rpx; height: 178rpx; background: $brand-primary; color: #121212; box-shadow: 0 12rpx 0 #7A9900; border: 10rpx solid #1C1C1E; outline: 8rpx solid rgba(204,255,0,.28); }
.lesson-node.locked { opacity: 1; filter: grayscale(1); }
.node-face { width: 96rpx; height: 96rpx; border-radius: 50%; background: rgba(255,255,255,.08); display: flex; align-items: center; justify-content: center; }
.lesson-node.current .node-face { background: rgba(18,18,18,.12); }
.node-icon { font-size: 38rpx; font-weight: 900; line-height: 1; }
.node-type { display: none; }
.node-title { position: absolute; left: 50%; top: calc(100% + 14rpx); transform: translateX(-50%); width: 220rpx; color: $text-gray; font-size: 20rpx; font-weight: 900; text-align: center; line-height: 1.25; }
.lesson-node.current .node-title { color: $brand-primary; }
.shuttle-guide { position: absolute; left: calc(100% + 12rpx); top: 50%; width: 128rpx; height: 150rpx; opacity: .98; transform: translateY(-50%); z-index: 3; }
.lesson-node.right .shuttle-guide { left: auto; right: calc(100% + 12rpx); }
.shuttle-shadow { position: absolute; left: 22rpx; bottom: 2rpx; width: 106rpx; height: 20rpx; border-radius: 50%; background: rgba(0,0,0,.28); }
.shuttle-character { position: absolute; left: 0; top: 0; width: 128rpx; height: 144rpx; transition: transform .18s ease; }
.shuttle-guide.speaking .shuttle-character { transform: translateY(-10rpx) rotate(-3deg) scale(1.04); }
.shuttle-guide.speaking .shuttle-shadow { transform: scale(.86); opacity: .72; }
.section-head { padding: 10rpx 24rpx 18rpx; display: flex; align-items: center; justify-content: space-between; color: $text-white; font-size: 32rpx; font-weight: 900; }
.see-all { display: flex; align-items: center; color: $text-gray; font-size: 24rpx; font-weight: 500; }
.arrow { margin-left: 8rpx; font-size: 34rpx; }
.lesson-scroll { width: 100%; white-space: nowrap; }
.lesson-row { display: inline-flex; gap: 18rpx; padding: 0 24rpx 24rpx; }
.lesson-card { width: 260rpx; border-radius: 16rpx; background: $bg-card; border: 2rpx solid $border-color; overflow: hidden; }
.lesson-card.active { border-color: $brand-primary; }
.lesson-photo { width: 100%; height: 150rpx; background: #2C2C2E; }
.lesson-body { padding: 16rpx; }
.lesson-title { display: block; color: $text-white; font-size: 28rpx; font-weight: 900; }
.lesson-tag { display: inline-flex; margin-top: 14rpx; padding: 8rpx 12rpx; border-radius: 999rpx; background: rgba(204,255,0,.12); color: $brand-primary; font-size: 20rpx; }
.difficulty { display: block; margin-top: 12rpx; color: $text-gray; font-size: 22rpx; }
.training-card { margin: 0 24rpx 24rpx; padding: 24rpx; border-radius: 18rpx; background: $bg-card; border: 1rpx solid $border-color; }
.compact-training { margin-bottom: 24rpx; }
.training-head { display: flex; justify-content: space-between; gap: 18rpx; }
.training-title { display: block; color: $text-white; font-size: 34rpx; font-weight: 900; }
.training-sub { display: block; margin-top: 10rpx; color: $text-gray; font-size: 24rpx; line-height: 1.5; }
.duration { color: $brand-primary; font-size: 24rpx; font-weight: 900; white-space: nowrap; }
.step-list { margin-top: 20rpx; display: flex; flex-direction: column; gap: 14rpx; }
.step { min-height: 72rpx; padding: 14rpx; border-radius: 12rpx; background: #242424; display: flex; align-items: center; gap: 14rpx; border: 1rpx solid transparent; }
.step.current { border-color: rgba(204,255,0,.6); }
.step-index { width: 38rpx; height: 38rpx; border-radius: 50%; background: rgba(204,255,0,.14); color: $brand-primary; display: flex; align-items: center; justify-content: center; text-align: center; line-height: 38rpx; font-size: 22rpx; font-weight: 900; }
.step-text { flex: 1; color: $text-white; font-size: 25rpx; line-height: 1.45; }
.feedback-box { margin-top: 18rpx; padding: 18rpx; border-radius: 12rpx; background: rgba(204,255,0,.1); }
.feedback-title { display: block; color: $brand-primary; font-size: 26rpx; font-weight: 900; }
.feedback-copy { display: block; margin-top: 8rpx; color: $text-white; font-size: 24rpx; line-height: 1.5; }
.start-btn { width: 100%; min-height: 78rpx; margin-top: 20rpx; padding: 10rpx 24rpx; border-radius: 999rpx; background: $brand-primary; color: #121212; font-size: 28rpx; line-height: 1.25; font-weight: 900; }
.modal-mask { position: fixed; inset: 0; z-index: 20; display: flex; align-items: flex-end; background: rgba(0,0,0,.58); }
.practice-modal, .plan-basket-modal { width: 100%; padding: 30rpx 24rpx calc(30rpx + env(safe-area-inset-bottom)); border-radius: 26rpx 26rpx 0 0; background: #181818; border: 1rpx solid $border-color; box-sizing: border-box; }
.practice-modal { padding-bottom: calc(120rpx + env(safe-area-inset-bottom)); }
.plan-basket-modal { max-height: calc(100vh - var(--top-safe-height) - 40rpx); overflow: hidden; }
.modal-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 18rpx; }
.close-btn { width: 58rpx; height: 58rpx; border-radius: 50%; background: #2C2C2E; color: $text-white; font-size: 34rpx; line-height: 1; padding: 0; display: flex; align-items: center; justify-content: center; }
.modal-scroll { margin: 22rpx -24rpx 4rpx; }
.modal-row { padding-bottom: 20rpx; }
.modal-card { width: 300rpx; }
.plan-list { max-height: 68vh; margin-top: 22rpx; }
.plan-card { margin-bottom: 18rpx; padding: 22rpx; border-radius: 18rpx; background: #202020; border: 1rpx solid $border-color; }
.plan-card-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 18rpx; }
.plan-card-title { display: block; color: $text-white; font-size: 31rpx; font-weight: 900; }
.plan-progress { min-width: 78rpx; min-height: 48rpx; padding: 4rpx 12rpx; border-radius: 999rpx; background: rgba(204,255,0,.14); color: $brand-primary; text-align: center; line-height: 1.2; font-size: 22rpx; font-weight: 900; display: flex; align-items: center; justify-content: center; box-sizing: border-box; }
.plan-card-copy { display: block; margin-top: 12rpx; color: #D8D8D8; font-size: 24rpx; line-height: 1.45; }
.plan-track { margin-top: 18rpx; height: 14rpx; border-radius: 999rpx; background: #303033; overflow: hidden; }
.plan-fill { height: 100%; border-radius: 999rpx; background: $brand-primary; }
.plan-meta-row { margin-top: 14rpx; display: flex; align-items: center; justify-content: space-between; gap: 16rpx; color: $text-gray; font-size: 21rpx; }
.plan-actions { margin-top: 18rpx; display: grid; grid-template-columns: repeat(2, 1fr); gap: 12rpx; }
.plan-secondary { min-height: 70rpx; padding: 8rpx 18rpx; border-radius: 999rpx; font-size: 25rpx; line-height: 1.25; font-weight: 900; text-align: center; white-space: normal; word-break: break-word; }
.plan-secondary { background: #2C2C2E; color: $text-white; }
.plan-secondary.full { grid-column: 1 / -1; }
.practice-kicker { color: $brand-primary; font-size: 24rpx; font-weight: 900; }
.practice-title { display: block; margin-top: 8rpx; color: $text-white; font-size: 36rpx; font-weight: 900; }
.practice-question { display: block; margin-top: 18rpx; color: #D8D8D8; font-size: 28rpx; line-height: 1.5; }
.option-list { margin-top: 22rpx; display: flex; flex-direction: column; gap: 14rpx; }
.option { width: 100%; min-height: 76rpx; padding: 14rpx 18rpx; border-radius: 16rpx; background: #2A2A2D; color: #FFFFFF; border: 2rpx solid #3A3A3D; font-size: 26rpx; justify-content: flex-start; text-align: left; white-space: normal; word-break: break-word; line-height: 1.35; box-sizing: border-box; }
.option.picked { border-color: $brand-primary; }
.option.correct { background: rgba(204,255,0,.18); color: $brand-primary; }
.option.wrong { background: rgba(255,92,92,.16); color: #FF8585; border-color: #FF5C5C; }
.answer-box { margin-top: 18rpx; padding: 18rpx; border-radius: 14rpx; background: rgba(204,255,0,.1); }
.answer-box.wrong { background: rgba(255,92,92,.12); }
.answer-title { display: block; color: $brand-primary; font-size: 28rpx; font-weight: 900; }
.answer-box.wrong .answer-title { color: #FF8585; }
.answer-copy { display: block; margin-top: 8rpx; color: #D8D8D8; font-size: 24rpx; line-height: 1.45; }
.allow-btn, .secondary-btn { width: 100%; min-height: 78rpx; margin-top: 22rpx; padding: 10rpx 24rpx; border-radius: 999rpx; background: $brand-primary; color: #121212; font-size: 28rpx; line-height: 1.25; font-weight: 900; text-align: center; white-space: normal; word-break: break-word; }
.secondary-btn { margin-top: 14rpx; background: #2C2C2E; color: $text-white; }

@media screen and (max-width: 430px) {
	.stats-card {
		padding: 26rpx;
		flex-direction: column;
		gap: 22rpx;
	}

	.level-block {
		width: 100%;
	}

	.stat-list {
		width: 100%;
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 10rpx;
		text-align: center;
	}

	.stat-item {
		min-height: 82rpx;
		border-radius: 14rpx;
		background: rgba(255, 255, 255, .04);
		justify-content: center;
	}

	.daily-card {
		align-items: flex-start;
	}

	.daily-btn {
		min-width: 136rpx;
		max-width: 190rpx;
		padding: 8rpx 16rpx;
	}

	.plan-card-head,
	.plan-meta-row {
		align-items: flex-start;
	}

	.plan-meta-row {
		flex-direction: column;
	}
}
</style>
