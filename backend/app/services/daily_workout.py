"""Short, manually recorded practice arrangements; no claim to judge shot quality."""
from datetime import datetime, timedelta


def today():
    return (datetime.utcnow()+timedelta(hours=8)).date()


def key(day,step):
    return f'daily-v1-{day.strftime("%Y%m%d")}-{step}'


WARMUP={'title':'轻松热身','seconds':60,'reps':6,'instructions':['原地慢走，让呼吸保持平稳。','轻轻活动肩膀和手腕，不用大力甩动。','一轮慢走加活动算一次，完成后填写实际次数。']}
COOLDOWN={'title':'慢走放松','seconds':60,'reps':6,'instructions':['放慢脚步，让呼吸逐渐平稳。','轻轻放松肩膀和小腿，不憋气、不用力拉扯。','一轮慢走加放松算一次，完成后填写实际次数。']}
DRILLS={
 'front':{'title':'前后移动再回中','seconds':90,'reps':8,'instructions':['在空地中间选一个起点。','向前小步移动，再退回起点；向后小步移动，再回到起点。','前后各往返一次算一组，放慢练，站稳再走。']},
 'side':{'title':'左右小步移动','seconds':90,'reps':8,'instructions':['双膝微弯，身体朝前。','向左小步移动再回到起点，向右移动再回到起点。','左右各往返一次算一组，双脚不交叉，最后站稳。']},
 'racket':{'title':'举拍准备与收拍','seconds':90,'reps':10,'instructions':['双脚站稳，持拍手轻握球拍。','慢慢侧身举拍，再轻轻放下收拍。','举起并放下一次算一次；不用跳起，也不大力挥拍。']},
 'net':{'title':'向前迈步与举拍','seconds':90,'reps':8,'instructions':['面向前方，球拍放在身前。','向前迈一小步，同时将球拍轻轻举起，再回到起点。','往返一次算一次，步子不要过大，回到起点后站稳。']},
 'grip':{'title':'正反手握拍切换','seconds':60,'reps':12,'instructions':['站稳，将球拍放在身前。','轻握球拍，慢慢从正手握拍换到反手，再换回来。','来回切换一次算一组，手指保持放松。']},
 'ready':{'title':'准备姿势与小步启动','seconds':90,'reps':10,'instructions':['双脚自然分开，双膝微弯。','轻轻调整双脚，向前走一小步，再退回准备位置。','回到准备位置算一次，动作轻缓，不用跳高。']},
 'turn':{'title':'持拍侧身与回正','seconds':90,'reps':10,'instructions':['双脚站稳，球拍放在身前。','慢慢侧身，同时举起持拍手，再回正放下。','侧身再回正算一次，身体与手臂一起轻轻转动。']},
 'easy':{'title':'轻松移动回中','seconds':60,'reps':6,'instructions':['选一个起点，保持自然站姿。','向前、向左、向右各走小步并回到起点。','三个方向都走完算一组，保持轻松节奏。']}
}
ARRANGEMENTS=[('front','racket'),('side','net'),('easy','grip'),('front','ready'),('side','net'),('turn','grip'),('easy','racket')]


def plan(day):
    first,second=ARRANGEMENTS[day.weekday()]
    steps=[WARMUP,DRILLS[first],DRILLS[second],COOLDOWN]
    return {'day':day.isoformat(),'title':'今日基础练习','total_seconds':sum(s['seconds'] for s in steps),
        'steps':[{'index':i,**step} for i,step in enumerate(steps)]}
