from sqlalchemy import create_engine, inspect, text

from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app import models  # noqa: F401


def ensure_user_columns() -> None:
    missing_columns = {
        "session_version": "INTEGER NOT NULL DEFAULT 0",
        "can_review_reports": "INTEGER NOT NULL DEFAULT 0",
        "last_active_at": "DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
        "avatar": "VARCHAR(500) NOT NULL DEFAULT ''",
        "cover": "VARCHAR(500) NOT NULL DEFAULT ''",
        "city": "VARCHAR(80) NOT NULL DEFAULT ''",
        "level_tag": "VARCHAR(80) NOT NULL DEFAULT '羽毛球爱好者'",
        "bio": "VARCHAR(500) NOT NULL DEFAULT ''",
        "club": "VARCHAR(80) NOT NULL DEFAULT ''",
        "hand": "VARCHAR(20) NOT NULL DEFAULT '右手持拍'",
    }
    with engine.begin() as conn:
        columns = {column["name"] for column in inspect(conn).get_columns("users")}
        for column_name, column_sql in missing_columns.items():
            if column_name not in columns:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {column_name} {column_sql}"))


def init_db() -> None:
    server_engine = create_engine(settings.server_url, pool_pre_ping=True)
    with server_engine.connect() as conn:
        conn.execute(
            text(
                f"CREATE DATABASE IF NOT EXISTS `{settings.mysql_database}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        )
        conn.commit()
    Base.metadata.create_all(bind=engine)
    ensure_chat_columns(engine)
    ensure_user_columns()
    ensure_training_columns(engine)
    ensure_media_post_columns(engine)
    ensure_comment_columns(engine)
    ensure_report_columns(engine)
    ensure_game_columns(engine)


def ensure_media_post_columns(engine):
    with engine.begin() as conn:
        if 'removed_at' not in {c['name'] for c in inspect(conn).get_columns('posts')}:
            conn.execute(text('ALTER TABLE posts ADD COLUMN removed_at DATETIME NULL'))
        if 'storage_name' not in {c['name'] for c in inspect(conn).get_columns('media')}:
            conn.execute(text("ALTER TABLE media ADD COLUMN storage_name VARCHAR(255) NOT NULL DEFAULT ''"))
        if 'video_url' not in {c['name'] for c in inspect(conn).get_columns('posts')}:
            conn.execute(text("ALTER TABLE posts ADD COLUMN video_url VARCHAR(1000) NOT NULL DEFAULT ''"))
        if 'request_key' not in {c['name'] for c in inspect(conn).get_columns('posts')}:
            conn.execute(text('ALTER TABLE posts ADD COLUMN request_key VARCHAR(64) NULL'))
        post_indexes={i['name'] for i in inspect(conn).get_indexes('posts')}
        post_indexes.update(i['name'] for i in inspect(conn).get_unique_constraints('posts'))
        if 'uq_posts_user_request' not in post_indexes:
            conn.execute(text('CREATE UNIQUE INDEX uq_posts_user_request ON posts (user_id, request_key)'))


def ensure_chat_columns(engine):
    from sqlalchemy import inspect, text
    fields = {"note": "VARCHAR(300) NOT NULL DEFAULT ''", "requester_read_id": "INTEGER NOT NULL DEFAULT 0", "receiver_read_id": "INTEGER NOT NULL DEFAULT 0"}
    existing = {c["name"] for c in inspect(engine).get_columns("chats")}
    with engine.begin() as conn:
        for field, definition in fields.items():
            if field not in existing:
                conn.execute(text(f"ALTER TABLE chats ADD COLUMN {field} {definition}"))
        message_fields={c['name'] for c in inspect(conn).get_columns('chat_messages')}
        if 'recalled_at' not in message_fields:
            conn.execute(text('ALTER TABLE chat_messages ADD COLUMN recalled_at DATETIME NULL'))


def ensure_training_columns(engine):
    fields = {
        "task_id": "VARCHAR(80) NULL",
        "request_key": "VARCHAR(64) NULL",
        "reps": "INTEGER NOT NULL DEFAULT 0",
        "recording_method": "VARCHAR(20) NOT NULL DEFAULT 'manual'",
    }
    with engine.begin() as conn:
        existing = {c["name"] for c in inspect(conn).get_columns("training_records")}
        for field, definition in fields.items():
            if field not in existing:
                conn.execute(text(f"ALTER TABLE training_records ADD COLUMN {field} {definition}"))
        indexes = {i["name"] for i in inspect(conn).get_indexes("training_records")}
        indexes.update(c["name"] for c in inspect(conn).get_unique_constraints("training_records"))
        if "uq_training_user_request" not in indexes:
            conn.execute(text("CREATE UNIQUE INDEX uq_training_user_request ON training_records (user_id, request_key)"))


def ensure_comment_columns(engine):
    with engine.begin() as conn:
        columns={c['name'] for c in inspect(conn).get_columns('post_comments')}
        for name,definition in {'reply_to_id':'INTEGER NULL','request_key':'VARCHAR(64) NULL','deleted_at':'DATETIME NULL'}.items():
            if name not in columns:conn.execute(text(f'ALTER TABLE post_comments ADD COLUMN {name} {definition}'))
        indexes={i['name'] for i in inspect(conn).get_indexes('post_comments')}
        indexes.update(i['name'] for i in inspect(conn).get_unique_constraints('post_comments'))
        if 'uq_comment_user_request' not in indexes:
            conn.execute(text('CREATE UNIQUE INDEX uq_comment_user_request ON post_comments (user_id,request_key)'))


def ensure_report_columns(engine):
    with engine.begin() as conn:
        columns={c['name'] for c in inspect(conn).get_columns('reports')}
        for name,definition in {'action':"VARCHAR(30) NOT NULL DEFAULT ''",'handled_by':'INTEGER NULL','resolved_at':'DATETIME NULL','target_user_id':'INTEGER NULL'}.items():
            if name not in columns:conn.execute(text(f'ALTER TABLE reports ADD COLUMN {name} {definition}'))


def ensure_game_columns(engine):
    with engine.begin() as conn:
        columns={c['name'] for c in inspect(conn).get_columns('games')}
        if 'request_key' not in columns:
            conn.execute(text('ALTER TABLE games ADD COLUMN request_key VARCHAR(64) NULL'))
        indexes={i['name'] for i in inspect(conn).get_indexes('games')}
        indexes.update(i['name'] for i in inspect(conn).get_unique_constraints('games'))
        if 'uq_game_host_request' not in indexes:
            conn.execute(text('CREATE UNIQUE INDEX uq_game_host_request ON games (host_id,request_key)'))
