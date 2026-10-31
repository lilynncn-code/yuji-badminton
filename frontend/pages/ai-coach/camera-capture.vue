<template>
	<view class="page">
		<view class="preview">
			<!-- #ifdef H5 -->
			<video
				v-if="cameraEnabled"
				ref="videoRef"
				id="coachCamera"
				class="camera-video"
				:class="{ mirrored: mirrorPreview }"
				autoplay
				muted
				playsinline
				webkit-playsinline
				x5-playsinline
			></video>
				<image v-else class="court" :src="imageLibrary[0].url" mode="aspectFill" />
				<!-- #endif -->
				<!-- #ifdef APP-PLUS -->
				<template v-for="attempt in nativeAttempts" :key="attempt.generation"><live-pusher
					v-if="cameraEnabled"
					id="coachNativeCamera"
					class="camera-view"
					mode="SD"
					device-position="back"
					:muted="true"
					:enable-mic="false"
					:enable-camera="true"
					:auto-focus="true"
					:beauty="0"
					:whiteness="0"
					aspect="9:16"
					@statechange="onNativeCameraState($event, attempt)"
					@error="onNativeCameraError($event, attempt)"
				/></template>
			<image v-if="!cameraEnabled" class="court" :src="imageLibrary[0].url" mode="aspectFill" />
			<!-- #endif -->
			<!-- #ifndef H5 -->
			<!-- #ifndef APP-PLUS -->
			<image class="court" :src="imageLibrary[0].url" mode="aspectFill" />
			<!-- #endif -->
			<!-- #endif -->
			<view class="dark-layer"></view>
			<view class="scan-line"></view>
			<view class="hud top">
				<text class="pill live">{{ $tr(liveLabel) }}</text>
				<text class="pill">{{ $tr(lessonName) }}</text>
			</view>
			<button v-if="!running" class="camera-permission" :disabled="cameraBusy || savingRecord || finishing || Boolean(clipPath)" @click="startRecognition">{{ $tr(cameraBusy ? '正在打开...' : resultVisible ? '重新开始识别' : '打开摄像头开始识别') }}</button>
			<view v-if="cameraMessage" class="camera-tip">{{ $tr(cameraMessage) }}</view>
			<view v-if="false" class="skeleton" :class="{ active: running }">
				<view class="joint head"></view>
				<view class="limb body"></view>
				<view class="limb arm-left"></view>
				<view class="limb arm-right"></view>
				<view class="limb leg-left"></view>
				<view class="limb leg-right"></view>
				<view class="joint foot-left"></view>
				<view class="joint foot-right"></view>
			</view>
			<view class="target-zone">
				<view class="zone-line"></view>
				<text>{{ $tr("保持全身入框") }}</text>
			</view>
			<view class="hud bottom">
				<view class="hud-stat">
					<text class="hud-value">{{ $tr(reps) }}</text>
					<text class="hud-label">{{ $tr("记录次数") }}</text>
				</view>
				<view class="hud-stat">
					<text class="hud-value">{{ $tr(score) }}</text>
					<text class="hud-label">{{ $tr("目标完成率") }}</text>
				</view>
				<view class="hud-stat">
					<text class="hud-value">{{ $tr("{0}s", [secondsLeft]) }}</text>
					<text class="hud-label">{{ $tr("剩余") }}</text>
				</view>
			</view>
		</view>

		<view class="panel">
            <view v-if="pendingRecords" class="result"><text>{{ $tr("本机有 {0} 次训练尚待确认保存。", [pendingRecords]) }}</text><button class="ghost" @click="openHistory">{{ $tr("到训练记录继续保存") }}</button></view>
            <text v-if="draftError" class="desc">{{ $tr(draftError) }}</text>
            <!-- #ifdef H5 -->
            <view v-if="!running && !resultVisible" class="record-option"><switch :checked="keepVideo" @change="keepVideo=$event.detail.value"/><text>{{ $tr("保存本次训练录像（不录声音，仅本人可看）") }}</text></view>
            <!-- #endif -->
            <text v-if="clipStatus" class="desc">{{ $tr(clipStatus) }}</text>
			<view class="status-row">
				<view>
					<text class="title">{{ $tr(running ? '识别运行中' : resultVisible ? '训练完成' : '准备识别') }}</text>
					<text class="desc">{{ $tr(currentFeedback) }}</text>
				</view>
				<view class="confidence">
					<text>{{ $tr(confidence ? '已看清' : '未看清') }}</text>
					<text>{{ $tr("全身入框") }}</text>
				</view>
			</view>
			<view class="meter">
				<view class="fill" :style="{ width: progress + '%' }"></view>
			</view>
			<view class="metric-row">
				<view v-for="metric in metrics" :key="metric.label" class="metric">
					<text class="metric-value">{{ $tr(metric.value) }}</text>
					<text class="metric-label">{{ $tr(metric.label) }}</text>
				</view>
			</view>
			<button v-if="running && mode === 'manual'" class="button" @click="recordRep">{{ $tr("记录一次动作") }}</button>
            <button class="button" :disabled="cameraBusy || savingRecord || finishing || Boolean(clipPath)" :hover-class="'click-feedback'" @click="toggleChallenge">{{ $tr(finishing ? '正在结束录像...' : running ? '结束并生成报告' : resultVisible ? '重新开始识别' : cameraBusy ? '正在打开...' : '打开摄像头开始识别') }}</button>
			<view v-if="resultVisible" class="result">
				<text class="result-title">{{ $tr("训练记录") }}</text>
				<text>{{ $tr("记录方式：{0}", [mode === 'pose' ? '画面计数' : '自己记录']) }}</text>
				<text>{{ $tr("需要改进：{0}", [improvement]) }}</text>
				<text v-if="recordError">{{ $tr(recordError) }}</text>
                <button v-if="!recordSaved" class="ghost" :disabled="savingRecord||finishing" @click="saveReport">{{ $tr(savingRecord ? '保存中' : '重试保存记录') }}</button>
                <button v-if="clipPath" class="ghost" :disabled="savingRecord" @click="saveReport">{{ $tr(savingRecord?'视频保存中':'重试保存训练视频') }}</button>
                <button v-if="clipPath" class="ghost" :disabled="savingRecord" @click="discardClip">{{ $tr("放弃本次未保存的视频") }}</button>
                <button v-if="recordSaved && !clipPath && !savedClipId" class="ghost" :disabled="savingRecord" @click="chooseTrainingClip">{{ $tr("附上本次训练视频") }}</button>
                <button class="ghost" @click="goBackCoach">{{ $tr("返回 AI 教学") }}</button>
			</view>
		</view>
	</view>
