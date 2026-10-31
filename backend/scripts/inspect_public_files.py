"""Inventory public uploads without deleting or modifying anything."""
from collections import Counter
from pathlib import Path
import argparse
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main(argv=None):
    parser=argparse.ArgumentParser(description='检查公开图片和视频；只检查，不修改资料或删除文件。')
    parser.parse_args(argv)
    from app.db.session import SessionLocal
    from app.services.public_file_audit import inspect_public_files
    with SessionLocal() as db:
        report=inspect_public_files(db)
    counts=Counter(item.status for item in report.items)
    print('公开文件检查结果（未修改文件或记录）')
    for status,label in [('in_use','内容仍在使用'),('upload_only','仅有上传记录，可能是未发送草稿'),
                         ('queued','已登记等待清理'),('untracked','未找到对应记录，需核对'),
                         ('missing','记录中的文件未找到'),('needs_review','目录或文件需单独核对')]:
        print(f'{label}：{counts[status]}')
    print(f'全部待清理名单：{report.pending_cleanup}；正在使用或草稿文件不会自动删除。')
    return 1 if counts['untracked'] or counts['missing'] or counts['needs_review'] else 0


if __name__=='__main__':
    raise SystemExit(main())
