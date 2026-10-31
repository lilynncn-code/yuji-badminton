"""Move locally hosted legacy chat pictures while preserving public uses.

Run with the service stopped. Copies and changed references are committed before
the old public filename is queued for deletion. The default is an inspection.
"""
from dataclasses import dataclass, field
from pathlib import PurePosixPath
import shutil
from uuid import uuid4

from sqlalchemy import or_
from sqlalchemy.orm.attributes import flag_modified

from app.models.chat import Chat, ChatChange, ChatMessage
from app.models.media import Media
from app.models.post import Post
from app.models.training import TrainingRecord
from app.models.user import User
from app.models.account import AccountFileDeletion
from app.services import files
from app.services.file_cleanup import cleanup_files, queue_file_deletion


@dataclass
class ImageMove:
    url: str
    status: str = 'ready'
    messages: int = 0
    private_copies: int = 0
    public_copies: int = 0
    detail: str = ''
    leftover_copies: int = 0


@dataclass
class ImageMoveReport:
    items: list[ImageMove] = field(default_factory=list)
    pending_cleanup: int = 0


def local_name(url):
    path = PurePosixPath(url)
    if (not url.startswith('/uploads/images/') or len(path.parts) != 4
            or str(path) != url or '\\' in url or '?' in url or '#' in url or '%' in url
            or any(ord(char) < 32 for char in url)
            or path.name in ('.', '..') or path.suffix.lower() not in ('.jpg', '.jpeg', '.png', '.gif', '.webp')):
        raise ValueError('旧图片地址不符合本机图片规则，保留原记录待核对')
    return path.name


def checked_folder(name, create=False):
    root = files.UPLOADS.resolve()
    folder = root / name
    if folder.is_symlink() or folder.resolve() != root / name:
        raise ValueError('图片目录指向其他位置，保留原文件待核对')
    if create:
        folder.mkdir(parents=True, exist_ok=True)
    return folder


def copy_picture(source, folder, copies):
    destination = folder / (uuid4().hex + source.suffix.lower())
    # Exclusive creation prevents replacing an existing file, including a link.
    with destination.open('xb') as output:
        copies.append(destination)
        with source.open('rb') as original:
            shutil.copyfileobj(original, output)
    return destination.name


def inspect_source(db, url):
    item = ImageMove(url=url)
    name = local_name(url)
    source = checked_folder('images') / name
    if source.is_symlink() or not source.is_file():
        raise ValueError('原图不存在或指向其他位置，保留原记录待核对')
    messages = db.query(ChatMessage).filter_by(message_type='image', content=url).order_by(ChatMessage.id).all()
    item.messages = len(messages)
    groups = {}
    for message in messages:
        chat = db.get(Chat, message.chat_id)
        if not chat or message.sender_id not in (chat.requester_id, chat.receiver_id) or not db.get(User, message.sender_id):
            raise ValueError('旧消息与发送者不一致，保留原图和记录待核对')
        if not message.recalled_at:
            groups.setdefault((chat.id, message.sender_id), []).append(message)
    posts = [p for p in db.query(Post) if url in (p.image_urls or [])]
    profiles = db.query(User).filter(or_(User.avatar == url, User.cover == url)).all()
    training = db.query(TrainingRecord).filter_by(media_url=url).all()
    item.private_copies = len(groups)
    item.public_copies = len({p.user_id for p in posts if not p.removed_at}
                            | {u.id for u in profiles} | {r.user_id for r in training})
    return item, source, messages, groups, posts, profiles, training


def move_legacy_chat_images(db, *, apply=False):
    """Inspect by default; applying requires exclusive access to these records."""
    report = ImageMoveReport()
    urls = [r[0] for r in db.query(ChatMessage.content).filter(
        ChatMessage.message_type == 'image', ChatMessage.content.startswith('/uploads/images/'))
        .distinct().order_by(ChatMessage.content).all()]
    for url in urls:
        try:
            item, source, messages, groups, posts, profiles, training = inspect_source(db, url)
        except (ValueError, OSError) as error:
            report.items.append(ImageMove(url=url, status='needs_review', detail=str(error)))
            continue
        report.items.append(item)
        if not apply:
            continue
        copies = []
        try:
            private_folder = checked_folder('private', create=True)
            for (chat_id, sender_id), rows in groups.items():
                name = copy_picture(source, private_folder, copies)
                media = Media(user_id=sender_id, purpose='chat', media_type='image', url='', storage_name=name)
                db.add(media)
                db.flush()
                media.url = f'/chat/chats/{chat_id}/images/{media.id}'
                for message in rows:
                    message.content = media.url
                    db.add(ChatChange(chat_id=chat_id, message_id=message.id))
            for message in messages:
                if message.recalled_at:
                    message.content = ''
                    message.message_type = 'text'
                    db.add(ChatChange(chat_id=message.chat_id, message_id=message.id))
            old_media = db.query(Media).filter_by(url=url).all()
            if item.public_copies:
                public_owners = ({p.user_id for p in posts if not p.removed_at}
                                 | {u.id for u in profiles} | {r.user_id for r in training})
                public_urls = {uid: '/uploads/images/' + copy_picture(source, checked_folder('images'), copies)
                               for uid in sorted(public_owners)}
                for post in posts:
                    post.image_urls = ([public_urls[post.user_id] if value == url else value for value in post.image_urls]
                                       if not post.removed_at else [value for value in post.image_urls if value != url])
                for user in profiles:
                    # Moving a file must not refresh any editing or activity time.
                    if user.avatar == url:
                        user.avatar = public_urls[user.id]
                    if user.cover == url:
                        user.cover = public_urls[user.id]
                    flag_modified(user, 'updated_at')
                for record in training:
                    record.media_url = public_urls[record.user_id]
                    flag_modified(record, 'updated_at')
                tracked_owners = set()
                for media in old_media:
                    if media.purpose == 'chat' or media.user_id not in public_urls:
                        db.delete(media)
                    else:
                        media.url = public_urls[media.user_id]
                        flag_modified(media, 'updated_at')
                        tracked_owners.add(media.user_id)
                for uid in public_owners - tracked_owners:
                    db.add(Media(user_id=uid, purpose='post', media_type='image', url=public_urls[uid]))
            else:
                for post in posts:
                    post.image_urls = [value for value in post.image_urls if value != url]
                # Old generic upload metadata is replaced by per-chat media.
                for media in old_media:
                    db.delete(media)
            queue_file_deletion(db, 'images/' + source.name)
            db.commit()
        except Exception:
            db.rollback()
            item.status = 'failed'
            item.detail = '整理未能保存，原图和原消息保留，可重试'
            for path in copies:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    item.leftover_copies += 1
            continue
        item.status = 'moved'
    # Only already committed deletions are eligible. A rerun also retries any
    # previously locked source, even after its message URLs have been replaced.
    report.pending_cleanup = cleanup_files(db) if apply else db.query(AccountFileDeletion).count()
    return report
