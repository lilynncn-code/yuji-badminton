"""Inspect or explicitly assign report-review access; never grants access on startup.
Run from backend: .venv/bin/python scripts/report_reviewer.py USERNAME
Use --set allow|deny --confirm USERNAME to change this single account.
"""
import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.db.session import SessionLocal
from app.models.user import User


def main():
    parser=argparse.ArgumentParser(description='查看或设置单个账号的举报处理权限')
    parser.add_argument('username')
    parser.add_argument('--set',choices=['allow','deny'])
    parser.add_argument('--confirm')
    args=parser.parse_args()
    if args.set and args.confirm!=args.username:parser.error('更改时须用 --confirm 重复填写相同账号名')
    with SessionLocal() as db:
        user=db.query(User).filter_by(username=args.username).with_for_update().first()
        if not user:parser.error('账号不存在')
        if args.set:
            user.can_review_reports=int(args.set=='allow')
            db.commit()
        print('账号：'+user.username+'；举报处理权限：'+('已允许' if user.can_review_reports==1 else '未允许'))


if __name__=='__main__':main()
