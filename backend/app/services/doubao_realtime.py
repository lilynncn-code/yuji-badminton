import asyncio
import gzip
import json
import uuid
import wave
from io import BytesIO
from typing import Any, Dict, List, Optional

import websockets

from app.core.config import settings

CLIENT_FULL_REQUEST = 0b0001
CLIENT_AUDIO_ONLY_REQUEST = 0b0010
SERVER_FULL_RESPONSE = 0b1001
SERVER_ACK = 0b1011
SERVER_ERROR_RESPONSE = 0b1111
MSG_WITH_EVENT = 0b0100
JSON = 0b0001
NO_SERIALIZATION = 0b0000
GZIP = 0b0001


def realtime_ready() -> bool:
    return bool(
        settings.doubao_realtime_api_key
        or (settings.doubao_realtime_app_id and settings.doubao_realtime_access_key)
    )


def fallback_voice_reply() -> Dict[str, Any]:
    return {
        "text": "收到语音。豆包语音钥匙还没填好，我先用本地回复占位。",
        "audio_base64": "",
        "source": "local",
        "events": [],
    }


def _header(
    message_type: int = CLIENT_FULL_REQUEST,
    flags: int = MSG_WITH_EVENT,
    serial_method: int = JSON,
    compression: int = GZIP,
) -> bytearray:
    return bytearray([
        0x11,
        (message_type << 4) | flags,
        (serial_method << 4) | compression,
        0x00,
    ])


def _payload(payload: Dict[str, Any]) -> bytes:
    return gzip.compress(json.dumps(payload, ensure_ascii=False).encode("utf-8"))


def _full_request(event: int, payload: Dict[str, Any], session_id: Optional[str] = None) -> bytes:
    body = _payload(payload)
    request = _header()
    request.extend(int(event).to_bytes(4, "big"))
    if session_id:
        session_bytes = session_id.encode("utf-8")
        request.extend(len(session_bytes).to_bytes(4, "big"))
        request.extend(session_bytes)
    request.extend(len(body).to_bytes(4, "big"))
    request.extend(body)
    return bytes(request)


def _audio_request(session_id: str, audio: bytes) -> bytes:
    body = gzip.compress(audio)
    session_bytes = session_id.encode("utf-8")
    request = _header(CLIENT_AUDIO_ONLY_REQUEST, MSG_WITH_EVENT, NO_SERIALIZATION, GZIP)
    request.extend(int(200).to_bytes(4, "big"))
    request.extend(len(session_bytes).to_bytes(4, "big"))
    request.extend(session_bytes)
    request.extend(len(body).to_bytes(4, "big"))
    request.extend(body)
    return bytes(request)


def _parse_response(data: bytes) -> Dict[str, Any]:
    if not isinstance(data, (bytes, bytearray)) or len(data) < 4:
        return {}

    header_size = data[0] & 0x0F
    message_type = data[1] >> 4
    flags = data[1] & 0x0F
    serial_method = data[2] >> 4
    compression = data[2] & 0x0F
    payload = bytes(data[header_size * 4 :])
    result: Dict[str, Any] = {"message_type": message_type}

    start = 0
    if message_type in {SERVER_FULL_RESPONSE, SERVER_ACK}:
        result["kind"] = "ack" if message_type == SERVER_ACK else "full"
        if flags & MSG_WITH_EVENT:
            result["event"] = int.from_bytes(payload[start : start + 4], "big")
            start += 4
        payload = payload[start:]
        if len(payload) < 4:
            return result
        session_size = int.from_bytes(payload[:4], "big", signed=True)
        payload = payload[4:]
        if session_size > 0:
            result["session_id"] = payload[:session_size].decode("utf-8", errors="ignore")
            payload = payload[session_size:]
        if len(payload) < 4:
            return result
        payload_size = int.from_bytes(payload[:4], "big")
        payload_msg = payload[4 : 4 + payload_size]
    elif message_type == SERVER_ERROR_RESPONSE:
        result["kind"] = "error"
        if len(payload) < 8:
            return result
        result["code"] = int.from_bytes(payload[:4], "big")
        payload_size = int.from_bytes(payload[4:8], "big")
        payload_msg = payload[8 : 8 + payload_size]
    else:
        return result

    if compression == GZIP and payload_msg:
        payload_msg = gzip.decompress(payload_msg)
    if serial_method == JSON and payload_msg:
        result["payload_msg"] = json.loads(payload_msg.decode("utf-8"))
    else:
        result["payload_msg"] = payload_msg
    return result


