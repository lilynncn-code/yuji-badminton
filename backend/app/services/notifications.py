from sqlalchemy import and_, or_, exists
from app.models.notification import Notification
from app.models.user import User
from app.models.post import Post, PostComment
from app.models.chat import Chat
from app.models.game import Game
from app.models.clinic import ClinicQuestion, ClinicAnswer
from app.services.social import blocked_ids


def notify(db, user_id, actor_id, kind, target_type, target_id, context_id=0, event_key=None):
    if user_id==actor_id:return
    if kind!='game_cancelled' and actor_id in blocked_ids(db,user_id):return
    if event_key and db.query(Notification.id).filter_by(user_id=user_id,event_key=event_key).first():return
    db.add(Notification(user_id=user_id,actor_id=actor_id,kind=kind,target_type=target_type,target_id=target_id,context_id=context_id,event_key=event_key))


def visible_notifications(db,user_id):
    hidden=blocked_ids(db,user_id)
    comment_exists=exists().where(PostComment.id==Notification.target_id,PostComment.post_id==Notification.context_id,PostComment.deleted_at.is_(None))
    post_exists=exists().where(Post.id==Notification.context_id,Post.removed_at.is_(None),Post.user_id.notin_(hidden))
    chat_exists=exists().where(Chat.id==Notification.target_id,or_(Chat.requester_id==user_id,Chat.receiver_id==user_id))
    game_exists=exists().where(Game.id==Notification.target_id)
    answer_exists=exists().where(ClinicAnswer.id==Notification.target_id,ClinicAnswer.question_id==Notification.context_id)
    question_exists=exists().where(ClinicQuestion.id==Notification.context_id,ClinicQuestion.user_id.notin_(hidden))
    return db.query(Notification).filter(Notification.user_id==user_id,
        or_(Notification.actor_id.notin_(hidden),Notification.kind=='game_cancelled'),
        or_(and_(Notification.target_type=='comment',comment_exists,post_exists),
            and_(Notification.target_type=='chat',chat_exists),and_(Notification.target_type=='game',game_exists),
            and_(Notification.target_type=='answer',answer_exists,question_exists)))


def notification_data(row,db):
    actor=db.get(User,row.actor_id)
    name=actor.name if actor else '球友'
    title={'post_comment':'在你的动态下留言','comment_reply':'回复了你的留言','chat_request':'申请与你聊天',
        'chat_accepted':'同意了你的聊天申请','chat_rejected':'暂未同意你的聊天申请',
        'game_joined':'报名了你的球局','game_left':'退出了你的球局','game_cancelled':'取消了你参加的球局',
        'clinic_answer':'回答了你的问题'}.get(row.kind,'有了新动态')
    excerpt='';url=''
    if row.target_type=='comment':
        target=db.get(PostComment,row.target_id)
        excerpt=target.content[:160] if target else ''
        url=f'/pages/community/post-detail?id={row.context_id}&comment={row.target_id}'
    elif row.target_type=='chat':
        chat=db.get(Chat,row.target_id)
        url=f'/pages/chat/thread?id={row.target_id}' if chat and chat.status=='accepted' else '/pages/chat/inbox'
        excerpt=chat.note if chat and row.kind=='chat_request' else ''
    elif row.target_type=='game':
        game=db.get(Game,row.target_id)
        excerpt=game.title if game else ''
        url=f'/pages/match-making/games?id={row.target_id}'
    elif row.target_type=='answer':
        answer=db.get(ClinicAnswer,row.target_id)
        excerpt=answer.content[:160] if answer else ''
        url=f'/pages/video-feed/clinic-detail?id={row.context_id}&answer={row.target_id}'
    return {'id':row.id,'kind':row.kind,'actor_name':name,'actor_name_is_default':actor is None,'title':name+title,'excerpt':excerpt,'url':url,
        'created_at':row.created_at,'read_at':row.read_at}
