from typing import Annotated, Iterable, List, Optional, TypeVar

from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.discovery import (
    DiscoveryListResponse,
    DiscoverySearchResponse,
    PlayerCard,
    PlayerDetail,
    VenueCard,
    VenueListResponse,
)

router = APIRouter()


DEFAULT_VENUES = [
    VenueCard(
        id=1,
        name="源深体育中心羽毛球馆",
        avatar="https://images.unsplash.com/photo-1626224583764-f87db24ac4ea?auto=format&fit=crop&w=600&q=80",
        city="上海",
        level="初级/中级/高级",
        distance="1.6km",
        distance_text="1.6km",
        bio="场地多，交通方便，晚间人气高，适合下班后约球。",
        address="上海市浦东新区源深路655号",
        open_time="09:00-22:00",
        price_text="80-120元/小时",
        tags=["交通方便", "晚间热门", "停车"],
    ),
    VenueCard(
        id=2,
        name="万体馆羽毛球中心",
        avatar="https://images.unsplash.com/photo-1547347298-4074fc3086f0?auto=format&fit=crop&w=600&q=80",
        city="上海",
        level="中级/高级",
        distance="3.0km",
        distance_text="3.0km",
        bio="老牌球馆，高手局较多，适合想打强度的球友。",
        address="上海市徐汇区漕溪北路1111号",
        open_time="08:30-22:30",
        price_text="90-140元/小时",
        tags=["高手局", "地铁近", "器材店"],
    ),
    VenueCard(
        id=3,
        name="黄龙体育中心羽毛球馆",
        avatar="https://images.unsplash.com/photo-1612872087720-bb876e2e67d1?auto=format&fit=crop&w=600&q=80",
        city="杭州",
        level="初级/中级",
        distance="2.4km",
        distance_text="2.4km",
        bio="环境舒服，周末上午适合练球和新手局。",
        address="杭州市西湖区黄龙路1号",
        open_time="08:00-22:00",
        price_text="70-110元/小时",
        tags=["新手友好", "周末", "环境好"],
    ),
    VenueCard(
        id=4,
        name="深圳湾体育中心羽毛球馆",
        avatar="https://images.unsplash.com/photo-1521537634581-0dced2fee2ef?auto=format&fit=crop&w=600&q=80",
        city="深圳",
        level="初级/中级/高级",
        distance="2.2km",
        distance_text="2.2km",
        bio="设施新，预约方便，适合固定局和公司局。",
        address="深圳市南山区滨海大道3001号",
        open_time="09:00-23:00",
        price_text="90-150元/小时",
        tags=["设施新", "预约方便", "公司局"],
    ),
]

T = TypeVar("T", PlayerCard, VenueCard)


