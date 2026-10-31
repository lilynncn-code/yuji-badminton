"""Public attachments use isolated accounts, a temporary database and files."""
import base64
import io
import unittest
import wave
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import test_app_flows as flows
from fastapi.staticfiles import StaticFiles
from app.main import app
from app.models.account import AccountFileDeletion
from app.models.chat import ChatMessage
from app.models.media import Media
from app.models.post import Post
from app.models.training import TrainingRecord
from app.models.user import User
from app.services.account_deletion import delete_account_data
from app.services.file_cleanup import cleanup_files, queue_file_deletion


PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=')


class PublicMediaChecks(unittest.TestCase):
    setUp = flows.AppFlows.setUp
    tearDown = flows.AppFlows.tearDown
    api = flows.AppFlows.api
    accepted_chat = flows.AppFlows.accepted_chat

    def upload(self, who=1, video=False):
        data = (Path(__file__).parent / 'fixtures' / 'recording.webm').read_bytes() if video else PNG
        result = self.api('POST', '/media/upload-video' if video else '/media/upload', who,
                          files={'file': ('check.webm' if video else 'check.png', data, 'video/webm' if video else 'image/png')})
        path = Path(self.folder.name) / result['url'].removeprefix('/uploads/')
        return result, path

    def post(self, *images, video='', who=1):
        return self.api('POST', '/posts', who, json={'content': '临时文件检查', 'image_urls': list(images), 'video_url': video})['id']

    def public_route(self, folder='images'):
        route = next(r for r in app.routes if getattr(r, 'path', '') == '/uploads/' + folder)
        old = route.app
        route.app = StaticFiles(directory=Path(self.folder.name) / folder)
        self.addCleanup(setattr, route, 'app', old)

    def fresh_activity(self, *ids):
        with self.Session() as db:
            for uid in ids or (1, 2, 3):
                db.get(User, uid).last_active_at = datetime.utcnow()
            db.commit()

    def test_post_delete_removes_files_and_public_addresses_after_commit(self):
        image, picture = self.upload()
        video, clip = self.upload(video=True)
        pid = self.post(image['url'], video=video['url'])
        self.public_route(); self.public_route('videos')
        for item in (image, video): self.assertEqual(self.client.get(item['url']).status_code, 200)
        self.api('DELETE', f'/posts/{pid}', 2, 403)
        self.api('DELETE', f'/posts/{pid}')
        for item in (image, video): self.assertEqual(self.client.get(item['url']).status_code, 404)
        self.assertFalse(picture.exists()); self.assertFalse(clip.exists())
        with self.Session() as db:
            self.assertEqual(db.query(Media).count(), 0)
            self.assertEqual(db.query(AccountFileDeletion).count(), 0)

    def test_replacing_post_attachments_preserves_other_current_uses(self):
        first, original = self.upload()
        second, replacement = self.upload()
        pid = self.post(first['url'])
        other = self.post(first['url'])
        self.api('PUT', f'/posts/{pid}', json={'content': '已更换', 'image_urls': [second['url']]})
        self.assertTrue(original.exists()); self.assertTrue(replacement.exists())
        self.api('DELETE', f'/posts/{other}')
        self.assertFalse(original.exists()); self.assertTrue(replacement.exists())
        self.api('DELETE', f'/posts/{pid}')
        self.assertFalse(replacement.exists())

    def test_avatar_and_cover_replacement_waits_for_all_own_uses(self):
        first, old = self.upload(); second, new = self.upload()
        self.api('PATCH', '/profile/me', json={'avatar': first['url'], 'cover': first['url']})
        self.api('PATCH', '/profile/me', json={'avatar': second['url']})
        self.assertTrue(old.exists())
        self.api('PATCH', '/profile/me', json={'cover': ''})
        self.assertFalse(old.exists()); self.assertTrue(new.exists())
        self.api('PATCH', '/profile/me', json={'avatar': ''})
        self.assertFalse(new.exists())

    def test_legacy_shared_file_survives_owner_deletion_then_last_use_removal(self):
        item, path = self.upload(); pid = self.post(item['url'])
        # Old versions allowed another account to reuse a public local URL.
        with self.Session() as db:
            db.get(User, 2).avatar = item['url']; db.commit()
        self.api('DELETE', f'/posts/{pid}')
        self.assertTrue(path.exists())
        with self.Session() as db:
            self.assertIsNone(db.get(Media, item['id']))
            self.assertEqual(db.query(AccountFileDeletion).count(), 1)
        self.api('PATCH', '/profile/me', 2, json={'avatar': ''})
        self.assertFalse(path.exists())

    def test_account_removal_retains_other_accounts_public_reference(self):
        item, path = self.upload()
        with self.Session() as db:
            db.add(Post(user_id=2, content='旧版共享图片', image_urls=[item['url']]))
            db.commit()
            delete_account_data(db.get(User, 1), db)
            cleanup_files(db)
            self.assertTrue(path.exists())
            pid = db.query(Post.id).scalar()
        self.api('DELETE', f'/posts/{pid}', 2)
        self.assertFalse(path.exists())

    def test_training_chat_and_other_upload_references_protect_files(self):
        item, path = self.upload(); pid = self.post(item['url'])
        cid = self.accepted_chat()
        with self.Session() as db:
            db.add(TrainingRecord(user_id=2, training_type='旧记录', duration_seconds=30, score=0, media_url=item['url']))
            db.add(ChatMessage(chat_id=cid, sender_id=2, message_type='image', content=item['url']))
            duplicate = Media(user_id=3, purpose='post', media_type='image', url=item['url'])
            db.add(duplicate); db.commit(); mid = duplicate.id
        self.api('DELETE', f'/posts/{pid}')
        with self.Session() as db:
            self.assertEqual(cleanup_files(db), 1); self.assertTrue(path.exists())
            db.query(TrainingRecord).delete(); db.commit()
            self.assertEqual(cleanup_files(db), 1); self.assertTrue(path.exists())
            db.query(ChatMessage).delete(); db.commit()
            self.assertEqual(cleanup_files(db), 1); self.assertTrue(path.exists())
        self.api('DELETE', f'/media/{mid}', 3, 204)
        self.assertFalse(path.exists())

    def test_file_list_deletion_keeps_active_post_until_post_removed(self):
        item, path = self.upload(); pid = self.post(item['url'])
        self.api('DELETE', f"/media/{item['id']}", status=204)
        self.assertTrue(path.exists())
        self.assertEqual(self.api('GET', f'/posts/{pid}')['image_urls'], [item['url']])
        self.api('DELETE', f'/posts/{pid}')
        self.assertFalse(path.exists())
        spare, spare_path = self.upload()
        self.api('DELETE', f"/media/{spare['id']}", status=204)
        self.assertFalse(spare_path.exists())

    def test_save_failure_preserves_post_profile_metadata_and_files(self):
        first, old = self.upload(); second, new = self.upload()
        pid = self.post(first['url'])
        self.api('PATCH', '/profile/me', json={'avatar': first['url']})
        self.fresh_activity()
        for method, url, body in [('DELETE', f'/posts/{pid}', None),
                                  ('PUT', f'/posts/{pid}', {'content': '替换', 'image_urls': [second['url']]}),
                                  ('PATCH', '/profile/me', {'avatar': second['url']}),
                                  ('DELETE', f"/media/{first['id']}", None)]:
            with self.subTest(method=method, url=url):
                with patch('sqlalchemy.orm.Session.commit', side_effect=RuntimeError('save failed')):
                    with self.assertRaisesRegex(RuntimeError, 'save failed'):
                        self.client.request(method, url, headers=self.headers[1], **({'json': body} if body else {}))
                self.assertTrue(old.exists()); self.assertTrue(new.exists())
                with self.Session() as db:
                    self.assertEqual(db.get(Post, pid).image_urls, [first['url']])
                    self.assertIsNone(db.get(Post, pid).removed_at)
                    self.assertEqual(db.get(User, 1).avatar, first['url'])
                    self.assertEqual(db.query(Media).count(), 2)
                    self.assertEqual(db.query(AccountFileDeletion).count(), 0)

    def test_locked_file_is_queued_and_can_retry_after_success_response(self):
        item, path = self.upload(); pid = self.post(item['url'])
        with patch('pathlib.Path.unlink', side_effect=OSError('file locked')):
            self.api('DELETE', f'/posts/{pid}')
        self.api('GET', f'/posts/{pid}', status=404)
        self.assertTrue(path.exists())
        with self.Session() as db:
            self.assertEqual(db.query(AccountFileDeletion).count(), 1)
            self.assertEqual(cleanup_files(db), 0)
        self.assertFalse(path.exists())

    def test_report_removal_cleans_public_attachments(self):
        item, path = self.upload(); pid = self.post(item['url'])
        with self.Session() as db:
            db.get(User, 3).can_review_reports = 1; db.commit()
        report = self.api('POST', '/social/reports', 2, json={'target_type': 'post', 'target_id': pid, 'reason': '临时核查内容'})
        self.api('POST', f"/social/review/reports/{report['id']}", 3, json={'action': 'remove_content', 'result': '临时检查移除'})
        self.assertFalse(path.exists())

    def test_question_video_survives_post_and_upload_removal_until_question_deleted(self):
        item, path = self.upload(video=True)
        qid = self.api('POST', '/clinic', json={'title': '临时视频提问', 'content': '检查共享视频的保留', 'video_url': item['url']})['id']
        pid = self.post(video=item['url'])
        self.api('DELETE', f'/posts/{pid}')
        self.assertTrue(path.exists())
        self.api('DELETE', f"/media/{item['id']}", status=204)
        self.assertTrue(path.exists())
        self.assertEqual(self.api('GET', f'/clinic/{qid}')['video_url'], item['url'])
        self.fresh_activity()
        with patch('sqlalchemy.orm.Session.commit', side_effect=RuntimeError('save failed')):
            with self.assertRaises(RuntimeError): self.api('DELETE', f'/clinic/{qid}')
        self.assertTrue(path.exists()); self.api('GET', f'/clinic/{qid}')
        self.api('DELETE', f'/clinic/{qid}')
        self.assertFalse(path.exists())

    def test_question_rejects_missing_and_foreign_video_but_retry_keeps_existing(self):
        item, path = self.upload(video=True)
        body = {'title': '临时视频提问', 'content': '检查真实文件', 'video_url': item['url'], 'request_key': 'question-media-check'}
        self.api('POST', '/clinic', 2, 400, json=body)
        qid = self.api('POST', '/clinic', json=body)['id']
        path.unlink()
        self.assertEqual(self.api('POST', '/clinic', json=body)['id'], qid)
        self.api('POST', '/clinic', status=400, json={**body, 'request_key': 'question-other-check'})

    def test_missing_foreign_and_noncanonical_local_attachments_rejected(self):
        item, path = self.upload()
        for url in (item['url'], '/uploads/images/missing.png', item['url'] + '?x=1',
                    item['url'].replace('/images/', '/images/./'), '/uploads/images/%2fmissing.png'):
            with self.subTest(url=url):
                self.api('POST', '/posts', 2, 400, json={'content': '不应成功', 'image_urls': [url]})
                self.api('PATCH', '/profile/me', 2, 400, json={'avatar': url})
        path.unlink()
        self.api('POST', '/posts', status=400, json={'content': '缺失文件', 'image_urls': [item['url']]})
        self.api('PATCH', '/profile/me', status=400, json={'cover': item['url']})
        video, clip = self.upload(video=True)
        self.api('POST', '/posts', 2, 400, json={'content': '其他人的视频', 'video_url': video['url']})
        clip.unlink()
        self.api('POST', '/posts', status=400, json={'content': '缺失视频', 'video_url': video['url']})
        self.post('https://example.com/public.png')

    def test_attachment_validation_rejects_files_or_folders_pointing_elsewhere(self):
        item, path = self.upload()
        target = Path(self.folder.name) / 'outside.png'; target.write_bytes(PNG)
        path.unlink(); path.symlink_to(target)
        self.api('POST', '/posts', status=400, json={'content': '不能使用指向别处的文件', 'image_urls': [item['url']]})
        self.api('PATCH', '/profile/me', status=400, json={'avatar': item['url']})
        path.unlink(); path.parent.rmdir()
        folder = Path(self.folder.name) / 'elsewhere'; folder.mkdir(); (folder / path.name).write_bytes(PNG)
        path.parent.symlink_to(folder, target_is_directory=True)
        self.api('POST', '/posts', status=400, json={'content': '不能使用指向别处的目录', 'image_urls': [item['url']]})
        self.assertTrue(target.exists()); self.assertTrue((folder / path.name).exists())

    def test_cleanup_skips_unsafe_paths_and_protected_front_of_queue(self):
        item, protected = self.upload()
        extra = Path(self.folder.name) / 'images' / 'zz-unused.png'; extra.write_bytes(PNG)
        with self.Session() as db:
            for path in (item['url'].removeprefix('/uploads/'), 'images/zz-unused.png', '../outside', 'images/../outside', '/images/unsafe', 'images//unsafe'):
                queue_file_deletion(db, path)
            db.commit(); cleanup_files(db, limit=1)
        self.assertTrue(protected.exists()); self.assertFalse(extra.exists())
        target = Path(self.folder.name) / 'safe-outside.png'; target.write_bytes(PNG)
        link = Path(self.folder.name) / 'images' / 'linked.png'; link.symlink_to(target)
        folder_target = Path(self.folder.name) / 'another'; folder_target.mkdir()
        folder_file = folder_target / 'keep.png'; folder_file.write_bytes(PNG)
        (Path(self.folder.name) / 'videos').symlink_to(folder_target, target_is_directory=True)
        with self.Session() as db:
            for path in ('images/linked.png', 'videos/keep.png'): queue_file_deletion(db, path)
            db.commit(); cleanup_files(db)
        self.assertTrue(target.exists()); self.assertTrue(link.is_symlink()); self.assertTrue(folder_file.exists())

    def test_legacy_encoded_and_absolute_references_are_conservatively_kept(self):
        item, path = self.upload()
        with self.Session() as db:
            db.get(User, 2).cover = 'https://old.example' + item['url'].replace('/images/', '/images/%2e/') + '?old=1'
            db.commit()
        self.api('DELETE', f"/media/{item['id']}", status=204)
        self.assertTrue(path.exists())
        self.api('PATCH', '/profile/me', 2, json={'cover': ''})
        # An unrecognized old spelling is handled by a later cleanup pass.
        with self.Session() as db: self.assertEqual(cleanup_files(db), 0)
        self.assertFalse(path.exists())

    def test_chat_recall_save_failure_and_locked_file_recovery(self):
        cid = self.accepted_chat(); prefix = f'/chat/chats/{cid}'
        item = self.api('POST', prefix + '/images', files={'file': ('chat.png', PNG, 'image/png')})
        message = self.api('POST', prefix + '/messages', json={'image_url': item['url']})['messages'][0]
        with self.Session() as db: name = db.get(Media, item['id']).storage_name
        path = Path(self.folder.name) / 'private' / name
        self.fresh_activity()
        with patch('sqlalchemy.orm.Session.commit', side_effect=RuntimeError('save failed')):
            with self.assertRaises(RuntimeError): self.api('POST', prefix + f"/messages/{message['id']}/recall")
        self.assertTrue(path.exists()); self.assertEqual(self.client.get(item['url'], headers=self.headers[2]).status_code, 200)
        with patch('pathlib.Path.unlink', side_effect=OSError('locked')):
            self.api('POST', prefix + f"/messages/{message['id']}/recall")
        self.api('GET', item['url'], 2, 404)
        self.assertTrue(path.exists())
        with self.Session() as db: self.assertEqual(cleanup_files(db), 0)
        self.assertFalse(path.exists())
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as output:
            output.setnchannels(1); output.setsampwidth(2); output.setframerate(16000); output.writeframes(b'\0' * 3200)
        voice = self.api('POST', prefix + '/messages/voice', files={'audio': ('voice.wav', buffer.getvalue(), 'audio/wav')})['message']
        with patch('pathlib.Path.unlink', side_effect=OSError('locked')):
            self.api('POST', prefix + f"/messages/{voice['id']}/recall")
        self.api('GET', prefix + f"/messages/{voice['id']}/audio", 2, 404)
        with self.Session() as db: self.assertEqual(cleanup_files(db), 0)

    def test_legacy_chat_recall_preserves_other_uses_until_last_recall(self):
        item, path = self.upload(); cid = self.accepted_chat()
        with self.Session() as db:
            rows = [ChatMessage(chat_id=cid, sender_id=1, message_type='image', content=item['url']) for _ in range(2)]
            db.add_all(rows); db.commit(); ids = [r.id for r in rows]
        self.api('POST', f'/chat/chats/{cid}/messages/{ids[0]}/recall')
        self.assertTrue(path.exists())
        self.api('POST', f'/chat/chats/{cid}/messages/{ids[1]}/recall')
        self.assertFalse(path.exists())

    def test_public_upload_save_failure_removes_only_unsaved_new_files(self):
        original, path = self.upload()
        self.fresh_activity()
        for video in (False, True):
            with self.subTest(video=video):
                with patch('sqlalchemy.orm.Session.commit', side_effect=RuntimeError('save failed')):
                    with self.assertRaisesRegex(RuntimeError, 'save failed'): self.upload(video=video)
                self.assertEqual(list((Path(self.folder.name) / 'images').iterdir()), [path])
                self.assertEqual(list((Path(self.folder.name) / 'videos').glob('*')), [])
                with self.Session() as db: self.assertEqual(db.query(Media).count(), 1)

    def test_public_upload_lost_commit_response_keeps_saved_file(self):
        self.fresh_activity()
        from sqlalchemy.orm import Session
        original_commit = Session.commit
        def commit_then_fail(db):
            original_commit(db)
            raise RuntimeError('lost response after saving')
        with patch.object(Session, 'commit', commit_then_fail):
            with self.assertRaisesRegex(RuntimeError, 'lost response'): self.upload()
        with self.Session() as db:
            row = db.query(Media).one()
            path = Path(self.folder.name) / row.url.removeprefix('/uploads/')
            self.assertTrue(path.is_file())
