"""Read relationships in creation order without moving boundaries on name edits."""
import base64
import hashlib
import hmac
import json
import time
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import and_, or_
from app.core.config import settings
from app.models.user import User
from app.models.social import Follow, Block, PeopleRevision


def changed_people(db, user_ids):
    rows = [{'user_id': uid, 'revision': 1} for uid in sorted(set(user_ids)) if uid > 0]
    if not rows: return
    if db.get_bind().dialect.name == 'sqlite':
        from sqlalchemy.dialects.sqlite import insert
        statement = insert(PeopleRevision).values(rows)
        statement = statement.on_conflict_do_update(index_elements=['user_id'], set_={'revision': PeopleRevision.revision + 1})
    else:
        from sqlalchemy.dialects.mysql import insert
        statement = insert(PeopleRevision).values(rows)
        statement = statement.on_duplicate_key_update(revision=PeopleRevision.revision + 1)
    db.execute(statement)


def revision(db, user_id):
    return db.query(PeopleRevision.revision).filter_by(user_id=user_id).scalar() or 0


def people_query(db, user_id, kind):
    model = Block if kind == 'blocked' else Follow
    other = model.user_id if kind == 'followers' else model.target_id
    own = model.target_id if kind == 'followers' else model.user_id
    query = db.query(User, model.id.label('relation_id'), model.created_at.label('relation_created_at')).join(model, User.id == other).filter(own == user_id, User.id != user_id)
    if kind != 'blocked':
        blocked = db.query(Block.id).filter(or_(
            and_(Block.user_id == user_id, Block.target_id == User.id),
            and_(Block.target_id == user_id, Block.user_id == User.id))).exists()
        query = query.filter(~blocked)
    return query, model


def next_position(user_id, kind, through, row, revision):
    data = {'u': user_id, 'kind': kind, 'rev': revision, 'through': through.isoformat(), 't': row.relation_created_at.isoformat(), 'id': row.relation_id, 'exp': int(time.time()) + 1800}
    body = base64.urlsafe_b64encode(json.dumps(data, separators=(',', ':')).encode()).decode().rstrip('=')
    signature = hmac.new(settings.secret_key.encode(), ('people-list:' + body).encode(), hashlib.sha256).hexdigest()
    return body + '.' + signature


def read_position(cursor, user_id, kind, revision):
    try:
        body, signature = cursor.rsplit('.', 1)
        expected = hmac.new(settings.secret_key.encode(), ('people-list:' + body).encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected): raise ValueError()
        data = json.loads(base64.urlsafe_b64decode(body + '=' * (-len(body) % 4)))
        if data['u'] != user_id or data['kind'] != kind or data['rev'] != revision or data['exp'] <= time.time(): raise ValueError()
        through, at = datetime.fromisoformat(data['through']), datetime.fromisoformat(data['t'])
        if through.tzinfo is not None or at.tzinfo is not None or at > through or not isinstance(data['id'], int) or data['id'] <= 0: raise ValueError()
        return through, at, data['id']
    except (ValueError, TypeError, KeyError, UnicodeError):
        raise HTTPException(400, '名单有变化或翻看位置已失效，请刷新球友列表后继续')
