"""Validate local public attachments and retire the owner's unused uploads."""
from fastapi import HTTPException

from app.models.media import Media
from app.models.account import AccountFileDeletion
from app.services import files
from app.services.file_references import public_path, reference_paths
from app.services.file_cleanup import queue_file_deletion


def strict_public_path(url, kind=None):
    path = public_path(url)
    if not path or url != '/uploads/' + path or '%' in url or any(ord(c) < 32 for c in url):
        return None
    folder = 'images' if kind == 'image' else 'videos' if kind == 'video' else None
    return path if folder is None or path.startswith(folder + '/') else None


def validate_public_media(db, url, owner, kind):
    if not url:
        return
    if kind == 'image' and url.startswith('https://'):
        return
    path = strict_public_path(url, kind)
    if not path:
        raise HTTPException(400, '图片或视频地址不正确，请重新选择自己的文件')
    row = db.query(Media).filter(Media.user_id == owner, Media.url == url, Media.media_type == kind,
                                  Media.purpose.in_(('post', 'avatar') if kind == 'image' else ('post',)))
    if not row.with_for_update().populate_existing().first():
        raise HTTPException(400, '请重新上传自己的图片或视频')
    root = files.UPLOADS.resolve()
    location = root / path
    if location.parent.is_symlink() or location.is_symlink() or not location.is_file():
        raise HTTPException(400, '图片或视频已不存在，请重新上传后再保存')


def retire_public_media(db, owner, urls):
    """Call after changing references, within the same data transaction."""
    candidates = {url: strict_public_path(url) for url in urls if url}
    candidates = {url: path for url, path in candidates.items() if path}
    if not candidates:
        return []
    db.flush()
    # Remove only this owner's unused metadata; cleanup checks every account.
    used = reference_paths(db, include_media=False, user_id=owner)
    paths = []
    for url, path in candidates.items():
        if path in used:
            continue
        rows = db.query(Media).filter(Media.user_id == owner, Media.url == url,
                                      Media.storage_name == '', Media.purpose.in_(('post', 'avatar'))).with_for_update().all()
        if not rows:
            if db.get(AccountFileDeletion, path):
                paths.append(path)
            continue
        for row in rows:
            db.delete(row)
        queue_file_deletion(db, path)
        paths.append(path)
    return paths
