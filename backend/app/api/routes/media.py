from typing import Optional
import hashlib
import re

from fastapi import APIRouter, Depends, HTTPException, Query, status, File, UploadFile, Form
from app.services.files import store_file
from app.services import files as file_storage
from fastapi.responses import FileResponse
from pathlib import Path
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.routes.profile import current_user_dep
from app.db.session import get_db
from app.models.media import Media, TrainingVideoUpload
from app.models.training import TrainingRecord
from app.services.file_cleanup import queue_file_deletion, cleanup_files
from app.services.public_media import strict_public_path
from app.services.private_files import private_path, discard_private_upload
from app.models.user import User
from app.schemas.media import (
    ALLOWED_PURPOSES,
    MediaCreateRequest,
    MediaListResponse,
    MediaResponse,
    MediaUpdateRequest,
)

router = APIRouter()


def ensure_media_table(db: Session) -> None:
    Media.__table__.create(bind=db.get_bind(), checkfirst=True)


def get_my_media(db: Session, media_id: int, user_id: int) -> Media:
    media = db.query(Media).filter(Media.id == media_id, Media.user_id == user_id).first()
    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="内容不存在")
    return media


@router.post("", response_model=MediaResponse)
def create_media(
    payload: MediaCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_user_dep),
) -> MediaResponse:
    ensure_media_table(db)
    media = db.query(Media).filter_by(user_id=current_user.id, url=payload.url, media_type=payload.media_type).first()
    if not media: raise HTTPException(400, '请先上传自己的文件')
    if media.purpose != payload.purpose:
        raise HTTPException(400, '文件用途不能直接更换，请重新上传')
    db.commit()
    db.refresh(media)
    return MediaResponse.model_validate(media)


@router.get("", response_model=MediaListResponse)
def list_media(
    purpose: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(current_user_dep),
) -> MediaListResponse:
    ensure_media_table(db)
    if purpose is not None and purpose not in ALLOWED_PURPOSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件用途不正确")

    query = db.query(Media).filter(Media.user_id == current_user.id)
    if purpose:
        query = query.filter(Media.purpose == purpose)

    total = query.with_entities(func.count(Media.id)).scalar() or 0
    items = query.order_by(Media.created_at.desc(), Media.id.desc()).all()
    return MediaListResponse(items=[MediaResponse.model_validate(item) for item in items], total=total)


@router.post("/upload")
async def upload_image(file: UploadFile = File(...), current_user: User = Depends(current_user_dep), db: Session = Depends(get_db)):
    url = await store_file(file, 'image')
    return save_public_upload(db,current_user.id,url,'image')


@router.post('/upload-video')
async def upload_video(file: UploadFile = File(...), current_user: User = Depends(current_user_dep), db: Session = Depends(get_db)):
    url = await store_file(file, 'video')
    return save_public_upload(db,current_user.id,url,'video')


def save_public_upload(db,user_id,url,kind):
    row=Media(user_id=user_id,purpose='post',media_type=kind,url=url)
    try:
        db.query(User).filter_by(id=user_id).with_for_update().populate_existing().one()
        db.add(row)
        db.flush()
        result={'url':url,'id':row.id}
        db.commit()
        return result
    except Exception:
        db.rollback()
        path=strict_public_path(url,kind)
        try:
            saved=db.query(Media.id).filter_by(user_id=user_id,url=url).first()
        except Exception:
            db.rollback()
            # The save outcome is unknown. Preserve the file until it can be
            # checked; a lost commit response must not break a saved upload.
            raise
        if path and not saved:
            try:
                (file_storage.UPLOADS/path).unlink(missing_ok=True)
            except OSError:
                # No saved upload can refer to this file; the read-only audit
                # reports it for maintenance without masking the save failure.
                pass
        raise


def check_upload_key(request_key):
    if not re.fullmatch(r'[a-zA-Z0-9_-]{8,64}', request_key):
        raise HTTPException(400, '视频保存编号不正确，请重新选择视频')


def uploaded_result(db, upload, digest=None):
    media = db.get(Media, upload.media_id) if upload.media_id else None
    if upload.cancelled or not media or media.user_id != upload.user_id or media.storage_name != upload.storage_name or not private_path(upload.storage_name, existing=True):
        raise HTTPException(410, '这次视频已放弃或删除，请重新选择视频')
    if digest is not None and upload.payload_hash != digest:
        raise HTTPException(409, '请选择原来那段视频，或先放弃这次待保存的视频')
    return {'url': media.url, 'id': media.id}


