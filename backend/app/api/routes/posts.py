import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.db.session import get_db
from app.models.post import Post, PostComment, PostLike
from app.models.user import User
from app.models.social import Follow
from app.services.social import blocked_ids, ensure_contact_allowed
from app.schemas.posts import (
    CommentCreateRequest,
    CommentResponse,
    LikeResponse,
    PostCreateRequest,
    PostListResponse,
    PostResponse,
    PostUpdateRequest,
    ReplyTargetResponse,CommentListResponse,
)

from app.api.deps import get_current_user
from app.services.files import valid_image_url
from app.services.public_media import validate_public_media, retire_public_media
from app.services.file_cleanup import cleanup_files
from app.models.notification import Notification
from app.services.notifications import notify
from app.services.feed_pages import next_position,read_position

router = APIRouter()

EDIT_LIMIT = timedelta(minutes=15)


def clean_list(values: list[str]) -> list[str]:
    items = [value.strip() for value in values if value.strip()]
    for item in items: valid_image_url(item)
    return items


current_user_dependency = get_current_user

def ensure_tables(db: Session) -> None:
    bind = db.get_bind()
    Post.__table__.create(bind=bind, checkfirst=True)
    PostLike.__table__.create(bind=bind, checkfirst=True)
    PostComment.__table__.create(bind=bind, checkfirst=True)


def get_post_or_404(db: Session, post_id: int, user_id: int, lock=False) -> Post:
    query = db.query(Post).filter(Post.id == post_id, Post.removed_at.is_(None))
    if lock: query = query.with_for_update().populate_existing()
    post = query.first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="动态不存在")
    ensure_contact_allowed(db, user_id, post.user_id, lock=lock)
    return post


def liked_by_user(db: Session, post_id: int, user_id: int) -> bool:
    return db.query(PostLike).filter(PostLike.post_id == post_id, PostLike.user_id == user_id).first() is not None


def can_edit(post: Post, user_id: int) -> bool:
    return post.user_id == user_id and datetime.utcnow() <= post.created_at + EDIT_LIMIT


def to_comment_response(comment: PostComment, db: Session, viewer_id: int) -> CommentResponse:
    target=db.get(PostComment,comment.reply_to_id) if comment.reply_to_id else None
    reply=None
    if target and not target.deleted_at and target.post_id==comment.post_id and target.user_id not in blocked_ids(db,viewer_id):
        reply=ReplyTargetResponse(id=target.id,user_id=target.user_id,author_name=target.user.name,content=target.content[:160])
    return CommentResponse(
        id=comment.id,
        post_id=comment.post_id,
        user_id=comment.user_id,
        author=comment.user,
        content=comment.content,
        reply_to_id=comment.reply_to_id,
        reply_to=reply,
        created_at=comment.created_at,
    )


def to_response(db: Session, post: Post, user_id: int, include_comments: bool = False, comment_id: Optional[int] = None) -> PostResponse:
    hidden = blocked_ids(db, user_id)
    comments_query=db.query(PostComment).filter(PostComment.post_id==post.id,PostComment.deleted_at.is_(None),PostComment.user_id.notin_(hidden))
    comments_count=comments_query.count()
    comments = []
    has_more=False
    if include_comments:
        if comment_id:
            if not comments_query.filter(PostComment.id==comment_id).first():raise HTTPException(404,'这条留言已删除或暂时无法查看')
            comments_query=comments_query.filter(PostComment.id<=comment_id)
        rows=comments_query.order_by(PostComment.id.desc()).limit(31).all()
        has_more=len(rows)>30;comments=list(reversed(rows[:30]))
    return PostResponse(
        id=post.id,
        user_id=post.user_id,
        author=post.author,
        content=post.content,
        image_urls=post.image_urls or [],
        video_url=post.video_url,
        likes_count=max(post.likes_count, 0),
        comments_count=comments_count,
        comments=[to_comment_response(comment,db,user_id) for comment in comments],
        comments_has_more=has_more,
        liked_by_me=liked_by_user(db, post.id, user_id),
        can_edit=can_edit(post, user_id),
        created_at=post.created_at,
        updated_at=post.updated_at,
    )


