"""Report review uses temporary accounts only, never grants real-account access."""
import unittest
from unittest.mock import patch
from sqlalchemy import create_engine,text,inspect
import test_app_flows as flows
from app.models.user import User
from app.models.social import Report
from app.models.post import Post,PostComment
from app.models.notification import Notification
from app.services.account_deletion import delete_account_data


class ReportReviewChecks(unittest.TestCase):
    setUp=flows.AppFlows.setUp
    tearDown=flows.AppFlows.tearDown
    api=flows.AppFlows.api

    def grant(self,who=3):
        with self.Session() as db:
            db.get(User,who).can_review_reports=1;db.commit()

    def report(self,kind='post',target=None,who=2):
        if target is None:target=self.api('POST','/posts',json={'content':'待核查的动态','request_key':'original-post'})['id']
        report=self.api('POST','/social/reports',who,json={'target_type':kind,'target_id':target,'reason':'核查内容问题'})['id']
        return report,target

    def resolve(self,report,action='remove_content',result='核查后移除违规内容',who=3,status=200):
        return self.api('POST',f'/social/review/reports/{report}',who,status,json={'action':action,'result':result})

    def test_access_is_server_checked_and_not_self_grantable(self):
        report,post=self.report()
        self.api('GET','/social/review/reports',0,401)
        self.api('GET','/social/review/reports',2,403)
        self.resolve(report,who=2,status=403)
        self.api('PATCH','/profile/me',2,json={'can_review_reports':True})
        self.assertFalse(self.api('GET','/profile/me',2)['can_review_reports'])
        self.grant()
        self.assertTrue(self.api('GET','/profile/me',3)['can_review_reports'])
        item=self.api('GET','/social/review/reports',3)['items'][0]
        self.assertEqual((item['snapshot'],item['current_content']),('待核查的动态','待核查的动态'))
        self.assertNotIn('snapshot',self.api('GET','/social/reports',2)['items'][0])
        with self.Session() as db:db.get(User,3).can_review_reports=0;db.commit()
        self.resolve(report,status=403)

    def test_post_removal_hides_replies_notices_and_old_send_retry(self):
        self.grant();report,post=self.report()
        comment=self.api('POST',f'/posts/{post}/comments',2,json={'content':'此动态的留言','request_key':'original-comment'})['id']
        self.assertEqual(self.api('GET','/notifications')['unread_count'],1)
        saved=self.resolve(report)
        self.assertEqual(saved['status'],'resolved');self.assertTrue(saved['resolved_at'])
        self.assertEqual(self.resolve(report),saved)
        self.resolve(report,action='no_violation',status=409)
        self.api('GET',f'/posts/{post}',status=404)
        self.api('POST','/posts',status=410,json={'content':'待核查的动态','request_key':'original-post'})
        self.api('PUT',f'/posts/{post}',status=404,json={'content':'不能复原'})
        self.api('POST',f'/posts/{post}/comments',2,404,json={'content':'不能再留言'})
        self.assertEqual(self.api('GET','/posts')['items'],[])
        self.assertEqual(self.api('GET','/notifications')['unread_count'],0)
        self.assertEqual(self.api('GET','/social/reports',2)['items'][0]['result'],saved['result'])
        with self.Session() as db:
            self.assertEqual(db.get(Post,post).content,'')
            self.assertEqual(db.get(PostComment,comment).content,'')
            self.assertEqual(db.query(Notification).count(),0)

    def test_comment_removal_retains_reply_without_original_and_repeat_is_safe(self):
        self.grant();post=self.api('POST','/posts',json={'content':'独立讨论'})['id']
        comment=self.api('POST',f'/posts/{post}/comments',2,json={'content':'待核查留言','request_key':'comment-review'})['id']
        self.api('POST',f'/posts/{post}/comments',json={'content':'保留的回复','reply_to_id':comment})
        report,_=self.report('comment',comment,who=1)
        self.resolve(report)
        detail=self.api('GET',f'/posts/{post}')
        self.assertEqual(detail['comments_count'],1)
        self.assertEqual(detail['comments'][0]['content'],'保留的回复')
        self.assertIsNone(detail['comments'][0]['reply_to'])
        self.api('POST',f'/posts/{post}/comments',2,410,json={'content':'待核查留言','request_key':'comment-review'})
        self.api('POST',f'/posts/{post}/comments',2,404,json={'content':'新回复','reply_to_id':comment})
        other,_=self.report('comment',detail['comments'][0]['id'],who=2)
        self.resolve(other,action='already_unavailable',status=409)
        self.resolve(other,action='no_violation',result='核查后未发现违规')
        self.assertEqual(self.api('GET',f'/posts/{post}')['comments_count'],1)

    def test_own_reports_and_own_content_cannot_be_reviewed_by_self(self):
        self.grant(1);self.grant(2)
        report,post=self.report()
        for who in (1,2):
            self.resolve(report,who=who,status=403)
            row=self.api('GET','/social/review/reports',who)['items'][0]
            self.assertFalse(row['can_handle']);self.assertFalse(row['can_remove'])
        self.api('DELETE',f'/posts/{post}')
        self.resolve(report,who=1,action='already_unavailable',status=403)

    def test_unavailable_target_account_report_validation_and_paging(self):
        self.grant();report,post=self.report()
        self.api('DELETE',f'/posts/{post}')
        self.resolve(report,status=409)
        self.resolve(report,action='no_violation',status=409)
        self.resolve(report,action='already_unavailable',result='原内容已由作者删除，无法继续核查')
        account,_=self.report('user',1)
        self.resolve(account,status=400)
        self.resolve(account,action='no_violation',result='  ',status=400)
        self.resolve(account,action='no_violation',result='账号资料未发现所述问题')
        account_note,_=self.report('user',2,who=1)
        self.resolve(account_note,action='record_result',result='已记录此次核查依据，此处未停用账号')
        with self.Session() as db:
            db.add_all(Report(user_id=1,target_type='user',target_id=2,reason='分页核查',snapshot='名字') for _ in range(105));db.commit()
        seen=[];more=True
        while more:
            data=self.api('GET','/social/review/reports'+(f'?before_id={seen[-1]}' if seen else ''),3)
            seen.extend(r['id'] for r in data['items']);more=data['has_more']
        self.assertEqual((len(seen),len(set(seen))),(105,105))
        self.assertEqual(len(self.api('GET','/social/review/reports?state=resolved',3)['items']),3)

    def test_reviewer_deletion_drops_identity_but_keeps_result(self):
        self.grant();report,post=self.report();self.resolve(report)
        with self.Session() as db:delete_account_data(db.get(User,3),db)
        with self.Session() as db:
            self.assertIsNone(db.get(Report,report).handled_by)
            self.assertEqual(db.get(Report,report).status,'resolved')
        with self.Session() as db:delete_account_data(db.get(User,1),db)
        with self.Session() as db:self.assertEqual(db.get(Report,report).snapshot,'内容已随账号注销删除')

    def test_review_save_failure_rolls_back_content_and_result(self):
        self.grant();report,post=self.report()
        # Skip unrelated last-active commits so the failure is the handling commit.
        from datetime import datetime
        with self.Session() as db:
            db.get(User,3).last_active_at=datetime.utcnow();db.commit()
        with patch('sqlalchemy.orm.Session.commit',side_effect=RuntimeError('temporary failure')):
            with self.assertRaises(RuntimeError):self.resolve(report)
        self.assertEqual(self.api('GET',f'/posts/{post}')['content'],'待核查的动态')
        self.assertEqual(self.api('GET','/social/reports',2)['items'][0]['status'],'pending')

    def test_old_report_and_user_columns_can_be_added_twice(self):
        import app.db.init_db as upgrade
        engine=create_engine('sqlite://')
        with engine.begin() as db:
            db.execute(text('CREATE TABLE users (id INTEGER PRIMARY KEY, username VARCHAR(50))'))
            db.execute(text('CREATE TABLE reports (id INTEGER PRIMARY KEY, result VARCHAR(500))'))
            db.execute(text("INSERT INTO reports (id,result) VALUES (1,'保留旧结果')"))
        with patch.object(upgrade,'engine',engine):
            for _ in range(2):upgrade.ensure_user_columns();upgrade.ensure_report_columns(engine)
        with engine.connect() as db:
            self.assertEqual(db.execute(text('SELECT result,action,handled_by FROM reports')).one(),('保留旧结果','',None))
        self.assertIn('can_review_reports',{c['name'] for c in inspect(engine).get_columns('users')})
        engine.dispose()
