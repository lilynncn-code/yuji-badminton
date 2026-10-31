"""Full lists stay readable when earlier rows are inserted or removed."""
from datetime import datetime
from unittest.mock import patch
from urllib.parse import urlencode
import unittest
import test_app_flows as flows
from app.models.post import Post
from app.models.clinic import ClinicQuestion


class FeedPageChecks(unittest.TestCase):
    setUp=flows.AppFlows.setUp
    tearDown=flows.AppFlows.tearDown
    api=flows.AppFlows.api

    def seed(self,model):
        with self.Session() as db:
            for i in range(105):
                row=model(user_id=1,content=f'临时内容{i:03}',created_at=datetime(2026,10,1,12))
                if model is ClinicQuestion:row.title=f'临时问题{i:03}'
                db.add(row)
            db.commit()
            return [r.id for r in db.query(model).order_by(model.id.desc())]

    def test_post_list_reads_all_original_rows_despite_insert_and_delete(self):
        ids=self.seed(Post);first=self.api('GET','/posts');seen=[p['id'] for p in first['items']]
        new=self.api('POST','/posts',json={'content':'翻看期间新动态'})['id']
        self.api('DELETE',f'/posts/{seen[0]}')
        page=first
        while page['has_more']:
            page=self.api('GET','/posts?'+urlencode({'cursor':page['next_cursor']}));seen.extend(p['id'] for p in page['items'])
        self.assertEqual(seen,ids);self.assertEqual(len(set(seen)),105);self.assertNotIn(new,seen)
        self.assertEqual(self.api('GET','/posts')['items'][0]['id'],new)

    def test_question_list_reads_all_original_rows_despite_insert_and_delete(self):
        ids=self.seed(ClinicQuestion);first=self.api('GET','/clinic');seen=[p['id'] for p in first['items']]
        new=self.api('POST','/clinic',json={'title':'新问题','content':'翻看期间新问题'})['id']
        self.api('DELETE',f'/clinic/{seen[0]}')
        page=first
        while page['has_more']:
            page=self.api('GET','/clinic?'+urlencode({'cursor':page['next_cursor']}));seen.extend(p['id'] for p in page['items'])
        self.assertEqual(seen,ids);self.assertEqual(len(set(seen)),105);self.assertNotIn(new,seen)
        self.assertEqual(self.api('GET','/clinic')['items'][0]['id'],new)

    def test_positions_are_private_bound_to_filters_and_expire(self):
        self.seed(Post);self.seed(ClinicQuestion)
        for path in ('/posts','/clinic'):
            with self.subTest(path=path):
                cursor=self.api('GET',path)['next_cursor'];encoded=urlencode({'cursor':cursor})
                self.api('GET',path+'?'+encoded,2,400)
                for changed in ('mine=true','keyword=变化','following=true' if path=='/posts' else 'saved=true'):
                    self.api('GET',path+'?'+encoded+'&'+changed,status=400)
                self.api('GET',path+'?cursor='+cursor[:-1]+('a' if cursor[-1]!='a' else 'b'),status=400)
                self.api('GET',path+'?page=2',status=400)
                with patch('app.services.feed_pages.time',return_value=9999999999):self.api('GET',path+'?'+encoded,status=400)
        post_cursor=self.api('GET','/posts')['next_cursor'];self.api('GET','/clinic?'+urlencode({'cursor':post_cursor}),status=400)

    def test_mine_following_saved_search_and_blocked_results(self):
        own=self.api('POST','/posts',json={'content':'本人%内容'})['id']
        other=self.api('POST','/posts',2,json={'content':'其他普通内容'})['id']
        self.assertEqual([r['id'] for r in self.api('GET','/posts?keyword=%25')['items']],[own])
        self.api('PUT','/social/users/2/follow')
        self.assertEqual([r['id'] for r in self.api('GET','/posts?following=true')['items']],[other])
        self.assertEqual([r['id'] for r in self.api('GET','/posts?mine=true')['items']],[own])
        q=self.api('POST','/clinic',2,json={'title':'带%问题','content':'用于检查字面搜索'})['id']
        self.api('PUT',f'/social/favorites/clinic/{q}')
        self.assertEqual([r['id'] for r in self.api('GET','/clinic?saved=true')['items']],[q])
        self.assertEqual([r['id'] for r in self.api('GET','/clinic?keyword=%25')['items']],[q])
        self.api('PUT','/social/users/2/block')
        self.assertEqual(self.api('GET','/posts?following=true')['items'],[])
        self.assertEqual(self.api('GET','/clinic?saved=true')['items'],[])