@router.post("", response_model=PostResponse)
def create_post(
    payload: PostCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_user_dependency),
) -> PostResponse:
    ensure_tables(db)
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="动态内容不能为空")

    images = clean_list(payload.image_urls)
    db.query(User).filter(User.id == current_user.id).with_for_update().populate_existing().one()
    if payload.request_key:
        existing = db.query(Post).filter_by(user_id=current_user.id,request_key=payload.request_key).first()
        if existing:
            if existing.removed_at:raise HTTPException(410,'这条动态已被处理移除，不能再次提交原发送内容')
            if (existing.content,existing.image_urls,existing.video_url)!=(content,images,payload.video_url):
                raise HTTPException(409,'这条动态已经保存，请重新打开后编辑')
            return to_response(db,existing,current_user.id)
    for image in images:
        validate_public_media(db, image, current_user.id, 'image')
    validate_public_media(db, payload.video_url, current_user.id, 'video')
    post = Post(
        user_id=current_user.id,
        content=content,
        image_urls=images,
        video_url=payload.video_url,
        request_key=payload.request_key,
        likes_count=0,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return to_response(db, post, current_user.id)


@router.get("", response_model=PostListResponse)
def list_posts(
    mine: bool = False,
    following: bool = False,
    keyword: Optional[str] = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    cursor: Optional[str] = Query(None,max_length=2000),
    db: Session = Depends(get_db),
    current_user: User = Depends(current_user_dependency),
) -> PostListResponse:
    ensure_tables(db)
    if page>1:raise HTTPException(400,'请刷新动态后使用新的翻看位置继续')
    query = db.query(Post).filter(Post.removed_at.is_(None), Post.user_id.notin_(blocked_ids(db, current_user.id)))
    if following: query = query.filter(Post.user_id.in_(db.query(Follow.target_id).filter_by(user_id=current_user.id)))
    if keyword: query = query.filter(Post.content.contains(keyword.strip(),autoescape=True))
    if mine: query = query.filter(Post.user_id == current_user.id)
    filters=[mine,following,(keyword or '').strip()]
    max_id,last_id=read_position(cursor,'posts',current_user.id,filters) if cursor else (query.with_entities(func.max(Post.id)).scalar() or 0,None)
    query=query.filter(Post.id<=max_id);total=query.count()
    if last_id:query=query.filter(Post.id<last_id)
    rows=query.order_by(Post.id.desc()).limit(page_size+1).all();posts=rows[:page_size];has_more=len(rows)>page_size
    position=next_position('posts',current_user.id,filters,max_id,posts[-1].id) if has_more else None
    return PostListResponse(items=[to_response(db,post,current_user.id) for post in posts],total=total,has_more=has_more,next_cursor=position)


@router.get("/{post_id}", response_model=PostResponse)
def get_post(
    post_id: int,
    comment_id: Optional[int]=Query(None,gt=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(current_user_dependency),
) -> PostResponse:
    ensure_tables(db)
    post = get_post_or_404(db, post_id, current_user.id)
    return to_response(db, post, current_user.id, include_comments=True,comment_id=comment_id)


@router.get('/{post_id}/comments',response_model=CommentListResponse)
def list_comments(post_id:int,before_id:Optional[int]=Query(None,gt=0),limit:int=Query(30,ge=1,le=100),db:Session=Depends(get_db),current_user:User=Depends(get_current_user)):
    get_post_or_404(db,post_id,current_user.id)
    query=db.query(PostComment).filter(PostComment.post_id==post_id,PostComment.deleted_at.is_(None),PostComment.user_id.notin_(blocked_ids(db,current_user.id)))
    if before_id:query=query.filter(PostComment.id<before_id)
    rows=query.order_by(PostComment.id.desc()).limit(limit+1).all()
    return CommentListResponse(items=[to_comment_response(c,db,current_user.id) for c in reversed(rows[:limit])],has_more=len(rows)>limit)


@router.post("/{post_id}/comments", response_model=CommentResponse)
def create_comment(
    post_id: int,
    payload: CommentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_user_dependency),
) -> CommentResponse:
    ensure_tables(db)
    post = get_post_or_404(db, post_id, current_user.id)
    db.query(User).filter_by(id=current_user.id).with_for_update().populate_existing().one()
    post=db.query(Post).filter_by(id=post_id).with_for_update().populate_existing().first()
    if not post or post.removed_at:raise HTTPException(404,'动态已删除或已被处理移除')
    ensure_contact_allowed(db,current_user.id,post.user_id,lock=True)
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="留言不能为空")
    def existing_comment():
        existing=db.query(PostComment).filter_by(user_id=current_user.id,request_key=payload.request_key).with_for_update().populate_existing().first()
        if existing:
            if existing.deleted_at:raise HTTPException(410,'这条留言已经删除，不能再次提交原发送内容')
            if (existing.post_id,existing.content,existing.reply_to_id)!=(post_id,content,payload.reply_to_id):raise HTTPException(409,'这次留言的内容已变化，请重新发送')
        return existing
    if payload.request_key:
        existing=existing_comment()
        if existing:return to_comment_response(existing,db,current_user.id)
    target=None
    if payload.reply_to_id:
        target=db.query(PostComment).filter_by(id=payload.reply_to_id,post_id=post.id,deleted_at=None).with_for_update().populate_existing().first()
        if not target:raise HTTPException(404,'要回复的留言已删除，请重新选择')
        ensure_contact_allowed(db,current_user.id,target.user_id,lock=True)
    comment = PostComment(post_id=post.id,user_id=current_user.id,content=content,reply_to_id=payload.reply_to_id,request_key=payload.request_key)
    db.add(comment)
    try:
        db.flush()
        recipients={post.user_id:'post_comment'}
        if target:recipients[target.user_id]='comment_reply'
        for recipient,kind in recipients.items():notify(db,recipient,current_user.id,kind,'comment',comment.id,post.id,event_key=f'comment:{comment.id}')
        db.commit()
    except IntegrityError:
        db.rollback()
        existing=existing_comment() if payload.request_key else None
        if existing:return to_comment_response(existing,db,current_user.id)
        raise
    db.refresh(comment)
    return to_comment_response(comment,db,current_user.id)