</template>

<script setup>
import { computed, getCurrentInstance, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { imageLibrary } from '../../data/app-data'
import { saveTrainingRecord, uploadTrainingVideo, attachTrainingVideo, findTrainingVideoUpload, abandonTrainingVideoUpload } from '../../utils/training-api'
import { getAuthToken } from '../../utils/auth'
import { getUser } from '../../utils/store'
import { prepareTrainingVideoDraft, readTrainingVideoDraft, updateTrainingVideoDraft, clearTrainingVideoDraft } from '../../utils/training-video-draft'
import { createTrainingRecorder } from '../../utils/training-recorder'
import { readTrainingRecordDrafts, keepTrainingRecordDraft, clearTrainingRecordDraft } from '../../utils/training-record-draft'
import { onHide, onShow, onLoad } from '@dcloudio/uni-app'

const lessonName = ref('AI 步伐挑战')
const running = ref(false)
const resultVisible = ref(false)
const cameraEnabled = ref(false)
const cameraBusy = ref(false)
const cameraMessage = ref('点按钮后会请求摄像头权限，请把手机放在场边。')
const mirrorPreview = ref(false)
const pendingNativeStart = ref(false)
const nativeCameraReady = ref(false)
const nativeAttempts = ref([])
const videoRef = ref(null)
const reps = ref(0)
const score = ref(0)
const confidence = ref(0)
const secondsLeft = ref(30)
const currentFeedback = ref('把手机靠在场边，身体完整进入画面。')
const bestRep = ref(1)
const improvement = ref('启动步完成后回中再快一点。')
const taskId = ref('')
const mode = ref('manual')
const savingRecord = ref(false)
const recordSaved = ref(false)
const recordError = ref('')
const pendingRecords=ref(0),draftError=ref('')
const keepVideo = ref(false), clipStatus = ref(''), clipPath = ref(''), finishing = ref(false), savedClipId = ref(0)
let sessionRecorder = null, savedRecordId = 0, uploadedClipId = 0
function releaseClip() {
    // #ifdef H5
    if (clipPath.value.startsWith('blob:')) URL.revokeObjectURL(clipPath.value)
    // #endif
    clipPath.value = ''
}
async function discardClip() {
    if(!sameSave(saveContext())||savingRecord.value||finishing.value)return
    const c=saveContext(),recordId=savedRecordId
    savingRecord.value=true
    try{
        const draft=recordId?readTrainingVideoDraft(c.owner,recordId):null
        if(draft){await abandonTrainingVideoUpload(draft.request_key);clearTrainingVideoDraft(c.owner,recordId,draft.request_key)}
        if(!sameSave(c))return
        releaseClip();clipStatus.value='本次视频未保存，训练次数和时长仍保留。'
    }catch(e){if(sameSave(c))recordError.value=e.message}
    finally{if(sameSave(c))savingRecord.value=false}
}
function chooseTrainingClip() {
    if(!sameSave(saveContext())||!recordSaved.value||savingRecord.value||finishing.value)return
    const c=saveContext()
    uni.chooseVideo({sourceType:['album'],maxDuration:300,success:async r=>{
        if(!sameSave(c)||savingRecord.value)return
        if (r.size > 32*1024*1024) { uni.showToast({title:'请选择不超过32MB的视频',icon:'none'});return }
        releaseClip(); clipPath.value=r.tempFilePath; uploadedClipId=0; await saveReport()
    }})
}
const elapsed = ref(0)
const targetSeconds = ref(30)
let startedAt = 0
let pageActive = false
let startGeneration = 0
let sessionKey = ''
let trainingOwner=String(getUser()?.id||'')
let trainingToken=getAuthToken(),runContext=null
function saveContext(){return {generation:startGeneration,owner:trainingOwner,token:trainingToken}}
function sameSave(c){return Boolean(c&&pageActive&&c.token&&c.generation===startGeneration&&c.owner===trainingOwner&&c.token===trainingToken&&c.owner===String(getUser()?.id||'')&&c.token===getAuthToken())}
onShow(() => {
    const owner=String(getUser()?.id||'')
    if(trainingOwner!==owner||trainingToken!==getAuthToken()){
        suspendTraining();lastPayload=null;savedRecordId=0;uploadedClipId=0;recordSaved.value=false;recordError.value='';resultVisible.value=false;savedClipId.value=0
        reps.value=0;score.value=0;confidence.value=0;elapsed.value=0;secondsLeft.value=targetSeconds.value;mode.value='manual';clipStatus.value='';keepVideo.value=false
        cameraMessage.value='点按钮后会请求摄像头权限，请把手机放在场边。';currentFeedback.value='把手机靠在场边，身体完整进入画面。'
        trainingOwner=owner;trainingToken=getAuthToken()
    }
    pageActive=true
    if(!trainingToken){uni.reLaunch({url:'/pages/auth/login'});return}
    refreshRecordDrafts()
})
function refreshRecordDrafts(){
    if(!sameSave(saveContext()))return
    try{pendingRecords.value=readTrainingRecordDrafts(trainingOwner).length;draftError.value=''}
    catch(e){pendingRecords.value=0;draftError.value=e.message||'本机待确认训练暂时没有读到，请到训练记录重新读取'}
}
function rememberRecord(){
    try{keepTrainingRecordDraft(trainingOwner,lastPayload);refreshRecordDrafts();return true}
    catch(e){draftError.value=`${e.message||'本机未能保留待确认训练'}。当前页面仍保留本次内容，请先重试保存，关闭页面后可能丢失。`;return false}
}
let detector = null
let lastPayload = null
onLoad(query => { taskId.value = query.task || ''; targetSeconds.value = query.task ? 30 + ((Number(query.task.match(/m(\d+)/)?.[1]) || 1) - 1) % 3 * 30 : 30; secondsLeft.value = targetSeconds.value })
function suspendTraining() {
    pageActive = false
    startGeneration++
    runContext=null
    cameraBusy.value = false
    savingRecord.value = false
    finishing.value = false
    clearInterval(timer)
    if (running.value) { running.value = false; currentFeedback.value = '本次训练已停止，返回后可重新开始。' }
    detector?.stop(); detector = null; stopCamera()
    sessionRecorder?.cancel(); sessionRecorder = null; releaseClip()
}
onHide(suspendTraining)

let timer = null
let cameraStream = null
let nativeCameraTimer = null
let nativeCameraContext = null
const pageInstance = getCurrentInstance()

const progress = computed(() => Math.round(elapsed.value / targetSeconds.value * 100))
const liveLabel = computed(() => cameraEnabled.value ? 'CAMERA LIVE' : '等待摄像头')
const metrics = computed(() => [
    { label: '记录方式', value: mode.value === 'pose' ? '画面计数' : '自己记录' },
    { label: '已训练', value: `${elapsed.value}s` },
    { label: '本组目标', value: '10 次' }
])

onMounted(() => {
	const pages = getCurrentPages()
	const route = pages[pages.length - 1]
	if (route?.options?.lesson) {
		lessonName.value = decodeURIComponent(route.options.lesson)
	}
})

onUnmounted(suspendTraining)

async function openH5Camera(c) {
	if(!sameSave(c))return false
	if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
		cameraError(cameraUnavailableText())
		return false
	}
	if (!isSecureCameraAddress()) {
		cameraError(cameraUnavailableText())
		return false
	}
	try {
		stopCamera()
		cameraMessage.value = '正在请求摄像头权限。'
		const stream = await requestH5CameraStream(c)
        if (!sameSave(c)) { stream.getTracks().forEach(t => t.stop()); return false }
        cameraStream = stream
	} catch (error) {
		if(!sameSave(c))return false
		stopCamera()
		mirrorPreview.value = false
		cameraError(cameraUnavailableText(error))
		return false
	}
	const videoTrack = cameraStream.getVideoTracks?.()[0]
	const facingMode = videoTrack?.getSettings?.().facingMode
	mirrorPreview.value = facingMode ? facingMode !== 'environment' : !isMobileBrowser()
	cameraEnabled.value = true
	cameraMessage.value = ''
	await nextTick()
	if(!sameSave(c))return false
	const video = await waitForH5Video()
    if (!sameSave(c)) return false
	if (!video) {
		cameraError('摄像头画面尚未就绪，请重试。')
		return false
	}
	try {
		video.srcObject = cameraStream
		await video.play?.()
		if(!sameSave(c))return false
		cameraMessage.value = ''
	} catch (error) {
		if(!sameSave(c))return false
		cameraMessage.value = '摄像头已打开，如未看到画面请点一下页面后重试。'
	}
	return true
}

