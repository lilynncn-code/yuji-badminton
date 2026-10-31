"""Game drafts, bounded lists and retries use only temporary accounts."""
import time
import unittest
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from sqlalchemy import create_engine,inspect,text
import test_app_flows as flows
from app.models.game import Game,GameMember
from app.models.user import User
from app.services.account_deletion import delete_account_data
from app.db.init_db import ensure_game_columns


class GamePageChecks(unittest.TestCase):
    setUp=flows.AppFlows.setUp
    tearDown=flows.AppFlows.tearDown
    api=flows.AppFlows.api

    def payload(self,**extra):
        return {'title':'临时周末球局','city':'上海','venue':'临时检查场地','starts_at':(datetime.utcnow()+timedelta(days=2)).replace(microsecond=0).isoformat()+'Z','capacity':4,**extra}

    def test_create_retries_match_normalized_content_and_never_restore_cancelled_game(self):
        payload=self.payload(request_key='game-create-check')
        first=self.api('POST','/games',json=payload)
        normalized={**payload,'title':' '+payload['title']+' ','starts_at':datetime.fromisoformat(payload['starts_at'].replace('Z','+00:00')).astimezone(timezone(timedelta(hours=8))).isoformat()}
        self.assertEqual(self.api('POST','/games',json=normalized)['id'],first['id'])
        self.api('POST','/games',status=409,json={**payload,'capacity':5})
        other=self.api('POST','/games',2,json=payload)
        self.assertNotEqual(first['id'],other['id'])
        self.api('POST',f"/games/{first['id']}/cancel")
        cancelled=self.api('POST','/games',json=payload)
        self.assertEqual((cancelled['id'],cancelled['status']),(first['id'],'cancelled'))
        class Later(datetime):
            @classmethod
            def utcnow(cls):return datetime.utcnow()+timedelta(days=3)
        with patch('app.api.routes.games.datetime',Later):
            self.assertEqual(self.api('POST','/games',json=payload)['id'],first['id'])
        with self.Session() as db:
            self.assertEqual(db.query(Game).count(),2)
            self.assertEqual(db.query(GameMember).filter_by(game_id=first['id']).count(),1)
        self.api('POST','/games',status=400,json=self.payload(title=' a'))
        self.api('POST','/games',status=422,json=self.payload(request_key='bad key!'))

    def test_failed_create_keeps_no_game_or_member_and_can_retry(self):
        payload=self.payload(request_key='failed-game-save')
        with self.Session() as db:db.get(User,1).last_active_at=datetime.utcnow();db.commit()
        with patch('sqlalchemy.orm.Session.commit',side_effect=RuntimeError('temporary save failure')):
            with self.assertRaises(RuntimeError):self.api('POST','/games',json=payload)
        with self.Session() as db:
            self.assertEqual(db.query(Game).count(),0);self.assertEqual(db.query(GameMember).count(),0)
        self.assertEqual(self.api('POST','/games',json=payload)['count'],1)

    def seed(self,count=105):
        start=datetime.utcnow()+timedelta(days=2)
        with self.Session() as db:
            games=[Game(host_id=1,title=f'临时球局{i}',city='上海',venue='临时场地',starts_at=start,duration_minutes=60,capacity=4) for i in range(count)]
            db.add_all(games);db.flush();ids=[g.id for g in games]
            db.add_all([GameMember(game_id=i,user_id=1) for i in ids]);db.commit()
        return ids

    def test_long_list_equal_times_new_insert_and_cancellation_keep_position(self):
        ids=self.seed();first=self.api('GET','/games?city=上海')
        self.assertEqual([g['id'] for g in first['items']],ids[:20]);self.assertEqual(first['total'],105)
        # A new earlier game cannot push an already displayed record into a later page.
        inserted=self.api('POST','/games',2,json=self.payload(starts_at=(datetime.utcnow()+timedelta(days=1)).isoformat()+'Z'))
        self.api('POST',f'/games/{ids[25]}/cancel')
        seen=[g['id'] for g in first['items']];cursor=first['next_cursor']
        while cursor:
            more=self.api('GET','/games',params={'city':'上海','cursor':cursor})
            seen.extend(g['id'] for g in more['items']);cursor=more['next_cursor']
        self.assertEqual(seen,[i for i in ids if i!=ids[25]])
        self.assertEqual(len(seen),len(set(seen)));self.assertNotIn(inserted['id'],seen)
        self.assertEqual(self.api('GET','/games?city=上海')['items'][0]['id'],inserted['id'])
        mine=[];cursor=''
        while True:
            page=self.api('GET','/games',params={'mine':True,'cursor':cursor or None})
            mine.extend(g['id'] for g in page['items'])
            if not page['has_more']:break
            cursor=page['next_cursor']
        self.assertEqual(mine,ids)
        self.api('GET','/games?limit=101',status=422)

    def test_position_scope_tampering_and_expiry_are_rejected(self):
        self.seed(3);cursor=self.api('GET','/games?city=上海&limit=1')['next_cursor']
        for params in ({'city':'北京','cursor':cursor},{'city':'上海','mine':True,'cursor':cursor},{'city':'上海','cursor':cursor+'x'}):
            self.api('GET','/games',status=400,params=params)
        self.api('GET','/games',2,400,params={'city':'上海','cursor':cursor})
        with patch('app.services.game_pages.time.time',return_value=time.time()+1801):
            self.api('GET','/games',status=400,params={'city':'上海','cursor':cursor})
        self.api('GET','/games?cursor=missing',status=400)
        self.api('GET','/games',0,401)

    def test_blocked_outsider_cannot_read_but_joined_person_can_see_cancellation(self):
        game=self.api('POST','/games',json=self.payload())['id'];path=f'/games/{game}'
        self.api('PUT',path+'/join',2)
        self.api('PUT','/social/users/1/block',3)
        self.assertEqual(self.api('GET','/games',3)['items'],[])
        self.api('GET',path,3,404)
        self.api('DELETE',path+'/join',3,404)
        self.api('PUT',path+'/join',3,403)
        self.api('PUT','/social/users/1/block',2)
        self.assertEqual(self.api('GET',path,2)['count'],2)
        self.api('POST',path+'/cancel')
        self.assertEqual(self.api('GET',path,2)['status'],'cancelled')
        self.assertEqual(self.api('GET','/games?mine=true',2)['items'][0]['status'],'cancelled')
        self.api('DELETE',path+'/join',2)
        self.api('GET',path,2,404)
        self.api('DELETE',path+'/join',2,404)
        self.api('DELETE','/social/users/1/block',3)
        self.assertEqual(self.api('GET',path,3)['status'],'cancelled')

    def test_old_table_upgrade_keeps_rows_and_is_repeatable(self):
        engine=create_engine('sqlite://')
        try:
            with engine.begin() as conn:
                conn.execute(text('CREATE TABLE games (id INTEGER PRIMARY KEY,host_id INTEGER,title VARCHAR(80))'))
                conn.execute(text("INSERT INTO games VALUES (1,1,'existing game')"))
            ensure_game_columns(engine);ensure_game_columns(engine)
            with engine.begin() as conn:
                self.assertEqual(conn.execute(text('SELECT title,request_key FROM games')).all(),[('existing game',None)])
            self.assertIn('uq_game_host_request',{i['name'] for i in inspect(engine).get_indexes('games')})
        finally:engine.dispose()

    def test_account_deletion_keeps_other_game_and_removes_own_retry_record(self):
        first=self.api('POST','/games',json=self.payload(request_key='account-game-one'))['id']
        second=self.api('POST','/games',2,json=self.payload(request_key='account-game-two'))['id']
        self.api('PUT',f'/games/{second}/join')
        with self.Session() as db:
            db.execute(text('PRAGMA foreign_keys=ON'));delete_account_data(db.get(User,1),db)
        self.api('GET',f'/games/{first}',2,404)
        other=self.api('GET',f'/games/{second}',2)
        self.assertEqual(other['count'],1);self.assertEqual(other['host_id'],2)
        with self.Session() as db:self.assertEqual([g.request_key for g in db.query(Game)],['account-game-two'])