@router.put("/{post_id}", response_model=PostResponse)
def update_post(
    post_id: int,
    payload: PostUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_user_dependency),
) -> PostResponse:
    ensure_tables(db)
    post = get_post_or_404(db, post_id, current_user.id, lock=True)
    if post.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只能编辑自己的动态")
    if datetime.utcnow() > post.created_at + EDIT_LIMIT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="动态发布超过15分钟，不能编辑")

    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="动态内容不能为空")
    images=clean_list(payload.image_urls)
    old_urls=set(post.image_urls or [])|{post.video_url}
    for image in images:
        if image not in (post.image_urls or []):validate_public_media(db,image,current_user.id,'image')
    if payload.video_url!=post.video_url:validate_public_media(db,payload.video_url,current_user.id,'video')
    if (post.content,post.video_url,post.image_urls)!=(content,payload.video_url,images):post.updated_at=datetime.utcnow()
    post.content = content
    post.video_url = payload.video_url
    post.image_urls = images
    paths=retire_public_media(db,current_user.id,old_urls-set(images)-{payload.video_url})
    db.commit()
    if paths:cleanup_files(db,paths)
    db.refresh(post)
    return to_response(db, post, current_user.id)


@router.post("/{post_id}/like", response_model=LikeResponse)
def like_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_user_dependency),
) -> LikeResponse:
    ensure_tables(db)
    post = get_post_or_404(db, post_id, current_user.id, lock=True)
    exists = db.query(PostLike.id).filter_by(post_id=post.id,user_id=current_user.id).with_for_update().first() is not None
    if not exists:
        db.add(PostLike(post_id=post.id, user_id=current_user.id))
        post.likes_count = max(post.likes_count, 0) + 1
        db.commit()
        db.refresh(post)
    return LikeResponse(post_id=post.id, liked=True, likes_count=max(post.likes_count, 0))


@router.delete("/{post_id}/like", response_model=LikeResponse)
def unlike_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_user_dependency),
) -> LikeResponse:
    ensure_tables(db)
    post = get_post_or_404(db, post_id, current_user.id, lock=True)
    like = db.query(PostLike).filter(PostLike.post_id == post.id, PostLike.user_id == current_user.id).with_for_update().populate_existing().first()
    if like:
        db.delete(like)
        post.likes_count = max(post.likes_count - 1, 0)
        db.commit()
        db.refresh(post)
    elif post.likes_count < 0:
        post.likes_count = 0
        db.commit()
        db.refresh(post)
    return LikeResponse(post_id=post.id, liked=False, likes_count=max(post.likes_count, 0))


@router.delete("/{post_id}")
def delete_post(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    post = get_post_or_404(db, post_id, current_user.id, lock=True)
    if post.user_id != current_user.id: raise HTTPException(403, "只能删除自己的动态")
    old_urls=set(post.image_urls or [])|{post.video_url}
    db.query(Notification).filter_by(target_type='comment',context_id=post_id).delete(synchronize_session=False)
    db.query(PostLike).filter(PostLike.post_id == post_id).delete()
    # Keep only empty tombstones so retries cannot recreate deleted content.
    db.query(PostComment).filter(PostComment.post_id == post_id).update({'content':'','deleted_at':datetime.utcnow()},synchronize_session=False)
    post.removed_at=datetime.utcnow();post.content='';post.image_urls=[];post.video_url='';post.likes_count=0
    paths=retire_public_media(db,current_user.id,old_urls)
    db.commit()
    if paths:cleanup_files(db,paths)
    return {"message": "已删除"}


@router.delete("/{post_id}/comments/{comment_id}")
def delete_comment(post_id: int, comment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db.query(Post).filter_by(id=post_id).with_for_update().populate_existing().first()
    comment = db.query(PostComment).filter(PostComment.id == comment_id, PostComment.post_id == post_id).with_for_update().populate_existing().first()
    if not comment or comment.deleted_at: raise HTTPException(404, "留言不存在")
    if comment.user_id != current_user.id: raise HTTPException(403, "只能删除自己的留言")
    comment.content='';comment.deleted_at=datetime.utcnow()
    db.query(Notification).filter_by(target_type='comment',target_id=comment_id).delete(synchronize_session=False)
    db.commit()
    return {"message": "已删除"}
