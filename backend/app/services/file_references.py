"""Recognize existing file references before removing a committed file."""
import posixpath
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

from app.models.chat import ChatMessage
from app.models.clinic import ClinicQuestion
from app.models.media import Media
from app.models.post import Post
from app.models.training import TrainingRecord
from app.models.user import User


def public_path(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = urlsplit(value.replace('\\', '/'))
    except ValueError:
        return None
    if parsed.scheme and parsed.scheme not in ('http', 'https'):
        return None
    # Reading old records is conservative: an absolute URL or encoded spelling
    # with the same local path also prevents removing the local file.
    path = PurePosixPath(posixpath.normpath(unquote(parsed.path)))
    if len(path.parts) == 4 and path.parts[:3] in (('/', 'uploads', 'images'), ('/', 'uploads', 'videos')) and path.name not in ('.', '..'):
        return '/'.join(path.parts[2:])
    return None


def reference_paths(db, *, include_media=True, user_id=None):
    paths = set()

    def add(value):
        path = public_path(value)
        if path:
            paths.add(path)

    if include_media:
        media = db.query(Media.url, Media.storage_name)
        if user_id is not None:
            media = media.filter(Media.user_id == user_id)
        for url, name in media:
            add(url)
            if name and PurePosixPath(name).name == name and name not in ('.', '..'):
                paths.add('private/' + name)
    posts = db.query(Post.image_urls, Post.video_url).filter(Post.removed_at.is_(None))
    users = db.query(User.avatar, User.cover)
    records = db.query(TrainingRecord.media_url)
    questions = db.query(ClinicQuestion.video_url)
    messages = db.query(ChatMessage.message_type, ChatMessage.content).filter(
        ChatMessage.recalled_at.is_(None), ChatMessage.message_type.in_(('image', 'voice')))
    if user_id is not None:
        posts = posts.filter(Post.user_id == user_id)
        users = users.filter(User.id == user_id)
        records = records.filter(TrainingRecord.user_id == user_id)
        questions = questions.filter(ClinicQuestion.user_id == user_id)
        messages = messages.filter(ChatMessage.sender_id == user_id)
    for images, video in posts:
        for image in images or []:
            add(image)
        add(video)
    for avatar, cover in users:
        add(avatar)
        add(cover)
    for url, in records:
        add(url)
    for url, in questions:
        add(url)
    for kind, content in messages:
        if kind == 'image':
            add(content)
        elif content and PurePosixPath(content).name == content and content not in ('.', '..'):
            paths.add('private/' + content)
    return paths
