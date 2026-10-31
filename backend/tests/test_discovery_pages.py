"""Score-ordered players must not silently move between list pages."""
from datetime import datetime
from unittest.mock import patch
from urllib.parse import urlencode
import unittest
import test_app_flows as flows
from app.models.user import User
from app.models.training import TrainingRecord


class DiscoveryPageChecks(unittest.TestCase):
    setUp=flows.AppFlows.setUp
    tearDown=flows.AppFlows.tearDown
    api=flows.AppFlows.api

    def seed(self):
        with self.Session() as db:
            for i in range(4,109):db.add(User(id=i,username=f'discovery{i}',phone=f'137{i:08}',name=f'临时球友{i:03}',password_hash='unused',city='上海',club='训练双打'))
            db.commit()

    def test_read_every_player_when_names_and_activity_change(self):
        self.seed();first=self.api('GET','/discovery/players');seen=[u['id'] for u in first['items']]
        with self.Session() as db:db.get(User,4).name='改名后的临时球友';db.get(User,4).last_active_at=datetime.utcnow();db.commit()
        page=first
        while page['has_more']:
            page=self.api('GET','/discovery/players?'+urlencode({'cursor':page['next_cursor']}));seen.extend(u['id'] for u in page['items'])
        self.assertEqual(seen,list(range(108,1,-1)));self.assertEqual(len(set(seen)),107)
        self.assertEqual(page['total'],107)

    def test_score_changes_invalidate_old_order_and_report_status(self):
        self.seed();first=self.api('GET','/discovery/players');cursor=first['next_cursor']
        with self.Session() as db:db.add(TrainingRecord(user_id=108,training_type='临时训练',duration_seconds=30,reps=3,score=50));db.commit()
        self.api('GET','/discovery/players?'+urlencode({'cursor':cursor}),status=400)
        status=self.api('GET','/discovery/players/status?'+urlencode({'revision':first['revision']}))
        self.assertTrue(status['changed']);self.assertEqual(status['items'],[])
        refreshed=self.api('GET','/discovery/players');self.assertEqual(refreshed['items'][0]['id'],107)
        with self.Session() as db:db.add(TrainingRecord(user_id=1,training_type='本人临时训练',duration_seconds=30,reps=3,score=50));db.commit()
        self.api('GET','/discovery/players?'+urlencode({'cursor':refreshed['next_cursor']}),status=400)
        final=self.api('GET','/discovery/players');self.assertEqual(final['items'][0]['id'],108);self.assertEqual(final['my_points'],50)

    def test_new_user_block_and_filtered_profile_changes_require_refresh(self):
        self.seed();first=self.api('GET','/discovery/players?mode=near')
        self.api('PUT','/social/users/108/block')
        self.api('GET','/discovery/players?mode=near&'+urlencode({'cursor':first['next_cursor']}),status=400)
        first=self.api('GET','/discovery/players?mode=near')
        with self.Session() as db:db.get(User,4).city='杭州';db.commit()
        self.api('GET','/discovery/players?mode=near&'+urlencode({'cursor':first['next_cursor']}),status=400)
        first=self.api('GET','/discovery/players')
        with self.Session() as db:db.add(User(username='newplayer',phone='13711111111',name='新临时球友',password_hash='unused'));db.commit()
        self.api('GET','/discovery/players?'+urlencode({'cursor':first['next_cursor']}),status=400)

    def test_positions_are_bound_to_owner_filters_and_expiry(self):
        self.seed();first=self.api('GET','/discovery/players');cursor=first['next_cursor'];encoded=urlencode({'cursor':cursor})
        self.api('GET','/discovery/players?'+encoded,2,400)
        for extra in ('mode=near','keyword=临时','city=上海'):
            self.api('GET','/discovery/players?'+encoded+'&'+extra,status=400)
        self.api('GET','/discovery/players?cursor='+cursor[:-1]+('a' if cursor[-1]!='a' else 'b'),status=400)
        self.api('GET','/discovery/players?page=2',status=400)
        with patch('app.services.discovery_pages.time',return_value=9999999999):self.api('GET','/discovery/players?'+encoded,status=400)

    def test_status_refreshes_only_visible_requested_players_and_chat_state(self):
        self.seed();first=self.api('GET','/discovery/players');query=urlencode({'revision':first['revision']})+'&ids=2&ids=1&ids=999999'
        state=self.api('GET','/discovery/players/status?'+query)
        self.assertFalse(state['changed']);self.assertEqual([u['id'] for u in state['items']],[2]);self.assertEqual(state['items'][0]['chat_state'],'none')
        chat=self.api('POST','/chat/requests',2,json={'receiver_id':1})['chat']['id']
        state=self.api('GET','/discovery/players/status?'+query);self.assertEqual(state['items'][0]['chat_state'],'review')
        self.api('POST',f'/chat/requests/{chat}/accept')
        state=self.api('GET','/discovery/players/status?'+query);self.assertEqual(state['items'][0]['chat_state'],'accepted')
        self.api('GET','/discovery/players/status?'+('&'.join('ids=2' for _ in range(101))),status=422)
