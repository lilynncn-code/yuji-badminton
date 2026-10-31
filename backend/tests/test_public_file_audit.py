"""Historical file inspection must not delete drafts or change records."""
import importlib.util
import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import test_app_flows as flows
from app.models.account import AccountFileDeletion
from app.models.media import Media
from app.models.post import Post
from app.services.public_file_audit import inspect_public_files


class PublicFileAuditChecks(unittest.TestCase):
    setUp = flows.AppFlows.setUp
    tearDown = flows.AppFlows.tearDown

    def prepare(self):
        root=Path(self.folder.name)
        (root/'images').mkdir(); (root/'videos').mkdir()
        for name in ('used.png','draft.png','queued.png','orphan.png'):
            (root/'images'/name).write_bytes(name.encode())
        (root/'videos'/'draft.mp4').write_bytes(b'temporary video')
        with self.Session() as db:
            for name in ('used.png','draft.png','missing.png'):
                db.add(Media(user_id=1,purpose='post',media_type='image',url='/uploads/images/'+name))
            db.add(Media(user_id=2,purpose='post',media_type='video',url='/uploads/videos/draft.mp4'))
            db.add(Post(user_id=1,content='保持原资料',image_urls=['/uploads/images/used.png']))
            db.add(AccountFileDeletion(path='images/queued.png')); db.commit()
        return root

    def test_inventory_classifies_files_without_changing_them_or_records(self):
        root=self.prepare()
        before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
        with self.Session() as db:
            with patch('pathlib.Path.unlink',side_effect=AssertionError('inspection must not delete')), \
                 patch.object(db,'commit',side_effect=AssertionError('inspection must not save')):
                report=inspect_public_files(db)
            self.assertEqual({i.path:i.status for i in report.items},{
                'images/used.png':'in_use','images/draft.png':'upload_only','images/queued.png':'queued',
                'images/orphan.png':'untracked','images/missing.png':'missing','videos/draft.mp4':'upload_only'})
            self.assertEqual(report.pending_cleanup,1)
            self.assertEqual(db.query(Media).count(),4)
            self.assertEqual(db.query(Post).one().content,'保持原资料')
        self.assertEqual({str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()},before)

    def test_links_and_nested_folders_are_not_followed(self):
        root=self.prepare()
        target=root/'outside'; target.mkdir(); (target/'keep.png').write_bytes(b'keep')
        (root/'images'/'link.png').symlink_to(target/'keep.png')
        (root/'images'/'nested').mkdir()
        with self.Session() as db:
            states={i.path:i.status for i in inspect_public_files(db).items}
        self.assertEqual(states['images/link.png'],'needs_review')
        self.assertEqual(states['images/nested'],'needs_review')
        (root/'videos'/'draft.mp4').unlink(); (root/'videos').rmdir()
        (root/'videos').symlink_to(target,target_is_directory=True)
        with self.Session() as db:
            states={i.path:i.status for i in inspect_public_files(db).items}
        self.assertEqual(states['videos'],'needs_review')
        self.assertNotIn('videos/keep.png',states)
        self.assertNotIn('videos/draft.mp4',states)
        self.assertEqual((target/'keep.png').read_bytes(),b'keep')

    def test_command_is_read_only_and_prints_counts_without_private_addresses(self):
        root=self.prepare()
        spec=importlib.util.spec_from_file_location('inspect_public_command',Path(__file__).parents[1]/'scripts/inspect_public_files.py')
        command=importlib.util.module_from_spec(spec); spec.loader.exec_module(command)
        output=io.StringIO()
        with patch('app.db.session.SessionLocal',self.Session),redirect_stdout(output):
            self.assertEqual(command.main([]),1)
        self.assertIn('未修改文件或记录',output.getvalue())
        self.assertIn('可能是未发送草稿',output.getvalue())
        self.assertNotIn('used.png',output.getvalue()); self.assertNotIn(self.folder.name,output.getvalue())
        self.assertTrue((root/'images'/'queued.png').exists())
