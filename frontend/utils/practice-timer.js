// Count foreground practice only. Restored progress always starts paused.
export function createPracticeTimer(now=()=>Date.now()){
    let accumulated=0,started=0,running=false
    function milliseconds(){return accumulated+(running?Math.max(0,now()-started):0)}
    return {
        start(){if(!running){started=now();running=true}},
        pause(){accumulated=milliseconds();running=false;return accumulated},
        restore(value=0){accumulated=Math.max(0,Math.min(3600000,Number(value)||0));running=false},
        milliseconds,
        seconds(){return Math.floor(milliseconds()/1000)},
        isRunning(){return running}
    }
}
