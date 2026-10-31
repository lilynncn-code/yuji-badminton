"""Long discussions and retried sends use an isolated database only."""
import unittest
from datetime import datetime
from unittest.mock import patch
import test_app_flows as flows
from sqlalchemy import text
from app.models.clinic import ClinicQuestion,ClinicAnswer,ClinicSend
from app.models.notification import Notification
from app.models.user import User
from app.services.account_deletion import delete_account_data


class ClinicPageChecks(unittest.TestCase):
    setUp=flows.AppFlows.setUp
    tearDown=flows.AppFlows.tearDown
    api=flows.AppFlows.api

    def question(self,who=1,**extra):
        return self.api('POST','/clinic',who,json={'title':'启动步伐怎么练','content':'请球友分享练习建议',**extra})

    def test_long_answers_stable_pages_pinned_choice_and_notification_target(self):
        q=self.question()['id'];path=f'/clinic/{q}'
        with self.Session() as db:
            rows=[ClinicAnswer(question_id=q,user_id=2,content=f'临时建议{i}') for i in range(105)]
            db.add_all(rows);db.commit();ids=[r.id for r in rows]
            db.get(ClinicQuestion,q).accepted_answer_id=ids[2];db.commit()
        detail=self.api('GET',path)
        self.assertEqual([a['id'] for a in detail['answers']],ids[-30:])
        self.assertEqual(detail['answer_count'],105);self.assertTrue(detail['answers_has_more'])
        self.assertEqual(detail['accepted_answer']['id'],ids[2])
        seen=[a['id'] for a in detail['answers']];cursor=seen[0]
        # A new answer cannot shift the already loaded older-page boundary.
        latest=self.api('POST',path+'/answers',3,json={'content':'翻看时新增建议'})['answers'][-1]['id']
        more=True
        while more:
            page=self.api('GET',path+f'/answers?before_id={cursor}')
            older=[a['id'] for a in page['items']];seen=older+seen
            cursor=older[0] if older else cursor;more=page['has_more']
        self.assertEqual(seen,ids);self.assertNotIn(latest,seen)
        focused=self.api('GET',path+f'?answer_id={ids[5]}')
        self.assertEqual([a['id'] for a in focused['answers']],ids[:6])
        self.assertEqual(focused['answer_count'],106)
        notice=self.api('GET','/notifications')['items'][0]
        self.assertTrue(notice['url'].endswith(f'clinic-detail?id={q}&answer={latest}'))
        listing=self.api('GET','/clinic')['items'][0]
        self.assertEqual(listing['answers'],[]);self.assertEqual(listing['answer_count'],106)
        self.api('GET',path+'/answers?limit=0',status=422)

    def test_hidden_deleted_and_cross_question_focus_does_not_disclose_answers(self):
        q=self.question()['id'];other=self.question()['id'];path=f'/clinic/{q}'
        reply=self.api('POST',path+'/answers',2,json={'content':'稍后隐藏的建议'})['answers'][-1]['id']
        self.api('PUT',path+f'/accepted/{reply}')
        self.api('GET',f'/clinic/{other}?answer_id={reply}',status=404)
        self.api('PUT','/social/users/2/block')
        data=self.api('GET',path)
        self.assertEqual((data['answers'],data['answer_count'],data['accepted_answer_id'],data['accepted_answer']),([],0,0,None))
        self.assertEqual(self.api('GET',path+'/answers')['items'],[])
        self.api('GET',path+f'?answer_id={reply}',status=404)
        self.api('PUT',path+f'/accepted/{reply}',status=403)
        self.api('GET',path+'/answers',2,403)
        self.api('DELETE','/social/users/2/block')
        self.api('DELETE',path+f'/answers/{reply}',2)
        self.api('GET',path+f'?answer_id={reply}',status=404)
        self.api('DELETE',path)
        self.api('GET',path+'/answers',status=404)

    def test_question_answer_retry_account_isolation_and_deleted_sends_stay_deleted(self):
        key='clinic-send-one'
        q=self.question(request_key=key)
        self.assertEqual(self.question(request_key=key)['id'],q['id'])
        self.api('POST','/clinic',status=409,json={'title':'修改内容','content':'新的问题文字','request_key':key})
        other=self.question(2,request_key=key)
        self.assertNotEqual(other['id'],q['id'])
        path=f"/clinic/{q['id']}";payload={'content':'同一次回答只保存一次','request_key':'answer-retry-one'}
        first=self.api('POST',path+'/answers',2,json=payload)
        second=self.api('POST',path+'/answers',2,json=payload)
        self.assertEqual(second,first)
        self.assertEqual(self.api('GET','/notifications')['unread_count'],1)
        self.api('POST',f"/clinic/{other['id']}/answers",2,409,json=payload)
        self.api('POST',path+'/answers',2,409,json={**payload,'content':'改过的回答内容'})
        aid=first['answers'][0]['id']
        self.api('DELETE',path+f'/answers/{aid}',2)
        self.api('POST',path+'/answers',2,410,json=payload)
        self.api('DELETE',path)
        self.api('POST','/clinic',status=404,json={'title':'启动步伐怎么练','content':'请球友分享练习建议','request_key':key})
        newer=self.question(request_key='brand-new-question')
        self.assertNotEqual(newer['id'],q['id'])

    def test_failed_send_rolls_back_answer_notification_and_retry_marker(self):
        q=self.question()['id'];path=f'/clinic/{q}/answers'
        with self.Session() as db:db.get(User,2).last_active_at=datetime.utcnow();db.commit()
        payload={'content':'保存失败后仍可重试','request_key':'failed-answer-key'}
        with patch('sqlalchemy.orm.Session.commit',side_effect=RuntimeError('temporary failure')):
            with self.assertRaises(RuntimeError):self.api('POST',path,2,json=payload)
        with self.Session() as db:
            self.assertEqual(db.query(ClinicAnswer).count(),0)
            self.assertEqual(db.query(ClinicSend).count(),0)
            self.assertEqual(db.query(Notification).count(),0)
        self.assertEqual(self.api('POST',path,2,json=payload)['answer_count'],1)

    def test_account_deletion_cleans_send_markers_without_losing_other_discussions(self):
        q=self.question(request_key='question-owner-one')['id'];other=self.question(2,request_key='question-owner-two')['id']
        self.api('POST',f'/clinic/{q}/answers',2,json={'content':'他人回答本人问题','request_key':'answer-owner-two'})
        self.api('POST',f'/clinic/{other}/answers',json={'content':'本人回答他人问题','request_key':'answer-owner-one'})
        with self.Session() as db:
            db.execute(text('PRAGMA foreign_keys=ON'))
            delete_account_data(db.get(User,1),db)
        with self.Session() as db:
            self.assertEqual([(s.user_id,s.question_id) for s in db.query(ClinicSend)],[(2,other)])
            self.assertIsNotNone(db.get(ClinicQuestion,other))
        self.assertEqual(self.api('GET',f'/clinic/{other}',2)['answer_count'],0)