@router.post('/upload-training-video')
async def upload_training_video(file: UploadFile = File(...), request_key: Optional[str] = Form(default=None), current_user: User = Depends(current_user_dep), db: Session = Depends(get_db)):
    digest = None
    if request_key:
        check_upload_key(request_key)
        data = await file.read(32 * 1024 * 1024 + 1)
        if len(data) > 32 * 1024 * 1024:
            raise HTTPException(400, '请选择不超过32MB的视频')
        digest = hashlib.sha256(data).hexdigest()
        await file.seek(0)
        prior = db.query(TrainingVideoUpload).filter_by(user_id=current_user.id, request_key=request_key).first()
        if prior:
            return uploaded_result(db, prior, digest)
    # Do not keep an account lock while waiting for video validation.
    name = await store_file(file, 'video', private=True)
    row = Media(user_id=current_user.id, purpose='training', media_type='video', url='', storage_name=name)
    try:
        db.query(User).filter(User.id == current_user.id).with_for_update().populate_existing().one()
        if request_key:
            prior = db.query(TrainingVideoUpload).filter_by(user_id=current_user.id, request_key=request_key).with_for_update().populate_existing().first()
            if prior:
                result = uploaded_result(db, prior, digest)
                discard_private_upload(db, name)
                return result
        db.add(row)
        db.flush()
        row.url = f'/media/{row.id}/file'
        if request_key:
            db.add(TrainingVideoUpload(user_id=current_user.id, request_key=request_key, payload_hash=digest, media_id=row.id, storage_name=name))
        result={'url':row.url,'id':row.id}
        db.commit()
    except Exception:
        discard_private_upload(db, name, rollback=True)
        raise
    return result


@router.get('/training-uploads/{request_key}')
def get_training_upload(request_key: str, current_user: User = Depends(current_user_dep), db: Session = Depends(get_db)):
    check_upload_key(request_key)
    upload = db.query(TrainingVideoUpload).filter_by(user_id=current_user.id, request_key=request_key).first()
    if not upload:
        raise HTTPException(404, '还没有确认上传成功，可以继续保存')
    return uploaded_result(db, upload)


@router.delete('/training-uploads/{request_key}', status_code=204)
def abandon_training_upload(request_key: str, current_user: User = Depends(current_user_dep), db: Session = Depends(get_db)):
    check_upload_key(request_key)
    db.query(User).filter(User.id == current_user.id).with_for_update().populate_existing().one()
    upload = db.query(TrainingVideoUpload).filter_by(user_id=current_user.id, request_key=request_key).first()
    paths = []
    if not upload:
        db.add(TrainingVideoUpload(user_id=current_user.id, request_key=request_key, cancelled=True))
    elif not upload.cancelled:
        media = db.get(Media, upload.media_id) if upload.media_id else None
        if media and media.user_id == current_user.id and media.storage_name == upload.storage_name:
            if db.query(TrainingRecord.id).filter_by(user_id=current_user.id, media_url=media.url).first():
                raise HTTPException(409, '视频已经保存到训练记录，请刷新记录查看')
            paths.append('private/' + media.storage_name)
            queue_file_deletion(db, paths[0])
            db.delete(media)
        upload.cancelled = True
    db.commit()
    cleanup_files(db, paths)


@router.get('/{media_id}/file')
def training_file(media_id: int, current_user: User = Depends(current_user_dep), db: Session = Depends(get_db)):
    media = get_my_media(db, media_id, current_user.id)
    if media.purpose != 'training' or media.media_type != 'video' or media.url != f'/media/{media_id}/file':
        raise HTTPException(404, '训练视频不存在')
    path = private_path(media.storage_name, existing=True)
    if path: return FileResponse(path, headers={'Cache-Control': 'private, no-store'})
    raise HTTPException(404, '训练视频已删除或暂时无法读取')


@router.get("/{media_id}", response_model=MediaResponse)
def get_media(
    media_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_user_dep),
) -> MediaResponse:
    ensure_media_table(db)
    media = get_my_media(db, media_id, current_user.id)
    return MediaResponse.model_validate(media)


@router.patch("/{media_id}", response_model=MediaResponse)
def update_media(
    media_id: int,
    payload: MediaUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_user_dep),
) -> MediaResponse:
    ensure_media_table(db)
    media = get_my_media(db, media_id, current_user.id)
    changes = payload.model_dump(exclude_unset=True, exclude_none=True)
    if 'url' in changes and changes['url'] != media.url: raise HTTPException(400, '文件地址不能直接修改，请重新上传')
    if 'media_type' in changes and changes['media_type'] != media.media_type: raise HTTPException(400, '文件类型不能修改')
    if 'purpose' in changes and changes['purpose'] != media.purpose: raise HTTPException(400, '文件用途不能修改')
    for field, value in changes.items():
        setattr(media, field, value)
    db.commit()
    db.refresh(media)
    return MediaResponse.model_validate(media)


@router.delete("/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_media(
    media_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_user_dep),
) -> None:
    ensure_media_table(db)
    db.query(User).filter(User.id == current_user.id).with_for_update().populate_existing().one()
    media = get_my_media(db, media_id, current_user.id)
    paths = []
    public = strict_public_path(media.url)
    if public and not media.storage_name:
        paths.append(public)
    if media.purpose == 'chat':
        from app.models.chat import ChatMessage
        if db.query(ChatMessage.id).filter_by(message_type='image',content=media.url).first():
            raise HTTPException(400, '已发送的图片不能在文件列表中删除')
        if media.storage_name and Path(media.storage_name).name == media.storage_name:
            paths.append('private/' + media.storage_name)
    if media.purpose == 'training' and media.url == f'/media/{media_id}/file':
        from app.models.training import TrainingRecord
        db.query(TrainingRecord).filter_by(user_id=current_user.id, media_url=media.url).update({'media_url': None, 'media_type': None})
        if media.storage_name and Path(media.storage_name).name == media.storage_name:
            paths.append('private/' + media.storage_name)
    for path in paths:
        queue_file_deletion(db, path)
    db.delete(media)
    db.commit()
    cleanup_files(db, paths)
