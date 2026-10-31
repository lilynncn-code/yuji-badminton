import os, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path.cwd()/'backend'))
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.user import User
from app.models.chat import Chat, ChatMessage
from app.models.training import TrainingRecord, TrainingProgress
from app.models.post import Post,PostComment
from app.models.social import Follow,Block,Report
from app.models.clinic import ClinicQuestion,ClinicAnswer
from app.models.notification import Notification
from app.models.game import Game,GameMember
from app.services.security import hash_password
from app.services import files
from app.api.routes import chat
from starlette.routing import Mount
from fastapi.staticfiles import StaticFiles
folder = tempfile.TemporaryDirectory(prefix='haoyu-preview-')
files.UPLOADS=Path(folder.name)
chat.UPLOADS=files.UPLOADS
(files.UPLOADS/'images').mkdir()
(files.UPLOADS/'videos').mkdir()
for route in app.routes:
    if isinstance(route, Mount) and route.path == '/uploads/images':
        route.app=StaticFiles(directory=files.UPLOADS/'images')
    if isinstance(route, Mount) and route.path == '/uploads/videos':
        route.app=StaticFiles(directory=files.UPLOADS/'videos')
engine=create_engine('sqlite:///' + str(Path(folder.name)/'preview.sqlite'), connect_args={'check_same_thread':False, 'timeout':15})
Base.metadata.create_all(engine)
Session=sessionmaker(bind=engine)
with Session() as db:
    for i in range(1,5 if os.environ.get('HAOYU_PREVIEW_DAILY')=='1' else 4):db.add(User(id=i, username='preview'+str(i), name='检查账号'+str(i), phone='1380000000'+str(i), password_hash=hash_password('Check1234'), city='上海', club='周末练习',can_review_reports=int(i==3)))
    db.add(Chat(id=1,requester_id=1,receiver_id=2,status='accepted'))
    db.add(ChatMessage(chat_id=1,sender_id=2,message_type='text',content='这是一条隔离检查消息'))
    db.add(TrainingRecord(user_id=1,training_type='步伐练习',duration_seconds=60,score=30,reps=3,advice='隔离检查记录',recording_method='manual'))
    if os.environ.get('HAOYU_PREVIEW_PEOPLE')=='1':
        from datetime import datetime
        password=db.get(User,2).password_hash
        db.add_all([User(id=i,username=f'people{i}',name=f'临时名单球友{i:03}',phone=f'137{i:08}',password_hash=password,city='上海',bio='用于检查完整名单和资料返回') for i in range(4,109)])
        db.flush()
        for i in range(4,109):
            if i<39:row=Follow(user_id=1,target_id=i,created_at=datetime(2026,10,1,12))
            elif i<74:row=Follow(user_id=i,target_id=1,created_at=datetime(2026,10,1,12))
            else:row=Block(user_id=1,target_id=i,created_at=datetime(2026,10,1,12))
            db.add(row)
    if os.environ.get('HAOYU_PREVIEW_DISCOVERY')=='1':
        password=db.get(User,2).password_hash
        db.add_all([User(id=i,username=f'discovery{i}',name=f'临时发现球友{i:02}',phone=f'137{i:08}',password_hash=password,city='上海',club='训练双打') for i in range(4,37)])
    if os.environ.get('HAOYU_PREVIEW_TRAINING')=='1':
        for i in range(34):db.add(TrainingRecord(user_id=1,training_type=f'临时训练{i+2:02}',duration_seconds=30,score=0,reps=3,advice='用于检查更早记录',recording_method='manual'))
    db.add(Post(user_id=1, content='检查动态\n这是临时检查内容。'))
    if os.environ.get('HAOYU_PREVIEW_COMMENTS')=='1':
        db.flush()
        post=db.query(Post).first()
        comments=[PostComment(post_id=post.id,user_id=2,content=f'第{i+1:02}条临时留言，用于检查较早内容、回复和草稿。') for i in range(38)]
        db.add_all(comments);db.flush()
        db.add(Notification(user_id=1,actor_id=2,kind='post_comment',target_type='comment',target_id=comments[4].id,context_id=post.id))
    if os.environ.get('HAOYU_PREVIEW_FEED')=='1':
        for i in range(34):db.add(Post(user_id=2,content=f'临时列表动态{i+1:02}\n用于检查完整翻看，非真实发布内容。'))
        for i in range(35):db.add(ClinicQuestion(user_id=2,title=f'临时列表问题{i+1:02}',content='用于检查问题列表和继续读取，不是真实提问。'))
    if os.environ.get('HAOYU_PREVIEW_GAMES')=='1':
        from datetime import datetime,timedelta
        for i in range(35):
            game=Game(host_id=2,title=f'临时检查球局{i+1:02}',city='上海',venue='临时检查球馆，未实际订场',starts_at=datetime.utcnow()+timedelta(days=2),duration_minutes=60,capacity=4,cost_note='检查内容，不付款',note='生成的临时检查记录')
            db.add(game);db.flush();db.add(GameMember(game_id=game.id,user_id=2))
            if i in (0,20,34):db.add(GameMember(game_id=game.id,user_id=1))
        for status in ('cancelled','open'):
            game=Game(host_id=2,title='临时已取消球局' if status=='cancelled' else '临时已开始球局',city='上海',venue='临时检查场地',starts_at=datetime.utcnow()+timedelta(days=2 if status=='cancelled' else -2),duration_minutes=60,capacity=4,status=status)
            db.add(game);db.flush();db.add_all([GameMember(game_id=game.id,user_id=i) for i in (1,2)])
    if os.environ.get('HAOYU_PREVIEW_INBOX')=='1':
        from datetime import datetime
        password=db.get(User,2).password_hash
        db.add_all([User(id=i,username=f'inbox{i}',name=f'临时列表球友{i:02}',phone=f'137{i:08}',password_hash=password,city='上海') for i in range(4,41)])
        db.flush()
        for i in range(4,41):
            accepted=i<38
            row=Chat(requester_id=i if i in (38,39) else 1,receiver_id=1 if i in (38,39) else i,
                status='accepted' if accepted else 'pending',note='临时列表检查申请',updated_at=datetime(2026,10,1,12))
            db.add(row);db.flush()
            if accepted:db.add(ChatMessage(chat_id=row.id,sender_id=i,message_type='text',content=f'第{i:02}位球友的临时检查消息'))
    if os.environ.get('HAOYU_PREVIEW_CLINIC')=='1' or os.environ.get('HAOYU_PREVIEW_ALERTS')=='1':
        question=ClinicQuestion(user_id=1,title='长回答页面检查',content='这是一条临时检查问题，回答文字均为生成的检查内容。')
        db.add(question);db.flush()
        answers=[ClinicAnswer(question_id=question.id,user_id=2,content=f'第{i+1}条临时检查回答，用于检查分批读取与提醒定位。') for i in range(38)]
        db.add_all(answers);db.flush()
        question.accepted_answer_id=answers[0].id
        db.add(Notification(user_id=1,actor_id=2,kind='clinic_answer',target_type='answer',target_id=answers[4].id,context_id=question.id))
        if os.environ.get('HAOYU_PREVIEW_ALERTS')=='1':
            for answer in [a for a in answers if a.id!=answers[4].id][:34]:
                db.add(Notification(user_id=1,actor_id=2,kind='clinic_answer',target_type='answer',target_id=answer.id,context_id=question.id))
            for i in range(35):
                post=Post(user_id=2,content=f'第{i+1:02}条临时举报检查内容，不是真实球友发布。')
                db.add(post);db.flush()
                db.add(Report(user_id=1,target_type='post',target_id=post.id,target_user_id=2,reason=f'第{i+1:02}条临时检查原因',snapshot=post.content))
    db.commit()
