"""Run a bounded match import on startup and every fifteen minutes."""
import logging
from threading import Event, Thread

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.match_sync import sync_matches

logger = logging.getLogger(__name__)


class MatchScheduler:
    def __init__(self, session_factory=SessionLocal):
        self.session_factory = session_factory
        self.stopped = Event()
        self.thread = None

    def check(self):
        try:
            with self.session_factory() as db:
                return sync_matches(db, only_if_due=True)
        except Exception:
            logger.error("比赛定时检查未能连接后台，下次继续重试")
            return {"ok": False}

    def _run(self):
        while not self.stopped.is_set():
            self.check()
            if self.stopped.wait(900):
                break

    def start(self):
        if settings.match_sync_enabled and not self.thread:
            self.thread = Thread(target=self._run, name="match-sync", daemon=True)
            self.thread.start()

    def stop(self):
        self.stopped.set()
        if self.thread:
            self.thread.join(timeout=1)


match_scheduler = MatchScheduler()
