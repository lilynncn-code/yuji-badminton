from datetime import date, datetime, timedelta
import re
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.training import TrainingRecord, TrainingProgress
from app.models.user import User
from app.schemas.training import TrainingAdviceUpdate, TrainingMediaUpdate, TrainingHistoryResponse, TrainingRecordCreate, TrainingRecordResponse
from app.models.media import Media
from app.api.deps import get_current_user
from app.services import daily_workout
from app.services.private_files import private_path
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

router = APIRouter()


def ensure_training_table(db: Session) -> None:
    TrainingRecord.__table__.create(bind=db.get_bind(), checkfirst=True)


current_user_dependency = get_current_user

def get_user_record(record_id: int, user: User, db: Session) -> TrainingRecord:
    record = db.query(TrainingRecord).filter(TrainingRecord.id == record_id, TrainingRecord.user_id == user.id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="训练记录不存在")
    return record


@router.post("", response_model=TrainingRecordResponse)
def create_training_record(
    payload: TrainingRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_user_dependency),
) -> TrainingRecordResponse:
    if payload.request_key and payload.request_key.startswith('daily-v1-'):
        raise HTTPException(400,'今日练习请从每日安排中保存')
    ensure_training_table(db)
    # Serialize this account's retries and progress changes in the same transaction.
    db.query(User).filter(User.id == current_user.id).with_for_update().populate_existing().one()
    if payload.request_key:
        existing = db.query(TrainingRecord).filter(TrainingRecord.user_id == current_user.id, TrainingRecord.request_key == payload.request_key).first()
        if existing:
            if (existing.training_type, existing.duration_seconds, existing.score, existing.reps, existing.task_id) != (payload.training_type.strip(), payload.duration_seconds, payload.score, payload.reps, payload.task_id):
                raise HTTPException(409, "这次训练已经保存，请勿改为另一份记录")
            return TrainingRecordResponse.model_validate(existing)
    if not payload.training_type.strip():
        raise HTTPException(400, "请填写训练名称")
    if payload.media_url or payload.media_type:
        media = db.query(Media).filter_by(user_id=current_user.id, purpose='training', media_type='video', url=payload.media_url).first()
        if not media or payload.media_type != 'video' or media.url != f'/media/{media.id}/file':
            raise HTTPException(400, '请先上传自己的训练视频')
        if not private_path(media.storage_name,existing=True):
            raise HTTPException(400,'训练视频已不存在，请重新上传后保存')
        if db.query(TrainingRecord.id).filter_by(user_id=current_user.id, media_url=media.url).first():
            raise HTTPException(409, '这段视频已属于另一条训练记录，请重新上传本次视频')
    record = TrainingRecord(
        user_id=current_user.id,
        training_type=payload.training_type.strip(),
        task_id=payload.task_id,
        request_key=payload.request_key,
        reps=payload.reps,
        recording_method=payload.recording_method,
        duration_seconds=payload.duration_seconds,
        score=payload.score,
        advice=payload.advice.strip(),
        media_url=payload.media_url.strip() if payload.media_url else None,
        media_type=payload.media_type.strip() if payload.media_type else None,
    )
    if payload.task_id:
        order = task_order(payload.task_id)
        progress = get_progress(current_user, db)
        completed = list(progress.completed)
        mini_index = (order % 400) // 4 + 1
        required_seconds = 30 + ((mini_index - 1) % 3) * 30
        if payload.duration_seconds < required_seconds or payload.reps < 1:
            raise HTTPException(400, f"关卡训练需要至少{required_seconds}秒，并记录一次实际动作")
        if payload.task_id not in completed:
            if order != len(completed): raise HTTPException(400, "请先完成前面的关卡")
            progress.completed = completed + [payload.task_id]
    db.add(record)
    db.commit()
    db.refresh(record)
    return TrainingRecordResponse.model_validate(record)


@router.get("", response_model=TrainingHistoryResponse)
def list_training_records(
    before_id: Optional[int] = Query(default=None, gt=0),
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(current_user_dependency),
) -> TrainingHistoryResponse:
    ensure_training_table(db)
    query = db.query(TrainingRecord).filter(TrainingRecord.user_id == current_user.id)
    if before_id is not None:
        query = query.filter(TrainingRecord.id < before_id)
    records = query.order_by(TrainingRecord.id.desc()).limit(limit + 1).all()
    return TrainingHistoryResponse(records=[TrainingRecordResponse.model_validate(record) for record in records[:limit]], has_more=len(records)>limit)


def task_order(value):
    match = re.fullmatch(r"unit-([1-6])-m(\d+)-t([1-4])", value or "")
    if not match or not 1 <= int(match[2]) <= 100: raise HTTPException(400, "训练关卡不存在")
    return (int(match[1]) - 1) * 400 + (int(match[2]) - 1) * 4 + int(match[3]) - 1


def get_progress(user, db):
    progress = db.get(TrainingProgress, user.id)
    if not progress:
        progress = TrainingProgress(user_id=user.id, completed=[])
        db.add(progress)
        db.flush()
    return progress