def test_db():
    with Session() as db:yield db
app.dependency_overrides[get_db]=test_db
app.router.on_startup.clear()
if os.environ.get('HAOYU_PREVIEW_PROFILE')=='1':
    from fastapi.responses import JSONResponse
    summary_failures=2
    first_profile_save=True
    print('Temporary preview folder: '+folder.name,flush=True)
    @app.middleware('http')
    async def profile_failure_preview(request,call_next):
        global summary_failures,first_profile_save
        fail=False
        if request.method=='GET' and request.url.path=='/training/summary' and summary_failures:
            summary_failures-=1;fail=True
        if request.method=='PATCH' and request.url.path=='/profile/me' and first_profile_save:
            first_profile_save=False;fail=True
        if fail:return JSONResponse({'detail':'临时检查：连接未成功，请重试，原内容仍保留'},status_code=503,headers={'Access-Control-Allow-Origin':'*'})
        return await call_next(request)
if os.environ.get('HAOYU_PREVIEW_TRAINING')=='1':
    from fastapi.responses import JSONResponse
    first_attach=True
    @app.middleware('http')
    async def training_retry_preview(request,call_next):
        global first_attach
        if first_attach and request.method=='PATCH' and request.url.path.startswith('/training/') and request.url.path.endswith('/media'):
            first_attach=False
            return JSONResponse({'detail':'临时检查：视频已上传，记录暂未关联，请继续保存'},status_code=503,headers={'Access-Control-Allow-Origin':'*'})
        return await call_next(request)