function waitForH5Video() {
	return new Promise((resolve) => {
		let count = 0
		const findVideo = () => {
			const video = h5VideoElement()
			if (video || count >= 6) {
				resolve(video || null)
				return
			}
			count += 1
			setTimeout(findVideo, 80)
		}
		findVideo()
	})
}

function h5VideoElement() {
    const root = videoRef.value?.$el || videoRef.value || document.getElementById('coachCamera')
    return root?.tagName?.toLowerCase() === 'video' ? root : root?.querySelector?.('video')
}

async function requestH5CameraStream(c) {
	const options = h5CameraOptions()
	let lastError = null
	for (const option of options) {
		if(!sameSave(c))throw new Error('本次相机操作已结束')
		try {
			return await navigator.mediaDevices.getUserMedia(option)
		} catch (error) {
			if(!sameSave(c))throw error
			lastError = error
			if (!shouldTryNextCameraOption(error)) break
		}
	}
	throw lastError || new Error('camera unavailable')
}

function h5CameraOptions() {
	const stableVideo = { width: { ideal: 640 }, height: { ideal: 480 }, frameRate: { ideal: 24, max: 30 } }
	if (isMobileBrowser()) {
		return [
			{ video: { ...stableVideo, facingMode: { ideal: 'environment' } }, audio: false },
			{ video: { facingMode: { ideal: 'environment' } }, audio: false },
			{ video: stableVideo, audio: false },
			{ video: true, audio: false }
		]
	}
	return [
		{ video: stableVideo, audio: false },
		{ video: true, audio: false }
	]
}

