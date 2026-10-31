// Counts visible movement cycles; it does not judge racket contact or stroke quality.
import { FilesetResolver, PoseLandmarker } from '@mediapipe/tasks-vision'

export async function createPoseCounter(lesson, onSample) {
    const files = await FilesetResolver.forVisionTasks('/static/pose')
    const detector = await PoseLandmarker.createFromOptions(files, {
        baseOptions: { modelAssetPath: '/static/pose/pose_landmarker_lite.task', delegate: 'CPU' },
        runningMode: 'VIDEO', numPoses: 1, minPoseDetectionConfidence: 0.6, minTrackingConfidence: 0.6
    })
    let phase = 'ready', lastRep = 0, active = true, frame = 0, lastFrame = 0, baseline = null, evidence = 0
    const footwork = /步伐|步|移动|防守/.test(lesson)
    function read(video) {
        if (!active) return
        const now = performance.now()
        if (video?.readyState >= 2 && now - lastFrame > 140) {
            lastFrame = now
            let result
            try { result = detector.detectForVideo(video, now) }
            catch (error) {
                active = false
                detector.close()
                onSample({ unavailable: true })
                return
            }
            const p = result.landmarks?.[0]
            const ids = [11, 12, 15, 16, 23, 24, 27, 28]
            const visible = p && ids.every(i => (p[i].visibility || 0) > 0.55)
            if (!visible) { baseline = null; phase = 'ready'; evidence = 0; onSample({ visible: false, counted: false, points: [] }) }
            else {
                const hip = { x: (p[23].x + p[24].x) / 2, y: (p[23].y + p[24].y) / 2 }
                const body = Math.hypot(hip.x - (p[11].x + p[12].x) / 2, hip.y - (p[11].y + p[12].y) / 2)
                if (!baseline) baseline = hip
                const moved = Math.hypot(hip.x - baseline.x, hip.y - baseline.y) / Math.max(body, 0.12)
                const raised = Math.min(p[15].y - p[11].y, p[16].y - p[12].y) < -body * 0.35
                const lowered = p[15].y > p[11].y && p[16].y > p[12].y
                const outward = footwork ? moved > 0.75 : raised
                const returned = footwork ? moved < 0.30 : lowered
                let counted = false
                if (phase === 'ready' && outward) { evidence++; if (evidence >= 2) { phase = 'out'; evidence = 0 } }
                else if (phase === 'out' && returned) { evidence++; if (evidence >= 2 && now - lastRep > 900) { counted = true; lastRep = now; phase = 'ready'; evidence = 0 } }
                else evidence = 0
                onSample({ visible: true, counted, points: p, phase, footwork })
            }
        }
        frame = requestAnimationFrame(() => read(video))
    }
    return { start(video) { frame = requestAnimationFrame(() => read(video)) }, stop() { active = false; cancelAnimationFrame(frame); detector.close() } }
}
