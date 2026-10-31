"""Lost save responses must not destroy saved private files; temporary data only."""
import base64
import io
import unittest
import wave
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import test_app_flows as flows
from sqlalchemy import event
from sqlalchemy.orm import Session
from app.models.account import AccountFileDeletion
from app.models.chat import ChatMessage, ChatSend
from app.models.media import Media, TrainingVideoUpload
from app.models.training import TrainingRecord
from app.models.user import User
from app.services.file_cleanup import cleanup_files
from app.services.private_files import discard_private_upload


PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')


class PrivateFilePreservationChecks(unittest.TestCase):
    setUp = flows.AppFlows.setUp
    tearDown = flows.AppFlows.tearDown
    api = flows.AppFlows.api
    accepted_chat = flows.AppFlows.accepted_chat

    def fresh_activity(self):
        with self.Session() as db:
            for user in db.query(User): user.last_active_at = datetime.utcnow()
            db.commit()

    def upload(self, kind, *, cid=None, key='private-file-check', status=200):
        if kind == 'image':
            return self.api('POST', f'/chat/chats/{cid}/images', status=status, files={'file': ('image.png', PNG, 'image/png')})
        if kind == 'video':
            return self.api('POST', '/media/upload-training-video', status=status,
                            data={'request_key': key} if key else {}, files={'file': ('clip.webm', (Path(__file__).parent / 'fixtures' / 'recording.webm').read_bytes(), 'video/webm')})
        output = io.BytesIO()
        with wave.open(output, 'wb') as clip:
            clip.setnchannels(1); clip.setsampwidth(2); clip.setframerate(16000); clip.writeframes(b'\0' * 6400)
        return self.api('POST', f'/chat/chats/{cid}/messages/voice', status=status,
                        data={'request_key': key}, files={'audio': ('voice.wav', output.getvalue(), 'audio/wav')})

    @contextmanager
    def lost_commit_response(self):
        self.fresh_activity()
        commit = Session.commit
        def save_then_fail(db):
            commit(db)
            raise RuntimeError('saved but response lost')
        with patch.object(Session, 'commit', save_then_fail):
            yield

    def test_training_upload_lost_response_keeps_file_and_retry_reuses_original(self):
        with self.lost_commit_response():
            with self.assertRaisesRegex(RuntimeError, 'saved but response lost'): self.upload('video')
        with self.Session() as db:
            row = db.query(Media).one(); path = Path(self.folder.name) / 'private' / row.storage_name
            expected = {'id': row.id, 'url': row.url}
            self.assertEqual(db.query(TrainingVideoUpload).count(), 1)
        self.assertTrue(path.is_file())
        self.assertEqual(self.upload('video'), expected)
        self.assertEqual(self.api('GET', '/media/training-uploads/private-file-check'), expected)
        self.assertEqual(self.client.get(expected['url'], headers=self.headers[1]).status_code, 200)
        self.api('GET', expected['url'], 2, 404)
        self.assertEqual(len(list(path.parent.iterdir())), 1)

    def test_legacy_training_upload_without_number_preserves_saved_file(self):
        with self.lost_commit_response():
            with self.assertRaises(RuntimeError): self.upload('video', key=None)
        with self.Session() as db:
            row = db.query(Media).one()
            self.assertTrue((Path(self.folder.name) / 'private' / row.storage_name).is_file())
            url = row.url
        self.assertEqual(self.client.get(url, headers=self.headers[1]).status_code, 200)

    def test_chat_picture_lost_response_keeps_owner_preview_and_can_send(self):
        cid = self.accepted_chat()
        with self.lost_commit_response():
            with self.assertRaises(RuntimeError): self.upload('image', cid=cid)
        with self.Session() as db:
            row = db.query(Media).one(); url = row.url
            self.assertTrue((Path(self.folder.name) / 'private' / row.storage_name).exists())
        self.assertEqual(self.client.get(url, headers=self.headers[1]).status_code, 200)
        self.api('GET', url, 2, 404)
        sent = self.api('POST', f'/chat/chats/{cid}/messages', json={'content': '保留原图', 'image_url': url, 'request_key': 'kept-picture-send'})
        self.assertEqual(len(sent['messages']), 2)
        self.assertEqual(self.client.get(url, headers=self.headers[2]).status_code, 200)

    def test_voice_lost_response_keeps_audio_and_retry_sends_only_once(self):
        cid = self.accepted_chat()
        with self.lost_commit_response():
            with self.assertRaises(RuntimeError): self.upload('voice', cid=cid)
        with self.Session() as db:
            message = db.query(ChatMessage).one(); mid = message.id
            self.assertEqual(db.query(ChatSend).count(), 1)
            path = Path(self.folder.name) / 'private' / message.content
        self.assertTrue(path.is_file())
        self.assertEqual(self.upload('voice', cid=cid)['message']['id'], mid)
        self.assertEqual(self.api('GET', '/chat/chats', 2)['chats'][0]['unread_count'], 1)
        audio = self.client.get(f'/chat/chats/{cid}/messages/{mid}/audio', headers=self.headers[2])
        self.assertEqual(audio.status_code, 200); self.assertEqual(audio.content, path.read_bytes())
        self.assertEqual(len(list(path.parent.iterdir())), 1)

    def test_unknown_save_result_preserves_files_without_overriding_original_error(self):
        cid = self.accepted_chat()
        for kind in ('image', 'video', 'voice'):
            with self.subTest(kind=kind):
                self.fresh_activity()
                state = {'down': False}
                def cannot_save(db):
                    state['down'] = True
                    raise RuntimeError('original save failure')
                def cannot_read(conn, cursor, statement, parameters, context, executemany):
                    if state['down'] and statement.lstrip().upper().startswith('SELECT'):
                        raise RuntimeError('temporary read failure')
                event.listen(self.engine, 'before_cursor_execute', cannot_read)
                try:
                    with patch.object(Session, 'commit', cannot_save):
                        with self.assertRaisesRegex(RuntimeError, 'original save failure'):
                            self.upload(kind, cid=cid, key='unknown-file-' + kind)
                finally:
                    event.remove(self.engine, 'before_cursor_execute', cannot_read)
                paths = list((Path(self.folder.name) / 'private').iterdir())
                self.assertEqual(len(paths), 1)
                with self.Session() as db:
                    self.assertEqual(db.query(Media).count(), 0); self.assertEqual(db.query(ChatMessage).count(), 0)
                    # Once reads recover, the prepared unsaved file is removable.
                    self.assertTrue(discard_private_upload(db, paths[0].name))

    def test_failed_save_and_failed_file_cleanup_are_queued_for_retry(self):
        cid = self.accepted_chat()
        commit = Session.commit
        for kind in ('image', 'video', 'voice'):
            with self.subTest(kind=kind):
                self.fresh_activity(); state = {'failed': False}
                def fail_first_save(db):
                    if not state['failed']:
                        state['failed'] = True
                        raise RuntimeError('save unavailable')
                    return commit(db)
                with patch.object(Session, 'commit', fail_first_save), patch('pathlib.Path.unlink', side_effect=OSError('file locked')):
                    with self.assertRaisesRegex(RuntimeError, 'save unavailable'):
                        self.upload(kind, cid=cid, key='failed-file-' + kind)
                with self.Session() as db:
                    self.assertEqual(db.query(Media).count(), 0); self.assertEqual(db.query(ChatMessage).count(), 0)
                    self.assertEqual(db.query(AccountFileDeletion).count(), 1)
                    self.assertEqual(cleanup_files(db), 0)
                self.assertEqual(list((Path(self.folder.name) / 'private').iterdir()), [])

    def test_duplicate_voice_cleanup_failure_still_returns_saved_message(self):
        cid = self.accepted_chat(); first = self.upload('voice', cid=cid)['message']
        with patch('pathlib.Path.unlink', side_effect=OSError('extra copy locked')):
            self.assertEqual(self.upload('voice', cid=cid)['message']['id'], first['id'])
        self.assertEqual(len(list((Path(self.folder.name) / 'private').iterdir())), 2)
        with self.Session() as db:
            self.assertEqual(db.query(ChatMessage).count(), 1); self.assertEqual(db.query(AccountFileDeletion).count(), 1)
            self.assertEqual(cleanup_files(db), 0)
        self.assertEqual(len(list((Path(self.folder.name) / 'private').iterdir())), 1)
        self.assertEqual(self.client.get(f"/chat/chats/{cid}/messages/{first['id']}/audio", headers=self.headers[2]).status_code, 200)

    def test_missing_picture_is_not_sent_with_text_as_partial_success(self):
        cid = self.accepted_chat(); image = self.upload('image', cid=cid)
        with self.Session() as db: name = db.get(Media, image['id']).storage_name
        (Path(self.folder.name) / 'private' / name).unlink()
        self.api('POST', f'/chat/chats/{cid}/messages', status=400,
                 json={'content': '不能只发送文字', 'image_url': image['url'], 'request_key': 'missing-picture-send'})
        self.api('POST', f'/chat/chats/{cid}/messages/image', status=400, json={'image_url': image['url']})
        with self.Session() as db:
            self.assertEqual(db.query(ChatMessage).count(), 0); self.assertEqual(db.query(ChatSend).count(), 0)

    def test_missing_video_is_not_attached_or_counted_as_new_training(self):
        video = self.upload('video')
        record = self.api('POST', '/training', json={'training_type': '保留次数', 'duration_seconds': 30, 'reps': 2, 'score': 0})
        with self.Session() as db: name = db.get(Media, video['id']).storage_name
        (Path(self.folder.name) / 'private' / name).unlink()
        self.api('PATCH', f"/training/{record['id']}/media", status=400, json={'media_id': video['id']})
        self.api('POST', '/training', status=400, json={'training_type': '不应成功', 'duration_seconds': 30, 'reps': 2, 'score': 0, 'media_url': video['url'], 'media_type': 'video'})
        self.api('GET', '/media/training-uploads/private-file-check', status=410)
        with self.Session() as db:
            row = db.query(TrainingRecord).one(); self.assertIsNone(row.media_url)
            self.assertEqual((row.reps, row.duration_seconds), (2, 30))

    def test_missing_old_voice_retry_does_not_claim_audio_is_available(self):
        cid = self.accepted_chat(); first = self.upload('voice', cid=cid)['message']
        with self.Session() as db: name = db.get(ChatMessage, first['id']).content
        (Path(self.folder.name) / 'private' / name).unlink()
        self.upload('voice', cid=cid, status=410)
        self.assertEqual(list((Path(self.folder.name) / 'private').iterdir()), [])
        with self.Session() as db: self.assertEqual(db.query(ChatMessage).count(), 1)

    def test_private_file_links_are_not_read_sent_or_attached(self):
        cid = self.accepted_chat(); image = self.upload('image', cid=cid); video = self.upload('video')
        voice = self.upload('voice', cid=cid)['message']
        record = self.api('POST', '/training', json={'training_type': '保留训练', 'duration_seconds': 30, 'score': 0})
        outside = Path(self.folder.name) / 'outside.dat'; outside.write_bytes(b'must not be disclosed')
        with self.Session() as db:
            names = [db.get(Media, image['id']).storage_name, db.get(Media, video['id']).storage_name, db.get(ChatMessage, voice['id']).content]
        for name in names:
            path = Path(self.folder.name) / 'private' / name; path.unlink(); path.symlink_to(outside)
        self.api('GET', image['url'], status=404); self.api('GET', video['url'], status=404)
        self.api('GET', f"/chat/chats/{cid}/messages/{voice['id']}/audio", status=404)
        self.api('POST', f'/chat/chats/{cid}/messages', status=400, json={'image_url': image['url']})
        self.api('PATCH', f"/training/{record['id']}/media", status=400, json={'media_id': video['id']})
        self.api('GET', '/media/training-uploads/private-file-check', status=410)
        self.assertEqual(outside.read_bytes(), b'must not be disclosed')

    def test_private_directory_link_is_not_read_or_used(self):
        cid = self.accepted_chat(); image = self.upload('image', cid=cid)
        root = Path(self.folder.name); folder = root / 'private'; other = root / 'elsewhere'
        folder.rename(other); folder.symlink_to(other, target_is_directory=True)
        self.api('GET', image['url'], status=404)
        self.api('POST', f'/chat/chats/{cid}/messages', status=400, json={'image_url': image['url']})
        self.assertEqual(len(list(other.iterdir())), 1)
