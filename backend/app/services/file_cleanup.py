"""Queue file removal alongside the data change; only unlink after it commits."""
from pathlib import PurePosixPath
from app.models.account import AccountFileDeletion
from app.services import files
from app.services.file_references import reference_paths


def queue_file_deletion(db, path):
    if not db.get(AccountFileDeletion, path):
        db.add(AccountFileDeletion(path=path))


def cleanup_files(db, paths=None, limit=1000):
    query = db.query(AccountFileDeletion)
    if paths is not None:
        query = query.filter(AccountFileDeletion.path.in_(paths))
    rows = query.order_by(AccountFileDeletion.path).all()
    used = reference_paths(db) if rows else set()
    root = files.UPLOADS.resolve()
    removed = 0
    for row in rows:
        if removed >= limit:
            break
        relative = PurePosixPath(row.path)
        if row.path != str(relative) or len(relative.parts) != 2 or relative.parts[0] not in ('private', 'images', 'videos') or relative.name in ('.', '..') or any(ord(c) < 32 for c in row.path):
            continue
        if row.path in used:
            continue
        path = root / row.path
        if path.parent.is_symlink() or path.is_symlink():
            continue
        try:
            path.unlink(missing_ok=True)
        except OSError:
            continue
        db.delete(row)
        removed += 1
    try:
        db.commit()
    except Exception:
        # The data deletion is already committed; leave cleanup queued for retry.
        db.rollback()
    return db.query(AccountFileDeletion).count()
