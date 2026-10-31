from datetime import date,timedelta
import unittest
from unittest.mock import patch
import test_app_flows as flows
from app.models.training import TrainingRecord
from app.services import daily_workout


class DailyPracticeChecks(unittest.TestCase):
    setUp=flows.AppFlows.setUp
    tearDown=flows.AppFlows.tearDown
    api=flows.AppFlows.api

    def test_sequence_actual_duration_counts_retry_and_account_isolation(self):
        day=date(2026,10,12)
        with patch.object(daily_workout,'today',return_value=day):
            self.api('GET','/training/daily',0,401)
            plan=self.api('GET','/training/daily')
            self.assertEqual((len(plan['steps']),plan['total_seconds']),(4,300))
            self.assertTrue(all(not s['completed'] for s in plan['steps']))
            path=f'/training/daily/{plan["day"]}'
            self.api('POST',path+'/1',status=400,json={'duration_seconds':90,'reps':10})
            self.api('POST',path+'/0',status=400,json={'duration_seconds':59,'reps':6})
            self.api('POST',path+'/0',status=400,json={'duration_seconds':60,'reps':5})
            self.api('POST',path+'/4',status=404,json={'duration_seconds':60,'reps':6})
            self.api('POST','/training',status=400,json={'training_type':'不得冒用每日编号','duration_seconds':60,'score':100,'reps':6,'request_key':daily_workout.key(day,0)})
            saved=[]
            for step in plan['steps']:
                payload={'duration_seconds':step['seconds'],'reps':step['reps']}
                record=self.api('POST',path+f'/{step["index"]}',json=payload)
                again=self.api('POST',path+f'/{step["index"]}',json={**payload,'reps':payload['reps']+1})
                self.assertEqual(record['id'],again['id'])
                self.assertEqual(again['reps'],payload['reps'],'retry must preserve the original confirmed count')
                self.assertEqual(record['recording_method'],'manual')
                self.assertIsNone(record['task_id'])
                saved.append(record['id'])
            self.assertTrue(all(s['completed'] for s in self.api('GET','/training/daily')['steps']))
            self.assertTrue(all(not s['completed'] for s in self.api('GET','/training/daily',2)['steps']))
            self.assertEqual(self.api('GET','/training/summary')['sessions'],4)
            self.assertEqual(self.api('GET','/training/progress')['xp'],0)
            self.assertEqual(len(self.api('GET','/training')['records']),4)

    def test_new_date_has_new_arrangement_and_old_retry_cannot_create_backdated_practice(self):
        day=date(2026,10,12)
        with patch.object(daily_workout,'today',return_value=day):
            first=self.api('POST',f'/training/daily/{day}/0',json={'duration_seconds':60,'reps':6})
        with patch.object(daily_workout,'today',return_value=day+timedelta(days=1)):
            current=self.api('GET','/training/daily')
            self.assertEqual(current['day'],'2026-10-13')
            self.assertTrue(all(not s['completed'] for s in current['steps']))
            self.assertNotEqual(current['steps'][1]['title'],daily_workout.plan(day)['steps'][1]['title'])
            self.assertEqual(self.api('POST',f'/training/daily/{day}/0',json={'duration_seconds':60,'reps':6})['id'],first['id'])
            self.api('POST',f'/training/daily/{day}/1',status=409,json={'duration_seconds':90,'reps':8})
            self.api('POST',f'/training/daily/{day}/0',2,409,json={'duration_seconds':60,'reps':6})
            self.api('POST',f'/training/daily/{current["day"]}/0',json={'duration_seconds':60,'reps':6})
        with self.Session() as db:self.assertEqual(db.query(TrainingRecord).count(),2)
