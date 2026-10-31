from typing import Literal, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.social import Follow, Block, Report, Favorite
from app.models.post import Post, PostComment, PostLike
from app.services.social import ensure_contact_allowed
from app.models.notification import Notification
from app.services import people_pages
from app.services.public_media import retire_public_media
from app.services.file_cleanup import cleanup_files

router = APIRouter(prefix='/social', tags=['social'])


def lock_people(db, user_id, target_id, require_target=True):
    # All relationship changes lock both people in the same order.
    rows = db.query(User).filter(User.id.in_([user_id, target_id])).order_by(User.id).with_for_update().populate_existing().all()
    if user_id == target_id: raise HTTPException(400, '不能对自己进行此操作')
    if not any(row.id == user_id for row in rows): raise HTTPException(401, '登录已失效，请重新登录')
    if require_target and not any(row.id == target_id for row in rows): raise HTTPException(404, '球友不存在')


@router.get('/users/{target_id}')
def relation(target_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not db.get(User, target_id): raise HTTPException(404, '球友不存在')
    own_block = bool(db.query(Block.id).filter_by(user_id=user.id, target_id=target_id).first())
    other_block = bool(db.query(Block.id).filter_by(user_id=target_id, target_id=user.id).first())
    allowed = user.id != target_id and not own_block and not other_block
    return {'following': allowed and bool(db.query(Follow.id).filter_by(user_id=user.id, target_id=target_id).first()),
            'blocked': own_block, 'can_interact': allowed}


@router.put('/users/{target_id}/follow')
def follow(target_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lock_people(db, user.id, target_id)
    ensure_contact_allowed(db, user.id, target_id, lock=True)
    if not db.query(Follow.id).filter_by(user_id=user.id, target_id=target_id).with_for_update().first():
        db.add(Follow(user_id=user.id, target_id=target_id))
        people_pages.changed_people(db, [user.id, target_id])
    db.commit()
    return {'following': True}


@router.delete('/users/{target_id}/follow')
def unfollow(target_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    lock_people(db, user.id, target_id, require_target=False)
    removed = db.query(Follow).filter_by(user_id=user.id, target_id=target_id).delete()
    if removed: people_pages.changed_people(db, [user.id, target_id])
    db.commit()
    return {'following': False}


@router.put('/users/{target_id}/block')
def block(target_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.chat_inbox import changed_inboxes
    lock_people(db, user.id, target_id)
    if not db.query(Block.id).filter_by(user_id=user.id, target_id=target_id).with_for_update().first():
        db.add(Block(user_id=user.id, target_id=target_id))
        changed_inboxes(db,[user.id,target_id])
        people_pages.changed_people(db, [user.id, target_id])
    removed_follows = db.query(Follow).filter(or_(and_(Follow.user_id == user.id, Follow.target_id == target_id), and_(Follow.user_id == target_id, Follow.target_id == user.id))).delete(synchronize_session=False)
    if removed_follows: people_pages.changed_people(db, [user.id, target_id])
    db.commit()
    return {'blocked': True}


@router.delete('/users/{target_id}/block')
def unblock(target_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.chat_inbox import changed_inboxes
    lock_people(db, user.id, target_id, require_target=False)
    removed=db.query(Block).filter_by(user_id=user.id, target_id=target_id).delete()
    if removed:
        changed_inboxes(db,[user.id,target_id])
        people_pages.changed_people(db, [user.id, target_id])
    db.commit()
    return {'blocked': False}


@router.get('/people/status')
def people_status(kind: Literal['following', 'followers', 'blocked'] = 'following', user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query, _ = people_pages.people_query(db, user.id, kind)
    return {'revision': people_pages.revision(db, user.id), 'total': query.count()}


@router.get('/people')
def people(kind: Literal['following', 'followers', 'blocked'] = 'following', cursor: Optional[str] = Query(None, max_length=2000),
           limit: int = Query(30, ge=1, le=100), page: Optional[int] = Query(None, ge=1),
           user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if page is not None and page != 1: raise HTTPException(400, '列表已更新，请重新打开后继续查看')
    query, model = people_pages.people_query(db, user.id, kind)
    revision = people_pages.revision(db, user.id)
    through, at, relation_id = people_pages.read_position(cursor, user.id, kind, revision) if cursor else (datetime.utcnow(), None, None)
    query = query.filter(model.created_at <= through)
    total = query.count()
    if at is not None:
        query = query.filter(or_(model.created_at < at, and_(model.created_at == at, model.id < relation_id)))
    rows = query.order_by(model.created_at.desc(), model.id.desc()).limit(limit + 1).all()
    items = [{'id': row.User.id, 'name': row.User.name, 'avatar': row.User.avatar, 'city': row.User.city, 'bio': row.User.bio} for row in rows[:limit]]
    return {'items': items, 'total': total, 'revision': revision, 'has_more': len(rows) > limit,
            'next_cursor': people_pages.next_position(user.id, kind, through, rows[limit-1], revision) if len(rows) > limit else None}


class ReportInput(BaseModel):
    target_type: Literal['user', 'post', 'comment']
    target_id: int = Field(gt=0)
    reason: str = Field(min_length=2, max_length=500)


@router.post('/reports')
def report(payload: ReportInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    model = {'user': User, 'post': Post, 'comment': PostComment}[payload.target_type]
    target = db.get(model, payload.target_id)
    if not target or (payload.target_type=='comment' and target.deleted_at) or (payload.target_type=='post' and target.removed_at): raise HTTPException(404, '举报对象已不存在')
    reason = payload.reason.strip()
    if len(reason) < 2: raise HTTPException(400, '请说明举报原因')
    db.query(User).filter_by(id=user.id).with_for_update().first()
    # Preserve the submitted content if its author later deletes it.
    snapshot = target.name if payload.target_type == 'user' else target.content
    existing = db.query(Report).filter_by(user_id=user.id, target_type=payload.target_type, target_id=payload.target_id, status='pending').first()
    if existing: return {'id': existing.id, 'message': '已提交，请在举报记录查看状态'}
    row = Report(user_id=user.id, target_type=payload.target_type, target_id=payload.target_id, target_user_id=target.id if payload.target_type=='user' else target.user_id, reason=reason, snapshot=snapshot)
    db.add(row); db.commit()
    return {'id': row.id, 'message': '已提交，等待处理；可在设置查看举报记录'}


@router.get('/reports')
def reports(before_id:Optional[int]=Query(None,gt=0),limit:int=Query(30,ge=1,le=100),user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query=db.query(Report).filter_by(user_id=user.id)
    if before_id:query=query.filter(Report.id<before_id)
    rows=query.order_by(Report.id.desc()).limit(limit+1).all()
    return {'items': [report_data(r) for r in rows[:limit]],'has_more':len(rows)>limit}


def report_data(row):
    return {name:getattr(row,name) for name in ('id','target_type','target_id','reason','status','result','action','created_at','resolved_at')}


def report_reviewer(user:User=Depends(get_current_user)):
    if user.can_review_reports!=1:raise HTTPException(403,'此入口仅供获准的举报处理人员使用')
    return user


def report_target(db,row):
    model={'user':User,'post':Post,'comment':PostComment}.get(row.target_type)
    target=db.get(model,row.target_id) if model else None
    owner=row.target_user_id or (target.id if row.target_type=='user' and target else getattr(target,'user_id',None))
    available=bool(target) and not getattr(target,'deleted_at',None) and not getattr(target,'removed_at',None)
    if row.target_type=='comment' and target:
        post=db.get(Post,target.post_id)
        available=available and bool(post) and not post.removed_at
    return target,owner,bool(available)


def review_data(db,row,user_id):
    target,owner,available=report_target(db,row)
    own=row.user_id==user_id or owner==user_id
    return {**report_data(row),'snapshot':row.snapshot,'target_available':available,
            'current_content':(target.name if row.target_type=='user' else target.content) if available else '',
            'can_handle':row.status=='pending' and not own,
            'handle_note':'与本人有关，请交由其他处理人员核查' if own else '',
            'can_remove':available and row.target_type in ('post','comment') and not own}


@router.get('/review/reports')
def review_reports(state:Literal['pending','resolved']='pending',before_id:Optional[int]=Query(None,gt=0),limit:int=Query(30,ge=1,le=100),
                   user:User=Depends(report_reviewer),db:Session=Depends(get_db)):
    query=db.query(Report).filter_by(status=state)
    if before_id:query=query.filter(Report.id<before_id)
    rows=query.order_by(Report.id.desc()).limit(limit+1).all()
    return {'items':[review_data(db,r,user.id) for r in rows[:limit]],'has_more':len(rows)>limit}


class ReviewInput(BaseModel):
    action:Literal['no_violation','remove_content','already_unavailable','record_result']
    result:str=Field(min_length=2,max_length=500)


@router.post('/review/reports/{report_id}')
def resolve_report(report_id:int,payload:ReviewInput,user:User=Depends(report_reviewer),db:Session=Depends(get_db)):
    # Lock the target before the report, matching comment creation's post lock.
    initial=db.get(Report,report_id)
    if not initial:raise HTTPException(404,'举报记录不存在')
    target,owner,_=report_target(db,initial)
    if initial.target_type=='comment' and target:
        db.query(Post).filter_by(id=target.post_id).with_for_update().populate_existing().first()
        db.query(PostComment).filter_by(id=target.id).with_for_update().populate_existing().first()
    elif initial.target_type=='post':
        db.query(Post).filter_by(id=initial.target_id).with_for_update().populate_existing().first()
    row=db.query(Report).filter_by(id=report_id).with_for_update().populate_existing().first()
    if not row:raise HTTPException(404,'举报记录已不存在')
    target,owner,available=report_target(db,row)
    cleanup_paths=[]
    if row.user_id==user.id or owner==user.id:raise HTTPException(403,'不能处理与本人有关的举报，请交由其他处理人员')
    result=payload.result.strip()
    if len(result)<2:raise HTTPException(400,'请填写处理依据和结果')
    if row.status=='resolved':
        if (row.action,row.result,row.handled_by)==(payload.action,result,user.id):return report_data(row)
        raise HTTPException(409,'这条举报已经处理，请刷新查看结果')
    if payload.action=='record_result' and (row.target_type!='user' or not available):
        raise HTTPException(400,'仅可为仍存在的账号登记核查结果')
    if payload.action=='remove_content':
        if row.target_type not in ('post','comment'):raise HTTPException(400,'账号举报请核查说明；不能在这里删除账号')
        if not available:raise HTTPException(409,'内容已不存在，请刷新后选择“内容已不存在”')
        if row.target_type=='post':
            old_urls=set(target.image_urls or [])|{target.video_url}
            target.removed_at=datetime.utcnow();target.content='';target.image_urls=[];target.video_url='';target.likes_count=0
            db.query(PostLike).filter_by(post_id=target.id).delete(synchronize_session=False)
            db.query(PostComment).filter_by(post_id=target.id).update({'content':'','deleted_at':datetime.utcnow()},synchronize_session=False)
            db.query(Notification).filter_by(target_type='comment',context_id=target.id).delete(synchronize_session=False)
            cleanup_paths=retire_public_media(db,target.user_id,old_urls)
        else:
            target.content='';target.deleted_at=datetime.utcnow()
            db.query(Notification).filter_by(target_type='comment',target_id=target.id).delete(synchronize_session=False)
    elif payload.action=='already_unavailable' and available:
        raise HTTPException(409,'内容仍可查看，请先核查再选择处理方式')
    elif payload.action=='no_violation' and not available:
        raise HTTPException(409,'内容已不存在，请刷新后选择“内容已不存在”')
    row.status='resolved';row.result=result;row.action=payload.action;row.handled_by=user.id;row.resolved_at=datetime.utcnow()
    db.commit()
    if cleanup_paths:cleanup_files(db,cleanup_paths)
    return report_data(row)


@router.get('/favorites/{kind}')
def favorites(kind: Literal['equipment', 'clinic'], user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {'items': [r.item_key for r in db.query(Favorite).filter_by(user_id=user.id, kind=kind).order_by(Favorite.id.desc())]}


@router.put('/favorites/{kind}/{item_key}')
def favorite(kind: Literal['equipment', 'clinic'], item_key: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not item_key or len(item_key) > 80: raise HTTPException(400, '收藏内容不存在')
    db.query(User).filter_by(id=user.id).with_for_update().first()
    if not db.query(Favorite.id).filter_by(user_id=user.id, kind=kind, item_key=item_key).first():
        db.add(Favorite(user_id=user.id, kind=kind, item_key=item_key))
    db.commit()
    return {'saved': True}


@router.delete('/favorites/{kind}/{item_key}')
def unfavorite(kind: Literal['equipment', 'clinic'], item_key: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Favorite).filter_by(user_id=user.id, kind=kind, item_key=item_key).delete()
    db.commit()
    return {'saved': False}
