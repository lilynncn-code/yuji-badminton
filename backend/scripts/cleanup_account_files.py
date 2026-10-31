"""Retry only files queued by completed account-deletion requests.
Run from backend: .venv/bin/python scripts/cleanup_account_files.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.db.session import SessionLocal
from app.services.account_deletion import cleanup_account_files

if __name__ == '__main__':
    with SessionLocal() as db:
        remaining = cleanup_account_files(db)
    print(f'待清理文件剩余：{remaining}')