function shouldTryNextCameraOption(error) {
	const name = error?.name || ''
	return ['OverconstrainedError', 'ConstraintNotSatisfiedError', 'NotFoundError', 'NotReadableError', 'AbortError'].includes(name)
}

function isMobileBrowser() {
	if (typeof navigator === 'undefined') return false
	return /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent || '')
}

function isSecureCameraAddress() {
	if (typeof window === 'undefined') return true
	const hostname = window.location?.hostname
	return window.isSecureContext || window.location?.protocol === 'https:' || ['localhost', '127.0.0.1', '::1'].includes(hostname)
}

function cameraUnavailableText(error) {
	if (!isSecureCameraAddress()) {
		return '当前浏览器地址不能打开摄像头，请用 localhost 打开，或直接运行到手机 App。'
	}
	const name = error?.name || ''
	if (name === 'NotFoundError') return '没有找到可用摄像头，请接好摄像头后重试。'
	if (name === 'NotReadableError') return '摄像头可能正被其他软件占用，请关闭后重试。'
	return '摄像头没有打开，请允许摄像头权限后重试。'
}

function stopCamera() {
	nativeAttempts.value=[]
	clearTimeout(nativeCameraTimer)
	nativeCameraTimer = null
	pendingNativeStart.value = false
	nativeCameraReady.value = false
	// #ifdef APP-PLUS
	if (nativeCameraContext) {
		nativeCameraContext.stopPreview?.()
		nativeCameraContext.stop?.()
		nativeCameraContext = null
	}
	// #endif
	if (cameraStream) {
		cameraStream.getTracks().forEach((track) => track.stop())
		cameraStream = null
	}
	mirrorPreview.value = false
	cameraEnabled.value = false
}

async function startRecognition() {
	if (running.value || cameraBusy.value || savingRecord.value || finishing.value || clipPath.value || !sameSave(saveContext())) return
	if(lastPayload&&!recordSaved.value&&!rememberRecord())return
	try{
		if(readTrainingRecordDrafts(trainingOwner).length>=30){draftError.value='本机已有30次待确认训练，请先到训练记录核对后再开始';return}
	}catch(e){draftError.value=e.message||'本机待确认训练尚未读清，请到训练记录重新读取';return}
	const c={...saveContext(),generation:++startGeneration}
	if (cameraEnabled.value) {
		// #ifdef APP-PLUS
		if (pendingNativeStart.value && !nativeCameraReady.value) {
			cameraMessage.value = '摄像头还在打开，请稍等。'
			currentFeedback.value = '摄像头还在打开，请稍等。'
			return
		}
		// #endif
		startChallenge(c)
		return
	}
	cameraBusy.value = true
	currentFeedback.value = '正在打开摄像头。'
	let ready = true
	// #ifdef H5
	ready = await openH5Camera(c)
	// #endif
	// #ifdef APP-PLUS
	startNativeCamera(c)
	return
	// #endif
	// #ifndef H5
	// #ifndef APP-PLUS
	cameraError('当前设备暂不支持打开摄像头，请换手机 App 或电脑浏览器重试。')
	return
	// #endif
	// #endif
	if(!sameSave(c))return
	cameraBusy.value = false
	if (!ready) return
	startChallenge(c)
}

