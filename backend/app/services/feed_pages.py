"""Continue posts or questions without offsets that shift on insert or deletion."""
import base64
import hashlib
import hmac
import json
from time import time
from fastapi import HTTPException
from app.core.config import settings


def next_position(kind,user_id,filters,max_id,last_id):
    data={'u':user_id,'f':filters,'max':max_id,'id':last_id,'exp':int(time())+1800}
    body=base64.urlsafe_b64encode(json.dumps(data,separators=(',',':'),ensure_ascii=False).encode()).decode().rstrip('=')
    signature=hmac.new(settings.secret_key.encode(),(kind+':'+body).encode(),hashlib.sha256).hexdigest()
    return body+'.'+signature


def read_position(cursor,kind,user_id,filters):
    try:
        body,signature=cursor.rsplit('.',1)
        expected=hmac.new(settings.secret_key.encode(),(kind+':'+body).encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature,expected):raise ValueError()
        data=json.loads(base64.urlsafe_b64decode(body+'='*(-len(body)%4)))
        if data['u']!=user_id or data['f']!=filters or data['exp']<=time():raise ValueError()
        if not 0<data['id']<=data['max']:raise ValueError()
        return data['max'],data['id']
    except (ValueError,TypeError,KeyError,UnicodeError):
        raise HTTPException(400,'翻看位置已失效，请刷新列表后继续')
