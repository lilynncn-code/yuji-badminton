"""Read private uploads safely and discard only confirmed unsaved files."""
from pathlib import PurePosixPath

from app.models.chat import ChatMessage
from app.models.media import Media
from app.services import files
from app.services.file_cleanup import queue_file_deletion


def private_path(name, *, existing=False):
    if (not isinstance(name, str) or not name or PurePosixPath(name).name != name
            or name in ('.', '..') or '\\' in name or any(ord(c) < 32 for c in name)):
        return None
    try:
        root = files.UPLOADS.resolve()
        path = root / 'private' / name
        if path.parent.is_symlink() or path.is_symlink() or (existing and not path.is_file()):
            return None
    except (OSError, RuntimeError):
        return None
    return path


def discard_private_upload(db, name, *, rollback=False):
    """Use after failure or an already-saved duplicate, never with pending data.

    A commit exception does not prove the commit failed. Query the stored filename
    again; if that cannot be checked, preserve it. Cleanup must not replace a
    successful duplicate response or the original save error with a cleanup error.
    """
    path = private_path(name)
    if not path:
        return False
    try:
        if rollback:
            db.rollback()
        with db.no_autoflush:
            media = db.query(Media.id).filter_by(storage_name=name).first()
            voice = db.query(ChatMessage.id).filter_by(message_type='voice', content=name).first()
        if media or voice:
            return False
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        return False
    try:
        path.unlink(missing_ok=True)
    except OSError:
        try:
            queue_file_deletion(db, 'private/' + name)
            db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
        return False
    return True
