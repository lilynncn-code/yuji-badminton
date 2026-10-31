"""Replies and notifications against isolated accounts, including deletion boundaries."""
from datetime import datetime, timedelta
import unittest
import test_app_flows as flows
from app.models.notification import Notification
from app.models.post import PostComment


class ReplyAndNotificationChecks(unittest.TestCase):
    setUp = flows.AppFlows.setUp
    tearDown = flows.AppFlows.tearDown
    api = flows.AppFlows.api
    accepted_chat = flows.AppFlows.accepted_chat

    def post(self, who=1):
        return self.api('POST', '/posts', who, json={'content':'回复检查动态'})['id']

    def comment(self, post, who=2, **extra):
        return self.api('POST', f'/posts/{post}/comments', who, json={'content':'原留言内容', **extra})

    def notices(self, who=1, suffix=''):
        return self.api('GET', '/notifications'+suffix, who)

    def test_reply_targets_retry_and_deleted_original(self):
        post=self.post(); first=self.comment(post)
        payload={'content':'回复内容','reply_to_id':first['id'],'request_key':'reply-retry-once'}
        reply=self.comment(post,3,**payload)
        self.assertEqual(reply['reply_to']['content'],'原留言内容')
        self.assertEqual(self.comment(post,3,**payload)['id'],reply['id'])
        self.assertEqual([n['kind'] for n in self.notices(2)['items']],['comment_reply'])
        self.assertEqual(len(self.notices()['items']),2)
        self.assertEqual(self.notices(3)['items'],[])
        self.api('POST',f'/posts/{post}/comments',3,409,json={**payload,'content':'变化内容'})
        self.api('DELETE',f"/posts/{post}/comments/{first['id']}",2)
        detail=self.api('GET',f'/posts/{post}')
        self.assertEqual(detail['comments_count'],1)
        self.assertIsNone(detail['comments'][0]['reply_to'])
        self.assertEqual(detail['comments'][0]['reply_to_id'],first['id'])
        self.assertEqual(len(self.notices()['items']),1)
        self.api('POST',f'/posts/{post}/comments',3,404,json={**payload,'request_key':'another-reply'})
        self.api('DELETE',f"/posts/{post}/comments/{reply['id']}",3)
        self.api('POST',f'/posts/{post}/comments',3,410,json=payload)
        self.assertEqual(self.notices(2)['items'],[])
        with self.Session() as db:
            self.assertEqual(db.get(PostComment,first['id']).content,'')
            self.assertEqual(db.get(PostComment,reply['id']).content,'')

    def test_cross_post_reply_and_blocked_quotes_are_rejected_or_hidden(self):
        post=self.post(); other=self.post(); first=self.comment(post)
        self.api('POST',f'/posts/{other}/comments',3,404,json={'content':'跨动态回复','reply_to_id':first['id']})
        self.comment(post,3,content='引用回复',reply_to_id=first['id'])
        self.api('PUT','/social/users/2/block')
        detail=self.api('GET',f'/posts/{post}')
        self.assertEqual(detail['comments_count'],1)
        self.assertIsNone(detail['comments'][0]['reply_to'])
        self.assertEqual(len(self.notices()['items']),1)
        notice=self.notices()['items'][0]
        status=self.api('GET',f"/notifications/unread?ids={notice['id']}&ids=99999")
        self.assertEqual([n['id'] for n in status['items']],[notice['id']])
        self.assertEqual(self.api('GET',f"/notifications/unread?ids={notice['id']}",2)['items'],[])
        self.api('POST',f'/posts/{post}/comments',status=403,json={'content':'屏蔽后回复','reply_to_id':first['id']})
        self.api('GET',f"/posts/{post}?comment_id={first['id']}",status=404)
        self.api('PUT','/social/users/2/block',3)
        self.api('POST',f'/posts/{post}/comments',3,403,json={'content':'双方限制','reply_to_id':first['id']})
        # Deleting the containing post also removes reminders held by another account.
        self.api('DELETE',f'/posts/{post}')
        self.assertEqual(self.notices(2)['items'],[])
        with self.Session() as db:self.assertEqual(db.query(Notification).count(),0)

    def test_report_history_reads_past_one_hundred_and_is_account_private(self):
        from app.models.social import Report
        with self.Session() as db:
            db.add_all([Report(user_id=1,target_type='user',target_id=2,reason=f'检查记录{i}',snapshot='临时内容') for i in range(105)])
            db.add(Report(user_id=2,target_type='user',target_id=3,reason='另一账号记录',snapshot='不能读取'))
            db.commit()
        first=self.api('GET','/social/reports')
        self.assertEqual(len(first['items']),30)
        self.assertTrue(first['has_more'])
        seen=[r['id'] for r in first['items']]
        with self.Session() as db:
            db.add(Report(user_id=1,target_type='user',target_id=3,reason='翻看时新增',snapshot='临时内容'));db.commit()
        page=first
        while page['has_more']:
            page=self.api('GET',f"/social/reports?before_id={seen[-1]}")
            seen.extend(r['id'] for r in page['items'])
        self.assertEqual((len(seen),len(set(seen))),(105,105))
        self.assertEqual(len(self.api('GET','/social/reports',2)['items']),1)

    def test_comments_pages_and_reminder_target_stay_stable(self):
        post=self.post(); ids=[self.comment(post,content=f'留言{i}')['id'] for i in range(36)]
        recent=self.api('GET',f'/posts/{post}')
        self.assertTrue(recent['comments_has_more'])
        self.assertEqual([c['id'] for c in recent['comments']],ids[6:])
        earlier=self.api('GET',f'/posts/{post}/comments?before_id={ids[6]}')
        self.assertEqual([c['id'] for c in earlier['items']],ids[:6])
        self.assertFalse(earlier['has_more'])
        self.comment(post,content='翻看时新增')
        self.assertEqual(self.api('GET',f'/posts/{post}/comments?before_id={ids[6]}'),earlier)
        focused=self.api('GET',f'/posts/{post}?comment_id={ids[2]}')
        self.assertEqual([c['id'] for c in focused['comments']],ids[:3])
        self.assertEqual(focused['comments_count'],37)

    def test_notifications_paging_read_boundary_and_account_isolation(self):
        self.api('GET','/notifications',0,401)
        post=self.post()
        for i in range(6):self.comment(post,content=f'提醒{i}')
        first=self.notices(suffix='?limit=2')
        latest=first['latest_id']
        self.assertEqual((len(first['items']),first['has_more'],first['unread_count']),(2,True,6))
        next_page=self.notices(suffix=f"?limit=2&before_id={first['items'][-1]['id']}")
        self.assertFalse({n['id'] for n in first['items']} & {n['id'] for n in next_page['items']})
        self.api('POST','/notifications/read',2,json={'ids':[first['items'][0]['id']]})
        self.assertEqual(self.notices()['unread_count'],6)
        self.comment(post,content='点击已读时新到的提醒')
        self.api('POST','/notifications/read',json={'through_id':latest})
        unread=self.notices(suffix='?only_unread=true')
        self.assertEqual((len(unread['items']),unread['unread_count']),(1,1))
        self.assertEqual(unread['items'][0]['excerpt'],'点击已读时新到的提醒')
        self.assertEqual(self.api('GET','/notifications/unread')['unread_count'],1)
        self.api('POST','/notifications/read',json={'ids':[unread['items'][0]['id']]})
        self.assertEqual(self.notices(suffix='?only_unread=true')['items'],[])
        for payload in ({},{'ids':[-1]},{'ids':[1],'through_id':1}):
            self.api('POST','/notifications/read',status=422,json=payload)

    def test_chat_request_repeat_accept_reject_and_cancel_notifications(self):
        path='/chat/requests'
        chat=self.api('POST',path,json={'receiver_id':2})['chat']['id']
        self.api('POST',path,json={'receiver_id':2})
        self.api('POST',path,2,json={'receiver_id':1})
        self.assertEqual(len(self.notices(2)['items']),1)
        self.api('POST',f'{path}/{chat}/reject',2)
        self.api('POST',f'{path}/{chat}/reject',2)
        self.assertEqual(len(self.notices()['items']),1)
        self.api('POST',path,json={'receiver_id':2})
        self.assertEqual(len(self.notices(2)['items']),2)
        self.api('POST',f'{path}/{chat}/accept',2)
        self.api('POST',f'{path}/{chat}/accept',2)
        self.assertEqual([n['kind'] for n in self.notices()['items']],['chat_accepted','chat_rejected'])
        self.assertTrue(self.notices()['items'][0]['url'].endswith(f'thread?id={chat}'))
        other=self.api('POST',path,json={'receiver_id':3})['chat']['id']
        self.api('DELETE',f'{path}/{other}')
        self.assertEqual(self.notices(3)['items'],[])
        self.api('PUT','/social/users/2/block')
        self.assertEqual(self.notices()['items'],[])
        self.assertEqual(self.notices(2)['items'],[])

    def test_game_cancellation_notifies_joined_even_if_blocked_and_only_once(self):
        game=self.api('POST','/games',json={'title':'周末球局','city':'上海','venue':'练习球馆','starts_at':(datetime.utcnow()+timedelta(days=1)).isoformat()+'Z','capacity':4})['id']
        path=f'/games/{game}'
        self.api('PUT',path+'/join',2);self.api('PUT',path+'/join',2)
        self.assertEqual(len(self.notices()['items']),1)
        self.api('PUT',path+'/join',3)
        self.api('DELETE',path+'/join',3);self.api('DELETE',path+'/join',3)
        self.assertEqual(len(self.notices()['items']),3)
        self.api('PUT','/social/users/1/block',2)
        self.api('POST',path+'/cancel');self.api('POST',path+'/cancel')
        rows=self.notices(2)['items']
        self.assertEqual([n['kind'] for n in rows],['game_cancelled'])
        self.assertEqual(self.notices(3)['items'],[])
        self.assertEqual(self.api('GET',path,2)['status'],'cancelled')

    def test_answer_reminder_disappears_with_answer_or_question(self):
        q=self.api('POST','/clinic',json={'title':'怎么练习','content':'请球友指点步伐'})['id']
        path=f'/clinic/{q}'
        self.api('POST',path+'/answers',json={'content':'自己的补充'})
        self.assertEqual(self.notices()['items'],[])
        reply=self.api('POST',path+'/answers',2,json={'content':'先慢速练习'})['answers'][-1]['id']
        self.assertEqual(self.notices()['items'][0]['excerpt'],'先慢速练习')
        self.api('DELETE',path+f'/answers/{reply}',2)
        self.assertEqual(self.notices()['items'],[])
        self.api('POST',path+'/answers',3,json={'content':'从重心开始'})
        self.api('DELETE',path)
        with self.Session() as db:self.assertEqual(db.query(Notification).count(),0)