def normalize(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def has_text(value: str, keyword: str) -> bool:
    return keyword in value.lower()


def match_city(item: T, city: Optional[str]) -> bool:
    city_text = normalize(city)
    return not city_text or has_text(item.city, city_text)


def match_level(item: T, level: Optional[str]) -> bool:
    level_text = normalize(level)
    return not level_text or has_text(item.level, level_text)


def match_keyword(item: T, keyword: Optional[str]) -> bool:
    keyword_text = normalize(keyword)
    if not keyword_text:
        return True

    fields = [
        item.name,
        item.city,
        item.level,
        item.distance,
        item.distance_text,
        item.bio,
        " ".join(item.tags),
    ]
    if isinstance(item, PlayerCard):
        fields.extend([item.favorite_area, item.play_time])
    if isinstance(item, VenueCard):
        fields.extend([item.address, item.open_time, item.price_text])
    return any(has_text(field, keyword_text) for field in fields)


def filter_items(items: Iterable[T], city: Optional[str], level: Optional[str], keyword: Optional[str]) -> List[T]:
    return [
        item
        for item in items
        if match_city(item, city) and match_level(item, level) and match_keyword(item, keyword)
    ]


from datetime import datetime, timedelta
from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.training import TrainingRecord
from app.models.chat import Chat
from app.services.social import blocked_ids
from app.services.discovery_pages import roster,next_position,read_position


def player_data(user, db, points=None):
    if points is None: points = int(db.query(func.coalesce(func.sum(TrainingRecord.score), 0)).filter(TrainingRecord.user_id == user.id).scalar())
    online = bool(user.last_active_at and datetime.utcnow() - user.last_active_at < timedelta(minutes=5))
    return {"id": user.id, "name": user.name, "avatar": user.avatar, "city": user.city or "未设置城市", "level": user.level_tag, "role": user.club or "羽毛球爱好者", "bio": user.bio, "points": points, "tags": [user.level_tag, user.club] if user.club else [user.level_tag], "online": "最近在线" if online else "暂未在线", "hand": user.hand}


def player_cards(db,current_user,ids,points):
    users={u.id:u for u in db.query(User).filter(User.id.in_(ids)).all()}
    chats=db.query(Chat).filter(((Chat.requester_id==current_user.id)&Chat.receiver_id.in_(ids))|((Chat.receiver_id==current_user.id)&Chat.requester_id.in_(ids))).all()
    by_user={c.receiver_id if c.requester_id==current_user.id else c.requester_id:c for c in chats}
    items=[]
    for uid in ids:
        if uid not in users:continue
        item=player_data(users[uid],db,points[uid]);chat=by_user.get(uid)
        item['chat_id']=chat.id if chat else None
        item['chat_state']=('waiting' if chat.requester_id==current_user.id else 'review') if chat and chat.status=='pending' else (chat.status if chat else 'none')
        items.append(item)
    return items


@router.get('/players')
def players(city:Optional[str]=Query(None,max_length=80),keyword:Optional[str]=Query(None,max_length=80),mode:str=Query('all',pattern='^(all|near|training|doubles)$'),page:int=Query(1,ge=1),page_size:int=Query(30,ge=1,le=100),cursor:Optional[str]=Query(None,max_length=2000),current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    if page>1:raise HTTPException(400,'请刷新球友名单后使用新的翻看位置继续')
    _,rows,my_points,revision=roster(db,current_user,city,keyword,mode)
    filters=[(city or '').strip(),(keyword or '').strip(),mode]
    ids=[uid for uid,score in rows];start=0
    if cursor:
        last=read_position(cursor,current_user.id,filters,revision)
        if last not in ids:raise HTTPException(400,'球友名单已变化，请刷新后继续')
        start=ids.index(last)+1
    selected=ids[start:start+page_size];has_more=start+len(selected)<len(rows)
    position=next_position(current_user.id,filters,revision,selected[-1]) if has_more else None
    return {'items':player_cards(db,current_user,selected,dict(rows)),'total':len(rows),'has_more':has_more,'next_cursor':position,'revision':revision,'my_points':my_points}


@router.get('/players/status')
def players_status(city:Optional[str]=Query(None,max_length=80),keyword:Optional[str]=Query(None,max_length=80),mode:str=Query('all',pattern='^(all|near|training|doubles)$'),revision:str=Query('',max_length=64),ids:Optional[list[int]]=Query(None,max_length=100),current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    _,rows,my_points,current=roster(db,current_user,city,keyword,mode)
    points=dict(rows);selected=list(dict.fromkeys(uid for uid in (ids or []) if uid in points))
    return {'revision':current,'changed':revision!=current,'total':len(rows),'my_points':my_points,'items':[] if revision!=current else player_cards(db,current_user,selected,points)}


@router.get("/players/{player_id}")
def player_detail(player_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.get(User, player_id)
    if not user: raise HTTPException(404, "球友不存在")
    item=player_data(user, db)
    chat=None
    if player_id not in blocked_ids(db,current_user.id):
        from app.api.routes.chat import same_pair_filter
        chat=db.query(Chat).filter(same_pair_filter(current_user.id,player_id)).first()
    item['chat_id']=chat.id if chat else None
    item['chat_state']=('waiting' if chat.requester_id==current_user.id else 'review') if chat and chat.status=='pending' else (chat.status if chat else 'none')
    return item


@router.get("/venues")
def venues():
    return {"items": DEFAULT_VENUES, "total": len(DEFAULT_VENUES), "source": "example"}
