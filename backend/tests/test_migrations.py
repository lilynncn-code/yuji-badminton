"""Check old saved rows survive repeat upgrades in a disposable database."""
import sys
import unittest
from pathlib import Path
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import IntegrityError

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.db.init_db import ensure_chat_columns, ensure_training_columns, ensure_media_post_columns,ensure_comment_columns


class UpgradeChecks(unittest.TestCase):
    def test_existing_chat_training_posts_and_media_survive_repeat_upgrade(self):
        engine=create_engine('sqlite://')
        with engine.begin() as conn:
            for statement in [
                'CREATE TABLE chats (id INTEGER PRIMARY KEY, requester_id INTEGER, receiver_id INTEGER)',
                'CREATE TABLE chat_messages (id INTEGER PRIMARY KEY,chat_id INTEGER,content TEXT)',
                'CREATE TABLE training_records (id INTEGER PRIMARY KEY,user_id INTEGER,training_type TEXT)',
                'CREATE TABLE posts (id INTEGER PRIMARY KEY,user_id INTEGER,content TEXT)',
                'CREATE TABLE media (id INTEGER PRIMARY KEY,url TEXT)',
                'CREATE TABLE post_comments (id INTEGER PRIMARY KEY,user_id INTEGER,post_id INTEGER,content TEXT)',
                "INSERT INTO chats VALUES (1,1,2)",
                "INSERT INTO chat_messages VALUES (1,1,'原有聊天不能丢')",
                "INSERT INTO training_records VALUES (1,1,'原有训练')",
                "INSERT INTO posts VALUES (1,1,'原有动态')",
                "INSERT INTO media VALUES (1,'/uploads/images/original.png')",
                "INSERT INTO post_comments VALUES (1,1,1,'原有留言不能丢')",
            ]:conn.execute(text(statement))
        for _ in range(2):
            ensure_chat_columns(engine);ensure_training_columns(engine);ensure_media_post_columns(engine)
            ensure_comment_columns(engine)
        with engine.connect() as conn:
            self.assertEqual(conn.execute(text('SELECT content,recalled_at FROM chat_messages')).one(),('原有聊天不能丢',None))
            self.assertEqual(conn.execute(text('SELECT note,requester_read_id,receiver_read_id FROM chats')).one(),('',0,0))
            self.assertEqual(conn.execute(text('SELECT training_type,reps,request_key FROM training_records')).one(),('原有训练',0,None))
            self.assertEqual(conn.execute(text('SELECT content,video_url,request_key,removed_at FROM posts')).one(),('原有动态','',None,None))
            self.assertEqual(conn.execute(text('SELECT url,storage_name FROM media')).one(),('/uploads/images/original.png',''))
            self.assertEqual(conn.execute(text('SELECT content,reply_to_id,request_key,deleted_at FROM post_comments')).one(),('原有留言不能丢',None,None,None))
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO posts(id,user_id,content,request_key) VALUES (2,1,'新增','same-request')"))
        with self.assertRaises(IntegrityError),engine.begin() as conn:
            conn.execute(text("INSERT INTO posts(id,user_id,content,request_key) VALUES (3,1,'重复','same-request')"))
        self.assertIn('uq_training_user_request',{i['name'] for i in inspect(engine).get_indexes('training_records')})
        engine.dispose()
