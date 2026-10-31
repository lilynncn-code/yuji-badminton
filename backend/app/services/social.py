from fastapi import HTTPException
from sqlalchemy import or_, and_
from app.models.social import Block


def blocked_ids(db, user_id):
    rows = db.query(Block).filter(or_(Block.user_id == user_id, Block.target_id == user_id)).all()
    return {r.target_id if r.user_id == user_id else r.user_id for r in rows}


def ensure_contact_allowed(db, first_id, second_id, lock=False):
    query = db.query(Block.id).filter(or_(
        and_(Block.user_id == first_id, Block.target_id == second_id),
        and_(Block.user_id == second_id, Block.target_id == first_id)))
    if lock: query = query.with_for_update()
    if query.first():
        raise HTTPException(403, '已屏蔽，无法继续互动')
