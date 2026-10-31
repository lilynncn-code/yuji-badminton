"""Inspect legacy public chat images; --apply moves them with the service offline."""
import argparse
from collections import Counter
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main(argv=None):
    parser = argparse.ArgumentParser(description='检查旧聊天图片；默认不修改。实际整理前需停止服务。')
    parser.add_argument('--apply', action='store_true', help='将检查通过的旧图片改为按聊天读取，并清理旧地址')
    parser.add_argument('--offline', action='store_true', help='确认应用服务已停止，避免同时更改图片和消息')
    args = parser.parse_args(argv)
    if args.apply and not args.offline:
        parser.error('实际整理需先停止应用服务，再同时使用 --apply --offline')
    from app.db.session import SessionLocal
    from app.services.legacy_chat_images import move_legacy_chat_images
    with SessionLocal() as db:
        report = move_legacy_chat_images(db, apply=args.apply)
    counts = Counter(item.status for item in report.items)
    print('实际整理结果' if args.apply else '检查结果（未修改文件或记录）')
    print(f"可整理：{counts['ready']}；已整理：{counts['moved']}；待核对：{counts['needs_review']}；保存失败：{counts['failed']}")
    print(f'涉及消息：{sum(i.messages for i in report.items)}；待清理文件：{report.pending_cleanup}')
    leftovers = sum(i.leftover_copies for i in report.items)
    if leftovers:
        print(f'失败后未能移除的新增副本：{leftovers}，需核对后清理')
    return 1 if counts['needs_review'] or counts['failed'] or report.pending_cleanup or leftovers else 0


if __name__ == '__main__':
    raise SystemExit(main())
