"""Legacy-image maintenance uses temporary accounts, records and files only."""
import hashlib
import importlib.util
import io
import json
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
import unittest

import test_app_flows as flows
from app.main import app
from app.models.account import AccountFileDeletion
from app.models.chat import Chat, ChatChange, ChatMessage, ChatSend
from app.models.media import Media
from app.models.post import Post
from app.models.training import TrainingRecord
from app.models.user import User
from app.services.account_deletion import delete_account_data
from app.services.file_cleanup import cleanup_files
from app.services.legacy_chat_images import move_legacy_chat_images
from fastapi.staticfiles import StaticFiles


class LegacyImageChecks(unittest.TestCase):
    setUp = flows.AppFlows.setUp
    tearDown = flows.AppFlows.tearDown
    api = flows.AppFlows.api
    accepted_chat = flows.AppFlows.accepted_chat

    def legacy_image(self, *, count=1):
        chat_id = self.accepted_chat()
        path = Path(self.folder.name) / 'images' / 'legacy-picture.png'
        path.parent.mkdir()
        path.write_bytes(b'isolated legacy picture bytes')
        url = '/uploads/images/' + path.name
        with self.Session() as db:
            media = Media(user_id=1, purpose='post', media_type='image', url=url)
            db.add(media)
            rows = [ChatMessage(chat_id=chat_id, sender_id=1, message_type='image', content=url,
                                created_at=datetime(2026, 10, 1, 12)) for _ in range(count)]
            db.add_all(rows)
            db.flush()
            ids = [row.id for row in rows]
            digest = hashlib.sha256(json.dumps(['', url], ensure_ascii=False).encode()).hexdigest()
            db.add(ChatSend(chat_id=chat_id, user_id=1, request_key='legacy-picture-send',
                            payload_hash=digest, message_ids=ids))
            db.commit()
        # Exercise the actual public route with the isolated folder as well.
        route = next(r for r in app.routes if getattr(r, 'path', '') == '/uploads/images')
        old_app = route.app
        route.app = StaticFiles(directory=path.parent)
        self.addCleanup(setattr, route, 'app', old_app)
        return chat_id, path, url, ids

    def test_inspection_is_read_only_and_reports_shared_uses(self):
        chat_id, path, url, ids = self.legacy_image(count=2)
        with self.Session() as db:
            db.get(User, 2).avatar = url
            db.add(Post(user_id=2, content='公开使用', image_urls=[url]))
            db.commit()
        before = sorted(str(p.relative_to(Path(self.folder.name))) for p in Path(self.folder.name).rglob('*'))
        with self.Session() as db:
            report = move_legacy_chat_images(db)
            self.assertEqual((report.items[0].status, report.items[0].messages,
                              report.items[0].private_copies, report.items[0].public_copies), ('ready', 2, 1, 1))
            self.assertTrue(all(db.get(ChatMessage, mid).content == url for mid in ids))
            self.assertEqual(db.query(Media).count(), 1)
            self.assertEqual(db.query(ChatChange).count(), 0)
        self.assertTrue(path.exists())
        self.assertEqual(before, sorted(str(p.relative_to(Path(self.folder.name))) for p in Path(self.folder.name).rglob('*')))

    def test_move_keeps_message_identity_private_scope_and_original_retry(self):
        chat_id, path, url, ids = self.legacy_image(count=2)
        self.assertEqual(self.client.get(url).status_code, 200)
        with self.Session() as db:
            report = move_legacy_chat_images(db, apply=True)
            self.assertEqual((report.items[0].status, report.pending_cleanup), ('moved', 0))
            rows = [db.get(ChatMessage, mid) for mid in ids]
            new_url = rows[0].content
            self.assertTrue(new_url.startswith(f'/chat/chats/{chat_id}/images/'))
            self.assertEqual(rows[1].content, new_url)
            self.assertEqual([r.created_at for r in rows], [datetime(2026, 10, 1, 12)] * 2)
            self.assertEqual(db.query(ChatChange).count(), 2)
            self.assertEqual(db.query(Media).count(), 1)
            self.assertEqual(move_legacy_chat_images(db, apply=True).items, [])
        self.assertFalse(path.exists())
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get(new_url).status_code, 401)
        for uid in (1, 2):
            result = self.client.get(new_url, headers=self.headers[uid])
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.content, b'isolated legacy picture bytes')
        self.api('GET', new_url, 3, 404)
        retried = self.api('POST', f'/chat/chats/{chat_id}/messages', json={'image_url': url, 'request_key': 'legacy-picture-send'})
        self.assertEqual([m['id'] for m in retried['messages']], ids)
        self.assertEqual(retried['messages'][0]['content'], new_url)
        self.api('POST', f'/chat/chats/{chat_id}/messages', status=400, json={'image_url': url})

    def test_same_picture_in_different_chats_and_senders_gets_separate_private_files(self):
        chat_id, path, url, ids = self.legacy_image()
        with self.Session() as db:
            second = Chat(requester_id=1, receiver_id=3, status='accepted')
            db.add(second)
            db.flush()
            db.add_all([ChatMessage(chat_id=chat_id, sender_id=2, message_type='image', content=url),
                        ChatMessage(chat_id=second.id, sender_id=1, message_type='image', content=url)])
            second_id = second.id
            db.commit()
            report = move_legacy_chat_images(db, apply=True)
            self.assertEqual(report.items[0].private_copies, 3)
            media = db.query(Media).order_by(Media.id).all()
            self.assertEqual(len({m.storage_name for m in media}), 3)
            first_url = db.get(ChatMessage, ids[0]).content
            second_url = db.query(ChatMessage).filter_by(chat_id=second_id).first().content
        self.api('GET', first_url, 3, 404)
        self.assertEqual(self.client.get(second_url, headers=self.headers[3]).status_code, 200)
        self.assertEqual(len(list((Path(self.folder.name) / 'private').glob('*'))), 3)

    def test_public_uses_keep_their_content_without_sharing_account_cleanup(self):
        chat_id, path, url, ids = self.legacy_image()
        old = datetime.utcnow() - timedelta(days=30)
        with self.Session() as db:
            for uid in (1, 2):
                user = db.get(User, uid)
                user.avatar = url
                user.cover = url
                user.updated_at = old
                db.add(Post(user_id=uid, content='公开图片', image_urls=[url], updated_at=old))
            db.add(TrainingRecord(user_id=2, training_type='旧图片记录', duration_seconds=30, score=0,
                                  media_url=url, media_type='image', updated_at=old))
            db.commit()
            report = move_legacy_chat_images(db, apply=True)
            self.assertEqual(report.items[0].public_copies, 2)
            users = [db.get(User, uid) for uid in (1, 2)]
            public_urls = [u.avatar for u in users]
            self.assertEqual(len(set(public_urls)), 2)
            self.assertTrue(all(u.avatar == u.cover and u.updated_at == old for u in users))
            posts = db.query(Post).order_by(Post.user_id).all()
            self.assertEqual([p.image_urls for p in posts], [[url] for url in public_urls])
            self.assertTrue(all(p.updated_at == old for p in posts))
            training = db.query(TrainingRecord).one()
            self.assertEqual((training.media_url, training.updated_at), (public_urls[1], old))
        for public in public_urls:
            result = self.client.get(public)
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.content, b'isolated legacy picture bytes')
        with self.Session() as db:
            delete_account_data(db.get(User, 1), db)
            cleanup_files(db)
        self.assertEqual(self.client.get(public_urls[0]).status_code, 404)
        self.assertEqual(self.client.get(public_urls[1]).status_code, 200)

    def test_save_or_copy_failure_keeps_original_records_and_files(self):
        chat_id, path, url, ids = self.legacy_image()
        with self.Session() as db, patch('sqlalchemy.orm.Session.commit', side_effect=RuntimeError('save unavailable')):
            report = move_legacy_chat_images(db, apply=True)
            self.assertEqual(report.items[0].status, 'failed')
        with self.Session() as db:
            self.assertEqual(db.get(ChatMessage, ids[0]).content, url)
            self.assertEqual(db.query(Media).count(), 1)
            self.assertEqual(db.query(ChatChange).count(), 0)
        self.assertTrue(path.is_file())
        self.assertEqual(list((Path(self.folder.name) / 'private').glob('*')), [])
        with self.Session() as db, patch('app.services.legacy_chat_images.shutil.copyfileobj', side_effect=OSError('disk full')):
            self.assertEqual(move_legacy_chat_images(db, apply=True).items[0].status, 'failed')
        self.assertTrue(path.is_file())
        self.assertEqual(list((Path(self.folder.name) / 'private').glob('*')), [])

    def test_locked_old_file_remains_queued_and_rerun_finishes_cleanup(self):
        chat_id, path, url, ids = self.legacy_image()
        real_unlink = Path.unlink
        def unlink(item, *args, **kwargs):
            if item.resolve() == path.resolve():
                raise OSError('source temporarily locked')
            return real_unlink(item, *args, **kwargs)
        with self.Session() as db, patch('pathlib.Path.unlink', unlink):
            report = move_legacy_chat_images(db, apply=True)
            self.assertEqual((report.items[0].status, report.pending_cleanup), ('moved', 1))
            self.assertNotEqual(db.get(ChatMessage, ids[0]).content, url)
        self.assertTrue(path.is_file())
        with self.Session() as db:
            report = move_legacy_chat_images(db, apply=True)
            self.assertEqual((report.items, report.pending_cleanup), ([], 0))
        self.assertFalse(path.exists())

    def test_missing_invalid_sender_and_linked_paths_are_left_for_review(self):
        chat_id, path, url, ids = self.legacy_image()
        with self.Session() as db:
            db.get(ChatMessage, ids[0]).sender_id = 3
            db.commit()
            report = move_legacy_chat_images(db, apply=True)
            self.assertEqual(report.items[0].status, 'needs_review')
            db.get(ChatMessage, ids[0]).sender_id = 1
            db.commit()
        self.assertTrue(path.is_file())
        outside = Path(self.folder.name) / 'outside.png'
        path.rename(outside)
        path.symlink_to(outside)
        with self.Session() as db:
            self.assertEqual(move_legacy_chat_images(db, apply=True).items[0].status, 'needs_review')
            self.assertEqual(db.get(ChatMessage, ids[0]).content, url)
        self.assertTrue(outside.is_file())
        path.unlink()
        with self.Session() as db:
            self.assertEqual(move_legacy_chat_images(db, apply=True).items[0].status, 'needs_review')
            db.get(ChatMessage, ids[0]).content = '/uploads/images/../outside.png'
            db.commit()
            self.assertEqual(move_legacy_chat_images(db, apply=True).items[0].status, 'needs_review')
            db.get(ChatMessage, ids[0]).content = '/uploads/images/%2e%2e%2foutside.png'
            db.commit()
            self.assertEqual(move_legacy_chat_images(db, apply=True).items[0].status, 'needs_review')
        self.assertTrue(outside.is_file())

    def test_recalled_and_removed_content_is_not_restored(self):
        chat_id, path, url, ids = self.legacy_image()
        with self.Session() as db:
            db.get(ChatMessage, ids[0]).recalled_at = datetime.utcnow()
            db.add(Post(user_id=1, content='', image_urls=[url], removed_at=datetime.utcnow()))
            db.commit()
            report = move_legacy_chat_images(db, apply=True)
            self.assertEqual((report.items[0].private_copies, report.items[0].public_copies), (0, 0))
            self.assertEqual(db.get(ChatMessage, ids[0]).content, '')
            self.assertEqual(db.query(Post).one().image_urls, [])
            self.assertEqual(db.query(Media).count(), 0)
        self.assertFalse(path.exists())

    def test_command_defaults_to_inspection_and_requires_offline_for_changes(self):
        chat_id, path, url, ids = self.legacy_image()
        spec = importlib.util.spec_from_file_location('legacy_image_command', Path(__file__).parents[1] / 'scripts/protect_legacy_chat_images.py')
        command = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(command)
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            command.main(['--apply'])
        self.assertEqual(error.exception.code, 2)
        output = io.StringIO()
        with patch('app.db.session.SessionLocal', self.Session), redirect_stdout(output):
            self.assertEqual(command.main([]), 0)
        self.assertTrue(path.exists())
        self.assertNotIn(url, output.getvalue())
        with patch('app.db.session.SessionLocal', self.Session), redirect_stdout(io.StringIO()):
            self.assertEqual(command.main(['--apply', '--offline']), 0)
        self.assertFalse(path.exists())


if __name__ == '__main__':
    unittest.main()
