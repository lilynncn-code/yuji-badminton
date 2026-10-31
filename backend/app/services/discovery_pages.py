"""Keep the score-ordered discovery list consistent across reads."""
import base64
import hashlib
import hmac
import json
from time import time
from fastapi import HTTPException
from sqlalchemy import func
from app.core.config import settings
from app.models.user import User
from app.models.training import TrainingRecord
from app.services.social import blocked_ids


def roster(db,user,city,keyword,mode):
    query=db.query(User).filter(User.id!=user.id,User.id.notin_(blocked_ids(db,user.id)))
    if city:query=query.filter(User.city==city.strip())
    if mode=='near':query=query.filter(User.city==user.city) if user.city else query.filter(False)
    if mode in ('training','doubles'):
        word='训练' if mode=='training' else '双'
        query=query.filter(User.club.contains(word)|User.level_tag.contains(word)|User.bio.contains(word))
    if keyword and keyword.strip():
        word=keyword.strip()
        query=query.filter(User.name.contains(word,autoescape=True)|User.city.contains(word,autoescape=True)|User.club.contains(word,autoescape=True)|User.level_tag.contains(word,autoescape=True)|User.bio.contains(word,autoescape=True))
    my_points=int(db.query(func.coalesce(func.sum(TrainingRecord.score),0)).filter_by(user_id=user.id).scalar())
    totals=db.query(TrainingRecord.user_id.label('user_id'),func.sum(TrainingRecord.score).label('points')).group_by(TrainingRecord.user_id).subquery()
    points=func.coalesce(totals.c.points,0)
    rows=query.with_entities(User.id,points).outerjoin(totals,totals.c.user_id==User.id).order_by(func.abs(points-my_points),User.id.desc()).all()
    ordered=[(uid,int(score)) for uid,score in rows]
    revision=hashlib.sha256(json.dumps([my_points,ordered],separators=(',',':')).encode()).hexdigest()
    return query,ordered,my_points,revision


def next_position(user_id,filters,revision,last_id):
    data={'u':user_id,'f':filters,'rev':revision,'id':last_id,'exp':int(time())+1800}
    body=base64.urlsafe_b64encode(json.dumps(data,separators=(',',':'),ensure_ascii=False).encode()).decode().rstrip('=')
    signature=hmac.new(settings.secret_key.encode(),('discovery:'+body).encode(),hashlib.sha256).hexdigest()
    return body+'.'+signature


def read_position(cursor,user_id,filters,revision):
    try:
        body,signature=cursor.rsplit('.',1)
        expected=hmac.new(settings.secret_key.encode(),('discovery:'+body).encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature,expected):raise ValueError()
        data=json.loads(base64.urlsafe_b64decode(body+'='*(-len(body)%4)))
        if data['u']!=user_id or data['f']!=filters or data['rev']!=revision or data['exp']<=time():raise ValueError()
        if not isinstance(data['id'],int) or data['id']<=0:raise ValueError()
        return data['id']
    except (ValueError,TypeError,KeyError,UnicodeError):
        raise HTTPException(400,'球友名单或训练累计分有变化，请刷新后继续翻看')