async function startNativeCamera(c) {
	if(!sameSave(c))return
	clearTimeout(nativeCameraTimer)
	const allowed = await requestNativeCameraPermission()
    if (!sameSave(c)) return
	if (!allowed) {
		cameraError('摄像头没有打开，请允许摄像头权限后重试。')
		return
	}
	pendingNativeStart.value = true
	nativeAttempts.value=[c]
	nativeCameraReady.value = false
	cameraEnabled.value = true
	cameraMessage.value = '正在打开摄像头。'
	nextTick(() => {
		if(!sameSave(c))return
		try {
			nativeCameraContext = uni.createLivePusherContext('coachNativeCamera', pageInstance?.proxy)
			if (!nativeCameraContext?.startPreview) {
				cameraError('摄像头没有打开，请用新版真机调试基座重新运行。')
				return
			}
				setTimeout(() => {
					if (!sameSave(c)||!pendingNativeStart.value || !nativeCameraContext?.startPreview) return
					nativeCameraContext.startPreview({
						success: () => confirmNativeCameraReady(c),
						fail: () => nativeCameraFailed('摄像头没有打开，请允许摄像头权限后重试。',c)
					})
				}, 350)
				nativeCameraTimer = setTimeout(() => {
					if (!sameSave(c)||!pendingNativeStart.value) return
					cameraError('摄像头打开超时，请重试。')
				}, 6000)
		} catch (error) {
			if(!sameSave(c))return
			cameraError('摄像头没有打开，请用新版真机调试基座重新运行。')
		}
	})
}

function requestNativeCameraPermission() {
	return new Promise((resolve) => {
		// #ifdef APP-PLUS
		try {
			if (typeof plus === 'undefined' || !plus.android?.requestPermissions) {
				resolve(true)
				return
			}
			plus.android.requestPermissions(
				['android.permission.CAMERA'],
				(result) => {
					const denied = [
						...(result?.deniedAlways || []),
						...(result?.deniedPresent || [])
					]
					resolve(!denied.includes('android.permission.CAMERA'))
				},
				() => resolve(false)
			)
		} catch (error) {
			resolve(true)
		}
		// #endif
		// #ifndef APP-PLUS
		resolve(true)
		// #endif
	})
}

function onNativeCameraState(event,c) {
	if(!sameSave(c))return
	const code = nativeEventCode(event)
	if (code === 1003 || code === 1007) {
		confirmNativeCameraReady(c)
		return
	}
	if (isNativeCameraOpenError(code)) {
		nativeCameraFailed('摄像头没有打开，请允许摄像头权限后重试。',c)
	}
}

function isNativeCameraOpenError(code) {
	return [1001, 1002, -1301, -1302].includes(code)
}

function confirmNativeCameraReady(c) {
	if (!sameSave(c)||!pendingNativeStart.value) return
	clearTimeout(nativeCameraTimer)
	nativeCameraTimer = null
	pendingNativeStart.value = false
	nativeCameraReady.value = true
	cameraBusy.value = false
	cameraMessage.value = ''
	startChallenge(c)
}

function onNativeCameraError(event,c) {
	if(!sameSave(c))return
	const code = nativeEventCode(event)
	if (cameraEnabled.value && (nativeCameraReady.value || running.value) && !isNativeCameraOpenError(code)) {
		cameraBusy.value = false
		cameraMessage.value = ''
		return
	}
	if (isNativeCameraOpenError(code)) {
		nativeCameraFailed('摄像头没有打开，请允许摄像头权限后重试。',c)
		return
	}
	if (cameraEnabled.value) {
		cameraBusy.value = false
		return
	}
	nativeCameraFailed('摄像头不可用，请检查权限后重试。',c)
}

function nativeCameraFailed(text,c) {
	if(!sameSave(c))return
	cameraError(text)
}

function nativeEventCode(event) {
	const detail = event?.detail || {}
	return Number(detail.errCode ?? detail.code)
}