def _session_payload() -> Dict[str, Any]:
    return {
        "tts": {
            "audio_config": {
                "channel": 1,
                "format": "pcm",
                "sample_rate": 24000,
            },
        },
        "dialog": {
            "bot_name": "好羽教练",
            "system_role": "你是好羽App里的羽毛球语音教练，回答要短、清楚、鼓励用户继续练。",
            "speaking_style": "说话自然，语速适中，每次只讲重点。",
            "extra": {"strict_audit": False},
        },
    }


def _headers() -> Dict[str, str]:
    headers = {
        "X-Api-App-ID": settings.doubao_realtime_app_id,
        "X-Api-Resource-Id": settings.doubao_realtime_resource_id,
        "X-Api-App-Key": settings.doubao_realtime_app_key,
        "X-Api-Connect-Id": str(uuid.uuid4()),
    }
    if settings.doubao_realtime_api_key:
        headers["Authorization"] = f"Bearer {settings.doubao_realtime_api_key}"
    else:
        headers["X-Api-Access-Key"] = settings.doubao_realtime_access_key
    return headers


def _extract_pcm(audio: bytes) -> bytes:
    if audio.startswith(b"RIFF"):
        with wave.open(BytesIO(audio), "rb") as wav:
            return wav.readframes(wav.getnframes())
    return audio


async def ask_realtime_voice(audio: bytes) -> Dict[str, Any]:
    if not realtime_ready() or not audio:
        return fallback_voice_reply()

    session_id = str(uuid.uuid4())
    answer_chunks: List[bytes] = []
    texts: List[str] = []
    events: List[int] = []

    try:
        async with websockets.connect(
            settings.doubao_realtime_url,
            additional_headers=_headers(),
            ping_interval=None,
            open_timeout=12,
            close_timeout=4,
        ) as ws:
            await ws.send(_full_request(1, {}))
            _parse_response(await asyncio.wait_for(ws.recv(), timeout=8))

            await ws.send(_full_request(100, _session_payload(), session_id=session_id))
            _parse_response(await asyncio.wait_for(ws.recv(), timeout=8))

            pcm = _extract_pcm(audio)
            chunk_size = 3200
            for index in range(0, len(pcm), chunk_size):
                chunk = pcm[index : index + chunk_size]
                if len(chunk) < chunk_size:
                    chunk = chunk + (b"\x00" * (chunk_size - len(chunk)))
                await ws.send(_audio_request(session_id, chunk))
                await asyncio.sleep(0.02)

            await ws.send(_full_request(102, {}, session_id=session_id))

            end_at = asyncio.get_running_loop().time() + 12
            while asyncio.get_running_loop().time() < end_at:
                try:
                    response = _parse_response(await asyncio.wait_for(ws.recv(), timeout=1))
                except asyncio.TimeoutError:
                    continue
                if not response:
                    continue
                if response.get("event") is not None:
                    events.append(response["event"])
                payload = response.get("payload_msg")
                if isinstance(payload, (bytes, bytearray)):
                    answer_chunks.append(bytes(payload))
                elif isinstance(payload, dict):
                    for key in ("text", "content", "transcript"):
                        value = payload.get(key)
                        if isinstance(value, str) and value.strip():
                            texts.append(value.strip())
                    if response.get("event") in {152, 153}:
                        break
                if response.get("kind") == "error":
                    break

            await ws.send(_full_request(2, {}))

    except Exception:
        return fallback_voice_reply()

    import base64

    return {
        "text": texts[-1] if texts else "豆包已回复语音。",
        "audio_base64": base64.b64encode(b"".join(answer_chunks)).decode("ascii") if answer_chunks else "",
        "source": "doubao",
        "events": events,
        "audio_format": "pcm",
        "sample_rate": 24000,
    }
