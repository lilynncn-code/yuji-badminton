"""Import a complete, authorized JSON snapshot. Never fetch competition pages on phones."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.content import Event, Match, MatchSyncState

logger = logging.getLogger(__name__)
MAX_BYTES = 10 * 1024 * 1024
STATUSES = {"scheduled", "live", "finished", "cancelled", "postponed", "walkover", "retired"}


class SourceError(ValueError):
    """A message suitable for the public match pages (no credentials or local paths)."""


def _date(value: Any, label: str = "时间") -> Optional[datetime]:
    if value in (None, ""):
        return None
    try:
        result = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        raise SourceError(f"比赛来源的{label}不正确，已保留上次内容") from None
    if result.tzinfo:
        result = result.astimezone(timezone.utc).replace(tzinfo=None)
    return result


def _text(value: Any, label: str, maximum: int, required: bool = False) -> str:
    if value is None:
        value = ""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        value = str(value)
    if not isinstance(value, str):
        raise SourceError(f"比赛来源的{label}格式不正确")
    value = value.strip()
    if (required and not value) or len(value) > maximum:
        raise SourceError(f"比赛来源的{label}缺失或过长")
    return value


def _url(value: Any, label: str) -> str:
    value = _text(value, label, 500)
    if not value:
        return ""
    try:
        parsed = urlsplit(value)
        sensitive = {"token", "key", "apikey", "api_key", "secret", "password", "authorization", "access_token"}
        valid = parsed.scheme in {"https", "http"} and parsed.hostname and not parsed.username and not parsed.password and not (sensitive & {key.lower() for key in parse_qs(parsed.query)})
    except ValueError:
        valid = False
    # Public attribution addresses must never carry a private source token.
    if not valid:
        raise SourceError(f"比赛来源的{label}应为不带账号和密钥的公开网页地址")
    return value


def _source_payload(file_path: str = "") -> Any:
    path_value = file_path or settings.match_source_file
    try:
        if path_value:
            with Path(path_value).expanduser().open("rb") as stream:
                raw = stream.read(MAX_BYTES + 1)
        elif settings.match_source_url:
            parsed = urlsplit(settings.match_source_url)
            if parsed.scheme not in {"https", "http"}:
                raise SourceError("比赛来源地址不正确")
            headers = {"Accept": "application/json", "User-Agent": "HaoYu match updater"}
            if settings.match_source_token:
                headers["Authorization"] = "Bearer " + settings.match_source_token
            with urlopen(Request(settings.match_source_url, headers=headers), timeout=settings.match_sync_timeout) as response:
                raw = response.read(MAX_BYTES + 1)
        else:
            raise SourceError("比赛来源尚未接通，请稍后再试")
        if len(raw) > MAX_BYTES:
            raise SourceError("比赛来源内容过大，已保留上次内容")
        return json.loads(raw.decode("utf-8-sig"))
    except SourceError:
        raise
    except HTTPError as exc:
        raise SourceError(f"比赛来源暂时无法读取（{exc.code}），已保留上次内容") from None
    except (URLError, TimeoutError, OSError):
        raise SourceError("比赛来源连接失败，已保留上次内容") from None
    except (UnicodeError, ValueError):
        raise SourceError("比赛来源内容无法读取，已保留上次内容") from None


def _normalise(payload: Any) -> tuple[list[dict], list[dict], Optional[datetime]]:
    if not isinstance(payload, dict):
        raise SourceError("比赛来源必须包含完整的赛事和比赛列表")
    raw_events, raw_matches = payload.get("events"), payload.get("matches")
    if not isinstance(raw_events, list) or not raw_events or not isinstance(raw_matches, list) or not raw_matches:
        raise SourceError("比赛来源没有完整的赛事和比赛，已保留上次内容")
    if len(raw_events) > 200 or len(raw_matches) > 10000:
        raise SourceError("比赛来源数量过多，已保留上次内容")
    if payload.get("complete", True) is not True:
        raise SourceError("比赛来源尚未读完整，已保留上次内容")
    source_updated = _date(payload.get("source_updated_at"), "来源更新时间")
    events, matches, event_ids, match_ids = [], [], set(), set()
    public_source = _url(payload.get("source_url", ""), "公开来源地址")
    for raw in raw_events:
        if not isinstance(raw, dict):
            raise SourceError("赛事内容格式不正确")
        eid = _text(raw.get("id"), "赛事编号", 80, True)
        if eid in event_ids:
            raise SourceError("赛事编号重复，已保留上次内容")
        event_ids.add(eid)
        start = _date(raw.get("start_date"), "赛事开始时间")
        end = _date(raw.get("end_date"), "赛事结束时间")
        if not start or not end or end < start:
            raise SourceError("赛事起止日期不完整或顺序不正确")
        event_status = raw.get("status", "upcoming")
        if event_status not in {"upcoming", "ongoing", "finished", "cancelled"}:
            raise SourceError("赛事状态不正确")
        events.append(dict(id=eid, title=_text(raw.get("name"), "赛事名称", 160, True),
            start_date=start.date(), end_date=end.date(), location=_text(raw.get("location"), "赛事地点", 120),
            status=event_status, image_url=_url(raw.get("image_url"), "赛事图片地址"),
            source_url=_url(raw.get("source_url", public_source), "赛事来源地址"),
            summary=_text(raw.get("summary"), "赛事说明", 10000), level=_text(raw.get("level"), "赛事级别", 80),
            prize=_text(raw.get("prize"), "赛事奖金", 80), venue=_text(raw.get("venue"), "赛事场馆", 160),
            schedule_text=""))
    event_names = {row["id"]: row["title"] for row in events}
    for raw in raw_matches:
        if not isinstance(raw, dict):
            raise SourceError("比赛内容格式不正确")
        mid = _text(raw.get("id"), "比赛编号", 120, True)
        eid = _text(raw.get("event_id"), "比赛所属赛事", 80, True)
        if mid.startswith("history-") or mid in match_ids or eid not in event_ids:
            raise SourceError("比赛编号重复、占用历史编号或找不到所属赛事")
        if any(char in mid for char in "/?#\\"):
            raise SourceError("比赛编号不能包含斜线、问号或井号")
        match_ids.add(mid)
        player1 = _text(raw.get("player1"), "第一方选手", 200, True)
        player2 = _text(raw.get("player2"), "第二方选手", 200, True)
        winner = _text(raw.get("winner"), "胜者", 200)
        status = raw.get("status", "scheduled")
        if status not in STATUSES or (winner and winner not in {player1, player2}) or (status == "cancelled" and winner):
            raise SourceError("比赛状态或胜者不正确")
        matches.append(dict(id=mid, event_id=eid, event_name=event_names[eid],
            discipline=_text(raw.get("discipline"), "比赛项目", 40, True),
            round=_text(raw.get("round"), "比赛轮次", 60, True), court=_text(raw.get("court"), "比赛场地", 160),
            scheduled_at=_date(raw.get("scheduled_at"), "比赛时间"), player1=player1, player2=player2,
            score1=_text(raw.get("score1"), "第一方比分", 120), score2=_text(raw.get("score2"), "第二方比分", 120),
            score_text=_text(raw.get("score_text"), "单局比分", 180), winner=winner, status=status,
            image_url=_url(raw.get("image_url"), "比赛图片地址"), image_source=_text(raw.get("image_source"), "图片说明", 500),
            report=_text(raw.get("report"), "比赛说明", 10000), replay_url=_url(raw.get("replay_url"), "回放地址"),
            source_url=_url(raw.get("source_url", public_source), "比赛公开来源地址"),
            source_updated_at=_date(raw.get("source_updated_at"), "比赛来源更新时间") or source_updated))
    return events, matches, source_updated


def _locked_state(db: Session) -> MatchSyncState:
    # The singleton row serializes imports across server processes and manual runs.
    if db.get(MatchSyncState, "matches") is None:
        try:
            with db.begin_nested():
                db.add(MatchSyncState(id="matches", last_error=""))
                db.flush()
        except IntegrityError:
            pass
    return db.query(MatchSyncState).filter_by(id="matches").populate_existing().with_for_update().one()


def sync_matches(db: Session, payload: Any = None, *, file_path: str = "", only_if_due: bool = False) -> dict[str, Any]:
    """Validate everything before writing; rollback the whole snapshot on any failure."""
    attempted_at = datetime.utcnow()
    try:
        state = _locked_state(db)
        now = datetime.utcnow()
        attempted_at = now
        if only_if_due and state.last_attempt_at and (now - state.last_attempt_at).total_seconds() < 900 and (state.last_success_at or state.last_error):
            db.rollback()
            return {"ok": True, "skipped": True}
        state.last_attempt_at = now
        source = _source_payload(file_path) if payload is None else payload
        events, rows, source_updated = _normalise(source)
        if source_updated and state.source_updated_at and source_updated < state.source_updated_at:
            raise SourceError("比赛来源返回了更早的内容，已保留上次内容")
        saved_at = datetime.utcnow()
        for event in events:
            existing = db.get(Event, event["id"])
            if existing:
                for key, value in event.items():
                    setattr(existing, key, value)
                existing.updated_at = saved_at
            else:
                db.add(Event(**event, updated_at=saved_at))
        # Flush deletions before additions even if this Session previously loaded matches.
        db.query(Match).delete(synchronize_session="fetch")
        db.flush()
        db.add_all(Match(**row, saved_at=saved_at) for row in rows)
        state.last_success_at, state.source_updated_at = saved_at, source_updated
        state.source_url, state.last_error = source.get("source_url", ""), ""
        db.commit()
        logger.info("比赛同步成功：%s 站赛事，%s 场比赛", len(events), len(rows))
        return {"ok": True, "count": len(rows), "saved_at": saved_at.isoformat() + "Z"}
    except Exception as exc:
        db.rollback()
        message = str(exc) if isinstance(exc, SourceError) else "比赛更新未能保存，已保留上次内容"
        # Never publish a raw HTTP/DB exception: it may contain tokens or passwords.
        try:
            state = _locked_state(db)
            if state.last_attempt_at and state.last_attempt_at > attempted_at:
                db.rollback()
                return {"ok": False, "error": message}
            state.last_attempt_at, state.last_error = datetime.utcnow(), message
            db.commit()
        except Exception:
            db.rollback()
            logger.error("比赛同步失败，失败记录也未能保存")
        logger.warning("比赛同步失败：%s", message)
        return {"ok": False, "error": message}
