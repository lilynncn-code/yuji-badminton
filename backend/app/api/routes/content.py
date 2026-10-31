from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.content import Event, Match, MatchSyncState

from app.schemas.content import (
    EventDetailResponse,
    EventListItem,
    EventListResponse,
    NewsListItem,
    NewsListResponse,
    RankingDiscipline,
    RankingItem,
    RankingListResponse,
    RankingPlayer,
    MatchDetailResponse,
    MatchItem,
    MatchListResponse,
    MatchSyncInfo,
)

router = APIRouter(prefix="/content", tags=["content"])

SOURCE_URL = "https://bwfbadminton.com"
UPDATED_AT = datetime(2026, 6, 27, 9, 0, 0)

DISCIPLINE_TITLES: dict[RankingDiscipline, str] = {
    "men_single": "男单",
    "women_single": "女单",
    "men_double": "男双",
    "women_double": "女双",
    "mixed_double": "混双",
}

def ranking_item(
    rank: int,
    previous_rank: int,
    points: int,
    players: list[RankingPlayer],
    source_url: str = SOURCE_URL,
    updated_at: datetime = UPDATED_AT,
) -> RankingItem:
    return RankingItem(
        rank=rank,
        previous_rank=previous_rank,
        points=points,
        updated_at=updated_at,
        source_url=source_url,
        players=players,
    )


RANKINGS: dict[RankingDiscipline, list[RankingItem]] = {
    "men_single": [
        ranking_item(1, 1, 99615, [RankingPlayer(name="石宇奇", country="中国")]),
        ranking_item(2, 2, 94337, [RankingPlayer(name="安赛龙", country="丹麦")]),
        ranking_item(3, 4, 88406, [RankingPlayer(name="李诗沣", country="中国")]),
    ],
    "women_single": [
        ranking_item(1, 1, 101337, [RankingPlayer(name="安洗莹", country="韩国")]),
        ranking_item(2, 2, 94082, [RankingPlayer(name="王祉怡", country="中国")]),
        ranking_item(3, 3, 89321, [RankingPlayer(name="陈雨菲", country="中国")]),
    ],
    "men_double": [
        ranking_item(
            1,
            1,
            98520,
            [
                RankingPlayer(name="梁伟铿", country="中国"),
                RankingPlayer(name="王昶", country="中国"),
            ],
        ),
        ranking_item(
            2,
            2,
            93640,
            [
                RankingPlayer(name="金元昊", country="韩国"),
                RankingPlayer(name="徐承宰", country="韩国"),
            ],
        ),
        ranking_item(
            3,
            4,
            88770,
            [
                RankingPlayer(name="谢定峰", country="马来西亚"),
                RankingPlayer(name="苏伟译", country="马来西亚"),
            ],
        ),
    ],
    "women_double": [
        ranking_item(
            1,
            1,
            102880,
            [
                RankingPlayer(name="刘圣书", country="中国"),
                RankingPlayer(name="谭宁", country="中国"),
            ],
        ),
        ranking_item(
            2,
            2,
            96220,
            [
                RankingPlayer(name="白荷娜", country="韩国"),
                RankingPlayer(name="李昭希", country="韩国"),
            ],
        ),
        ranking_item(
            3,
            3,
            90410,
            [
                RankingPlayer(name="松山奈未", country="日本"),
                RankingPlayer(name="志田千阳", country="日本"),
            ],
        ),
    ],
    "mixed_double": [
        ranking_item(
            1,
            1,
            100120,
            [
                RankingPlayer(name="蒋振邦", country="中国"),
                RankingPlayer(name="魏雅欣", country="中国"),
            ],
        ),
        ranking_item(
            2,
            2,
            97850,
            [
                RankingPlayer(name="冯彦哲", country="中国"),
                RankingPlayer(name="黄东萍", country="中国"),
            ],
        ),
        ranking_item(
            3,
            4,
            91790,
            [
                RankingPlayer(name="德差波", country="泰国"),
                RankingPlayer(name="沙西丽", country="泰国"),
            ],
        ),
    ],
}

