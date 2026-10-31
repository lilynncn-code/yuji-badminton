"""Remove account data together; retry file cleanup after committing the data change."""
from pathlib import PurePosixPath
from sqlalchemy import or_, func
from app.models.account import PhoneChange, AccountFileDeletion
from app.models.chat import Chat, ChatMessage, ChatChange, ChatState, ChatSend, ChatInboxRevision
from app.models.clinic import ClinicQuestion, ClinicAnswer, ClinicSend
from app.models.game import Game, GameMember
from app.models.media import Media, TrainingVideoUpload
from app.models.post import Post, PostComment, PostLike
from app.models.sms import SmsChallenge
from app.models.social import Follow, Block, Report, Favorite, PeopleRevision
from app.models.training import TrainingProgress, TrainingRecord
from app.models.notification import Notification
from app.services import files
from app.services.chat_inbox import changed_inboxes
from app.services.file_cleanup import cleanup_files
from app.services.people_pages import changed_people


def file_path(media):
    if media.storage_name and PurePosixPath(media.storage_name).name == media.storage_name:
        return 'private/' + media.storage_name
    path = PurePosixPath(media.url)
    if len(path.parts) == 4 and path.parts[:3] in (('/', 'uploads', 'images'), ('/', 'uploads', 'videos')) and path.name not in ('.', '..'):
        return '/'.join(path.parts[2:])
    return None


def cleanup_account_files(db, limit=1000):
    return cleanup_files(db, limit=limit)


def delete_account_data(user, db):
    uid = user.id
    peers = {other for model in (Follow, Block) for row in db.query(model).filter(or_(model.user_id == uid, model.target_id == uid)) for other in (row.user_id, row.target_id) if other != uid}
    changed_people(db, peers)
    chats = db.query(Chat).filter(or_(Chat.requester_id == uid, Chat.receiver_id == uid)).all()
    chat_ids = [c.id for c in chats]
    changed_inboxes(db,[other for c in chats for other in (c.requester_id,c.receiver_id) if other!=uid])
    post_ids = [p.id for p in db.query(Post.id).filter_by(user_id=uid)]
    comment_ids = [c.id for c in db.query(PostComment.id).filter(or_(PostComment.user_id==uid,PostComment.post_id.in_(post_ids)))]
    affected_like_posts = [p.post_id for p in db.query(PostLike.post_id).filter(PostLike.user_id==uid,PostLike.post_id.notin_(post_ids))]
    question_ids = [q.id for q in db.query(ClinicQuestion.id).filter_by(user_id=uid)]
    answer_ids = [a.id for a in db.query(ClinicAnswer.id).filter(or_(ClinicAnswer.user_id==uid,ClinicAnswer.question_id.in_(question_ids)))]
    game_ids = [g.id for g in db.query(Game.id).filter_by(host_id=uid)]
    phones = {user.phone}

    media_rows = {m.id:m for m in db.query(Media).filter_by(user_id=uid)}
    # Also remove uploaded-but-unsent pictures from the removed conversations.
    for chat_id in chat_ids:
        for media in db.query(Media).filter(Media.purpose=='chat', Media.url.like(f'/chat/chats/{chat_id}/images/%')):
            media_rows[media.id]=media
    paths = {p for m in media_rows.values() if (p := file_path(m))}
    for voice in db.query(ChatMessage.content).filter(ChatMessage.chat_id.in_(chat_ids), ChatMessage.message_type=='voice'):
        if voice.content and PurePosixPath(voice.content).name == voice.content:
            paths.add('private/' + voice.content)
    for path in paths:
        if not db.get(AccountFileDeletion, path): db.add(AccountFileDeletion(path=path))
    for media in media_rows.values(): db.delete(media)
    db.flush()

    def remove(model, condition):
        db.query(model).filter(condition).delete(synchronize_session=False)
    remove(Notification,or_(Notification.user_id==uid,Notification.actor_id==uid,
        (Notification.target_type=='chat') & Notification.target_id.in_(chat_ids),
        (Notification.target_type=='game') & Notification.target_id.in_(game_ids),
        (Notification.target_type=='comment') & Notification.context_id.in_(post_ids),
        (Notification.target_type=='answer') & Notification.context_id.in_(question_ids)))
    remove(ChatChange, ChatChange.chat_id.in_(chat_ids))
    remove(ChatState, ChatState.chat_id.in_(chat_ids))
    remove(ChatSend, ChatSend.chat_id.in_(chat_ids))
    remove(ChatMessage, ChatMessage.chat_id.in_(chat_ids))
    remove(Chat, Chat.id.in_(chat_ids))
    remove(ChatInboxRevision, ChatInboxRevision.user_id==uid)
    remove(TrainingRecord, TrainingRecord.user_id==uid)
    remove(TrainingVideoUpload, TrainingVideoUpload.user_id==uid)
    remove(TrainingProgress, TrainingProgress.user_id==uid)
    remove(PostLike, or_(PostLike.user_id==uid, PostLike.post_id.in_(post_ids)))
    remove(PostComment, or_(PostComment.user_id==uid, PostComment.post_id.in_(post_ids)))
    remove(Post, Post.id.in_(post_ids))
    # Remaining authors keep accurate like counts after this account's likes disappear.
    for post in db.query(Post).filter(Post.id.in_(affected_like_posts)):
        post.likes_count = db.query(func.count(PostLike.id)).filter_by(post_id=post.id).scalar() or 0
    db.query(ClinicQuestion).filter(ClinicQuestion.accepted_answer_id.in_(answer_ids)).update({'accepted_answer_id':0},synchronize_session=False)
    remove(ClinicSend,or_(ClinicSend.user_id==uid,ClinicSend.question_id.in_(question_ids)))
    remove(ClinicAnswer, or_(ClinicAnswer.user_id==uid, ClinicAnswer.question_id.in_(question_ids)))
    remove(ClinicQuestion, ClinicQuestion.id.in_(question_ids))
    remove(GameMember, or_(GameMember.user_id==uid, GameMember.game_id.in_(game_ids)))
    remove(Game, Game.id.in_(game_ids))
    remove(PeopleRevision, PeopleRevision.user_id==uid)
    remove(Follow, or_(Follow.user_id==uid, Follow.target_id==uid))
    remove(Block, or_(Block.user_id==uid, Block.target_id==uid))
    remove(Favorite, Favorite.user_id==uid)
    remove(Favorite, (Favorite.kind=='clinic') & Favorite.item_key.in_([str(i) for i in question_ids]))
    # Reports about deleted content retain their status but no deleted text or identity.
    for kind, ids in (('user',[uid]),('post',post_ids),('comment',comment_ids),('question',question_ids),('answer',answer_ids)):
        db.query(Report).filter(Report.target_type==kind,Report.target_id.in_(ids)).update({'snapshot':'内容已随账号注销删除'},synchronize_session=False)
    remove(Report, Report.user_id==uid)
    db.query(Report).filter(Report.handled_by==uid).update({'handled_by':None},synchronize_session=False)
    db.query(Report).filter(Report.target_user_id==uid).update({'target_user_id':None},synchronize_session=False)
    remove(PhoneChange, PhoneChange.user_id==uid)
    remove(SmsChallenge, SmsChallenge.phone.in_(phones))
    db.delete(user)
    db.commit()
    return paths
