from typing import Literal,Optional
from datetime import datetime, timedelta
from fastapi.responses import FileResponse
from app.services.files import store_file, UPLOADS, valid_image_url
from app.schemas.chat import ChatCombinedRequest, ChatReadRequest

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, Query
from sqlalchemy import and_, desc, or_
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.chat import Chat, ChatMessage, ChatState, ChatChange, ChatSend
from app.models.user import User
from app.models.media import Media
from app.services import files as file_storage
from pathlib import Path
import re
import hashlib
import json
from sqlalchemy.exc import IntegrityError
from app.services.social import ensure_contact_allowed
from app.services.chat_inbox import changed_chat,changed_inboxes,inbox_revision,visible_chats,inbox_summary,page_cursor,read_page_cursor
from app.services.notifications import notify
from app.services.file_cleanup import queue_file_deletion, cleanup_files
from app.services.public_media import retire_public_media
from app.services.private_files import private_path, discard_private_upload
from app.models.notification import Notification
from app.schemas.chat import (
    ChatActionResponse,
    ChatApplyRequest,
    ChatImageMessageRequest,
    ChatListResponse,
    ChatMessageResponse,
    ChatMessagesResponse,
    ChatResponse,
    ChatTextMessageRequest,
    ChatVoiceReplyResponse,
)


router = APIRouter()


try:
    from app.api.deps import get_current_user
except ModuleNotFoundError:
    from app.api.routes.profile import get_current_user


def trim(value: str) -> str:
    return value.strip()


def ensure_tables(db: Session) -> None:
    bind = db.get_bind()
    Chat.__table__.create(bind=bind, checkfirst=True)
    ChatMessage.__table__.create(bind=bind, checkfirst=True)


def same_pair_filter(user_a_id: int, user_b_id: int):
    return or_(
        and_(Chat.requester_id == user_a_id, Chat.receiver_id == user_b_id),
        and_(Chat.requester_id == user_b_id, Chat.receiver_id == user_a_id),
    )


def get_owned_chat_or_fail(chat_id: int, user_id: int, db: Session, allow_blocked=False) -> Chat:
    chat = (
        db.query(Chat)
        .filter(
            Chat.id == chat_id,
            or_(Chat.requester_id == user_id, Chat.receiver_id == user_id),
        )
        .first()
    )
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="聊天不存在")
    if not allow_blocked: ensure_contact_allowed(db, user_id, other_user_id(chat, user_id))
    return chat


def latest_message(chat_id: int, db: Session) -> Optional[ChatMessage]:
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.chat_id == chat_id)
        .order_by(desc(ChatMessage.created_at), desc(ChatMessage.id))
        .first()
    )


def cleared_id(chat_id, user_id, db):
    state = db.get(ChatState, (chat_id, user_id))
    return state.cleared_through_id if state else 0


def lock_chat(chat_id, db):
    return db.query(Chat).filter_by(id=chat_id).with_for_update().populate_existing().one()


def reopen_chat(chat_id, db):
    db.query(ChatState).filter_by(chat_id=chat_id).update({'hidden':False}, synchronize_session=False)


def my_state(chat_id, user_id, db):
    state = db.get(ChatState,(chat_id,user_id))
    if not state:
        state=ChatState(chat_id=chat_id,user_id=user_id,cleared_through_id=0,hidden=False)
        db.add(state)
    return state


def to_message_response(message: ChatMessage) -> ChatMessageResponse:
    return ChatMessageResponse.model_validate(message)


def to_chat_response(chat: Chat, current_user_id: int, db: Session) -> ChatResponse:
    data = ChatResponse.model_validate(chat)
    data.other_user_id = chat.receiver_id if chat.requester_id == current_user_id else chat.requester_id
    other = db.get(User, data.other_user_id)
    data.other_name = other.name if other else "已停用账号"
    data.other_avatar = other.avatar if other else ""
    boundary=cleared_id(chat.id,current_user_id,db)
    read_id = max(chat.requester_read_id if chat.requester_id == current_user_id else chat.receiver_read_id,boundary)
    data.other_read_id=chat.receiver_read_id if chat.requester_id==current_user_id else chat.requester_read_id
    data.unread_count = db.query(ChatMessage).filter(ChatMessage.chat_id == chat.id, ChatMessage.sender_id != current_user_id, ChatMessage.id > read_id,ChatMessage.recalled_at.is_(None)).count()
    data.last_message = None
    message = db.query(ChatMessage).filter(ChatMessage.chat_id==chat.id,ChatMessage.id>boundary).order_by(ChatMessage.id.desc()).first()
    if message:
        data.last_message = to_message_response(message)
    return data


