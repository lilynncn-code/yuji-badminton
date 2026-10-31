"""Run one import. --file imports an authorized local snapshot without changing settings."""
import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.db.session import SessionLocal
from app.services.match_sync import sync_matches


def main():
    parser = argparse.ArgumentParser(description="同步后台比赛，或人工导入完整比赛文件")
    parser.add_argument("--file", default="", help="授权比赛 JSON 文件的本机路径")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    with SessionLocal() as db:
        result = sync_matches(db, file_path=args.file)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
