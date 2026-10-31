"""Use an isolated database and temporary files; never message real accounts.
Run: backend/.venv/bin/python -m unittest discover -s backend/tests -v
"""
import io
import sys
import tempfile
import unittest
import wave
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.user import User
from app.models.chat import Chat
from app.models.training import TrainingProgress, TrainingRecord
from app.services.security import create_token, hash_password
from app.services import files


class AppFlows(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        with self.Session() as db:
            for i in range(1, 4):
                db.add(User(id=i, username=f'check{i}', name=f'球友{i}', phone=f'1390000000{i}',
                            password_hash=hash_password('Test1234'), city='上海'))
            db.commit()
        def override_db():
            with self.Session() as db:
                yield db
        app.dependency_overrides[get_db] = override_db
        self.client = TestClient(app)
        self.headers = {i: {'Authorization': 'Bearer ' + create_token(i)} for i in range(1, 4)}
        self.folder = tempfile.TemporaryDirectory()
        self.files_patch = patch.object(files, 'UPLOADS', Path(self.folder.name))
        self.files_patch.start()
        from app.api.routes import chat
        self.chat_patch = patch.object(chat, 'UPLOADS', Path(self.folder.name))
        self.chat_patch.start()

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        self.chat_patch.stop()
        self.files_patch.stop()
        self.folder.cleanup()
        self.engine.dispose()

    def api(self, method, path, who=1, status=200, **args):
        result = self.client.request(method, path, headers=self.headers.get(who, {}), **args)
        self.assertEqual(result.status_code, status, f'{method} {path}: {result.text[:400]}')
        return result.json() if result.content else None

    def accepted_chat(self):
        result = self.api('POST', '/chat/requests', json={'receiver_id': 2, 'note': '周末约练'})
        chat_id = result['chat']['id']
        self.api('POST', f'/chat/requests/{chat_id}/accept', 2)
        return chat_id

    def test_profile_upload_and_discovery_use_real_users(self):
        self.api('GET', '/profile/me', 0, 401)
        # A genuine 1x1 transparent PNG.
        import base64
        data = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')
        upload = self.api('POST', '/media/upload', files={'file': ('avatar.png', data, 'image/png')})
        self.assertTrue(upload['url'].startswith('/uploads/images/'))
        self.assertEqual(len(list(Path(self.folder.name).rglob('*.png'))), 1)
        self.api('PATCH', '/profile/me', json={'avatar': upload['url'], 'cover': upload['url'], 'club': '周末俱乐部', 'hand': '左手持拍', 'nickname': '新昵称'})
        profile = self.api('GET', '/profile/me')
        self.assertEqual((profile['club'], profile['hand'], profile['cover']), ('周末俱乐部', '左手持拍', upload['url']))
        self.api('PATCH', '/profile/me', status=400, json={'avatar': 'blob:temporary'})
        self.api('POST', '/media/upload', status=400, files={'file': ('fake.jpg', b'<script>bad</script>', 'image/jpeg')})
        players = self.api('GET', '/discovery/players')
        self.assertEqual({p['id'] for p in players['items']}, {2, 3})
        self.assertEqual(self.api('GET', '/discovery/players/1', 2)['name'], '新昵称')

    def test_chat_identity_atomic_send_unread_and_sorting(self):
        request = self.api('POST', '/chat/requests', json={'receiver_id': 2, 'note': '周末约练'})['chat']
        chat_id = request['id']
        self.assertEqual(request['other_name'], '球友2')
        self.api('POST', f'/chat/chats/{chat_id}/messages', status=400, json={'content': '未同意不能发'})
        self.api('POST', f'/chat/requests/{chat_id}/accept', 3, 404)
        self.api('POST', f'/chat/requests/{chat_id}/accept', 2)
        with self.Session() as db:
            db.get(Chat, chat_id).updated_at = datetime.utcnow() - timedelta(days=1)
            db.commit()
        sent = self.api('POST', f'/chat/chats/{chat_id}/messages', json={'content': '你好', 'image_url': 'https://example.com/photo.jpg'})
        self.assertEqual(len(sent['messages']), 2)
        inbox = self.api('GET', '/chat/chats', 2)['chats'][0]
        self.assertEqual((inbox['unread_count'], inbox['note']), (2, '周末约练'))
        with self.Session() as db:
            self.assertGreater(db.get(Chat, chat_id).updated_at, datetime.utcnow() - timedelta(seconds=10))
        self.api('POST', f'/chat/chats/{chat_id}/messages', status=400, json={'content': '不得部分发出', 'image_url': 'blob:invalid'})
        self.assertEqual(len(self.api('GET', f'/chat/chats/{chat_id}/messages', 2)['messages']), 2)
        self.api('POST', f'/chat/chats/{chat_id}/read', 2, json={'last_message_id': sent['messages'][-1]['id']})
        self.assertEqual(self.api('GET', '/chat/chats', 2)['chats'][0]['unread_count'], 0)

    def test_player_pages_search_all_users_and_show_request_states(self):
        with self.Session() as db:
            for i in range(4, 209):
                db.add(User(id=i, username=f'pages{i}', name=f'列表球友{i}', phone=f'1390000{i:04}', password_hash='unused', city='杭州', club='训练双打'))
            db.commit()
        seen = []
        cursor=''
        while True:
            data=self.api('GET','/discovery/players?page_size=30'+('&cursor='+cursor if cursor else ''))
            seen.extend(p['id'] for p in data['items'])
            if not data['has_more']:break
            cursor=data['next_cursor']
        self.assertEqual(len(seen), 207)
        self.assertEqual(len(set(seen)), 207)
        self.assertFalse(data['has_more'])
        found = self.api('GET', '/discovery/players?keyword=列表球友4')
        self.assertIn(4, [p['id'] for p in found['items']])
        self.assertEqual(self.api('GET', '/discovery/players?keyword=%')['total'], 0)
        self.assertEqual(self.api('GET', '/discovery/players?mode=training')['total'], 205)
        self.api('POST', '/chat/requests', json={'receiver_id':2})
        own = self.api('GET', '/discovery/players?keyword=球友2&city=上海')['items'][0]
        incoming = self.api('GET', '/discovery/players?keyword=球友1&city=上海', 2)['items'][0]
        self.assertEqual((own['chat_state'], incoming['chat_state']), ('waiting', 'review'))
        self.api('POST', f"/chat/requests/{own['chat_id']}/accept", 2)
        self.assertEqual(self.api('GET', '/discovery/players?keyword=球友2&city=上海')['items'][0]['chat_state'], 'accepted')

    def test_chat_history_pages_do_not_mark_unseen_messages_read(self):
        chat_id = self.accepted_chat()
        for index in range(7):
            self.api('POST', f'/chat/chats/{chat_id}/messages', json={'content': f'消息{index}'})
        path = f'/chat/chats/{chat_id}/messages'
        recent = self.api('GET', path + '?limit=3', 2)
        self.assertTrue(recent['has_more'])
        self.assertEqual([m['content'] for m in recent['messages']], ['消息4', '消息5', '消息6'])
        before = recent['messages'][0]['id']
        earlier = self.api('GET', path + f'?limit=3&before_id={before}', 2)
        self.assertEqual([m['content'] for m in earlier['messages']], ['消息1', '消息2', '消息3'])
        self.api('POST', f'/chat/chats/{chat_id}/read', 2, json={'last_message_id': before})
        self.assertEqual(self.api('GET', '/chat/chats', 2)['chats'][0]['unread_count'], 2)
        latest = recent['messages'][-1]['id']
        self.api('POST', f'/chat/chats/{chat_id}/messages', json={'content': '尚未看到的新消息'})
        self.api('POST', f'/chat/chats/{chat_id}/read', 2, json={'last_message_id': latest})
        self.assertEqual(self.api('GET', '/chat/chats', 2)['chats'][0]['unread_count'], 1)
        delta = self.api('GET', path + f'?after_id={latest}', 2)
        self.assertEqual([m['content'] for m in delta['messages']], ['尚未看到的新消息'])
        self.api('POST', f'/chat/chats/{chat_id}/read', 2, 400, json={'last_message_id': 99999})

    def test_chat_retry_saves_once_and_never_restores_recalled_content(self):
        import base64
        chat_id=self.accepted_chat();path=f'/chat/chats/{chat_id}'
        picture=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')
        image=self.api('POST',path+'/images',files={'file':('chat.png',picture,'image/png')})['url']
        payload={'content':'网络恢复后重试','image_url':image,'request_key':'send-retry-check'}
        first=self.api('POST',path+'/messages',json=payload)['messages']
        again=self.api('POST',path+'/messages',json=payload)['messages']
        self.assertEqual([m['id'] for m in first],[m['id'] for m in again])
        self.assertEqual(self.api('GET','/chat/chats',2)['chats'][0]['unread_count'],2)
        self.api('POST',path+'/messages',status=409,json={**payload,'content':'不得用原编号改内容'})
        self.api('POST',path+f"/messages/{first[0]['id']}/recall")
        recalled=self.api('POST',path+'/messages',json=payload)['messages']
        self.assertTrue(recalled[0]['recalled_at'])
        self.assertEqual(recalled[0]['content'],'')
        self.api('GET',image,2,404)
        self.assertEqual(len(self.api('GET',path+'/messages',2)['messages']),2)
        # The other account and other conversations can use their own same key.
        self.api('POST',path+'/messages',2,json={'content':'另一方的发送','request_key':payload['request_key']})
        self.api('DELETE',path+'/history',2)
        self.api('POST',path+'/messages',json=payload)
        self.assertEqual(self.api('GET',path+'/messages',2)['messages'],[])
        self.assertEqual(self.api('GET','/chat/chats',2)['chats'][0]['unread_count'],0)
        other=self.api('POST','/chat/requests',json={'receiver_id':3})['chat']['id']
        self.api('POST',f'/chat/requests/{other}/accept',3)
        self.api('POST',f'/chat/chats/{other}/messages',json={'content':'另一个会话','request_key':payload['request_key']})
        self.api('POST',path+'/messages',status=422,json={'content':'非法编号','request_key':'bad key!'})

    def test_voice_keeps_sender_and_private_original_recording(self):
        chat_id = self.accepted_chat()
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(16000)
            output.writeframes(b'\0' * 3200)
        recording = buffer.getvalue()
        result = self.api('POST', f'/chat/chats/{chat_id}/messages/voice', files={'audio': ('voice.wav', recording, 'audio/wav')})
        message_id = result['message']['id']
        path = f'/chat/chats/{chat_id}/messages/{message_id}/audio'
        response = self.client.get(path, headers=self.headers[2])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, recording)
        self.api('GET', path, 3, 404)
        messages = self.api('GET', f'/chat/chats/{chat_id}/messages', 2)['messages']
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]['sender_id'], 1)
        self.api('POST', f'/chat/chats/{chat_id}/messages/voice', status=400, files={'audio': ('fake.wav', b'not audio', 'audio/wav')})

    def test_chat_images_are_private_to_the_correct_conversation(self):
        import base64
        data=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')
        chat_id=self.accepted_chat()
        clip=self.api('POST',f'/chat/chats/{chat_id}/images',files={'file':('chat.png',data,'image/png')})
        self.assertFalse((Path(self.folder.name)/'images').exists())
        self.api('GET',clip['url'],0,401)
        self.api('GET',clip['url'],3,404)
        self.api('GET',clip['url'],2,404)
        self.assertEqual(self.client.get(clip['url'],headers=self.headers[1]).content,data)
        self.api('POST',f'/chat/chats/{chat_id}/messages',2,400,json={'content':'不能冒用对方未发送图片','image_url':clip['url']})
        self.api('POST',f'/chat/chats/{chat_id}/messages',json={'content':'私有图片与文字','image_url':clip['url']})
        response=self.client.get(clip['url'],headers=self.headers[2])
        self.assertEqual(response.content,data)
        self.assertIn('no-store',response.headers['cache-control'])
        self.api('POST',f'/chat/chats/{chat_id}/messages',status=400,json={'content':'不要上传公开副本','image_url':'/uploads/images/old.png'})
        self.api('PATCH',f"/media/{clip['id']}",status=400,json={'purpose':'post'})
        self.api('DELETE',f"/media/{clip['id']}",status=400)
        self.api('PUT','/social/users/2/block')
        self.api('GET',clip['url'],2,403)

    def test_cancel_request_only_by_sender_before_acceptance(self):
        chat_id = self.api('POST', '/chat/requests', json={'receiver_id': 2})['chat']['id']
        self.api('DELETE', f'/chat/requests/{chat_id}', 2, 400)
        self.api('DELETE', f'/chat/requests/{chat_id}')
        self.assertEqual(self.api('GET', '/chat/chats')['chats'], [])
        accepted = self.accepted_chat()
        self.api('DELETE', f'/chat/requests/{accepted}', status=400)

    def test_recall_is_owner_only_timed_and_updates_already_open_pages(self):
        chat_id=self.accepted_chat();path=f'/chat/chats/{chat_id}'
        first=self.api('POST',path+'/messages',json={'content':'需要撤回的文字'})['messages'][0]
        opened=self.api('GET',path+'/messages',2)
        self.api('POST',path+f"/messages/{first['id']}/recall",2,403)
        self.api('POST',path+f"/messages/{first['id']}/recall",3,404)
        recalled=self.api('POST',path+f"/messages/{first['id']}/recall")
        self.assertEqual(recalled['content'],'')
        self.assertTrue(recalled['recalled_at'])
        self.assertEqual(self.api('POST',path+f"/messages/{first['id']}/recall")['id'],first['id'])
        delta=self.api('GET',path+f"/messages?after_id={first['id']}&after_change_id={opened['change_cursor']}",2)
        self.assertEqual(delta['messages'],[])
        self.assertEqual(delta['message_updates'][0]['id'],first['id'])
        self.assertEqual(delta['message_updates'][0]['content'],'')
        self.assertGreater(delta['change_cursor'],opened['change_cursor'])
        self.assertEqual(self.api('GET','/chat/chats',2)['chats'][0]['unread_count'],0)
        later=self.api('POST',path+'/messages',json={'content':'超过时限的文字'})['messages'][0]
        from app.models.chat import ChatMessage
        with self.Session() as db:
            db.get(ChatMessage,later['id']).created_at=datetime.utcnow()-timedelta(minutes=3);db.commit()
        self.api('POST',path+f"/messages/{later['id']}/recall",status=400)
        self.api('POST',path+'/read',2,json={'last_message_id':later['id']})
        self.assertEqual(self.api('GET',path+'/messages')['chat']['other_read_id'],later['id'])

    def test_recalled_private_images_and_voice_can_no_longer_be_downloaded(self):
        import base64
        chat_id=self.accepted_chat();path=f'/chat/chats/{chat_id}'
        data=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')
        clip=self.api('POST',path+'/images',files={'file':('chat.png',data,'image/png')})
        sent=[]
        for _ in range(2):sent.append(self.api('POST',path+'/messages',json={'image_url':clip['url']})['messages'][0])
        self.api('POST',path+f"/messages/{sent[0]['id']}/recall")
        self.assertEqual(self.client.get(clip['url'],headers=self.headers[2]).status_code,200)
        self.api('POST',path+f"/messages/{sent[1]['id']}/recall")
        self.api('GET',clip['url'],2,404)
        self.assertEqual(list((Path(self.folder.name)/'private').glob('*.png')),[])
        buffer=io.BytesIO()
        with wave.open(buffer,'wb') as output:
            output.setnchannels(1);output.setsampwidth(2);output.setframerate(16000);output.writeframes(b'\0'*3200)
        voice=self.api('POST',path+'/messages/voice',files={'audio':('voice.wav',buffer.getvalue(),'audio/wav')})['message']
        self.api('POST',path+f"/messages/{voice['id']}/recall")
        self.api('GET',path+f"/messages/{voice['id']}/audio",2,404)
        self.assertEqual(list((Path(self.folder.name)/'private').glob('*.wav')),[])

    def test_clear_and_remove_chat_only_affect_one_user_and_new_message_returns(self):
        chat_id=self.accepted_chat();path=f'/chat/chats/{chat_id}'
        for index in range(3):self.api('POST',path+'/messages',2,json={'content':f'旧消息{index}'})
        self.api('DELETE',path+'/history',3,404)
        self.api('DELETE',path+'/history')
        self.assertEqual(self.api('GET',path+'/messages')['messages'],[])
        self.assertEqual(len(self.api('GET',path+'/messages',2)['messages']),3)
        self.assertEqual(self.api('GET',path+'/messages?after_id=0')['messages'],[])
        own=self.api('GET','/chat/chats')['chats'][0]
        self.assertEqual(own['unread_count'],0);self.assertIsNone(own['last_message'])
        self.api('DELETE',path)
        self.assertEqual(self.api('GET','/chat/chats')['chats'],[])
        self.assertEqual(len(self.api('GET','/chat/chats',2)['chats']),1)
        self.api('POST',path+'/visible')
        self.assertEqual(len(self.api('GET','/chat/chats')['chats']),1)
        self.assertEqual(self.api('GET',path+'/messages')['messages'],[])
        self.api('DELETE',path)
        new=self.api('POST',path+'/messages',2,json={'content':'新消息重新出现'})['messages'][0]
        own=self.api('GET','/chat/chats')['chats'][0]
        self.assertEqual(own['unread_count'],1)
        self.assertEqual([m['id'] for m in self.api('GET',path+'/messages')['messages']],[new['id']])
        self.assertEqual(len(self.api('GET',path+'/messages',2)['messages']),4)

    def test_training_history_pages_are_stable_and_account_private(self):
        with self.Session() as db:
            for i in range(75):
                db.add(TrainingRecord(user_id=1,training_type=f'记录{i}',duration_seconds=60,score=0,reps=1))
            db.add(TrainingRecord(user_id=2,training_type='其他账号',duration_seconds=60,score=0))
            db.commit()
        page=self.api('GET','/training')
        self.assertEqual(len(page['records']),30)
        self.assertTrue(page['has_more'])
        seen=[r['id'] for r in page['records']]
        # A new training record arriving between pages must not shift old pages.
        added=self.api('POST','/training',json={'training_type':'新记录','duration_seconds':60,'score':0})
        while page['has_more']:
            page=self.api('GET',f"/training?before_id={seen[-1]}")
            seen.extend(r['id'] for r in page['records'])
        self.assertEqual(len(seen),75)
        self.assertEqual(len(set(seen)),75)
        self.assertNotIn(added['id'],seen)
        self.assertEqual(self.api('GET','/training',2)['records'][0]['training_type'],'其他账号')
        self.api('GET','/training?limit=101',status=422)
        self.api('GET','/training?before_id=0',status=422)

    def test_training_constraints_progress_and_account_isolation(self):
        self.api('POST', '/training', status=422, json={'training_type': '步伐', 'duration_seconds': 0, 'score': 9999})
        payload = {'training_type': '步伐', 'duration_seconds': 30, 'score': 30, 'reps': 3, 'task_id': 'unit-2-m1-t1'}
        self.api('POST', '/training', status=400, json=payload)
        payload['task_id'] = 'unit-1-m1-t1'
        for _ in range(2):
            self.api('POST', '/training', json=payload)
        self.assertEqual(self.api('GET', '/training/progress'), {'completed': ['unit-1-m1-t1'], 'xp': 20})
        payload['task_id'] = 'unit-1-m1-t2'
        self.api('POST', '/training', json=payload)
        self.assertEqual(self.api('GET', '/training/summary')['sessions'], 3)
        self.assertEqual(self.api('GET', '/training/summary', 2)['sessions'], 0)
        self.assertEqual(self.api('GET', '/training/progress', 2)['completed'], [])
        with self.Session() as db:
            db.get(TrainingProgress, 1).completed = [f'unit-1-m{m}-t{t}' for m in range(1, 101) for t in range(1, 5)]
            db.commit()
        payload['task_id'] = 'unit-2-m1-t1'
        self.api('POST', '/training', json=payload)
        self.assertIn(payload['task_id'], self.api('GET', '/training/progress')['completed'])

    def test_training_days_follow_china_date_and_require_movement(self):
        with self.Session() as db:
            for user_id, reps, when in [(1, 3, datetime(2026, 10, 17, 16, 10)), (1, 2, datetime(2026, 10, 17, 15, 10)), (2, 0, datetime(2026, 10, 17, 16, 10))]:
                db.add(TrainingRecord(user_id=user_id, training_type='步伐', duration_seconds=30, score=0, reps=reps, created_at=when))
            db.commit()
        with patch('app.api.routes.training.datetime') as clock:
            clock.utcnow.return_value = datetime(2026, 10, 17, 16, 30)
            first = self.api('GET', '/training/summary')
            second = self.api('GET', '/training/summary', 2)
        self.assertEqual((first['today_done'], first['last_date'], first['streak']), (True, '2026-10-18', 2))
        self.assertEqual((second['today_done'], second['streak']), (False, 0))

    def test_training_retry_saves_once_and_enforces_task_duration(self):
        payload = {'training_type': '步伐', 'duration_seconds': 30, 'score': 30, 'reps': 3, 'task_id': 'unit-1-m1-t1', 'request_key': 'training-check-0001'}
        saved = self.api('POST', '/training', json=payload)
        self.assertEqual(self.api('POST', '/training', json=payload)['id'], saved['id'])
        self.assertEqual(self.api('GET', '/training/summary')['sessions'], 1)
        self.api('POST', '/training', status=409, json={**payload, 'reps': 4})
        self.api('POST', '/training', status=400, json={**payload, 'task_id': 'unit-1-m1-t2', 'reps': 0, 'request_key': 'training-check-0002'})
        with self.Session() as db:
            db.get(TrainingProgress, 1).completed = [f'unit-1-m1-t{t}' for t in range(1, 5)]
            db.commit()
        self.api('POST', '/training', status=400, json={**payload, 'task_id': 'unit-1-m2-t1', 'request_key': 'training-check-0003'})
        self.api('POST', '/training', json={**payload, 'duration_seconds': 60, 'task_id': 'unit-1-m2-t1', 'request_key': 'training-check-0003'})

    def test_posts_pagination_deletion_and_permissions(self):
        post = self.api('POST', '/posts', json={'content': '标题\n正文', 'image_urls': []})
        post_id = post['id']
        self.api('POST', '/posts', 2, json={'content': '其他人的动态'})
        own = self.api('GET', '/posts?mine=true&page_size=1')
        self.assertEqual((own['total'], own['items'][0]['id']), (1, post_id))
        self.api('DELETE', f'/posts/{post_id}', 2, 403)
        comment = self.api('POST', f'/posts/{post_id}/comments', 2, json={'content': '测试留言'})
        path = f'/posts/{post_id}/comments/{comment["id"]}'
        self.api('DELETE', path, 1, 403)
        self.api('DELETE', path, 2)
        self.api('DELETE', f'/posts/{post_id}')
        self.api('GET', f'/posts/{post_id}', status=404)

    def test_post_retry_only_creates_one_post_per_account(self):
        payload={'content':'重试时不重复发布','request_key':'post-retry-check-0001'}
        first=self.api('POST','/posts',json=payload)
        again=self.api('POST','/posts',json=payload)
        self.assertEqual(first['id'],again['id'])
        self.assertEqual(self.api('GET','/posts?mine=true')['total'],1)
        self.api('POST','/posts',status=409,json={**payload,'content':'不能悄悄覆盖原动态'})
        second=self.api('POST','/posts',2,json=payload)
        self.assertNotEqual(first['id'],second['id'])
        self.assertEqual(self.api('GET','/posts?mine=true',2)['total'],1)

    def test_follow_block_filters_and_report_history(self):
        self.api('PUT', '/social/users/2/follow')
        self.api('PUT', '/social/users/2/follow')
        self.assertEqual(self.api('GET', '/profile/me')['following'], 1)
        self.assertEqual(self.api('GET', '/profile/me', 2)['followers'], 1)
        self.assertEqual(self.api('GET', '/social/people?kind=following')['items'][0]['id'], 2)
        post = self.api('POST', '/posts', 2, json={'content': 'followed hello'})
        self.assertEqual(self.api('GET', '/posts?following=true&keyword=hello')['total'], 1)
        chat_id = self.accepted_chat()
        self.api('PUT', '/social/users/2/block')
        self.assertEqual(self.api('GET', '/profile/me')['following'], 0)
        self.assertEqual(self.api('GET', '/posts')['total'], 0)
        self.assertEqual(self.api('GET', '/discovery/players')['total'], 1)
        self.api('POST', f'/chat/chats/{chat_id}/messages', 2, 403, json={'content': 'blocked'})
        self.api('PUT', '/social/users/1/follow', 2, 403)
        report = self.api('POST', '/social/reports', json={'target_type': 'post', 'target_id': post['id'], 'reason': 'spam test'})
        self.assertEqual(self.api('GET', '/social/reports')['items'][0]['id'], report['id'])
        self.assertEqual(self.api('GET', '/social/reports', 2)['items'], [])
        self.api('DELETE', '/social/users/2/block')
        self.api('POST', f'/chat/chats/{chat_id}/messages', 2, json={'content': 'unblocked'})

    def test_game_capacity_permissions_cancellation_and_repeat_join(self):
        payload = {'title':'test game','city':'Shanghai','venue':'test venue','starts_at':(datetime.utcnow()+timedelta(days=1)).isoformat()+'Z','capacity':2}
        game = self.api('POST', '/games', json=payload)
        self.assertTrue(game['joined'])
        path = f"/games/{game['id']}"
        self.api('PUT', path+'/join', 2)
        self.api('PUT', path+'/join', 2)
        self.assertEqual(self.api('GET', path)['count'], 2)
        self.api('PUT', path+'/join', 3, 409)
        self.api('POST', path+'/cancel', 2, 403)
        self.api('DELETE', path+'/join', 1, 400)
        self.api('DELETE', path+'/join', 2)
        self.api('PUT', path+'/join', 3)
        self.api('POST', path+'/cancel')
        self.assertEqual(self.api('GET', '/games?mine=true', 3)['items'][0]['status'], 'cancelled')
        self.api('PUT', path+'/join', 2, 400)
        self.api('POST', '/games', status=400, json={**payload,'starts_at':datetime.utcnow().isoformat()+'Z'})

    def test_favorites_are_saved_per_account(self):
        self.api('PUT', '/social/favorites/equipment/racket1')
        self.api('PUT', '/social/favorites/equipment/racket1')
        self.assertEqual(self.api('GET', '/social/favorites/equipment')['items'], ['racket1'])
        self.assertEqual(self.api('GET', '/social/favorites/equipment', 2)['items'], [])
        self.api('DELETE', '/social/favorites/equipment/racket1')
        self.assertEqual(self.api('GET', '/social/favorites/equipment')['items'], [])

    def test_changed_password_and_logout_invalidate_old_login(self):
        new = self.api('POST', '/auth/change-password', json={'old_password': 'Test1234', 'new_password': 'New12345', 'confirm_password': 'New12345'})
        self.api('GET', '/profile/me', status=401)
        self.headers[1] = {'Authorization': 'Bearer ' + new['token']}
        self.api('GET', '/profile/me')
        self.api('POST', '/auth/logout')
        self.api('GET', '/profile/me', status=401)

    def test_clinic_questions_answers_selection_and_deletion(self):
        question = self.api('POST', '/clinic', json={'title': '步伐怎么练', 'content': '启动后重心偏高，请球友指点。'})
        path = f"/clinic/{question['id']}"
        self.api('POST', path+'/answers', 2, json={'content': '先降低重心，慢速练习再加快。'})
        detail = self.api('GET', path)
        aid = detail['answers'][0]['id']
        self.assertEqual(detail['answers'][0]['author']['id'], 2)
        self.api('PUT', path+f'/accepted/{aid}', 3, 403)
        self.assertEqual(self.api('PUT', path+f'/accepted/{aid}')['accepted_answer_id'], aid)
        self.api('PUT', f"/social/favorites/clinic/{question['id']}", 3)
        self.assertEqual(self.api('GET', '/clinic?saved=true', 3)['total'], 1)
        self.api('DELETE', path, 2, 403)
        self.api('DELETE', path+f'/answers/{aid}', 2)
        self.assertEqual(self.api('GET', path)['accepted_answer_id'], 0)
        self.api('DELETE', path)
        self.api('GET', path, 3, 404)
        self.assertEqual(self.api('GET', '/clinic?saved=true', 3)['total'], 0)

    def test_video_upload_ownership_and_invalid_files(self):
        data = (Path(__file__).parent / 'fixtures' / 'clip.mp4').read_bytes()
        video = self.api('POST', '/media/upload-video', files={'file': ('clip.mp4', data, 'video/mp4')})
        self.assertTrue(video['url'].startswith('/uploads/videos/'))
        self.api('POST', '/posts', json={'content': '实际视频', 'video_url': video['url']})
        self.api('POST', '/posts', 2, 400, json={'content': '他人的视频', 'video_url': video['url']})
        self.api('POST', '/media', 2, 400, json={'purpose': 'post', 'media_type': 'video', 'url': video['url']})
        self.api('POST', '/media/upload-video', status=400, files={'file': ('fake.mp4', b'not video', 'video/mp4')})

    def test_training_video_is_private_attached_and_deletable(self):
        data = (Path(__file__).parent / 'fixtures' / 'clip.mp4').read_bytes()
        clip = self.api('POST', '/media/upload-training-video', files={'file': ('training.mp4', data, 'video/mp4')})
        self.assertEqual(clip['url'], f"/media/{clip['id']}/file")
        response = self.client.get(clip['url'], headers=self.headers[1])
        self.assertEqual(response.content, data)
        self.assertIn('no-store', response.headers['cache-control'])
        self.api('GET', clip['url'], 2, 404)
        self.api('GET', clip['url'], 0, 401)
        self.assertEqual(len(list((Path(self.folder.name)/'private').glob('*.mp4'))), 1)
        self.assertFalse((Path(self.folder.name)/'videos').exists())
        payload = {'training_type':'步伐', 'duration_seconds':30, 'score':30, 'reps':3}
        record = self.api('POST', '/training', json=payload)
        self.api('PATCH', f"/training/{record['id']}/media", 2, 404, json={'media_id':clip['id']})
        other_record = self.api('POST', '/training', 2, json=payload)
        self.api('PATCH', f"/training/{other_record['id']}/media", 2, 400, json={'media_id':clip['id']})
        for _ in range(2):
            saved = self.api('PATCH', f"/training/{record['id']}/media", json={'media_id':clip['id']})
            self.assertEqual(saved['media_url'], clip['url'])
        self.api('POST', '/posts', status=400, json={'content':'不能公开训练视频', 'video_url':clip['url']})
        self.api('PATCH', f"/media/{clip['id']}", status=400, json={'purpose':'post'})
        self.api('POST', '/training', status=400, json={**payload,'media_url':'https://example.com/not-owned.mp4','media_type':'video'})
        self.api('DELETE', f"/media/{clip['id']}", 2, 404)
        self.api('DELETE', f"/media/{clip['id']}", status=204)
        self.api('GET', clip['url'], status=404)
        self.assertEqual(list((Path(self.folder.name)/'private').glob('*.mp4')), [])
        self.assertIsNone(self.api('GET', f"/training/{record['id']}")['media_url'])
        self.assertEqual(self.api('GET', '/training/summary')['sessions'], 1)

    def test_browser_recording_without_container_duration_can_be_saved(self):
        # WebM produced in live mode, like a browser MediaRecorder: no format duration.
        import json, subprocess, shutil
        path = Path(__file__).parent / 'fixtures' / 'recording.webm'
        info = json.loads(subprocess.check_output([shutil.which('ffprobe'), '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', str(path)]))
        self.assertNotIn('duration', info.get('format', {}))
        clip = self.api('POST', '/media/upload-training-video', files={'file': ('recording.webm', path.read_bytes(), 'video/webm')})
        response = self.client.get(clip['url'], headers=self.headers[1])
        self.assertEqual(response.content, path.read_bytes())
        self.assertIn('video/webm', response.headers['content-type'])

    def test_courts_city_and_nearby_queries_keep_real_source_and_pages(self):
        from urllib.parse import urlparse, parse_qs
        from app.services import amap
        import json
        response = unittest.mock.MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({'status':'1','count':'21','pois':[{'id':'court1','name':'检查球馆','cityname':'上海市','adname':'浦东新区','address':'检查路1号','tel':[], 'location':'121.5,31.2','distance':'1500','type':'体育;球馆'}]}).encode()
        with patch.object(amap.settings, 'amap_key', 'test-only'), patch.object(amap, 'urlopen', return_value=response) as fetch:
            data = self.api('POST', '/integrations/amap/courts/city', json={'city':'上海','keyword':'浦东','page':1})
            parsed = urlparse(fetch.call_args.args[0]); params = parse_qs(parsed.query)
            self.assertEqual(parsed.path, '/v3/place/text')
            self.assertEqual((params['city'], params['citylimit'], params['keywords']), (['上海'],['true'],['浦东 羽毛球馆']))
            self.assertEqual((data['source'],data['items'][0]['distance'],data['items'][0]['tel'],data['has_more']), ('amap','','',True))
            data = self.api('POST', '/integrations/amap/courts', json={'latitude':31.2,'longitude':121.5,'page':2})
            self.assertEqual(parse_qs(urlparse(fetch.call_args.args[0]).query)['page'], ['2'])
            self.assertEqual((data['items'][0]['distance'],data['has_more']), ('1.5 公里',False))
            self.api('POST', '/integrations/amap/courts', json={'latitude':31.2,'longitude':121.5,'keyword':'馆'*80})
            self.assertEqual(parse_qs(urlparse(fetch.call_args.args[0]).query)['keywords'], ['馆'*80+' 羽毛球馆'])
            self.api('POST', '/integrations/amap/courts/city', json={'city':'上海','keyword':'馆'*80})
        self.api('POST', '/integrations/amap/courts', status=422, json={'latitude':31.2,'longitude':121.5,'keyword':'馆'*81})
        self.api('POST', '/integrations/amap/courts/city', status=422, json={'city':'上海','keyword':'馆'*81})
        self.api('POST', '/integrations/amap/courts/city', status=400, json={'city':'   '})
        self.api('POST', '/integrations/amap/courts', status=422, json={'longitude':999,'latitude':31})
        self.api('POST', '/integrations/amap/courts/city', 0, 401, json={'city':'上海'})

    def test_sms_codes_are_bound_to_purpose_expire_and_only_work_once(self):
        from app.services import sms
        from app.models.sms import SmsChallenge
        from types import SimpleNamespace as Obj
        client = unittest.mock.MagicMock()
        sent = {}
        def send(request):
            code = '482917' if request.template_code == 'test-register' else '731806'
            self.assertTrue(request.return_verify_code)
            sent[request.out_id] = code
            return Obj(body=Obj(success=True,model=Obj(verify_code=code)))
        client.send_sms_verify_code.side_effect = send
        client.check_sms_verify_code.side_effect = lambda request: Obj(body=Obj(model=Obj(verify_result='PASS' if sent.get(request.out_id)==request.verify_code else 'FAIL')))
        with patch.object(sms.settings,'app_env','prod'), patch.object(sms,'_ensure_sms_settings'), patch.object(sms,'_template_code',side_effect=lambda scene:'test-'+scene), patch.object(sms,'_client',return_value=client):
            with self.Session() as db:
                phone = '13912340001'
                sms.send_sms(phone,'register',db)
                register_id = db.get(SmsChallenge,(phone,'register')).out_id
                with self.assertRaisesRegex(sms.SmsError,'先获取'): sms.check_sms_code(phone,'482917','reset_password',db)
                db.rollback()
                sms.send_sms(phone,'reset_password',db)
                with self.assertRaisesRegex(sms.SmsError,'本次操作'): sms.check_sms_code(phone,'482917','reset_password',db)
                self.assertEqual(client.check_sms_verify_code.call_count,0, 'wrong-purpose code never reaches provider')
                self.assertTrue(sms.check_sms_code(phone,'731806','reset_password',db))
                with self.assertRaisesRegex(sms.SmsError,'失效'): sms.check_sms_code(phone,'731806','reset_password',db)
                db.rollback()
                self.assertTrue(sms.check_sms_code(phone,'482917','register',db))
                self.assertEqual(client.check_sms_verify_code.call_args.args[0].out_id,register_id)
                row=db.get(SmsChallenge,(phone,'register'))
                self.assertNotIn('482917',row.code_hash)
                row.sent_at-=timedelta(seconds=300);db.commit()
                sms.send_sms(phone,'register',db)
                self.assertNotEqual(db.get(SmsChallenge,(phone,'register')).out_id,register_id)
                for _ in range(5):
                    with self.assertRaisesRegex(sms.SmsError,'不正确'):sms.check_sms_code(phone,'000000','register',db)
                with self.assertRaisesRegex(sms.SmsError,'次数'):sms.check_sms_code(phone,'482917','register',db)
                db.rollback()
                row=db.get(SmsChallenge,(phone,'register'));row.expires_at=datetime.utcnow()-timedelta(seconds=1);db.commit()
                with self.assertRaisesRegex(sms.SmsError,'过期'):sms.check_sms_code(phone,'482917','register',db)
        self.assertEqual(client.check_sms_verify_code.call_count,2)

    def test_local_sms_registration_and_reset_use_saved_challenges(self):
        from app.services import sms
        with patch.object(sms.settings,'app_env','dev'), patch.object(sms.settings,'allow_local_sms_code',True):
            phone='13912340002'
            self.api('POST','/auth/send-sms',json={'phone':phone,'scene':'register'})
            payload={'username':'sms-check','phone':phone,'password':'Test1234','sms_code':sms.settings.local_sms_code}
            registered=self.api('POST','/auth/register',json=payload)
            self.assertEqual(registered['user']['phone'],phone)
            self.api('POST','/auth/forgot-password',status=400,json={'account':'sms-check','phone':phone,'new_password':'Test5678','sms_code':sms.settings.local_sms_code})
            self.api('POST','/auth/send-sms',json={'phone':phone,'scene':'reset_password'})
            self.api('POST','/auth/forgot-password',json={'account':'sms-check','phone':phone,'new_password':'Test5678','sms_code':sms.settings.local_sms_code})

    def test_phone_change_requires_password_both_phones_and_revokes_old_login(self):
        from app.services import sms
        with patch.object(sms.settings,'app_env','dev'),patch.object(sms.settings,'allow_local_sms_code',True):
            self.api('POST','/auth/change-phone/code')
            payload={'password':'Test1234','new_phone':'13912345001','old_code':sms.settings.local_sms_code}
            self.api('POST','/auth/change-phone/start',status=400,json={**payload,'password':'wrong'})
            self.api('POST','/auth/change-phone/start',status=400,json={**payload,'new_phone':'13900000002'})
            started=self.api('POST','/auth/change-phone/start',json=payload)
            change_id=started['change_id']
            self.api('POST','/auth/change-phone/finish',2,404,json={'change_id':change_id,'new_code':sms.settings.local_sms_code})
            self.api('POST','/auth/change-phone/finish',status=400,json={'change_id':change_id,'new_code':'000000'})
            self.assertEqual(self.api('GET','/profile/me')['phone'],'13900000001')
            self.api('POST','/training',json={'training_type':'保留训练','duration_seconds':30,'score':0,'reps':1})
            result=self.api('POST','/auth/change-phone/finish',json={'change_id':change_id,'new_code':sms.settings.local_sms_code})
            self.assertEqual(result['user']['phone'],payload['new_phone'])
            self.api('GET','/profile/me',status=401)
            self.headers[1]={'Authorization':'Bearer '+result['token']}
            self.assertEqual(self.api('GET','/training/summary')['sessions'],1)
            self.api('POST','/auth/change-phone/finish',status=400,json={'change_id':change_id,'new_code':sms.settings.local_sms_code})
            self.api('POST','/auth/login',status=401,json={'account':'13900000001','password':'Test1234'})
            self.api('POST','/auth/login',json={'account':payload['new_phone'],'password':'Test1234'})

    def test_account_deletion_verification_removes_related_data_and_keeps_other_accounts(self):
        from app.models.notification import Notification
        from app.services import sms
        from app.models.post import Post,PostLike,PostComment
        from app.models.media import Media
        from app.models.clinic import ClinicQuestion,ClinicAnswer
        from app.models.social import Follow,Block,Favorite,Report
        from app.models.game import Game,GameMember
        from app.models.chat import ChatMessage,ChatSend,ChatState,ChatChange
        from app.models.account import PhoneChange,AccountFileDeletion
        from app.models.sms import SmsChallenge
        from sqlalchemy import text
        with self.engine.connect() as conn: conn.execute(text('PRAGMA foreign_keys=ON'))
        chat_id=self.accepted_chat()
        import base64
        data=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')
        image=self.api('POST',f'/chat/chats/{chat_id}/images',2,files={'file':('chat.png',data,'image/png')})
        self.api('POST',f'/chat/chats/{chat_id}/messages',2,json={'content':'双方临时聊天','image_url':image['url'],'request_key':'account-delete-chat'})
        upload=self.api('POST','/media/upload',files={'file':('avatar.png',data,'image/png')})
        unrelated=self.api('POST','/media/upload',2,files={'file':('other.png',data,'image/png')})
        with self.Session() as db:
            # A legacy shared public address must not delete the other person's independent file.
            db.add(ChatMessage(chat_id=chat_id,sender_id=2,message_type='image',content=unrelated['url']))
            db.add_all([Post(id=11,user_id=1,content='本人动态'),Post(id=12,user_id=2,content='别人的独立动态',likes_count=1),ClinicQuestion(id=11,user_id=1,title='本人的提问',content='内容'),ClinicQuestion(id=12,user_id=2,title='他人的提问',content='保留',accepted_answer_id=12),Game(id=11,host_id=1,title='本人球局',city='上海',venue='练习馆',starts_at=datetime.utcnow(),duration_minutes=60,capacity=4),TrainingRecord(user_id=1,training_type='本人训练',duration_seconds=60,score=0)])
            db.flush()
            db.add_all([PostComment(id=11,post_id=12,user_id=1,content='本人的留言'),PostComment(id=12,post_id=11,user_id=2,content='本人动态下的留言'),PostLike(post_id=12,user_id=1),ClinicAnswer(id=11,user_id=2,question_id=11,content='相关回答'),ClinicAnswer(id=12,user_id=1,question_id=12,content='本人的回答'),GameMember(game_id=11,user_id=2),Follow(user_id=2,target_id=1),Block(user_id=1,target_id=3),Favorite(user_id=2,kind='clinic',item_key='11'),Report(user_id=2,target_type='comment',target_id=11,reason='检查原因',snapshot='本人的留言'),PhoneChange(key_hash='temporary',user_id=1,old_phone='13900000001',new_phone='13912345555',session_version=0,expires_at=datetime.utcnow()+timedelta(minutes=5))])
            db.flush()
            # A third person's reminders also lose the deleted account's containing content.
            db.add_all([Notification(user_id=3,actor_id=2,kind='comment_reply',target_type='comment',target_id=12,context_id=11),Notification(user_id=3,actor_id=2,kind='clinic_answer',target_type='answer',target_id=11,context_id=11),Notification(user_id=3,actor_id=2,kind='game_joined',target_type='game',target_id=11)])
            db.commit()
        payload={'password':'Test1234','sms_code':'000000','confirmation':'确认注销'}
        self.api('POST','/account/deletion',status=400,json=payload)
        with patch.object(sms.settings,'app_env','dev'),patch.object(sms.settings,'allow_local_sms_code',True):
            self.api('POST','/account/deletion/code')
            payload['sms_code']=sms.settings.local_sms_code
            self.api('POST','/account/deletion',status=400,json={**payload,'password':'Wrong1234'})
            self.api('POST','/account/deletion',status=400,json={**payload,'confirmation':'取消'})
            self.api('POST','/account/deletion',2,400,json=payload)
            result=self.api('POST','/account/deletion',json=payload)
        self.assertFalse(result['files_pending'])
        self.api('GET','/profile/me',status=401)
        self.api('GET',image['url'],2,404)
        self.assertFalse((files.UPLOADS/upload['url'].removeprefix('/uploads/')).exists())
        self.assertTrue((files.UPLOADS/unrelated['url'].removeprefix('/uploads/')).exists())
        self.assertEqual(self.api('GET','/profile/me',2)['username'],'check2')
        self.assertEqual(self.api('GET','/chat/chats',2)['chats'],[])
        with self.Session() as db:
            self.assertIsNone(db.get(User,1))
            self.assertEqual(db.get(Post,12).content,'别人的独立动态')
            self.assertEqual(db.get(Post,12).likes_count,0)
            self.assertEqual(db.get(ClinicQuestion,12).accepted_answer_id,0)
            self.assertEqual(db.query(Report).one().snapshot,'内容已随账号注销删除')
            for model in (Notification,Chat,ChatMessage,ChatSend,ChatState,ChatChange,TrainingRecord,PostComment,PostLike,ClinicAnswer,Game,GameMember,Follow,Block,Favorite,PhoneChange,SmsChallenge,AccountFileDeletion):
                self.assertEqual(db.query(model).count(),0,model.__name__)
            # A newly registered account must never inherit the deleted account's old login.
            new=User(username='new-check',phone='13912345555',name='新账号',password_hash='unused')
            db.add(new);db.commit();self.assertGreater(new.id,3)

    def test_account_deletion_rollback_keeps_original_data_and_files(self):
        from app.models.media import Media
        from app.models.account import AccountFileDeletion
        from app.services.account_deletion import delete_account_data
        path=files.UPLOADS/'images'/'original.png';path.parent.mkdir();path.write_bytes(b'original')
        with self.Session() as db:
            db.add(Media(user_id=1,purpose='post',media_type='image',url='/uploads/images/original.png'));db.commit()
            with patch.object(db,'commit',side_effect=RuntimeError('simulated commit failure')):
                with self.assertRaises(RuntimeError):delete_account_data(db.get(User,1),db)
            db.rollback()
            self.assertIsNotNone(db.get(User,1))
            self.assertEqual(db.query(Media).count(),1)
            self.assertEqual(db.query(AccountFileDeletion).count(),0)
            self.assertEqual(path.read_bytes(),b'original')

    def test_account_deletion_failed_file_cleanup_can_be_retried(self):
        from app.models.account import AccountFileDeletion
        from app.services.account_deletion import cleanup_account_files
        path=files.UPLOADS/'images'/'retry.png';path.parent.mkdir();path.write_bytes(b'test')
        with self.Session() as db:
            db.add(AccountFileDeletion(path='images/retry.png'));db.commit()
            with patch.object(Path,'unlink',side_effect=OSError('temporarily unavailable')):
                self.assertEqual(cleanup_account_files(db),1)
            self.assertTrue(path.exists())
            self.assertEqual(cleanup_account_files(db),0)
            self.assertFalse(path.exists())

    def test_phone_change_expiry_cancel_and_password_change_invalidate_ticket(self):
        from app.services import sms
        from app.models.account import PhoneChange
        with patch.object(sms.settings,'app_env','dev'),patch.object(sms.settings,'allow_local_sms_code',True):
            self.api('POST','/auth/change-phone/code')
            started=self.api('POST','/auth/change-phone/start',json={'password':'Test1234','new_phone':'13912345002','old_code':sms.settings.local_sms_code})
            change_id=started['change_id']
            new=self.api('POST','/auth/change-password',json={'old_password':'Test1234','new_password':'Changed5678','confirm_password':'Changed5678'})
            self.headers[1]={'Authorization':'Bearer '+new['token']}
            self.api('POST','/auth/change-phone/finish',status=400,json={'change_id':change_id,'new_code':sms.settings.local_sms_code})
            with self.Session() as db:
                row=db.query(PhoneChange).filter_by(user_id=1).one()
                row.session_version=1;row.expires_at=datetime.utcnow()-timedelta(seconds=1);db.commit()
            self.api('POST','/auth/change-phone/resend',status=400,json={'change_id':change_id})
            self.api('POST','/auth/change-phone/cancel',2,404,json={'change_id':change_id})
            self.api('POST','/auth/change-phone/cancel',json={'change_id':change_id})
            self.assertEqual(self.api('GET','/profile/me')['phone'],'13900000001')


if __name__ == '__main__':
    unittest.main()