def ensure_accepted(chat: Chat) -> None:
    if chat.status != "accepted":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="双方同意后才能发消息")


def create_message(chat: Chat, sender_id: int, message_type: str, content: str, db: Session) -> ChatMessage:
    chat=lock_chat(chat.id,db)
    ensure_accepted(chat)
    message = ChatMessage(
        chat_id=chat.id,
        sender_id=sender_id,
        message_type=message_type,
        content=content,
    )
    db.add(message)
    reopen_chat(chat.id,db)
    chat.updated_at = datetime.utcnow()
    changed_chat(db,chat)
    db.commit()
    db.refresh(message)
    return message


def other_user_id(chat: Chat, current_user_id: int) -> int:
    return chat.receiver_id if chat.requester_id == current_user_id else chat.requester_id


def validate_chat_image(url, chat_id, user_id, db):
    if not url or url.startswith('https://'): return
    match = re.fullmatch(r'/chat/chats/(\d+)/images/(\d+)', url)
    if match and int(match[1]) == chat_id:
        media = db.query(Media).filter_by(id=int(match[2]),user_id=user_id,purpose='chat',media_type='image',url=url).with_for_update().populate_existing().first()
        if media:
            if not private_path(media.storage_name,existing=True):
                raise HTTPException(400,'聊天图片已不存在，请重新选择图片后发送')
            return
    raise HTTPException(400, '请在这个聊天中重新选择自己的图片')


