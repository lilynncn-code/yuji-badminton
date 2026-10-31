"""Complete relationship lists and state checks using temporary accounts only."""
import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch
import test_app_flows as flows
from app.models.user import User
from app.models.social import Follow, Block, PeopleRevision
from app.services.account_deletion import delete_account_data


class PeoplePageChecks(unittest.TestCase):
    setUp=flows.AppFlows.setUp
    tearDown=flows.AppFlows.tearDown
    api=flows.AppFlows.api

    def seed(self,count=105,kind='following'):
        with self.Session() as db:
            password=db.get(User,2).password_hash
            users=[User(id=i,username=f'people{i}',name=f'临时球友{i:03}',phone=f'137{i:08}',password_hash=password,city='上海') for i in range(4,count+4)]
            db.add_all(users);db.flush()
            model=Block if kind=='blocked' else Follow
            pairs=[{'user_id':u.id,'target_id':1} if kind=='followers' else {'user_id':1,'target_id':u.id} for u in users]
            db.add_all([model(**pair,created_at=datetime(2026,10,1,12)) for pair in pairs]);db.commit()
        return list(range(count+3,3,-1))

    def test_all_three_lists_can_be_read_completely_without_duplicate_names_or_times(self):
        for kind in ('following','followers','blocked'):
            expected=self.seed(105,kind) if kind=='following' else None
            if kind!='following':
                with self.Session() as db:
                    model=Follow if kind=='followers' else Block
                    db.add_all([model(user_id=i if kind=='followers' else 1,target_id=1 if kind=='followers' else i,created_at=datetime(2026,10,1,12)) for i in range(4,109)]);db.commit()
            seen=[];cursor=''
            while True:
                page=self.api('GET','/social/people',params={'kind':kind,'cursor':cursor or None})
                self.assertEqual(page['total'],105);self.assertLessEqual(len(page['items']),30)
                seen.extend(u['id'] for u in page['items']);cursor=page['next_cursor']
                if not page['has_more']:break
            self.assertEqual(seen,list(range(108,3,-1)));self.assertEqual(len(seen),len(set(seen)))
            # Remove the test blocks before the next kind's list is read.
            if kind=='blocked':
                with self.Session() as db:db.query(Block).delete();db.commit()

    def test_rename_keeps_position_and_relationship_changes_require_refresh(self):
        ids=self.seed();first=self.api('GET','/social/people')
        self.assertEqual([u['id'] for u in first['items']],ids[:30])
        with self.Session() as db:db.get(User,ids[50]).name='AAA改名后的球友';db.commit()
        seen=[u['id'] for u in first['items']];cursor=first['next_cursor']
        while cursor:
            page=self.api('GET','/social/people',params={'cursor':cursor})
            seen.extend(u['id'] for u in page['items']);cursor=page['next_cursor']
        self.assertEqual(seen,ids);self.assertEqual(len(seen),len(set(seen)))
        for method,path in (('DELETE',f'/social/users/{ids[0]}/follow'),('DELETE',f'/social/users/{ids[40]}/follow'),('PUT','/social/users/2/follow')):
            before=self.api('GET','/social/people')
            self.api(method,path)
            self.api('GET','/social/people',status=400,params={'cursor':before['next_cursor']})
            self.assertNotEqual(self.api('GET','/social/people/status')['revision'],before['revision'])
        before=self.api('GET','/social/people')
        with self.Session() as db:delete_account_data(db.get(User,ids[60]),db)
        self.api('GET','/social/people',status=400,params={'cursor':before['next_cursor']})
        fresh=self.api('GET','/social/people')
        self.assertEqual(fresh['items'][0]['id'],2);self.assertEqual(fresh['total'],103)
        self.assertEqual(self.api('GET','/profile/me')['following'],fresh['total'])
        with self.Session() as db:self.assertIsNone(db.get(PeopleRevision,ids[60]))

    def test_cursor_is_bound_to_owner_kind_and_expiry_and_old_page_reads_are_rejected(self):
        self.seed(3);cursor=self.api('GET','/social/people?limit=1')['next_cursor']
        self.api('GET','/social/people',2,400,params={'cursor':cursor})
        self.api('GET','/social/people',status=400,params={'kind':'followers','cursor':cursor})
        self.api('GET','/social/people',status=400,params={'cursor':cursor+'x'})
        self.api('GET','/social/people?cursor=invalid',status=400)
        with patch('app.services.people_pages.time.time',return_value=time.time()+1801):self.api('GET','/social/people',status=400,params={'cursor':cursor})
        self.api('GET','/social/people?page=2',status=400)
        for suffix in ('limit=0','limit=101','kind=invalid','page=0','cursor='+'x'*2001):self.api('GET','/social/people?'+suffix,status=422)
        self.api('GET','/social/people',0,401)

    def test_block_visibility_and_profile_counts_use_the_same_visible_people(self):
        self.seed(3)
        with self.Session() as db:
            db.add_all([Follow(user_id=i,target_id=1) for i in (4,5,6)])
            # Legacy inconsistent rows must not appear in visible counts.
            db.add_all([Block(user_id=1,target_id=4),Block(user_id=5,target_id=1)]);db.commit()
        for kind in ('following','followers'):
            page=self.api('GET','/social/people',params={'kind':kind})
            self.assertEqual(page['total'],1);self.assertEqual([u['id'] for u in page['items']],[6])
        profile=self.api('GET','/profile/me');self.assertEqual((profile['following'],profile['followers']),(1,1))
        self.assertEqual([u['id'] for u in self.api('GET','/social/people?kind=blocked')['items']],[4])
        self.assertEqual(self.api('GET','/social/users/4'),{'following':False,'blocked':True,'can_interact':False})
        self.assertEqual(self.api('GET','/social/users/5'),{'following':False,'blocked':False,'can_interact':False})
        self.assertFalse(self.api('GET','/social/users/1')['can_interact'])
        self.api('PUT','/social/users/5/follow',status=403)

    def test_follow_and_block_retries_preserve_state_and_unblock_does_not_restore_follow(self):
        for who,target in ((1,2),(2,1)):
            for _ in range(2):self.api('PUT',f'/social/users/{target}/follow',who)
        self.assertTrue(self.api('GET','/social/users/2')['following'])
        revision=self.api('GET','/social/people/status')['revision']
        self.api('PUT','/social/users/2/follow')
        self.assertEqual(self.api('GET','/social/people/status')['revision'],revision)
        for _ in range(2):self.api('PUT','/social/users/2/block')
        self.assertEqual(self.api('GET','/profile/me')['following'],0)
        self.assertEqual(self.api('GET','/profile/me')['followers'],0)
        self.api('PUT','/social/users/1/follow',2,403)
        self.api('PUT','/social/users/1/block',2)
        for _ in range(2):self.api('DELETE','/social/users/2/block')
        self.assertFalse(self.api('GET','/social/users/2')['can_interact'])
        self.api('DELETE','/social/users/1/block',2)
        self.assertEqual(self.api('GET','/social/users/2'),{'following':False,'blocked':False,'can_interact':True})
        for action in ('follow','block'):
            self.api('PUT','/social/users/1/'+action,status=400)
            self.api('PUT','/social/users/999/'+action,status=404)
            self.api('DELETE','/social/users/999/'+action)

    def test_failed_relationship_save_leaves_previous_state_and_counts(self):
        self.api('PUT','/social/users/2/follow')
        with self.Session() as db:db.get(User,1).last_active_at=datetime.utcnow();db.commit()
        with patch('sqlalchemy.orm.Session.commit',side_effect=RuntimeError('temporary save failure')):
            with self.assertRaises(RuntimeError):self.api('PUT','/social/users/2/block')
            with self.assertRaises(RuntimeError):self.api('DELETE','/social/users/2/follow')
        self.assertEqual(self.api('GET','/social/users/2'),{'following':True,'blocked':False,'can_interact':True})
        self.assertEqual(self.api('GET','/profile/me')['following'],1)

    def test_deleted_last_relationship_id_reuse_cannot_restore_old_list(self):
        self.seed(3);first=self.api('GET','/social/people?limit=1');cursor=first['next_cursor']
        with self.Session() as db:db.query(Follow).filter_by(user_id=1).delete();db.commit()
        self.api('PUT','/social/users/2/follow')
        self.api('GET','/social/people',status=400,params={'cursor':cursor})
        self.assertEqual(self.api('GET','/social/people')['items'][0]['id'],2)


if __name__=='__main__':unittest.main()
