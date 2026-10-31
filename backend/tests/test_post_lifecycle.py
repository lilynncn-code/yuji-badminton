"""Post deletion, retry and failure boundaries using only temporary accounts."""
from datetime import datetime
from unittest.mock import patch
import unittest
import test_app_flows as flows
from app.models.post import Post, PostComment, PostLike
from app.models.notification import Notification
from app.models.user import User


class PostLifecycleChecks(unittest.TestCase):
    setUp=flows.AppFlows.setUp
    tearDown=flows.AppFlows.tearDown
    api=flows.AppFlows.api

    def post(self,who=1,**extra):
        return self.api('POST','/posts',who,json={'content':'临时动态','request_key':'post-check-once',**extra})

    def test_deleted_post_retry_cannot_restore_content_or_comments(self):
        post=self.post();pid=post['id']
        comment=self.api('POST',f'/posts/{pid}/comments',2,json={'content':'临时留言','request_key':'comment-check-once'})
        self.api('POST',f'/posts/{pid}/like',2)
        other=self.post(3,content='独立动态')
        self.api('DELETE',f'/posts/{pid}')
        self.api('POST','/posts',status=410,json={'content':'临时动态','request_key':'post-check-once'})
        self.api('GET',f'/posts/{pid}',status=404)
        self.api('GET',f'/posts/{pid}/comments',status=404)
        self.api('POST',f'/posts/{pid}/comments',2,404,json={'content':'临时留言','request_key':'comment-check-once'})
        self.api('POST',f"/posts/{other['id']}/comments",2,410,json={'content':'临时留言','request_key':'comment-check-once'})
        for method,path,body in [('POST',f'/posts/{pid}/like',None),('DELETE',f'/posts/{pid}/like',None),('PUT',f'/posts/{pid}',{'content':'恢复内容'})]:
            self.api(method,path,status=404,**({'json':body} if body else {}))
        self.assertEqual(self.api('GET','/posts')['total'],1)
        with self.Session() as db:
            row=db.get(Post,pid);reply=db.get(PostComment,comment['id'])
            self.assertIsNotNone(row.removed_at);self.assertEqual((row.content,row.image_urls,row.video_url,row.likes_count),('',[],'',0))
            self.assertIsNotNone(reply.deleted_at);self.assertEqual(reply.content,'')
            self.assertEqual(db.query(PostLike).count(),0);self.assertEqual(db.query(Notification).count(),0)
        self.assertEqual(self.api('GET',f"/posts/{other['id']}")['content'],'独立动态')

    def test_delete_save_failure_retains_content_likes_comments_and_reminders(self):
        pid=self.post()['id']
        self.api('POST',f'/posts/{pid}/comments',2,json={'content':'保留留言'})
        self.api('POST',f'/posts/{pid}/like',3)
        with self.Session() as db:db.get(User,1).last_active_at=datetime.utcnow();db.commit()
        with patch('sqlalchemy.orm.Session.commit',side_effect=RuntimeError('temporary failure')):
            with self.assertRaisesRegex(RuntimeError,'temporary failure'):self.api('DELETE',f'/posts/{pid}')
        data=self.api('GET',f'/posts/{pid}')
        self.assertEqual((data['content'],data['likes_count'],data['comments_count']),('临时动态',1,1))
        self.assertEqual(data['comments'][0]['content'],'保留留言')
        self.assertEqual(len(self.api('GET','/notifications')['items']),1)
        self.api('DELETE',f'/posts/{pid}')
        self.assertEqual(self.api('GET','/notifications')['items'],[])

    def test_like_repeat_unlike_and_multiple_people_count(self):
        pid=self.post()['id'];path=f'/posts/{pid}/like'
        for who,count in [(2,1),(2,1),(3,2),(1,3)]:self.assertEqual(self.api('POST',path,who)['likes_count'],count)
        for who,count in [(2,2),(2,2),(3,1),(1,0)]:self.assertEqual(self.api('DELETE',path,who)['likes_count'],count)
        self.assertEqual(self.api('GET',f'/posts/{pid}')['likes_count'],0)

    def test_own_comment_still_deletable_after_author_blocks(self):
        pid=self.post()['id'];cid=self.api('POST',f'/posts/{pid}/comments',2,json={'content':'本人留言'})['id']
        self.api('PUT','/social/users/2/block')
        self.api('DELETE',f'/posts/{pid}/comments/{cid}',2)
        with self.Session() as db:self.assertEqual(db.get(PostComment,cid).content,'')

    def test_like_and_unchanged_save_do_not_mark_content_as_edited(self):
        post=self.post();pid=post['id'];stamp=post['updated_at']
        self.api('POST',f'/posts/{pid}/like',2)
        self.api('DELETE',f'/posts/{pid}/like',2)
        self.assertEqual(self.api('GET',f'/posts/{pid}')['updated_at'],stamp)
        self.assertEqual(self.api('PUT',f'/posts/{pid}',json={'content':'临时动态'})['updated_at'],stamp)
        edited=self.api('PUT',f'/posts/{pid}',json={'content':'真正修改正文'})
        self.assertNotEqual(edited['updated_at'],stamp)
        self.api('POST',f'/posts/{pid}/like',3)
        self.assertEqual(self.api('GET',f'/posts/{pid}')['updated_at'],edited['updated_at'])
