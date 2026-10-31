// Record the existing camera stream without requesting microphone access.
export function createTrainingRecorder(stream, options = {}) {
    const Recorder = options.Recorder || globalThis.MediaRecorder
    if (!Recorder || !stream?.getVideoTracks?.().length) throw new Error('当前设备不支持保存训练录像，可在结束后附上相册视频。')
    const mimeType = ['video/webm;codecs=vp8', 'video/webm', 'video/mp4'].find(type => Recorder.isTypeSupported(type))
    if (!mimeType) throw new Error('当前浏览器不支持录像，请换浏览器，或在结束后附上相册视频。')
    const recorder = new Recorder(stream, { mimeType, videoBitsPerSecond: 1200000 })
    const chunks = [], limit = options.limit || 32 * 1024 * 1024
    let bytes = 0, failure = '', cancelled = false, settled = false, timeout = null, stopping = false
    let resolveResult
    const result = new Promise(resolve => { resolveResult = resolve })
    function settle() {
        if (settled) return
        settled = true; clearTimeout(timeout)
        const blob = !cancelled && !failure && bytes ? new Blob(chunks, { type: recorder.mimeType || mimeType }) : null
        chunks.length = 0
        resolveResult({ blob, error: cancelled ? '' : failure || (!blob ? '没有录到视频，请重新录制。' : '') })
    }
    function stop() {
        if (settled || stopping) return
        stopping = true
        timeout = setTimeout(() => { failure = '录像结束超时，本次训练记录仍可保存。'; settle() }, options.timeoutMs || 8000)
        try { if (recorder.state !== 'inactive') recorder.stop(); else settle() }
        catch { failure = '录像没有正常结束，请重新录制。'; settle() }
    }
    recorder.ondataavailable = event => {
        if (settled || cancelled || !event.data?.size) return
        bytes += event.data.size
        if (bytes > limit) { failure = '录像超过32MB，本次只保存次数和时长。'; chunks.length = 0; stop(); return }
        chunks.push(event.data)
    }
    recorder.onerror = () => { failure = '录像中断，本次训练记录仍可保存。'; stop() }
    recorder.onstop = settle
    recorder.start(1000)
    return {
        async stop() { stop(); const value = await result; if (value.error) throw new Error(value.error); return value.blob },
        cancel() { cancelled = true; chunks.length = 0; stop() }
    }
}
