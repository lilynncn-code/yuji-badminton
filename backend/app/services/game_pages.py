"""Continue ordered games within the original creation boundary."""
import base64
import hashlib
import hmac
import json
import time
from datetime import datetime
from fastapi import HTTPException
from app.core.config import settings


def next_position(user_id,mine,city,max_id,game):
    data={'u':user_id,'mine':mine,'city':city,'max':max_id,'t':game.starts_at.isoformat(),'id':game.id,'exp':int(time.time())+1800}
    body=base64.urlsafe_b64encode(json.dumps(data,separators=(',',':')).encode()).decode().rstrip('=')
    signature=hmac.new(settings.secret_key.encode(),('game-list:'+body).encode(),hashlib.sha256).hexdigest()
    return body+'.'+signature


def read_position(cursor,user_id,mine,city):
    try:
        body,signature=cursor.rsplit('.',1)
        expected=hmac.new(settings.secret_key.encode(),('game-list:'+body).encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature,expected):raise ValueError()
        data=json.loads(base64.urlsafe_b64decode(body+'='*(-len(body)%4)))
        if data['u']!=user_id or data['mine']!=mine or data['city']!=city or data['exp']<=time.time():raise ValueError()
        if not 0<data['id']<=data['max']:raise ValueError()
        starts_at=datetime.fromisoformat(data['t'])
        if starts_at.tzinfo is not None:raise ValueError()
        return data['max'],starts_at,data['id']
    except (ValueError,TypeError,KeyError,UnicodeError):
        raise HTTPException(400,'翻看位置已失效，请刷新球局列表后继续')
