from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import and_,or_,func
from sqlalchemy.exc import IntegrityError
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.game import Game, GameMember
from app.services.social import blocked_ids, ensure_contact_allowed
from app.services.notifications import notify
from app.services.game_pages import next_position,read_position

router = APIRouter(prefix='/games', tags=['games'])


class GameInput(BaseModel):
    title: str = Field(min_length=2, max_length=80)
    city: str = Field(min_length=1, max_length=80)
    venue: str = Field(min_length=2, max_length=200)
    starts_at: datetime
    duration_minutes: int = Field(60, ge=30, le=480)
    capacity: int = Field(4, ge=2, le=40)
    cost_note: str = Field('', max_length=200)
    note: str = Field('', max_length=1000)
    request_key:Optional[str]=Field(None,min_length=8,max_length=64,pattern=r'^[A-Za-z0-9_-]+$')


def find_game(db, game_id, lock=False):
    query = db.query(Game).filter_by(id=game_id)
    if lock: query = query.with_for_update().populate_existing()
    game = query.first()
    if not game: raise HTTPException(404, '这场球局不存在')
    return game


def game_data(db, game, user_id):
    members = db.query(User).join(GameMember, GameMember.user_id == User.id).filter(GameMember.game_id == game.id).order_by(GameMember.id).all()
    host = db.get(User, game.host_id)
    return {'id': game.id, 'host_id': game.host_id, 'host_name': host.name if host else '已停用账号',
            'title': game.title, 'city': game.city, 'venue': game.venue, 'starts_at': game.starts_at.isoformat()+'Z',
            'duration_minutes': game.duration_minutes, 'capacity': game.capacity, 'cost_note': game.cost_note,
            'note': game.note, 'status': 'ended' if game.status == 'open' and game.starts_at <= datetime.utcnow() else game.status,
            'joined': any(m.id == user_id for m in members), 'count': len(members),
            'members': [{'id': m.id, 'name': m.name, 'avatar': m.avatar} for m in members]}


def repeated_game(db,user_id,key,values):
    existing=db.query(Game).filter_by(host_id=user_id,request_key=key).first() if key else None
    if existing and any(getattr(existing,field)!=value for field,value in values.items()):
        raise HTTPException(409,'这次球局已经保存，不能用同一次发送改为另一场')
    return existing


def ensure_game_visible(db,game,user_id):
    # Existing participants still need cancellation details even after blocking.
    if game.host_id in blocked_ids(db,user_id) and not db.query(GameMember.id).filter_by(game_id=game.id,user_id=user_id).first():
        raise HTTPException(404,'这场球局已不可查看')


@router.post('')
def create_game(payload: GameInput, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.starts_at.tzinfo is None: raise HTTPException(400, '请重新选择日期和时间')
    starts_at = payload.starts_at.astimezone(timezone.utc).replace(tzinfo=None)
    values={**payload.model_dump(exclude={'request_key'}),'starts_at':starts_at}
    for field in ('title','city','venue','cost_note','note'):values[field]=values[field].strip()
    db.query(User).filter_by(id=user.id).with_for_update().populate_existing().one()
    existing=repeated_game(db,user.id,payload.request_key,values)
    if existing:return game_data(db,existing,user.id)
    if not datetime.utcnow()+timedelta(minutes=5) < starts_at < datetime.utcnow()+timedelta(days=180):
        raise HTTPException(400, '请选择5分钟后、半年内的时间')
    if len(values['title'])<2 or len(values['venue'])<2 or not values['city']:
        raise HTTPException(400,'名称和场地需要至少2字，并填写城市')
    game = Game(host_id=user.id,request_key=payload.request_key,**values)
    try:
        db.add(game); db.flush()
        db.add(GameMember(game_id=game.id, user_id=user.id)); db.commit()
    except IntegrityError:
        db.rollback()
        existing=repeated_game(db,user.id,payload.request_key,values)
        if existing:return game_data(db,existing,user.id)
        raise
    return game_data(db, game, user.id)


@router.get('')
def list_games(city: str = Query('', max_length=80), mine: bool = False, cursor:Optional[str]=Query(None,max_length=1024),limit:int=Query(20,ge=1,le=100),user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    city='' if mine else city.strip()
    maximum,before,before_id=read_position(cursor,user.id,mine,city) if cursor else (db.query(func.max(Game.id)).scalar() or 0,None,None)
    query = db.query(Game)
    if mine: query = query.filter(Game.id.in_(db.query(GameMember.game_id).filter_by(user_id=user.id)))
    else: query = query.filter(Game.status == 'open', Game.starts_at > datetime.utcnow(), Game.host_id.notin_(blocked_ids(db, user.id)))
    if city: query = query.filter(Game.city == city)
    query=query.filter(Game.id<=maximum)
    total = query.count()
    if cursor:query=query.filter(or_(Game.starts_at>before,and_(Game.starts_at==before,Game.id>before_id)))
    rows=query.order_by(Game.starts_at,Game.id).limit(limit+1).all()
    games=rows[:limit];more=len(rows)>limit
    return {'items': [game_data(db, g, user.id) for g in games], 'total': total,'has_more':more,
            'next_cursor':next_position(user.id,mine,city,maximum,games[-1]) if more else None}


@router.get('/{game_id}')
def get_game(game_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    game = find_game(db, game_id)
    ensure_game_visible(db,game,user.id)
    return game_data(db, game, user.id)


@router.put('/{game_id}/join')
def join_game(game_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    game = find_game(db, game_id, lock=True)
    ensure_contact_allowed(db, user.id, game.host_id)
    if game.status != 'open' or game.starts_at <= datetime.utcnow(): raise HTTPException(400, '这场球局已关闭报名')
    if not db.query(GameMember.id).filter_by(game_id=game.id, user_id=user.id).first():
        if db.query(GameMember).filter_by(game_id=game.id).count() >= game.capacity: raise HTTPException(409, '人数已满，请选择其他球局')
        db.add(GameMember(game_id=game.id, user_id=user.id))
        notify(db,game.host_id,user.id,'game_joined','game',game.id)
    db.commit()
    return game_data(db, game, user.id)


@router.delete('/{game_id}/join')
def leave_game(game_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    game = find_game(db, game_id, lock=True)
    ensure_game_visible(db,game,user.id)
    if game.host_id == user.id: raise HTTPException(400, '发起人请使用取消球局')
    if game.starts_at <= datetime.utcnow(): raise HTTPException(400, '开始后不能退出，请联系发起人')
    membership=db.query(GameMember).filter_by(game_id=game.id,user_id=user.id).first()
    if membership:
        db.delete(membership)
        notify(db,game.host_id,user.id,'game_left','game',game.id)
    db.commit()
    return game_data(db, game, user.id)


@router.post('/{game_id}/cancel')
def cancel_game(game_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    game = find_game(db, game_id, lock=True)
    if game.host_id != user.id: raise HTTPException(403, '只有发起人可以取消')
    if game.status=='cancelled':return game_data(db,game,user.id)
    if game.starts_at <= datetime.utcnow(): raise HTTPException(400, '球局已经开始，无法取消')
    game.status = 'cancelled'
    for member in db.query(GameMember).filter_by(game_id=game.id):
        notify(db,member.user_id,user.id,'game_cancelled','game',game.id,event_key=f'game-cancelled:{game.id}')
    db.commit()
    return game_data(db, game, user.id)