@router.post('/chats/{chat_id}/images')
async def upload_chat_image(chat_id: int, file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    chat = get_owned_chat_or_fail(chat_id,current_user.id,db)
    ensure_accepted(chat)
    name = await store_file(file,'image',private=True)
    row = Media(user_id=current_user.id,purpose='chat',media_type='image',url='',storage_name=name)
    try:
        chat=get_owned_chat_or_fail(chat_id,current_user.id,db)
        chat=lock_chat(chat_id,db)
        ensure_accepted(chat)
        db.add(row)
        db.flush(); row.url=f'/chat/chats/{chat_id}/images/{row.id}'
        result={'url':row.url,'id':row.id}
        db.commit()
    except Exception:
        discard_private_upload(db,name,rollback=True)
        raise
    return result


@router.get('/chats/{chat_id}/images/{media_id}')
def read_chat_image(chat_id: int, media_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    chat = get_owned_chat_or_fail(chat_id,current_user.id,db)
    media=db.query(Media).filter_by(id=media_id,purpose='chat',media_type='image',url=f'/chat/chats/{chat_id}/images/{media_id}').first()
    if not media or media.user_id not in (chat.requester_id,chat.receiver_id): raise HTTPException(404,'图片不存在')
    # Before sending, only its owner can preview the uploaded draft.
    if media.user_id != current_user.id and not db.query(ChatMessage.id).filter_by(chat_id=chat_id,message_type='image',content=media.url).first():
        raise HTTPException(404,'图片尚未发送')
    path=private_path(media.storage_name,existing=True)
    if not path: raise HTTPException(404,'图片暂时无法读取')
    return FileResponse(path,headers={'Cache-Control':'private, no-store'})


@router.post("/requests", response_model=ChatActionResponse)
def apply_chat(
    payload: ChatApplyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatActionResponse:
    ensure_tables(db)
    if payload.receiver_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能向自己发起聊天")

    receiver = db.query(User).filter(User.id == payload.receiver_id).first()
    if not receiver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    ensure_contact_allowed(db, current_user.id, receiver.id)
    # Serialize opposite-direction requests for the same two accounts.
    db.query(User).filter_by(id=min(current_user.id,receiver.id)).with_for_update().populate_existing().first()
    chat = db.query(Chat).filter(same_pair_filter(current_user.id, receiver.id)).first()
    if chat:
        if chat.status == "rejected":
            chat.requester_id = current_user.id
            chat.receiver_id = receiver.id
            chat.status = "pending"
            chat.note = payload.note.strip()
            notify(db,receiver.id,current_user.id,'chat_request','chat',chat.id)
            changed_chat(db,chat)
            db.commit()
            db.refresh(chat)
            return ChatActionResponse(message="聊天申请已重新发起", chat=to_chat_response(chat, current_user.id, db))
        return ChatActionResponse(message="聊天申请已存在", chat=to_chat_response(chat, current_user.id, db))

    chat = Chat(requester_id=current_user.id, receiver_id=receiver.id, status="pending", note=payload.note.strip())
    db.add(chat)
    db.flush()
    notify(db,receiver.id,current_user.id,'chat_request','chat',chat.id)
    changed_chat(db,chat)
    db.commit()
    db.refresh(chat)
    return ChatActionResponse(message="聊天申请已发起", chat=to_chat_response(chat, current_user.id, db))


@router.post("/requests/{chat_id}/accept", response_model=ChatActionResponse)
def accept_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatActionResponse:
    ensure_tables(db)
    chat = get_owned_chat_or_fail(chat_id, current_user.id, db)
    chat = lock_chat(chat_id,db)
    if chat.receiver_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有接收人可以同意申请")
    if chat.status == "accepted":
        return ChatActionResponse(message="已同意聊天申请", chat=to_chat_response(chat, current_user.id, db))
    if chat.status == "rejected":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="申请已拒绝")

    chat.status = "accepted"
    notify(db,chat.requester_id,current_user.id,'chat_accepted','chat',chat.id,event_key=f'chat-accepted:{chat.id}')
    changed_chat(db,chat)
    db.commit()
    db.refresh(chat)
    return ChatActionResponse(message="已同意聊天申请", chat=to_chat_response(chat, current_user.id, db))


@router.post("/requests/{chat_id}/reject", response_model=ChatActionResponse)
def reject_chat(
    chat_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatActionResponse:
    ensure_tables(db)
    chat = get_owned_chat_or_fail(chat_id, current_user.id, db)
    chat = lock_chat(chat_id,db)
    if chat.receiver_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只有接收人可以拒绝申请")
    if chat.status == "rejected":
        return ChatActionResponse(message="已拒绝聊天申请", chat=to_chat_response(chat, current_user.id, db))
    if chat.status == "accepted":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="已同意的聊天不能拒绝")

    chat.status = "rejected"
    notify(db,chat.requester_id,current_user.id,'chat_rejected','chat',chat.id)
    changed_chat(db,chat)
    db.commit()
    db.refresh(chat)
    return ChatActionResponse(message="已拒绝聊天申请", chat=to_chat_response(chat, current_user.id, db))


@router.get("/chats", response_model=ChatListResponse)
def list_chats(
    kind:Literal['all','threads','requests']='all',
    cursor:Optional[str]=Query(None,max_length=1024),
    limit:int=Query(30,ge=1,le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatListResponse:
    ensure_tables(db)
    revision=inbox_revision(db,current_user.id)
    query=visible_chats(db,current_user.id)
    summary=inbox_summary(db,current_user.id,query)
    if kind=='threads':query=query.filter(Chat.status=='accepted')
    if cursor:
        before,before_id=read_page_cursor(cursor,current_user.id,kind,revision)
        query=query.filter(or_(Chat.updated_at<before,and_(Chat.updated_at==before,Chat.id<before_id)))
    rows=query.order_by(Chat.updated_at.desc(),Chat.id.desc()).limit(limit+1).all()
    chats=rows[:limit];has_more=len(rows)>limit
    return ChatListResponse(chats=[to_chat_response(chat,current_user.id,db) for chat in chats],has_more=has_more,
        next_cursor=page_cursor(current_user.id,kind,revision,chats[-1]) if has_more else None,revision=revision,summary=summary)


@router.get('/chats/status')
def chat_status(ids:list[int]=Query(default=[],max_length=100),current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    if any(i<=0 for i in ids):raise HTTPException(400,'请选择有效的聊天记录')
    query=visible_chats(db,current_user.id)
    return {'revision':inbox_revision(db,current_user.id),'summary':inbox_summary(db,current_user.id,query),
            'chats':[to_chat_response(chat,current_user.id,db) for chat in query.filter(Chat.id.in_(ids)).all()] if ids else []}


@router.get("/chats/{chat_id}/messages", response_model=ChatMessagesResponse)
def list_messages(
    chat_id: int,
    before_id: Optional[int] = Query(default=None, gt=0),
    after_id: Optional[int] = Query(default=None, ge=0),
    after_change_id: Optional[int] = Query(default=None, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatMessagesResponse:
    ensure_tables(db)
    chat = get_owned_chat_or_fail(chat_id, current_user.id, db)
    newest_change=db.query(ChatChange).filter_by(chat_id=chat.id).order_by(ChatChange.id.desc()).first() if after_change_id is None else None
    if before_id is not None and after_id is not None:
        raise HTTPException(400, "请按顺序加载聊天记录")
    boundary=cleared_id(chat.id,current_user.id,db)
    query = db.query(ChatMessage).filter(ChatMessage.chat_id == chat.id,ChatMessage.id>boundary)
    if before_id is not None: query = query.filter(ChatMessage.id < before_id)
    if after_id is not None: query = query.filter(ChatMessage.id > after_id)
    order = ChatMessage.id.asc() if after_id is not None else ChatMessage.id.desc()
    messages = query.order_by(order).limit(limit + 1).all()
    has_more = len(messages) > limit
    messages = messages[:limit]
    if after_id is None: messages.reverse()
    changes=db.query(ChatChange).filter(ChatChange.chat_id==chat.id)
    updates=[]
    if after_change_id is None:
        cursor=newest_change.id if newest_change else 0
    else:
        events=changes.filter(ChatChange.id>after_change_id).order_by(ChatChange.id).limit(100).all()
        cursor=events[-1].id if events else after_change_id
        ids={event.message_id for event in events if event.message_id>boundary}
        updates=db.query(ChatMessage).filter(ChatMessage.id.in_(ids),ChatMessage.chat_id==chat.id).populate_existing().all() if ids else []
    return ChatMessagesResponse(chat=to_chat_response(chat, current_user.id, db), messages=[to_message_response(message) for message in messages], has_more=has_more,message_updates=[to_message_response(m) for m in updates],change_cursor=cursor)



@router.post("/chats/{chat_id}/messages/text", response_model=ChatMessageResponse)
def send_text_message(
    chat_id: int,
    payload: ChatTextMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatMessageResponse:
    ensure_tables(db)
    chat = get_owned_chat_or_fail(chat_id, current_user.id, db)
    content = trim(payload.content)
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="消息不能为空")

    message = create_message(chat, current_user.id, "text", content, db)
    return to_message_response(message)


@router.post("/chats/{chat_id}/messages/image", response_model=ChatMessageResponse)
def send_image_message(
    chat_id: int,
    payload: ChatImageMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatMessageResponse:
    ensure_tables(db)
    chat = get_owned_chat_or_fail(chat_id, current_user.id, db)
    image_url = trim(payload.image_url)
    if not image_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="图片地址不能为空")

    validate_chat_image(image_url, chat_id, current_user.id, db)
    message = create_message(chat, current_user.id, "image", image_url, db)
    return to_message_response(message)


@router.post("/chats/{chat_id}/messages")
def send_combined(chat_id: int, payload: ChatCombinedRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    chat = get_owned_chat_or_fail(chat_id, current_user.id, db)
    chat=lock_chat(chat.id,db)
    ensure_accepted(chat)
    text, image = payload.content.strip(), payload.image_url.strip()
    if not text and not image: raise HTTPException(400, "消息不能为空")
    fingerprint = hashlib.sha256(json.dumps([text, image], ensure_ascii=False).encode()).hexdigest()
    def previous_send():
        saved = db.query(ChatSend).filter_by(chat_id=chat_id, user_id=current_user.id, request_key=payload.request_key).first()
        if not saved:
            return None
        if saved.payload_hash != fingerprint:
            raise HTTPException(409, '这次发送的内容已变化，请重新发送')
        rows = db.query(ChatMessage).filter(ChatMessage.chat_id==chat_id, ChatMessage.id.in_(saved.message_ids)).order_by(ChatMessage.id).populate_existing().all()
        return {'messages': [to_message_response(m) for m in rows]}
    if payload.request_key:
        previous = previous_send()
        if previous is not None:
            return previous
    validate_chat_image(image, chat_id, current_user.id, db)
    messages = []
    for kind, content in (("image", image), ("text", text)):
        if content:
            message = ChatMessage(chat_id=chat.id, sender_id=current_user.id, message_type=kind, content=content)
            db.add(message)
            messages.append(message)
    chat.updated_at = datetime.utcnow()
    reopen_chat(chat.id,db)
    try:
        db.flush()
        if payload.request_key:
            db.add(ChatSend(chat_id=chat_id, user_id=current_user.id, request_key=payload.request_key, payload_hash=fingerprint, message_ids=[m.id for m in messages]))
        changed_chat(db,chat)
        db.commit()
    except IntegrityError:
        db.rollback()
        if payload.request_key:
            previous = previous_send()
            if previous is not None:
                return previous
        raise
    return {"messages": [to_message_response(m) for m in messages]}


@router.post("/chats/{chat_id}/read")
def mark_read(chat_id: int, payload: ChatReadRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    chat = get_owned_chat_or_fail(chat_id, current_user.id, db)
    chat=lock_chat(chat_id,db)
    message = db.query(ChatMessage).filter(ChatMessage.chat_id == chat.id, ChatMessage.id == payload.last_message_id).first()
    if payload.last_message_id and not message: raise HTTPException(400, "消息不存在")
    field = "requester_read_id" if current_user.id == chat.requester_id else "receiver_read_id"
    next_id=max(getattr(chat, field),message.id if message else 0)
    if next_id!=getattr(chat,field):db.query(Chat).filter_by(id=chat.id).update({field:next_id,'updated_at':chat.updated_at})
    db.commit()
    return {"message": "已读"}


@router.post('/chats/{chat_id}/messages/{message_id}/recall',response_model=ChatMessageResponse)
def recall_message(chat_id: int,message_id: int,current_user: User=Depends(get_current_user),db: Session=Depends(get_db)):
    get_owned_chat_or_fail(chat_id,current_user.id,db,allow_blocked=True)
    chat=lock_chat(chat_id,db)
    message=db.query(ChatMessage).filter_by(id=message_id,chat_id=chat_id).first()
    if not message: raise HTTPException(404,'消息不存在')
    if message.sender_id!=current_user.id: raise HTTPException(403,'只能撤回自己发送的消息')
    if message.recalled_at: return to_message_response(message)
    if datetime.utcnow()-message.created_at>timedelta(minutes=2): raise HTTPException(400,'发送已超过2分钟，不能撤回')
    old_type,old_content=message.message_type,message.content
    message.content='';message.message_type='text';message.recalled_at=datetime.utcnow()
    db.add(ChatChange(chat_id=chat_id,message_id=message.id))
    chat.updated_at=datetime.utcnow()
    db.flush()
    changed_chat(db,chat)
    paths=[]
    if old_type=='voice' and old_content and Path(old_content).name==old_content:
        paths.append('private/'+old_content)
    elif old_type=='image' and old_content.startswith(f'/chat/chats/{chat_id}/images/'):
        remaining=db.query(ChatMessage.id).filter_by(chat_id=chat_id,message_type='image',content=old_content).first()
        if not remaining:
            media=db.query(Media).filter_by(user_id=current_user.id,purpose='chat',url=old_content).first()
            if media:
                if media.storage_name and Path(media.storage_name).name==media.storage_name:paths.append('private/'+media.storage_name)
                db.delete(media)
    elif old_type=='image':
        paths.extend(retire_public_media(db,current_user.id,[old_content]))
    for path in paths:queue_file_deletion(db,path)
    db.commit()
    if paths:cleanup_files(db,paths)
    return to_message_response(message)


def clear_my_chat(chat_id,user_id,db,hide=False):
    chat=lock_chat(chat_id,db)
    ensure_accepted(chat)
    state=my_state(chat_id,user_id,db)
    latest=latest_message(chat_id,db)
    state.cleared_through_id=max(state.cleared_through_id,latest.id if latest else 0)
    newly_hidden=hide and not state.hidden
    if hide:state.hidden=True
    field='requester_read_id' if chat.requester_id==user_id else 'receiver_read_id'
    db.query(Chat).filter_by(id=chat.id).update({field:max(getattr(chat,field),state.cleared_through_id),'updated_at':chat.updated_at})
    if newly_hidden:changed_inboxes(db,[user_id])
    db.commit()


@router.delete('/chats/{chat_id}/history')
def clear_history(chat_id:int,current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    get_owned_chat_or_fail(chat_id,current_user.id,db,allow_blocked=True)
    clear_my_chat(chat_id,current_user.id,db)
    return {'message':'已清空你这边的聊天记录，对方的记录不受影响'}


@router.delete('/chats/{chat_id}')
def remove_conversation(chat_id:int,current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    get_owned_chat_or_fail(chat_id,current_user.id,db,allow_blocked=True)
    clear_my_chat(chat_id,current_user.id,db,hide=True)
    return {'message':'已删除你这边的会话，收到新消息时会重新出现'}


@router.post('/chats/{chat_id}/visible')
def open_conversation(chat_id:int,current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    chat=get_owned_chat_or_fail(chat_id,current_user.id,db)
    ensure_accepted(chat);lock_chat(chat_id,db)
    state=my_state(chat_id,current_user.id,db)
    if state.hidden:changed_inboxes(db,[current_user.id])
    state.hidden=False
    db.commit()
    return {'message':'已打开聊天'}


@router.delete("/requests/{chat_id}")
def cancel_request(chat_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    chat = get_owned_chat_or_fail(chat_id, current_user.id, db)
    chat=lock_chat(chat_id,db)
    if chat.requester_id != current_user.id or chat.status != "pending":
        raise HTTPException(400, "只能撤销自己待同意的申请")
    db.query(Notification).filter_by(target_type='chat',target_id=chat_id).delete(synchronize_session=False)
    changed_chat(db,chat)
    db.delete(chat)
    db.commit()
    return {"message": "已撤销"}


@router.post("/chats/{chat_id}/messages/voice")
async def send_voice_message(chat_id: int, audio: UploadFile = File(...), request_key: Optional[str] = Form(None,min_length=8,max_length=64,pattern=r'^[A-Za-z0-9_-]+$'), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    chat = get_owned_chat_or_fail(chat_id, current_user.id, db)
    ensure_accepted(chat)
    name = await store_file(audio, "audio", private=True)
    path=file_storage.UPLOADS/'private'/name
    committed=False
    try:
        fingerprint=hashlib.sha256(b'voice\0'+path.read_bytes()).hexdigest()
        chat=lock_chat(chat_id,db)
        ensure_accepted(chat)
        ensure_contact_allowed(db,current_user.id,chat.receiver_id if chat.requester_id==current_user.id else chat.requester_id)
        def previous_send():
            saved=db.query(ChatSend).filter_by(chat_id=chat_id,user_id=current_user.id,request_key=request_key).first()
            if not saved:return None
            if saved.payload_hash!=fingerprint:raise HTTPException(409,'这次录音已变化，请重新录制后发送')
            message=db.query(ChatMessage).filter(ChatMessage.chat_id==chat_id,ChatMessage.id.in_(saved.message_ids)).populate_existing().first()
            if not message:raise HTTPException(410,'这条录音已经删除，不能重新发送原录音')
            if message.message_type=='voice' and not private_path(message.content,existing=True):
                raise HTTPException(410,'原录音文件已不存在，请重新录制后发送')
            return {'message':to_message_response(message),'source':'user'}
        if request_key:
            previous=previous_send()
            if previous is not None:return previous
        message=ChatMessage(chat_id=chat.id,sender_id=current_user.id,message_type='voice',content=name)
        db.add(message)
        chat.updated_at=datetime.utcnow();reopen_chat(chat.id,db)
        try:
            db.flush()
            if request_key:db.add(ChatSend(chat_id=chat_id,user_id=current_user.id,request_key=request_key,payload_hash=fingerprint,message_ids=[message.id]))
            changed_chat(db,chat)
            db.commit();committed=True
        except IntegrityError:
            db.rollback()
            if request_key:
                previous=previous_send()
                if previous is not None:return previous
            raise
        return {'message':to_message_response(message),'source':'user'}
    finally:
        if not committed:discard_private_upload(db,name,rollback=True)


@router.get("/chats/{chat_id}/messages/{message_id}/audio")
def voice_audio(chat_id: int, message_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    get_owned_chat_or_fail(chat_id, current_user.id, db)
    message = db.query(ChatMessage).filter(ChatMessage.id == message_id, ChatMessage.chat_id == chat_id, ChatMessage.message_type == "voice").first()
    if not message: raise HTTPException(404, "录音不存在")
    path=private_path(message.content,existing=True)
    if not path: raise HTTPException(404, "旧录音未保存，请重新发送")
    return FileResponse(path, headers={"Cache-Control": "private, no-store"})
