from datetime import datetime
from typing import Optional
from fastapi import APIRouter,Depends,Query
from pydantic import BaseModel,Field,model_validator
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.notification import Notification
from app.services.notifications import visible_notifications,notification_data

router=APIRouter(prefix='/notifications',tags=['notifications'])


@router.get('/unread')
def unread(ids:list[int]=Query(default=[],max_length=100),user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    query=visible_notifications(db,user.id)
    latest=query.order_by(Notification.id.desc()).first()
    return {'unread_count':query.filter_by(read_at=None).count(),'latest_id':latest.id if latest else 0,
        'items':[notification_data(row,db) for row in query.filter(Notification.id.in_(ids)).all()] if ids else []}


@router.get('')
def list_notifications(before_id:Optional[int]=Query(None,gt=0),limit:int=Query(30,ge=1,le=100),only_unread:bool=False,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    query=visible_notifications(db,user.id)
    latest=query.order_by(Notification.id.desc()).first()
    unread_count=query.filter_by(read_at=None).count()
    if only_unread:query=query.filter_by(read_at=None)
    if before_id:query=query.filter(Notification.id<before_id)
    rows=query.order_by(Notification.id.desc()).limit(limit+1).all()
    return {'items':[notification_data(row,db) for row in rows[:limit]],'has_more':len(rows)>limit,'unread_count':unread_count,'latest_id':latest.id if latest else 0}


class ReadRequest(BaseModel):
    ids:list[int]=Field(default_factory=list,max_length=100)
    through_id:Optional[int]=Field(None,gt=0)

    @model_validator(mode='after')
    def valid_selection(self):
        if bool(self.ids)==bool(self.through_id) or any(i<=0 for i in self.ids):raise ValueError('请选择要标记的提醒')
        return self


@router.post('/read')
def mark_read(payload:ReadRequest,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    query=visible_notifications(db,user.id).filter(Notification.read_at.is_(None))
    query=query.filter(Notification.id<=payload.through_id) if payload.through_id else query.filter(Notification.id.in_(payload.ids))
    query.update({'read_at':datetime.utcnow()},synchronize_session=False)
    db.commit()
    return {'unread_count':visible_notifications(db,user.id).filter_by(read_at=None).count()}
