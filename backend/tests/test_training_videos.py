"""Retry and removal checks with isolated accounts and temporary video files."""
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
import test_app_flows as flows
from app.models.media import Media, TrainingVideoUpload
from app.models.training import TrainingRecord
from app.models.user import User
from app.models.account import AccountFileDeletion
from app.services.file_cleanup import cleanup_files
from app.services.account_deletion import delete_account_data


class TrainingVideoChecks(unittest.TestCase):
    setUp=flows.AppFlows.setUp
    tearDown=flows.AppFlows.tearDown
    api=flows.AppFlows.api

    def upload(self,key='video-retry-check',who=1,status=200,data=None):
        return self.api('POST','/media/upload-training-video',who,status,data={'request_key':key},files={'file':('recording.webm', data if data is not None else (Path(__file__).parent/'fixtures'/'recording.webm').read_bytes(),'video/webm')})

    def record(self):
        return self.api('POST','/training',json={'training_type':'本次临时训练','duration_seconds':30,'score':0,'reps':3})

    def test_same_send_reuses_file_rejects_changed_file_and_other_account(self):
        first=self.upload()
        with patch('app.api.routes.media.store_file',side_effect=AssertionError('must not rewrite')):
            self.assertEqual(self.upload(),first)
            self.upload(status=409,data=b'different video bytes')
        self.assertEqual(self.api('GET','/media/training-uploads/video-retry-check'),first)
        self.api('GET','/media/training-uploads/video-retry-check',2,404)
        other=self.upload(who=2)
        self.assertNotEqual(other['id'],first['id'])
        with self.Session() as db:self.assertEqual(db.query(TrainingVideoUpload).count(),2);self.assertEqual(db.query(Media).count(),2)
        self.upload(key='bad key!',status=400)

    def test_abandon_before_and_after_upload_never_restores_file(self):
        self.api('DELETE','/media/training-uploads/video-before-upload',status=204)
        self.upload(key='video-before-upload',status=410)
        self.api('GET','/media/training-uploads/video-before-upload',status=410)
        first=self.upload()
        for _ in range(2):self.api('DELETE','/media/training-uploads/video-retry-check',status=204)
        self.upload(status=410)
        self.api('GET',first['url'],status=404)
        self.assertEqual(list((Path(self.folder.name)/'private').glob('*')),[])
        # A cancellation committed during file preparation wins over the old upload.
        from app.api.routes.media import store_file
        async def prepare_then_cancel(file,*args,**kwargs):
            name=await store_file(file,*args,**kwargs)
            with self.Session() as db:
                db.add(TrainingVideoUpload(user_id=1,request_key='video-racing-cancel',cancelled=True));db.commit()
            return name
        with patch('app.api.routes.media.store_file',side_effect=prepare_then_cancel):self.upload(key='video-racing-cancel',status=410)
        self.assertEqual(list((Path(self.folder.name)/'private').glob('*')),[])

    def test_delete_keeps_file_on_save_failure_and_cleanup_can_retry(self):
        clip=self.upload();record=self.record();path=Path(self.folder.name)/'private'
        self.api('PATCH',f"/training/{record['id']}/media",json={'media_id':clip['id']})
        with patch('sqlalchemy.orm.Session.commit',side_effect=RuntimeError('save unavailable')):
            with self.assertRaises(RuntimeError):self.api('DELETE',f"/media/{clip['id']}",status=204)
        self.assertEqual(self.api('GET',f"/training/{record['id']}")['media_url'],clip['url'])
        self.assertEqual(len(list(path.glob('*'))),1)
        with patch('pathlib.Path.unlink',side_effect=OSError('temporary file lock')):
            self.api('DELETE',f"/media/{clip['id']}",status=204)
        self.assertIsNone(self.api('GET',f"/training/{record['id']}")['media_url'])
        with self.Session() as db:
            self.assertEqual(db.query(AccountFileDeletion).count(),1)
            self.assertEqual(cleanup_files(db),0)
        self.assertEqual(list(path.glob('*')),[])
        self.upload(status=410)

    def test_saved_video_cannot_be_abandoned_or_reused_by_another_record(self):
        clip=self.upload();record=self.record();second=self.record()
        for _ in range(2):self.api('PATCH',f"/training/{record['id']}/media",json={'media_id':clip['id']})
        self.api('DELETE','/media/training-uploads/video-retry-check',status=409)
        self.api('PATCH',f"/training/{second['id']}/media",status=409,json={'media_id':clip['id']})
        self.api('POST','/training',status=409,json={'training_type':'另一训练','duration_seconds':30,'score':0,'media_url':clip['url'],'media_type':'video'})
        # Old shared rows are all detached on deletion; counts and duration survive.
        with self.Session() as db:
            row=db.get(TrainingRecord,second['id']);row.media_url=clip['url'];row.media_type='video';db.commit()
        self.api('DELETE',f"/media/{clip['id']}",status=204)
        self.assertTrue(all(r['media_url'] is None for r in self.api('GET','/training')['records']))
        self.assertEqual(self.api('GET','/training/summary')['sessions'],2)
        newer=self.upload(key='video-newer-file')
        self.api('GET','/media/training-uploads/video-retry-check',status=410)
        self.assertEqual(self.api('GET','/media/training-uploads/video-newer-file'),newer)

    def test_upload_and_abandon_save_failures_keep_consistent_files(self):
        # Avoid last-active writes consuming the deliberately failed commit.
        with self.Session() as db:db.get(User,1).last_active_at=datetime.utcnow();db.commit()
        with patch('sqlalchemy.orm.Session.commit',side_effect=RuntimeError('save failed')):
            with self.assertRaises(RuntimeError):self.upload()
        self.assertEqual(list((Path(self.folder.name)/'private').glob('*')),[])
        clip=self.upload()
        with patch('sqlalchemy.orm.Session.commit',side_effect=RuntimeError('save failed')):
            with self.assertRaises(RuntimeError):self.api('DELETE','/media/training-uploads/video-retry-check',status=204)
        self.assertEqual(self.api('GET','/media/training-uploads/video-retry-check'),clip)
        self.assertEqual(self.client.get(clip['url'],headers=self.headers[1]).status_code,200)

    def test_account_removal_clears_upload_markers_keeps_other_account(self):
        self.upload();other=self.upload(who=2)
        with self.Session() as db:
            delete_account_data(db.get(User,1),db)
            self.assertIsNone(db.query(TrainingVideoUpload).filter_by(user_id=1).first())
            cleanup_files(db)
        self.assertEqual(self.api('GET','/media/training-uploads/video-retry-check',2),other)
        self.assertEqual(self.client.get(other['url'],headers=self.headers[2]).status_code,200)


if __name__=='__main__':unittest.main()