EVENTS: list[EventDetailResponse] = [
    EventDetailResponse(
        id="indonesia-open-2026",
        title="印尼公开赛",
        start_date=date(2026, 6, 2),
        end_date=date(2026, 6, 7),
        location="印度尼西亚 雅加达",
        status="finished",
        image_url="https://images.unsplash.com/photo-1626224583764-f87db24ac4ea",
        updated_at=UPDATED_AT,
        source_url="https://bwfbadminton.com/tournament/",
        summary="世界巡回赛高级别赛事，聚集多位顶尖选手。",
        level="Super 1000",
        prize="1,450,000 美元",
        venue="Istora Senayan",
        schedule=["6月2日 首轮", "6月5日 四分之一决赛", "6月6日 半决赛", "6月7日 决赛"],
    ),
    EventDetailResponse(
        id="japan-open-2026",
        title="日本公开赛",
        start_date=date(2026, 7, 14),
        end_date=date(2026, 7, 19),
        location="日本 东京",
        status="upcoming",
        image_url="https://images.unsplash.com/photo-1613918431703-aa50889e3be3",
        updated_at=UPDATED_AT,
        source_url="https://bwfbadminton.com/tournament/",
        summary="夏季重要分站赛，五个单项都会产生冠军。",
        level="Super 750",
        prize="950,000 美元",
        venue="Tokyo Metropolitan Gymnasium",
        schedule=["7月14日 首轮", "7月17日 四分之一决赛", "7月18日 半决赛", "7月19日 决赛"],
    ),
    EventDetailResponse(
        id="china-masters-2026",
        title="中国大师赛",
        start_date=date(2026, 9, 15),
        end_date=date(2026, 9, 20),
        location="中国 深圳",
        status="upcoming",
        image_url="https://images.unsplash.com/photo-1600679472829-3044539ce8ed",
        updated_at=UPDATED_AT,
        source_url="https://bwfbadminton.com/tournament/",
        summary="中国主场高级别赛事，适合作为本地观赛重点内容。",
        level="Super 750",
        prize="1,150,000 美元",
        venue="深圳体育馆",
        schedule=["9月15日 首轮", "9月18日 四分之一决赛", "9月19日 半决赛", "9月20日 决赛"],
    ),
]

NEWS: list[NewsListItem] = [
    NewsListItem(
        id="china-team-preview",
        title="中国队公布夏季参赛重点",
        summary="多位主力将连续出战亚洲赛程，双打项目保持稳定搭档。",
        image_url="https://images.unsplash.com/photo-1599474924187-334a4ae5bd3c",
        body="中国队将把夏季赛程作为阵容磨合的重要阶段。单打项目继续争取高分，双打项目则以稳定配合和减少失误为重点。",
        source="好羽整理",
        source_url="https://bwfbadminton.com/news/",
        published_at=datetime(2026, 6, 27, 8, 30, 0),
        updated_at=UPDATED_AT,
    ),
    NewsListItem(
        id="tour-calendar-update",
        title="世界巡回赛下半年赛程密集",
        summary="7月至10月将连续进行多站高级别赛事，排名竞争会更激烈。",
        image_url="https://images.unsplash.com/photo-1521537634581-0dced2fee2ef",
        body="下半年赛程包含日本、中国、欧洲多站赛事。球员需要在积分、体能和伤病管理之间做好平衡。",
        source="好羽整理",
        source_url="https://bwfbadminton.com/news/",
        published_at=datetime(2026, 6, 26, 20, 0, 0),
        updated_at=UPDATED_AT,
    ),
    NewsListItem(
        id="doubles-form-watch",
        title="双打项目进入抢分窗口",
        summary="多对组合近期状态接近，连续参赛的表现可能影响前八席位。",
        image_url="https://images.unsplash.com/photo-1567220720374-a67f33f8a6b5",
        body="男双、女双和混双的前列差距不大。接下来几站比赛的签表和临场发挥，会直接影响年终排名格局。",
        source="好羽整理",
        source_url="https://bwfbadminton.com/news/",
        published_at=datetime(2026, 6, 25, 18, 45, 0),
        updated_at=UPDATED_AT,
    ),
]


