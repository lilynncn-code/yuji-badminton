from pathlib import Path
from uuid import uuid4
import io
import json
import shutil
import subprocess
from starlette.concurrency import run_in_threadpool
from PIL import Image, UnidentifiedImageError
from fastapi import HTTPException, UploadFile

UPLOADS = Path(__file__).resolve().parents[2] / "uploads"

async def store_file(upload: UploadFile, kind: str, private=False) -> str:
    limit = {"image": 8, "video": 32, "audio": 4}[kind] * 1024 * 1024
    data = await upload.read(limit + 1)
    if not data or len(data) > limit:
        raise HTTPException(400, "文件为空或太大，请重新选择")
    if kind == "image":
        if data.startswith(b"\xff\xd8\xff"): ext = ".jpg"
        elif data.startswith(b"\x89PNG\r\n\x1a\n"): ext = ".png"
        elif data[:6] in (b"GIF87a", b"GIF89a"): ext = ".gif"
        elif data[:4] == b"RIFF" and data[8:12] == b"WEBP": ext = ".webp"
        else: raise HTTPException(400, "请选择 JPG、PNG、GIF 或 WebP 图片")
        try:
            with Image.open(io.BytesIO(data)) as picture:
                if picture.width * picture.height > 20000000: raise ValueError('image dimensions')
                picture.verify()
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
            raise HTTPException(400, '图片损坏或尺寸太大，请重新选择')
    elif kind == 'video':
        if len(data) >= 24 and data[4:8] == b'ftyp' and (b'mdat' in data or b'moov' in data): ext = '.mp4'
        elif len(data) >= 64 and data[:4] == b'\x1a\x45\xdf\xa3' and b'webm' in data[:256]: ext = '.webm'
        else: raise HTTPException(400, '请选择 MP4 或 WebM 视频，单个不超过32MB')
    else:
        if data[:4] == b"RIFF" and data[8:12] == b"WAVE": ext = ".wav"
        elif data[:3] == b"ID3" or data[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"): ext = ".mp3"
        elif data[4:8] == b"ftyp": ext = ".m4a"
        elif data[:4] == b"\x1a\x45\xdf\xa3": ext = ".webm"
        elif data[:2] in (b"\xff\xf1", b"\xff\xf9"): ext = ".aac"
        else: raise HTTPException(400, "录音格式无法读取，请重新录制")
    folder_name = 'videos' if kind == 'video' else 'images'
    folder = UPLOADS / ("private" if private else folder_name)
    folder.mkdir(parents=True, exist_ok=True)
    name = uuid4().hex + ext
    path = folder / name
    path.write_bytes(data)
    if kind == 'video':
        try:
            probe = shutil.which('ffprobe')
            if not probe: raise HTTPException(503, '视频检查暂时不可用，请稍后再试')
            result = await run_in_threadpool(subprocess.run, [probe, '-v', 'error', '-protocol_whitelist', 'file,pipe', '-read_intervals', '%+301', '-select_streams', 'v:0', '-show_entries', 'stream=codec_type,width,height:format=duration:packet=pts_time,duration_time', '-of', 'json', str(path)], capture_output=True, timeout=10, check=True)
            info = json.loads(result.stdout)
            streams = [s for s in info.get('streams', []) if s.get('codec_type') == 'video']
            packets = info.get('packets', [])
            duration = info.get('format', {}).get('duration')
            if duration in (None, 'N/A'):
                # Browser recordings often omit container duration until remuxed.
                points = [(float(p['pts_time']), float(p.get('duration_time', 0))) for p in packets if p.get('pts_time') not in (None, 'N/A')]
                duration = max((t+d for t,d in points), default=0) - min((t for t,d in points), default=0)
            if not streams or not 0 < float(duration) <= 300 or any(s.get('width',0) * s.get('height',0) > 20000000 for s in streams):
                raise ValueError('invalid video')
        except HTTPException:
            path.unlink(missing_ok=True)
            raise
        except (subprocess.SubprocessError, ValueError, OSError):
            path.unlink(missing_ok=True)
            raise HTTPException(400, '视频损坏、过长或无法读取，请选择5分钟内的视频')
    return name if private else f'/uploads/{folder_name}/' + name


def valid_image_url(value: str):
    if value and not (value.startswith("/uploads/images/") or value.startswith("https://")):
        raise HTTPException(400, "请先上传图片再保存")


def valid_video_url(value: str, user_id: int, db):
    from app.models.media import Media
    if not value: return
    if not value.startswith('/uploads/videos/') or not db.query(Media.id).filter_by(user_id=user_id, url=value, media_type='video', purpose='post').first():
        raise HTTPException(400, '请先上传自己的视频')
