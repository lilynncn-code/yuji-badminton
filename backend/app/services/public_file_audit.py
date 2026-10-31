"""Read-only inventory; unused upload metadata may belong to unsent drafts."""
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from app.models.account import AccountFileDeletion
from app.services import files
from app.services.file_references import reference_paths


@dataclass
class PublicFileItem:
    path: str
    status: str
    size: int = 0


@dataclass
class PublicFileAudit:
    items: list[PublicFileItem] = field(default_factory=list)
    pending_cleanup: int = 0


def inspect_public_files(db):
    """No file writes, reference changes, cleanup or database commits."""
    with db.no_autoflush:
        used = reference_paths(db, include_media=False)
        tracked = reference_paths(db)
        queued = {row.path for row in db.query(AccountFileDeletion)}
    report = PublicFileAudit(pending_cleanup=len(queued))
    root = files.UPLOADS.resolve()
    seen = set()
    blocked = set()
    for name in ('images', 'videos'):
        folder = root / name
        if folder.is_symlink():
            blocked.add(name)
            report.items.append(PublicFileItem(name, 'needs_review'))
            continue
        if not folder.exists():
            continue
        try:
            entries = sorted(folder.iterdir(), key=lambda p: p.name)
        except OSError:
            blocked.add(name)
            report.items.append(PublicFileItem(name, 'needs_review'))
            continue
        for path in entries:
            relative = name + '/' + path.name
            seen.add(relative)
            try:
                if path.is_symlink() or not path.is_file() or any(ord(c) < 32 for c in relative):
                    status, size = 'needs_review', 0
                else:
                    size = path.stat().st_size
                    status = ('in_use' if relative in used else 'upload_only' if relative in tracked
                              else 'queued' if relative in queued else 'untracked')
            except OSError:
                status, size = 'needs_review', 0
            report.items.append(PublicFileItem(relative, status, size))
    for relative in sorted(tracked - seen):
        path = PurePosixPath(relative)
        if len(path.parts) == 2 and path.parts[0] in ('images', 'videos') and path.parts[0] not in blocked:
            report.items.append(PublicFileItem(relative, 'missing'))
    return report
