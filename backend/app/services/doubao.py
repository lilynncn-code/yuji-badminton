import json
from typing import Dict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import settings


def _fallback_advice(payload) -> Dict[str, str]:
    if payload.score >= 88:
        improvement = "节奏不错，下一组可以增加连续动作数量。"
    elif payload.reps < 8:
        improvement = "先放慢速度，把启动步和回中动作做完整。"
    else:
        improvement = "回中稍慢，注意击球后马上回到准备位置。"
    return {
        "advice": f"本次完成 {payload.reps} 次，评分 {int(payload.score)}。{improvement}",
        "improvement": improvement,
        "source": "local",
    }


def get_training_advice(payload) -> Dict[str, str]:
    if not settings.doubao_api_key or not settings.doubao_model:
        return _fallback_advice(payload)

    prompt = (
        "你是羽毛球教练。请用中文给一条短训练建议，语气直接、鼓励。"
        f"训练项目：{payload.lesson_name}。"
        f"次数：{payload.reps}。评分：{payload.score}。"
        f"识别率：{payload.confidence}。时长：{payload.duration_seconds}秒。"
        f"现场反馈：{payload.feedback or '无'}。"
        "只返回JSON，格式为：{\"advice\":\"...\",\"improvement\":\"...\"}。"
    )
    data = json.dumps(
        {
            "model": settings.doubao_model,
            "messages": [
                {"role": "system", "content": "你只输出简短中文JSON。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.4,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = Request(
        f"{settings.doubao_base_url.rstrip('/')}/chat/completions",
        data=data,
        headers={
            "Authorization": f"Bearer {settings.doubao_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=12) as response:
            result = json.loads(response.read().decode("utf-8"))
        content = result["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        fallback = _fallback_advice(payload)
        return {
            "advice": str(parsed.get("advice") or "").strip() or fallback["advice"],
            "improvement": str(parsed.get("improvement") or "").strip() or fallback["improvement"],
            "source": "doubao",
        }
    except (HTTPError, URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError):
        return _fallback_advice(payload)
