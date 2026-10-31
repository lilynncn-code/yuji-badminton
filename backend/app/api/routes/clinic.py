from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
import hashlib
import json
from pydantic import BaseModel, Field
from sqlalchemy import cast, String,func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.clinic import ClinicQuestion, ClinicAnswer, ClinicSend
from app.models.social import Favorite
from app.services.social import blocked_ids, ensure_contact_allowed
from app.services.public_media import validate_public_media, retire_public_media
from app.services.file_cleanup import cleanup_files
from app.services.notifications import notify
from app.models.notification import Notification
from app.services.feed_pages import next_position,read_position

router = APIRouter(prefix='/clinic', tags=['clinic'])


class QuestionInput(BaseModel):
    title: str = Field(min_length=2, max_length=100)
    content: str = Field(min_length=2, max_length=2000)
    video_url: str = Field('', max_length=1000)
    request_key:Optional[str]=Field(None,min_length=8,max_length=64,pattern=r'^[A-Za-z0-9_-]+$')


class AnswerInput(BaseModel):
    content: str = Field(min_length=2, max_length=2000)
    request_key:Optional[str]=Field(None,min_length=8,max_length=64,pattern=r'^[A-Za-z0-9_-]+$')


def send_hash(parts):
    return hashlib.sha256(json.dumps(parts,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def saved_send(db,user_id,key,kind,digest):
    row=db.query(ClinicSend).filter_by(user_id=user_id,request_key=key).first() if key else None
    if row:
        if row.kind!=kind or row.content_hash!=digest:raise HTTPException(409,'这次发送的内容已变化，请重新确认后发送')
        question=find_question(db,row.question_id,user_id)
        if kind=='answer':
            answer=db.get(ClinicAnswer,row.answer_id)
            if not answer or answer.question_id!=row.question_id or answer.user_id!=user_id:raise HTTPException(410,'这条回答已经删除，不能恢复原发送内容')
        return question
    return None


def find_question(db, qid, user_id,lock=False):
    query=db.query(ClinicQuestion).filter_by(id=qid)
    if lock:query=query.with_for_update().populate_existing()
    q=query.first()
    if not q: raise HTTPException(404, '这条问题不存在或已删除')
    ensure_contact_allowed(db, user_id, q.user_id)
    return q


def author(db, user_id):
    u = db.get(User, user_id)
    return {'id': user_id, 'name': u.name if u else '已停用账号', 'avatar': u.avatar if u else ''}


def visible_answers(db,qid,user_id):
    return db.query(ClinicAnswer).filter(ClinicAnswer.question_id==qid,ClinicAnswer.user_id.notin_(blocked_ids(db,user_id)))


def answer_data(db,answer):
    return {'id':answer.id,'author':author(db,answer.user_id),'content':answer.content,'created_at':answer.created_at}


def answer_page(db,q,user_id,before_id=None,limit=30,answer_id=None):
    query=visible_answers(db,q.id,user_id)
    count=query.count()
    if answer_id:
        if not query.filter(ClinicAnswer.id==answer_id).first():raise HTTPException(404,'提醒对应的回答已删除或暂时无法查看')
        query=query.filter(ClinicAnswer.id<=answer_id)
    if before_id:query=query.filter(ClinicAnswer.id<before_id)
    rows=query.order_by(ClinicAnswer.id.desc()).limit(limit+1).all()
    accepted=visible_answers(db,q.id,user_id).filter(ClinicAnswer.id==q.accepted_answer_id).first() if q.accepted_answer_id else None
    return {'items':[answer_data(db,a) for a in reversed(rows[:limit])], 'has_more':len(rows)>limit,'answer_count':count,
            'accepted_answer_id':accepted.id if accepted else 0,'accepted_answer':answer_data(db,accepted) if accepted else None}


def question_data(db, q, user_id, detail=False,answer_id=None):
    page=answer_page(db,q,user_id,answer_id=answer_id) if detail else None
    return {'id': q.id, 'author': author(db, q.user_id), 'title': q.title, 'content': q.content, 'video_url': q.video_url,
            'created_at': q.created_at, 'accepted_answer_id': page['accepted_answer_id'] if page else 0,
            'accepted_answer':page['accepted_answer'] if page else None,
            'answer_count':page['answer_count'] if page else visible_answers(db,q.id,user_id).count(),
            'answers':page['items'] if page else [],'answers_has_more':page['has_more'] if page else False}


@router.get('')
def list_questions(mine: bool = False, saved: bool = False, keyword: str = Query('', max_length=100), page: int = Query(1, ge=1), cursor:Optional[str]=Query(None,max_length=2000),user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if page>1:raise HTTPException(400,'请刷新问题后使用新的翻看位置继续')
    query = db.query(ClinicQuestion).filter(ClinicQuestion.user_id.notin_(blocked_ids(db, user.id)))
    if mine: query = query.filter_by(user_id=user.id)
    if saved:
        keys=db.query(Favorite.item_key).filter_by(user_id=user.id,kind='clinic')
        query=query.filter(cast(ClinicQuestion.id,String).in_(keys))
    if keyword.strip(): query = query.filter(ClinicQuestion.title.contains(keyword.strip(),autoescape=True) | ClinicQuestion.content.contains(keyword.strip(),autoescape=True))
    filters=[mine,saved,keyword.strip()]
    max_id,last_id=read_position(cursor,'clinic',user.id,filters) if cursor else (query.with_entities(func.max(ClinicQuestion.id)).scalar() or 0,None)
    query=query.filter(ClinicQuestion.id<=max_id);total=query.count()
    if last_id:query=query.filter(ClinicQuestion.id<last_id)
    rows=query.order_by(ClinicQuestion.id.desc()).limit(21).all();items=rows[:20];has_more=len(rows)>20
    position=next_position('clinic',user.id,filters,max_id,items[-1].id) if has_more else None
    return {'items':[question_data(db,q,user.id) for q in items],'total':total,'has_more':has_more,'next_cursor':position}


@router.post('')
def create_question(payload: QuestionInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if len(payload.title.strip())<2 or len(payload.content.strip())<2: raise HTTPException(400, '请写清楚标题和问题')
    db.query(User).filter_by(id=user.id).with_for_update().first()
    digest=send_hash(['question',payload.title.strip(),payload.content.strip(),payload.video_url])
    existing=saved_send(db,user.id,payload.request_key,'question',digest)
    if existing:return question_data(db,existing,user.id,True)
    validate_public_media(db, payload.video_url, user.id, 'video')
    q = ClinicQuestion(user_id=user.id, title=payload.title.strip(), content=payload.content.strip(), video_url=payload.video_url)
    db.add(q)
    try:
        db.flush()
        if payload.request_key:db.add(ClinicSend(user_id=user.id,request_key=payload.request_key,kind='question',question_id=q.id,content_hash=digest))
        db.commit()
    except IntegrityError:
        db.rollback()
        existing=saved_send(db,user.id,payload.request_key,'question',digest)
        if existing:return question_data(db,existing,user.id,True)
        raise
    return question_data(db, q, user.id, True)


@router.get('/{qid}')
def get_question(qid: int,answer_id:Optional[int]=Query(None,gt=0),user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return question_data(db, find_question(db, qid, user.id), user.id, True,answer_id=answer_id)


@router.get('/{qid}/answers')
def list_answers(qid:int,before_id:Optional[int]=Query(None,gt=0),limit:int=Query(30,ge=1,le=100),user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    return answer_page(db,find_question(db,qid,user.id),user.id,before_id,limit)


@router.post('/{qid}/answers')
def answer_question(qid: int, payload: AnswerInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(User).filter_by(id=user.id).with_for_update().first()
    q = find_question(db, qid, user.id,lock=True)
    if len(payload.content.strip())<2: raise HTTPException(400, '请写下具体建议')
    digest=send_hash(['answer',qid,payload.content.strip()])
    existing=saved_send(db,user.id,payload.request_key,'answer',digest)
    if existing:return question_data(db,existing,user.id,True)
    answer=ClinicAnswer(question_id=q.id,user_id=user.id,content=payload.content.strip())
    db.add(answer)
    try:
        db.flush()
        if payload.request_key:db.add(ClinicSend(user_id=user.id,request_key=payload.request_key,kind='answer',question_id=q.id,answer_id=answer.id,content_hash=digest))
        notify(db,q.user_id,user.id,'clinic_answer','answer',answer.id,q.id,event_key=f'answer:{answer.id}')
        db.commit()
    except IntegrityError:
        db.rollback()
        existing=saved_send(db,user.id,payload.request_key,'answer',digest)
        if existing:return question_data(db,existing,user.id,True)
        raise
    return question_data(db, q, user.id, True)


@router.put('/{qid}/accepted/{aid}')
def accept_answer(qid: int, aid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(ClinicQuestion).filter_by(id=qid).with_for_update().first()
    if not q: raise HTTPException(404, '问题不存在')
    if q.user_id != user.id: raise HTTPException(403, '只有提问者可以选择有帮助的回答')
    answer = db.query(ClinicAnswer).filter_by(id=aid, question_id=qid).first()
    if not answer or answer.user_id == user.id: raise HTTPException(400, '请选择其他球友的回答')
    ensure_contact_allowed(db,user.id,answer.user_id)
    q.accepted_answer_id=aid; db.commit()
    return question_data(db, q, user.id, True)


@router.delete('/{qid}/answers/{aid}')
def delete_answer(qid: int, aid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = find_question(db, qid, user.id,lock=True)
    a = db.query(ClinicAnswer).filter_by(id=aid, question_id=qid, user_id=user.id).first()
    if not a: raise HTTPException(404, '只能删除自己的回答')
    if q.accepted_answer_id == aid: q.accepted_answer_id=0
    db.query(Notification).filter_by(target_type='answer',target_id=aid).delete(synchronize_session=False)
    db.delete(a); db.commit()
    return {'message': '已删除'}


@router.delete('/{qid}')
def delete_question(qid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = find_question(db, qid, user.id,lock=True)
    if q.user_id != user.id: raise HTTPException(403, '只能删除自己的问题')
    db.query(Notification).filter_by(target_type='answer',context_id=qid).delete(synchronize_session=False)
    db.query(ClinicAnswer).filter_by(question_id=qid).delete()
    db.query(Favorite).filter_by(kind='clinic', item_key=str(qid)).delete()
    old_video=q.video_url
    db.delete(q)
    paths=retire_public_media(db,user.id,[old_video])
    db.commit()
    if paths:cleanup_files(db,paths)
    return {'message': '已删除'}
