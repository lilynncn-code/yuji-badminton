"""Bounded chat lists, private previews, and stable ordering in temporary data."""
import unittest
from datetime import datetime
import time
from unittest.mock import patch
from sqlalchemy import text
import test_app_flows as flows
from app.models.chat import Chat,ChatMessage,ChatInboxRevision
from app.models.user import User
from app.services.account_deletion import delete_account_data


class ChatInboxPageChecks(unittest.TestCase):
    setUp=flows.AppFlows.setUp
    tearDown=flows.AppFlows.tearDown
    api=flows.AppFlows.api

    def seed(self,count=105):
        when=datetime(2026,10,1,12)
        with self.Session() as db:
            password=db.get(User,1).password_hash
            db.add_all([User(id=i+4,username=f'inbox{i}',name=f'列表球友{i}',phone=f'137{i:08}',password_hash=password) for i in range(count)])
            db.flush()
            rows=[Chat(requester_id=1,receiver_id=i+4,status='accepted',updated_at=when) for i in range(count)]
            db.add_all(rows);db.commit()
            return [row.id for row in rows]

    def test_all_long_lists_and_totals_without_duplicates_at_equal_times(self):
        ids=self.seed()
        with self.Session() as db:
            db.add(Chat(requester_id=2,receiver_id=1,status='pending'))
            db.add(Chat(requester_id=1,receiver_id=3,status='pending'));db.commit()
        first=self.api('GET','/chat/chats?kind=threads')
        self.assertEqual(len(first['chats']),30)
        self.assertEqual(first['summary'],{'total_threads':105,'total_requests':107,'pending_incoming':1,'unread_count':0})
        for kind,total in [('threads',105),('requests',107)]:
            seen=[];cursor=''
            while True:
                data=self.api('GET','/chat/chats',params={'kind':kind,'cursor':cursor or None,'limit':30})
                seen.extend(c['id'] for c in data['chats'])
                if not data['has_more']:break
                self.assertTrue(data['next_cursor']);cursor=data['next_cursor']
            self.assertEqual(len(seen),total);self.assertEqual(len(set(seen)),total)
            if kind=='threads':self.assertEqual(seen,list(reversed(ids)))
        one=self.api('GET','/chat/chats?kind=threads&limit=1')
        self.assertEqual(one['summary'],first['summary'])
        self.api('GET','/chat/chats?limit=101',status=422)
        self.api('GET','/chat/chats?kind=unknown',status=422)

    def test_cursors_reject_other_accounts_categories_tampering_and_expiry(self):
        self.seed(3)
        first=self.api('GET','/chat/chats?kind=threads&limit=1');cursor=first['next_cursor']
        self.api('GET','/chat/chats',2,400,params={'kind':'threads','cursor':cursor})
        self.api('GET','/chat/chats',status=400,params={'kind':'requests','cursor':cursor})
        self.api('GET','/chat/chats',status=400,params={'kind':'threads','cursor':cursor+'x'})
        self.api('GET','/chat/chats?cursor=not-a-position',status=400)
        # Keep the login valid while expiring only the 30-minute list position.
        with patch('app.services.chat_inbox.time.time',return_value=time.time()+1801):
            self.api('GET','/chat/chats',status=400,params={'kind':'threads','cursor':cursor})
        self.api('GET','/chat/chats',0,401)
        self.api('GET','/chat/chats/status',0,401)

    def test_read_and_clear_preserve_order_counts_and_old_boundary(self):
        ids=self.seed(3);cid=ids[0]
        with self.Session() as db:
            messages=[ChatMessage(chat_id=cid,sender_id=4,message_type='text',content='对方旧消息') for _ in range(3)]
            db.add_all(messages);db.flush();messages[2].recalled_at=datetime.utcnow()
            db.add(ChatMessage(chat_id=cid,sender_id=1,message_type='text',content='本人消息'))
            db.commit();mid=messages[0].id;when=db.get(Chat,cid).updated_at
        page=self.api('GET','/chat/chats?kind=threads&limit=1')
        self.assertEqual(page['summary']['unread_count'],2)
        self.api('POST',f'/chat/chats/{cid}/read',json={'last_message_id':mid})
        self.assertEqual(self.api('GET','/chat/chats/status')['summary']['unread_count'],1)
        self.api('DELETE',f'/chat/chats/{cid}/history')
        status=self.api('GET','/chat/chats/status',params={'ids':[cid]})
        self.assertEqual(status['summary']['unread_count'],0)
        self.assertIsNone(status['chats'][0]['last_message'])
        self.assertEqual(status['revision'],page['revision'])
        self.api('GET','/chat/chats',params={'kind':'threads','cursor':page['next_cursor']})
        with self.Session() as db:self.assertEqual(db.get(Chat,cid).updated_at,when)
        self.api('DELETE',f'/chat/chats/{cid}')
        self.assertEqual(self.api('GET','/chat/chats/status',params={'ids':[cid]})['chats'],[])
        self.api('GET','/chat/chats',status=409,params={'kind':'threads','cursor':page['next_cursor']})
        self.api('POST',f'/chat/chats/{cid}/visible')
        self.assertEqual(len(self.api('GET','/chat/chats/status',params={'ids':[cid]})['chats']),1)

    def test_block_unblock_filter_previews_counts_and_invalidate_boundaries(self):
        ids=self.seed(3)
        with self.Session() as db:
            db.add(ChatMessage(chat_id=ids[0],sender_id=4,message_type='text',content='屏蔽后不得显示的文字'));db.commit()
        page=self.api('GET','/chat/chats?kind=threads&limit=1')
        self.api('PUT','/social/users/4/block')
        status=self.api('GET','/chat/chats/status',params={'ids':ids})
        self.assertEqual(status['summary']['total_threads'],2);self.assertEqual(status['summary']['unread_count'],0)
        self.assertNotIn(ids[0],[c['id'] for c in status['chats']])
        self.assertNotIn('屏蔽后不得显示的文字',str(status))
        revision=status['revision'];self.api('PUT','/social/users/4/block')
        self.assertEqual(self.api('GET','/chat/chats/status')['revision'],revision)
        self.api('GET','/chat/chats',status=409,params={'kind':'threads','cursor':page['next_cursor']})
        blocked=self.api('GET','/chat/chats?kind=threads&limit=1')
        self.api('DELETE','/social/users/4/block')
        self.api('GET','/chat/chats',status=409,params={'kind':'threads','cursor':blocked['next_cursor']})
        self.assertEqual(self.api('GET','/chat/chats/status')['summary']['total_threads'],3)
        # Opposite-direction blocking has the same visibility rule.
        from app.services.security import create_token
        self.headers[4]={'Authorization':'Bearer '+create_token(4)}
        self.api('PUT','/social/users/1/block',4)
        self.assertNotIn(ids[0],[c['id'] for c in self.api('GET','/chat/chats')['chats']])
        self.assertEqual(self.api('GET','/chat/chats/status',4,params={'ids':[ids[0]]})['chats'],[])
        self.api('PUT','/social/users/1/block',2)
        own=self.api('POST','/chat/requests',3,json={'receiver_id':1})['chat']['id']
        self.api('GET','/chat/chats/status',params={'ids':[own]*101},status=422)
        self.api('GET','/chat/chats/status?ids=-1',status=400)
        self.assertEqual(self.api('GET','/chat/chats/status',2,params={'ids':ids})['chats'],[])

    def test_player_detail_finds_older_or_hidden_chat_without_loading_the_inbox(self):
        ids=self.seed(105)
        oldest=self.api('GET','/discovery/players/4')
        self.assertEqual((oldest['chat_state'],oldest['chat_id']),('accepted',ids[0]))
        self.api('DELETE',f'/chat/chats/{ids[0]}')
        self.assertEqual(self.api('GET','/discovery/players/4')['chat_id'],ids[0])
        self.api('PUT','/social/users/4/block')
        self.assertIsNone(self.api('GET','/discovery/players/4')['chat_id'])
        pending=self.api('POST','/chat/requests',2,json={'receiver_id':1})['chat']['id']
        self.assertEqual(self.api('GET','/discovery/players/2')['chat_state'],'review')
        self.assertEqual(self.api('GET','/discovery/players/1',2)['chat_state'],'waiting')

    def test_new_sends_retries_recall_and_request_changes(self):
        ids=self.seed(3);cid=ids[0]
        page=self.api('GET','/chat/chats?kind=threads&limit=1')
        payload={'content':'新的列表预览','request_key':'inbox-retry-send'}
        sent=self.api('POST',f'/chat/chats/{cid}/messages',json=payload)['messages'][0]
        self.api('GET','/chat/chats',status=409,params={'kind':'threads','cursor':page['next_cursor']})
        rev=self.api('GET','/chat/chats/status')['revision']
        self.api('POST',f'/chat/chats/{cid}/messages',json=payload)
        self.assertEqual(self.api('GET','/chat/chats/status')['revision'],rev)
        self.api('POST',f'/chat/chats/{cid}/messages/{sent["id"]}/recall')
        self.assertGreater(self.api('GET','/chat/chats/status')['revision'],rev)
        request=self.api('POST','/chat/requests',json={'receiver_id':2})['chat']['id']
        pending=self.api('GET','/chat/chats/status',2)
        self.assertEqual(pending['summary']['pending_incoming'],1)
        self.api('POST',f'/chat/requests/{request}/reject',2)
        self.assertGreater(self.api('GET','/chat/chats/status',2)['revision'],pending['revision'])
        self.api('POST','/chat/requests',json={'receiver_id':2})
        self.api('DELETE',f'/chat/requests/{request}')
        self.assertEqual(self.api('GET','/chat/chats/status',2)['summary']['total_requests'],0)
        request=self.api('POST','/chat/requests',json={'receiver_id':2})['chat']['id']
        self.api('POST',f'/chat/requests/{request}/accept',2)
        self.assertEqual(self.api('GET','/chat/chats/status',2)['summary']['total_threads'],1)

    def test_account_deletion_removes_revision_and_invalidates_other_inboxes(self):
        ids=self.seed(3)
        self.api('POST','/chat/requests',json={'receiver_id':2})
        self.api('POST','/chat/requests',3,json={'receiver_id':2})
        page=self.api('GET','/chat/chats?kind=requests&limit=1',2)
        with self.Session() as db:
            db.execute(text('PRAGMA foreign_keys=ON'))
            delete_account_data(db.get(User,1),db)
            self.assertIsNone(db.get(ChatInboxRevision,1))
            self.assertIsNotNone(db.get(ChatInboxRevision,2))
        self.api('GET','/chat/chats',2,409,params={'kind':'requests','cursor':page['next_cursor']})
        remaining=self.api('GET','/chat/chats?kind=requests',2)
        self.assertEqual(len(remaining['chats']),1)
        self.assertEqual(remaining['chats'][0]['requester_id'],3)