async function startChallenge(c=saveContext()) {
    if(!sameSave(c)||running.value||savingRecord.value||finishing.value)return
	if (!cameraEnabled.value) {
		currentFeedback.value = '请先打开摄像头。'
		return
	}
	// #ifdef APP-PLUS
	if (pendingNativeStart.value && !nativeCameraReady.value) {
		cameraMessage.value = '摄像头还在打开，请稍等。'
		currentFeedback.value = '摄像头还在打开，请稍等。'
		return
	}
	// #endif
    clearInterval(timer)
    detector?.stop(); detector = null
    running.value = false
    resultVisible.value = false
    recordSaved.value = false
    recordError.value = ''
    lastPayload = null
    releaseClip(); savedRecordId = 0; uploadedClipId = 0; savedClipId.value=0; clipStatus.value=''
    reps.value = 0; score.value = 0; confidence.value = 0; elapsed.value = 0
    secondsLeft.value = targetSeconds.value
    mode.value = 'manual'
    // #ifdef H5
    cameraBusy.value = true
    cameraMessage.value = '正在准备画面计数，请保持全身入框。'
    try {
        const { createPoseCounter } = await import('../../utils/pose')
        if(!sameSave(c))return
        const preparedDetector = await createPoseCounter(lessonName.value, sample => {
            if (!sameSave(c)||!running.value) return
            if (sample.unavailable) {
                mode.value = 'manual'; confidence.value = 0
                cameraMessage.value = '画面计数已停止，请点击“记录一次动作”继续自己记录。'
                currentFeedback.value = cameraMessage.value
                return
            }
            confidence.value = sample.visible ? 100 : 0
            if (sample.counted) { reps.value++; score.value = Math.min(100, reps.value * 10) }
            currentFeedback.value = !sample.visible ? '没有看清全身，请后退或调整光线。' : sample.footwork ? '向两侧移动，再回到起点；只记录移动次数。' : '举高手臂，再自然放下；只记录动作次数。'
        })
        if (!sameSave(c)) { preparedDetector.stop(); return }
        detector = preparedDetector
        mode.value = 'pose'
        detector.start(h5VideoElement())
    } catch (error) {
        if(!sameSave(c))return
        console.warn('Training movement counter unavailable', error)
        detector?.stop(); detector = null
        cameraMessage.value = '画面计数暂不可用，本次由你点击记录动作，不会自动生成次数或动作评分。'
    } finally { if(sameSave(c))cameraBusy.value = false }
    // #endif
    if (!sameSave(c)) return
    // #ifdef H5
    if (keepVideo.value) {
        try { sessionRecorder=createTrainingRecorder(cameraStream);clipStatus.value='正在录制本次训练，不录声音。' }
        catch(e){clipStatus.value=e.message}
    }
    // #endif
    sessionKey = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`
    if (mode.value === 'pose') cameraMessage.value = '画面只计算可见动作次数，无法判断击球是否标准。'
    else cameraMessage.value = '自己记录模式：每完成一个动作，点击“记录一次”。'
    running.value = true
    runContext=c
    startedAt = Date.now()
    currentFeedback.value = cameraMessage.value
    timer = setInterval(tick, 250)
}

function tick() {
    if(!sameSave(runContext)){suspendTraining();return}
    elapsed.value = Math.min(targetSeconds.value, Math.floor((Date.now() - startedAt) / 1000))
    secondsLeft.value = Math.max(0, targetSeconds.value - elapsed.value)
    if (secondsLeft.value === 0) finishChallenge()
}
function recordRep() {
    if(!sameSave(runContext)){suspendTraining();return}
    if (running.value && mode.value === 'manual') { reps.value=Math.min(10000,reps.value+1); score.value = Math.min(100, reps.value * 10) }
}
async function saveReport() {
    if (!sameSave(saveContext())||running.value||finishing.value||!lastPayload || savingRecord.value || (recordSaved.value && !clipPath.value)) return
    const c=saveContext(),payload={...lastPayload},path=clipPath.value
    if(!recordSaved.value)rememberRecord()
    savingRecord.value=true
    try{
        const recordId=savedRecordId||(await saveTrainingRecord(payload)).id
        try{clearTrainingRecordDraft(c.owner,payload.request_key);if(sameSave(c))refreshRecordDrafts()}
        catch{if(sameSave(c))draftError.value='本次训练已保存，但本机待确认列表未能清理；到训练记录再次确认也不会重复增加记录。'}
        if(getAuthToken()!==c.token||String(getUser()?.id||'')!==c.owner)return
        if(sameSave(c)){savedRecordId=recordId;recordSaved.value=true;recordError.value='';currentFeedback.value='训练记录已保存，可在“我的训练记录”查看。'}
        // The history page can resume this video even after leaving the camera page.
        const draft=path?prepareTrainingVideoDraft(c.owner,recordId):null
        if(!sameSave(c))return
        if(path){
            clipStatus.value='正在保存训练视频…'
            let clip
            try{clip=await findTrainingVideoUpload(draft.request_key)}catch(e){if(e.status!==404)throw e}
            if(!sameSave(c))return
            if(!clip)clip=await uploadTrainingVideo(path,draft.request_key)
            if(!updateTrainingVideoDraft(c.owner,recordId,draft.request_key,clip)||!sameSave(c))return
            uploadedClipId=clip.id
            await attachTrainingVideo(recordId,clip.id)
            clearTrainingVideoDraft(c.owner,recordId,draft.request_key)
            if(!sameSave(c))return
            savedClipId.value=clip.id;releaseClip();clipStatus.value='训练视频已保存，可在“我的训练记录”重看，仅本人可看。'
        }
    }catch(error){
        if(!sameSave(c))return
        recordError.value=error.message
        if(recordSaved.value)clipStatus.value='次数和时长已保存，视频尚未确认保存，请重试，也可以去训练记录继续保存。'
        else currentFeedback.value='训练已结束，记录暂未保存，请点击重试。'
    }finally{if(sameSave(c))savingRecord.value=false}
}
async function finishChallenge() {
    const c=runContext
    if (!sameSave(c)){if(running.value)suspendTraining();return}
    if (!running.value||finishing.value) return
    clearInterval(timer)
    elapsed.value = Math.min(targetSeconds.value, Math.floor((Date.now() - startedAt) / 1000))
    running.value = false
    detector?.stop(); detector = null
    if(elapsed.value>=1){
        resultVisible.value=true
        improvement.value = `${mode.value === 'pose' ? '画面记录' : '自己记录'} ${reps.value} 次，训练 ${elapsed.value} 秒。只记录完成情况，不作为动作是否标准的判断。`
        const completedTask = taskId.value && elapsed.value >= targetSeconds.value && reps.value >= 1
        lastPayload = { training_type: lessonName.value, duration_seconds: elapsed.value, score: score.value, reps: reps.value, recording_method: mode.value, request_key: sessionKey,
            advice: improvement.value + (taskId.value && !completedTask ? ' 本次未达到关卡时长或未记录动作，关卡尚未完成。' : ''),
            ...(completedTask ? { task_id: taskId.value } : {}) }
        rememberRecord()
    }
    const recording = sessionRecorder; sessionRecorder = null
    const clipResult = recording?.stop()
    finishing.value = true
    stopCamera()
    try {
        if (clipResult) {
            const blob = await clipResult
            if (blob && sameSave(c)) {
                // #ifdef H5
                clipPath.value=URL.createObjectURL(blob)
                // #endif
            }
        }
    } catch(e) { if(sameSave(c))clipStatus.value=e.message }
    finally { if(sameSave(c))finishing.value=false }
    if (!sameSave(c)) return
    if (elapsed.value < 1) { releaseClip();clipStatus.value='';currentFeedback.value = '训练时间太短，请重新开始。'; return }
    await saveReport()
}

function toggleChallenge() {
	if (running.value) {
		finishChallenge()
		return
	}
	startRecognition()
}

function cameraError(message = '摄像头不可用，请检查权限后重试。') {
	const text = typeof message === 'string' ? message : '摄像头不可用，请检查权限后重试。'
    clearInterval(timer); running.value = false; detector?.stop(); detector = null; sessionRecorder?.cancel();sessionRecorder=null;stopCamera()
	clearTimeout(nativeCameraTimer)
	nativeCameraTimer = null
	pendingNativeStart.value = false
	nativeCameraReady.value = false
	// #ifdef APP-PLUS
	if (nativeCameraContext) {
		nativeCameraContext.stopPreview?.()
		nativeCameraContext.stop?.()
		nativeCameraContext = null
	}
	// #endif
	cameraBusy.value = false
	cameraEnabled.value = false
	cameraMessage.value = text
	currentFeedback.value = text
}

function goBackCoach() {
	if(sameSave(saveContext()))uni.navigateBack()
}
function openHistory(){if(sameSave(saveContext()))uni.navigateTo({url:'/pages/ai-coach/history'})}
</script>

<style lang="scss" scoped>
.page { min-height: 100vh; background: #121212; color: #FFFFFF; }
.preview { position: relative; height: 58vh; min-height: 520rpx; max-height: 760rpx; overflow: hidden; background: #050505; }
.camera-view, .camera-video, .court { position: absolute; inset: 0; z-index: 0; width: 100%; height: 100%; opacity: .86; }
.camera-video { object-fit: cover; display: block; }
.camera-video.mirrored { transform: scaleX(-1); }
.dark-layer { position: absolute; inset: 0; z-index: 1; background: linear-gradient(180deg, rgba(0,0,0,.16), rgba(0,0,0,.52)); pointer-events: none; }
.scan-line { position: absolute; left: 0; right: 0; top: 0; z-index: 2; height: 4rpx; background: #CCFF00; box-shadow: 0 0 20rpx #CCFF00; animation: scan 1.7s infinite ease-in-out; }
.hud { position: absolute; left: 24rpx; right: 24rpx; z-index: 2; display: flex; align-items: center; justify-content: space-between; }
.hud.top { top: calc(24rpx + constant(safe-area-inset-top)); top: calc(24rpx + env(safe-area-inset-top)); }
.hud.bottom { bottom: 28rpx; gap: 14rpx; }
.pill { padding: 10rpx 14rpx; border-radius: 999rpx; background: rgba(0,0,0,.55); color: #FFFFFF; font-size: 22rpx; font-weight: 900; }
.pill.live { color: #CCFF00; }
.camera-permission { position: absolute; left: 48rpx; right: 48rpx; top: calc(18% + constant(safe-area-inset-top)); top: calc(18% + env(safe-area-inset-top)); z-index: 3; min-height: 76rpx; padding: 10rpx 28rpx; border-radius: 999rpx; background: #CCFF00; color: #121212; font-size: 25rpx; line-height: 1.25; font-weight: 900; white-space: normal; }
.camera-tip { position: absolute; left: 60rpx; right: 60rpx; top: calc(18% + 84rpx + constant(safe-area-inset-top)); top: calc(18% + 84rpx + env(safe-area-inset-top)); z-index: 3; padding: 14rpx 18rpx; border-radius: 16rpx; background: rgba(0,0,0,.6); color: #FFFFFF; text-align: center; font-size: 22rpx; line-height: 1.45; }
.hud-stat { flex: 1; padding: 16rpx 8rpx; border-radius: 14rpx; background: rgba(0,0,0,.55); text-align: center; }
.hud-value { display: block; color: #CCFF00; font-size: 34rpx; font-weight: 900; }
.hud-label { display: block; margin-top: 4rpx; color: #D8D8D8; font-size: 20rpx; }
.skeleton { position: absolute; left: 50%; top: 43%; width: 240rpx; height: 280rpx; margin-left: -120rpx; margin-top: -140rpx; z-index: 2; transition: transform .3s ease; }
.skeleton.active { animation: athlete 1s infinite alternate ease-in-out; }
.joint { position: absolute; border-radius: 50%; background: #CCFF00; box-shadow: 0 0 14rpx rgba(204,255,0,.8); }
.head { width: 34rpx; height: 34rpx; left: 102rpx; top: 0; }
.foot-left { width: 22rpx; height: 22rpx; left: 32rpx; top: 220rpx; }
.foot-right { width: 22rpx; height: 22rpx; right: 30rpx; top: 220rpx; }
.limb { position: absolute; height: 8rpx; border-radius: 999rpx; background: #CCFF00; transform-origin: left center; }
.body { width: 95rpx; left: 116rpx; top: 42rpx; transform: rotate(90deg); }
.arm-left { width: 96rpx; left: 116rpx; top: 88rpx; transform: rotate(154deg); }
.arm-right { width: 128rpx; left: 116rpx; top: 88rpx; transform: rotate(24deg); background: #FF5722; }
.leg-left { width: 126rpx; left: 116rpx; top: 142rpx; transform: rotate(134deg); }
.leg-right { width: 138rpx; left: 116rpx; top: 142rpx; transform: rotate(42deg); }
.target-zone { position: absolute; left: 82rpx; right: 82rpx; top: 22%; bottom: 18%; border: 3rpx solid rgba(204,255,0,.58); border-radius: 18rpx; z-index: 2; display: flex; align-items: flex-end; justify-content: center; color: #CCFF00; font-size: 22rpx; padding-bottom: 14rpx; box-sizing: border-box; }
.zone-line { position: absolute; left: 0; right: 0; top: 50%; border-top: 2rpx dashed rgba(204,255,0,.5); }
.panel { padding: 28rpx 24rpx calc(30rpx + env(safe-area-inset-bottom)); }
.record-option{display:flex;gap:16rpx;align-items:center;color:#ccc;font-size:25rpx;line-height:1.6;margin-bottom:24rpx}
.status-row { display: flex; justify-content: space-between; gap: 20rpx; }
.status-row > view:first-child { flex: 1; min-width: 0; }
.title { display: block; color: #CCFF00; font-size: 40rpx; font-weight: 900; }
.desc { display: block; margin-top: 12rpx; color: #D8D8D8; font-size: 26rpx; line-height: 40rpx; }
.confidence { width: 112rpx; height: 112rpx; flex: 0 0 112rpx; border-radius: 50%; background: rgba(204,255,0,.12); color: #CCFF00; display: flex; flex-direction: column; align-items: center; justify-content: center; font-size: 22rpx; font-weight: 900; }
.confidence text:first-child { font-size: 30rpx; }
.meter { margin: 24rpx 0; height: 14rpx; border-radius: 999rpx; background: #2C2C2E; overflow: hidden; }
.fill { height: 100%; background: #CCFF00; transition: width .3s ease; }
.metric-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14rpx; margin-bottom: 22rpx; }
.metric { padding: 18rpx 8rpx; border-radius: 14rpx; background: #1E1E1E; text-align: center; }
.metric-value { display: block; color: #FFFFFF; font-size: 28rpx; font-weight: 900; }
.metric-label { display: block; margin-top: 6rpx; color: #8E8E93; font-size: 21rpx; }
.button, .ghost { width: 100%; min-height: 84rpx; padding: 12rpx 26rpx; border-radius: 999rpx; background: #CCFF00; color: #121212; font-size: 29rpx; line-height: 1.25; font-weight: 900; white-space: normal; }
.result { margin-top: 22rpx; padding: 22rpx; border-radius: 14rpx; background: rgba(204,255,0,.1); color: #FFFFFF; display: flex; flex-direction: column; gap: 10rpx; font-size: 26rpx; line-height: 1.45; }
.result-title { color: #CCFF00; font-size: 30rpx; font-weight: 900; }
.ghost { margin-top: 12rpx; background: #2C2C2E; color: #FFFFFF; }
@keyframes scan { 0%,100% { top: 0; } 50% { top: 92%; } }
@keyframes athlete { from { transform: translateX(-16rpx) rotate(-2deg); } to { transform: translateX(16rpx) rotate(2deg); } }
</style>
