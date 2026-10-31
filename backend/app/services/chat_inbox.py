"""Bounded inbox reads; reject an old page boundary after ordering changes."""
import base64
import hashlib
import hmac
import json
import time
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import and_,or_,case,func
from app.core.config import settings
from app.models.chat import Chat,ChatMessage,ChatState,ChatInboxRevision
from app.services.social import blocked_ids


def changed_inboxes(db,user_ids):
    rows=[{'user_id':uid,'revision':1} for uid in sorted(set(user_ids)) if uid>0]
    if not rows:return
    if db.get_bind().dialect.name=='sqlite':
        from sqlalchemy.dialects.sqlite import insert
        statement=insert(ChatInboxRevision).values(rows)
        statement=statement.on_conflict_do_update(index_elements=['user_id'],set_={'revision':ChatInboxRevision.revision+1})
    else:
        from sqlalchemy.dialects.mysql import insert
        statement=insert(ChatInboxRevision).values(rows)
        statement=statement.on_duplicate_key_update(revision=ChatInboxRevision.revision+1)
    db.execute(statement)


def changed_chat(db,chat):
    changed_inboxes(db,[chat.requester_id,chat.receiver_id])


def inbox_revision(db,user_id):
    return db.query(ChatInboxRevision.revision).filter_by(user_id=user_id).scalar() or 0


def visible_chats(db,user_id):
    hidden=blocked_ids(db,user_id)
    return (db.query(Chat).outerjoin(ChatState,and_(ChatState.chat_id==Chat.id,ChatState.user_id==user_id))
            .filter(or_(Chat.requester_id==user_id,Chat.receiver_id==user_id),
                    or_(ChatState.hidden.is_(None),ChatState.hidden.is_(False)),
                    Chat.requester_id.notin_(hidden),Chat.receiver_id.notin_(hidden)))


def inbox_summary(db,user_id,query):
    accepted=query.filter(Chat.status=='accepted')
    read_id=case((Chat.requester_id==user_id,Chat.requester_read_id),else_=Chat.receiver_read_id)
    unread=(accepted.join(ChatMessage,ChatMessage.chat_id==Chat.id).with_entities(func.count(ChatMessage.id))
            .filter(ChatMessage.sender_id!=user_id,
                    ChatMessage.id>read_id,ChatMessage.id>func.coalesce(ChatState.cleared_through_id,0),ChatMessage.recalled_at.is_(None)).scalar())
    return {'total_threads':accepted.count(),'total_requests':query.count(),
            'pending_incoming':query.filter(Chat.status=='pending',Chat.receiver_id==user_id).count(),'unread_count':unread or 0}


def page_cursor(user_id,kind,revision,chat):
    data={'u':user_id,'k':kind,'r':revision,'t':chat.updated_at.isoformat(),'id':chat.id,'exp':int(time.time())+1800}
    body=base64.urlsafe_b64encode(json.dumps(data,separators=(',',':')).encode()).decode().rstrip('=')
    signature=hmac.new(settings.secret_key.encode(),('chat-inbox:'+body).encode(),hashlib.sha256).hexdigest()
    return body+'.'+signature


def read_page_cursor(cursor,user_id,kind,revision):
    try:
        body,signature=cursor.rsplit('.',1)
        expected=hmac.new(settings.secret_key.encode(),('chat-inbox:'+body).encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected,signature):raise ValueError()
        data=json.loads(base64.urlsafe_b64decode(body+'='*(-len(body)%4)))
        if data['u']!=user_id or data['k']!=kind or data['exp']<=time.time() or data['id']<=0:raise ValueError()
        before=datetime.fromisoformat(data['t'])
        if before.tzinfo is not None:raise ValueError()
    except (ValueError,TypeError,KeyError,UnicodeError):
        raise HTTPException(400,'翻看位置已失效，请刷新列表后继续')
    if data['r']!=revision:raise HTTPException(409,'聊天列表有更新，请刷新后继续翻看')
    return before,data['id']