@router.get("/rankings", response_model=RankingListResponse)
def list_rankings(
    discipline: RankingDiscipline = Query(default="men_single", description="men_single/women_single/men_double/women_double/mixed_double")
) -> RankingListResponse:
    return RankingListResponse(
        discipline=discipline,
        title=DISCIPLINE_TITLES[discipline],
        updated_at=UPDATED_AT,
        source_url=SOURCE_URL,
        items=RANKINGS[discipline],
    )


@router.get("/events", response_model=EventListResponse)
def list_events() -> EventListResponse:
    items = [
        EventListItem(
            id=event.id,
            title=event.title,
            start_date=event.start_date,
            end_date=event.end_date,
            location=event.location,
            status=event.status,
            image_url=event.image_url,
            updated_at=event.updated_at,
            source_url=event.source_url,
        )
        for event in EVENTS
    ]
    return EventListResponse(updated_at=UPDATED_AT, items=items)


@router.get("/events/{event_id}", response_model=EventDetailResponse)
def get_event(event_id: str) -> EventDetailResponse:
    event = next((item for item in EVENTS if item.id == event_id), None)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="赛事不存在")
    return event


@router.get("/news", response_model=NewsListResponse)
def list_news() -> NewsListResponse:
    return NewsListResponse(updated_at=UPDATED_AT, items=NEWS)


def _match_item(row: Match) -> MatchItem:
    return MatchItem(
        id=row.id, event_id=row.event_id, event_name=row.event_name,
        discipline=row.discipline, round=row.round, court=row.court,
        scheduled_at=row.scheduled_at, player1=row.player1, player2=row.player2,
        score1=row.score1, score2=row.score2, score_text=row.score_text,
        winner=row.winner, status=row.status, image_url=row.image_url,
        image_source=row.image_source, report=row.report, replay_url=row.replay_url,
        source_url=row.source_url, source_updated_at=row.source_updated_at,
        saved_at=row.saved_at,
    )


def _sync_info(db: Session) -> MatchSyncInfo:
    state = db.get(MatchSyncState, "matches")
    if state is None:
        return MatchSyncInfo(using_old_data=True, last_error="比赛来源尚未接通，请稍后再试")
    overdue = not state.last_success_at or (datetime.utcnow() - state.last_success_at).total_seconds() > 1800
    return MatchSyncInfo(
        latest_updated_at=state.last_success_at,
        source_updated_at=state.source_updated_at,
        last_attempt_at=state.last_attempt_at,
        using_old_data=bool(state.last_error) or overdue,
        last_error=state.last_error or ("比赛有一段时间没有更新，请稍后再试" if overdue else ""),
        source_url=state.source_url,
    )


@router.get("/matches", response_model=MatchListResponse)
def list_matches(
    response: Response,
    event_id: Optional[str] = Query(default=None, max_length=80),
    limit: Optional[int] = Query(default=None, ge=1, le=500),
    db: Session = Depends(get_db),
) -> MatchListResponse:
    response.headers["Cache-Control"] = "no-store"
    # Event choices are independent of the homepage's small match limit.
    event_rows = (db.query(Event).filter(Event.id.in_(db.query(Match.event_id)))
                  .order_by(Event.start_date.desc(), Event.id.asc()).limit(5).all())
    query = db.query(Match)
    if event_id:
        query = query.filter(Match.event_id == event_id)
    else:
        query = query.filter(Match.event_id.in_([event.id for event in event_rows]))
    query = query.order_by(Match.scheduled_at.desc(), Match.id.asc())
    if limit:
        query = query.limit(limit)
    rows = query.all()
    sync = _sync_info(db)
    return MatchListResponse(
        updated_at=sync.latest_updated_at,
        events=[dict(id=event.id, name=event.title, start_date=event.start_date, end_date=event.end_date,
                     location=event.location, image_url=event.image_url, source_url=event.source_url,
                     summary=event.summary, status=event.status) for event in event_rows],
        items=[_match_item(row) for row in rows], sync=sync,
    )


@router.get("/matches/{match_id}", response_model=MatchDetailResponse)
def get_match(match_id: str, response: Response, db: Session = Depends(get_db)) -> MatchDetailResponse:
    response.headers["Cache-Control"] = "no-store"
    row = db.get(Match, match_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="比赛不存在或已被来源移除，请返回赛事页查看")
    return MatchDetailResponse(item=_match_item(row), sync=_sync_info(db))
