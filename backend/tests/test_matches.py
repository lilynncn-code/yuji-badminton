"""Isolated competition imports, public reads, failure preservation and scheduling."""
import copy
import io
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app import models
from app.api.routes.content import router
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.models.content import Event, Match, MatchSyncState
from app.services.match_scheduler import MatchScheduler
from app.services.match_sync import _source_payload, sync_matches


def snapshot():
    now = datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'
    return dict(source_updated_at=now, source_url='https://example.com/results', complete=True,
        events=[dict(id='e1', name='检查赛事甲', start_date='2026-10-20', end_date='2026-10-25', status='ongoing', location='检查场地甲'),
                dict(id='e2', name='检查赛事乙', start_date='2026-10-26', end_date='2026-11-01', status='ongoing')],
        matches=[dict(id='e1-ms-final', event_id='e1', discipline='男单', round='决赛', player1='选手甲', player2='选手乙', scheduled_at='2026-10-25T18:00:00+08:00', status='finished', winner='选手甲', score1='21 21', score2='19 18', score_text='21-19, 21-18'),
                 dict(id='e2-ws-semi', event_id='e2', discipline='女单', round='半决赛', player1='选手丙', player2='选手丁', scheduled_at='2026-10-31T10:00:00Z', status='live', score_text='11-10')])


class MatchTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        app = FastAPI(); app.include_router(router)
        def override_db():
            with self.Session() as db:
                yield db
        app.dependency_overrides[get_db] = override_db
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close(); self.engine.dispose()

    def sync(self, data=None, **kwargs):
        with self.Session() as db:
            return sync_matches(db, data, **kwargs)

    def test_import_list_limit_stable_ids_event_choices_and_detail(self):
        self.assertTrue(self.sync(snapshot())['ok'])
        response = self.client.get('/content/matches?limit=1')
        self.assertEqual(response.headers['cache-control'], 'no-store')
        data = response.json()
        self.assertEqual([event['id'] for event in data['events']], ['e2', 'e1'])
        self.assertEqual(data['items'][0]['id'], 'e2-ws-semi')
        detail = self.client.get('/content/matches/e2-ws-semi').json()
        self.assertEqual(data['items'][0], detail['item'])
        self.assertFalse(detail['sync']['using_old_data'])
        data = self.client.get('/content/matches?event_id=e1').json()
        self.assertEqual(len(data['items']), 1)
        self.assertEqual(data['items'][0]['scheduled_at'], '2026-10-25T10:00:00')

    def test_new_score_new_event_and_source_removal_replace_together(self):
        data = snapshot(); self.sync(data)
        data['matches'][1]['score_text'] = '21-19'
        data['matches'][1]['status'] = 'finished'
        data['matches'][1]['winner'] = '选手丙'
        data['matches'] = data['matches'][1:]
        data['events'][1]['name'] = '已更新赛事名称'
        self.assertTrue(self.sync(data)['ok'])
        detail = self.client.get('/content/matches/e2-ws-semi').json()['item']
        self.assertEqual((detail['score_text'], detail['status'], detail['event_name']), ('21-19', 'finished', '已更新赛事名称'))
        self.assertEqual(self.client.get('/content/matches/e1-ms-final').status_code, 404)

    def test_cancelled_match_keeps_identity_without_claiming_winner(self):
        data = snapshot(); data['matches'][1].update(status='cancelled', score_text='')
        self.assertTrue(self.sync(data)['ok'])
        item = self.client.get('/content/matches/e2-ws-semi').json()['item']
        self.assertEqual((item['id'], item['status'], item['winner']), ('e2-ws-semi', 'cancelled', ''))

    def test_empty_or_partial_or_invalid_import_never_erases_last_success(self):
        self.sync(snapshot())
        mutations = [lambda d: d.update(matches=[]), lambda d: d.update(events=[]), lambda d: d.update(complete=False),
            lambda d: d['matches'].append(copy.deepcopy(d['matches'][0])),
            lambda d: d['matches'][1].update(scheduled_at='not-a-date'),
            lambda d: d['matches'][1].update(event_id='missing'),
            lambda d: d['matches'][1].update(winner='不存在的选手'),
            lambda d: d['matches'][1].update(player1='a' * 201),
            lambda d: d['events'][1].update(end_date='2026-10-01')]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                data = snapshot(); mutate(data)
                self.assertFalse(self.sync(data)['ok'])
                result = self.client.get('/content/matches').json()
                self.assertEqual(len(result['items']), 2)
                self.assertTrue(result['sync']['using_old_data'])
                self.assertTrue(result['sync']['last_error'])
                self.assertEqual(self.client.get('/content/matches/e2-ws-semi').json()['item']['score_text'], '11-10')

    def test_save_failure_rolls_back_event_name_matches_and_success_stamp(self):
        self.sync(snapshot())
        before = self.client.get('/content/matches').json()
        data = snapshot(); data['events'][1]['name'] = '不能保存的名称'; data['matches'][1]['score_text'] = '99-99'
        with self.Session() as db:
            commit = db.commit
            with patch.object(db, 'commit', side_effect=[RuntimeError('secret db password'), None]):
                result = sync_matches(db, data)
            # The mocked second commit is only for the failure record.
            commit()
        self.assertFalse(result['ok'])
        after = self.client.get('/content/matches').json()
        self.assertEqual(after['items'], before['items'])
        self.assertEqual(after['events'], before['events'])
        self.assertEqual(after['sync']['latest_updated_at'], before['sync']['latest_updated_at'])
        self.assertNotIn('secret', after['sync']['last_error'])

    def test_older_source_snapshot_rejected_and_failure_clears_on_recovery(self):
        data = snapshot(); self.sync(data)
        old = copy.deepcopy(data); old['source_updated_at'] = '2020-01-01T00:00:00Z'
        self.assertFalse(self.sync(old)['ok'])
        self.assertTrue(self.sync(data)['ok'])
        self.assertEqual(self.client.get('/content/matches').json()['sync']['last_error'], '')

    def test_source_403_does_not_expose_token_or_clear_content(self):
        self.sync(snapshot())
        with patch.object(settings, 'match_source_file', ''), patch.object(settings, 'match_source_url', 'https://example.com/private?token=PRIVATE'), patch('app.services.match_sync.urlopen', side_effect=HTTPError('https://example.com/?token=PRIVATE', 403, 'PRIVATE', {}, None)):
            self.assertFalse(self.sync()['ok'])
        data = self.client.get('/content/matches').json()
        self.assertEqual(len(data['items']), 2)
        self.assertIn('403', data['sync']['last_error'])
        self.assertNotIn('PRIVATE', json.dumps(data))

    def test_authorized_file_and_private_source_header(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'matches.json'; path.write_text(json.dumps(snapshot()))
            self.assertTrue(self.sync(file_path=str(path))['ok'])
        response = io.BytesIO(json.dumps(snapshot()).encode())
        with patch.object(settings, 'match_source_file', ''), patch.object(settings, 'match_source_url', 'https://example.com/private'), patch.object(settings, 'match_source_token', 'PRIVATE'), patch('app.services.match_sync.urlopen', return_value=response) as fetch:
            self.assertEqual(len(_source_payload()['matches']), 2)
            self.assertEqual(fetch.call_args.args[0].get_header('Authorization'), 'Bearer PRIVATE')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'broken.json'; path.write_text('broken')
            self.assertFalse(self.sync(file_path=str(path))['ok'])
        self.assertEqual(len(self.client.get('/content/matches').json()['items']), 2)

    def test_missing_source_empty_install_is_honest_and_invalid_id_is_404(self):
        data = self.client.get('/content/matches').json()
        self.assertEqual(data['items'], [])
        self.assertTrue(data['sync']['last_error'])
        self.assertTrue(data['sync']['using_old_data'])
        self.assertEqual(self.client.get('/content/matches/no-such-id').status_code, 404)
        with patch.object(settings, 'match_source_file', ''), patch.object(settings, 'match_source_url', ''):
            self.assertFalse(self.sync()['ok'])

    def test_scheduler_skips_recent_attempt_and_runs_when_fifteen_minutes_due(self):
        self.sync(snapshot())
        scheduler = MatchScheduler(self.Session)
        with patch('app.services.match_sync._source_payload', return_value=snapshot()) as fetch:
            self.assertTrue(scheduler.check()['skipped']); fetch.assert_not_called()
            with self.Session() as db:
                db.get(MatchSyncState, 'matches').last_attempt_at = datetime.utcnow() - timedelta(minutes=16); db.commit()
            self.assertTrue(scheduler.check()['ok']); fetch.assert_called_once()
        with patch.object(scheduler, 'check') as check, patch.object(scheduler.stopped, 'wait', return_value=True) as wait:
            scheduler._run(); check.assert_called_once(); wait.assert_called_once_with(900)

    def test_long_gap_marks_saved_content_old_even_if_last_error_empty(self):
        self.sync(snapshot())
        with self.Session() as db:
            db.get(MatchSyncState, 'matches').last_success_at = datetime.utcnow() - timedelta(hours=1); db.commit()
        self.assertTrue(self.client.get('/content/matches').json()['sync']['using_old_data'])

    def test_recent_events_are_independent_of_match_limit_and_ties_are_stable(self):
        data = snapshot()
        for number in range(3, 8):
            data['events'].append(dict(id=f'e{number}', name=f'检查赛事{number}', start_date=f'2026-11-{number:02}', end_date=f'2026-11-{number:02}'))
            data['matches'].append(dict(id=f'm{number}', event_id=f'e{number}', player1='甲', player2='乙', discipline='男单', round='首轮', scheduled_at=f'2026-11-{number:02}T10:00:00Z'))
        self.sync(data)
        result = self.client.get('/content/matches?limit=1').json()
        self.assertEqual(len(result['events']), 5)
        self.assertEqual(len(result['items']), 1)
        all_matches = self.client.get('/content/matches').json()['items']
        self.assertEqual(len(all_matches), 5)
        self.assertEqual(all_matches, self.client.get('/content/matches').json()['items'])


if __name__ == '__main__':
    unittest.main()