if os.environ.get('HAOYU_PREVIEW_COURTS')=='1':
    from app.api.routes import integrations
    court_queries=set()
    def preview_courts(payload):
        city=getattr(payload,'city','附近')
        key=(city,payload.keyword,payload.page)
        if key not in court_queries:
            court_queries.add(key)
            return {'source':'local','message':f'临时检查：{city}第{payload.page}批连接失败，重试会返回生成的球馆。','items':[]}
        return {'source':'amap','message':'临时检查结果，不是真实球馆或订场信息。','items':[
            {'id':f'{city}-{payload.page}-{i}','name':f'{city}临时检查球馆{(payload.page-1)*2+i}',
             'address':f'{city}检查用地址，不提供真实场地','hours':'生成的检查内容，请勿订场','features':['临时生成'],
             'location':'','tel':'','distance':''} for i in (1,2)],'has_more':payload.page<2}
    integrations.search_city_courts=preview_courts
    integrations.search_courts=preview_courts
if os.environ.get('HAOYU_PREVIEW_LEARNING')=='1':
    from fastapi.responses import JSONResponse
    learning_failures={'/training/progress':1,'/training/summary':1}
    @app.middleware('http')
    async def learning_failure_preview(request,call_next):
        key=request.url.path
        if request.method=='GET' and learning_failures.get(key,0):
            learning_failures[key]-=1
            return JSONResponse({'detail':'临时检查：未读到本人数据，请重试'},status_code=503,headers={'Access-Control-Allow-Origin':'*'})
        return await call_next(request)

if os.environ.get('HAOYU_PREVIEW_AUTH')=='1':
    from fastapi.responses import JSONResponse
    first_login=True
    print('Temporary preview folder: '+folder.name,flush=True)
    @app.middleware('http')
    async def auth_failure_preview(request,call_next):
        global first_login
        if first_login and request.method=='POST' and request.url.path=='/auth/login':
            first_login=False
            return JSONResponse({'detail':'临时检查：本次登录未完成，请重试，输入仍保留'},status_code=503,headers={'Access-Control-Allow-Origin':'*'})
        return await call_next(request)

if os.environ.get('HAOYU_PREVIEW_ALERTS')=='1':
    from fastapi.responses import JSONResponse
    alert_failures={'/notifications':1,'/social/reports':1,'/social/review/reports':1}
    print('Temporary preview folder: '+folder.name,flush=True)
    @app.middleware('http')
    async def alerts_failure_preview(request,call_next):
        key=request.url.path
        if request.method=='GET' and alert_failures.get(key,0):
            alert_failures[key]-=1
            return JSONResponse({'detail':'临时检查：本次记录未读到，请重试'},status_code=503,headers={'Access-Control-Allow-Origin':'*'})
        return await call_next(request)

if os.environ.get('HAOYU_PREVIEW_DAILY')=='1':
    from fastapi.responses import JSONResponse
    daily_read_failure=True
    daily_saved_failure=True
    print('Temporary preview folder: '+folder.name,flush=True)
    @app.middleware('http')
    async def daily_failure_preview(request,call_next):
        global daily_read_failure,daily_saved_failure
        if request.method=='GET' and request.url.path=='/training/daily' and daily_read_failure:
            daily_read_failure=False
            return JSONResponse({'detail':'临时检查：本次安排未读到，请重新读取'},status_code=503,headers={'Access-Control-Allow-Origin':'*'})
        response=await call_next(request)
        if request.method=='POST' and request.url.path.startswith('/training/daily/') and response.status_code<300 and daily_saved_failure:
            daily_saved_failure=False;daily_read_failure=True
        return response

if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=int(os.environ.get('HAOYU_PREVIEW_PORT','18000')),log_level=os.environ.get('HAOYU_PREVIEW_LOG_LEVEL','warning'))