@router.get("/progress")
def progress_data(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    progress = get_progress(current_user, db)
    db.commit()
    return {"completed": progress.completed, "xp": len(progress.completed) * 20}


@router.get("/summary")
def summary(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    records = db.query(TrainingRecord).filter(TrainingRecord.user_id == current_user.id).order_by(TrainingRecord.created_at.desc()).all()
    # User-facing days follow China local date, not server UTC date.
    today = (datetime.utcnow() + timedelta(hours=8)).date()
    active_records = [r for r in records if r.reps > 0]
    dates = {(r.created_at + timedelta(hours=8)).date() for r in active_records}
    cursor = today if today in dates else today - timedelta(days=1)
    streak = 0
    while cursor in dates:
        streak += 1
        cursor -= timedelta(days=1)
    weekly = [r for r in active_records if (r.created_at + timedelta(hours=8)).date() >= today - timedelta(days=6)]
    progress = get_progress(current_user, db)
    db.commit()
    return {"sessions": len(records), "weekly_sessions": len(weekly), "weekly_minutes": sum(r.duration_seconds for r in weekly) // 60,
            "active_days": len({(r.created_at + timedelta(hours=8)).date() for r in weekly}), "today_done": today in dates,
            "streak": streak, "xp": len(progress.completed) * 20,
            "last_date": max(dates).isoformat() if dates else "", "total_minutes": sum(r.duration_seconds for r in records) // 60}


@router.get('/daily')
def daily_arrangement(current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    day=daily_workout.today();plan=daily_workout.plan(day)
    records={r.request_key:r for r in db.query(TrainingRecord).filter(TrainingRecord.user_id==current_user.id,TrainingRecord.request_key.in_([daily_workout.key(day,s['index']) for s in plan['steps']]))}
    for step in plan['steps']:
        record=records.get(daily_workout.key(day,step['index']))
        step['record_id']=record.id if record else None
        step['completed']=bool(record)
        step['actual_reps']=record.reps if record else 0
    return plan


class DailyStepInput(BaseModel):
    duration_seconds:int=Field(ge=1,le=3600)
    reps:int=Field(ge=1,le=1000)


@router.post('/daily/{day}/{step_index}',response_model=TrainingRecordResponse)
def save_daily_step(day:date,step_index:int,payload:DailyStepInput,current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    db.query(User).filter_by(id=current_user.id).with_for_update().populate_existing().one()
    plan=daily_workout.plan(day)
    if not 0<=step_index<len(plan['steps']):raise HTTPException(404,'这组练习不存在')
    request_key=daily_workout.key(day,step_index)
    existing=db.query(TrainingRecord).filter_by(user_id=current_user.id,request_key=request_key).first()
    if existing:return TrainingRecordResponse.model_validate(existing)
    if day!=daily_workout.today():raise HTTPException(409,'今日日期已变化，请重新打开每日安排')
    previous=[daily_workout.key(day,i) for i in range(step_index)]
    if db.query(TrainingRecord).filter(TrainingRecord.user_id==current_user.id,TrainingRecord.request_key.in_(previous)).count()!=step_index:
        raise HTTPException(400,'请先完成前面的练习')
    step=plan['steps'][step_index]
    if payload.duration_seconds<step['seconds'] or payload.reps<step['reps']:
        raise HTTPException(400,f"这组需要至少{step['seconds']}秒，并填写不少于{step['reps']}次的实际次数")
    record=TrainingRecord(user_id=current_user.id,training_type='今日练习 · '+step['title'],duration_seconds=payload.duration_seconds,reps=payload.reps,score=100,recording_method='manual',request_key=request_key,advice='次数由本人填写；已达到本组时长和次数目标，此记录不判断动作是否标准。')
    db.add(record)
    try:db.commit()
    except IntegrityError:
        db.rollback()
        existing=db.query(TrainingRecord).filter_by(user_id=current_user.id,request_key=request_key).first()
        if existing:return TrainingRecordResponse.model_validate(existing)
        raise
    db.refresh(record)
    return TrainingRecordResponse.model_validate(record)


@router.get("/{record_id}", response_model=TrainingRecordResponse)
def get_training_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_user_dependency),
) -> TrainingRecordResponse:
    ensure_training_table(db)
    record = get_user_record(record_id, current_user, db)
    return TrainingRecordResponse.model_validate(record)


@router.patch("/{record_id}/advice", response_model=TrainingRecordResponse)
def save_training_advice(
    record_id: int,
    payload: TrainingAdviceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_user_dependency),
) -> TrainingRecordResponse:
    ensure_training_table(db)
    record = get_user_record(record_id, current_user, db)
    record.advice = payload.advice.strip()
    db.commit()
    db.refresh(record)
    return TrainingRecordResponse.model_validate(record)


@router.patch('/{record_id}/media', response_model=TrainingRecordResponse)
def attach_training_video(record_id: int, payload: TrainingMediaUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db.query(User).filter(User.id == current_user.id).with_for_update().populate_existing().one()
    record = get_user_record(record_id, current_user, db)
    media = db.query(Media).filter_by(id=payload.media_id, user_id=current_user.id, purpose='training', media_type='video').first()
    if not media or media.url != f'/media/{media.id}/file': raise HTTPException(400, '请先上传自己的训练视频')
    if db.query(TrainingRecord.id).filter(TrainingRecord.user_id == current_user.id, TrainingRecord.media_url == media.url, TrainingRecord.id != record_id).first():
        raise HTTPException(409, '这段视频已属于另一条训练记录，请重新上传本次视频')
    if record.media_url and record.media_url != media.url: raise HTTPException(409, '已有训练视频，请先删除旧视频')
    if not private_path(media.storage_name,existing=True):
        raise HTTPException(400,'训练视频已不存在，请重新上传后保存')
    record.media_url, record.media_type = media.url, 'video'
    db.commit(); db.refresh(record)
    return TrainingRecordResponse.model_validate(record)
