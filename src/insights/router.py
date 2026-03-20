from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from src.db.session import get_db
from src.insights.service import AnalyticsService
from src.insights.schemas import LeaderboardQuerySchema, DecadeQuerySchema

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get(
    "/leaderboard",
    summary="Top games by metric (meta_score, user_review, total_sales)",
)
def get_leaderboard(
    metric: str = Query(default="total_sales", example="meta_score"),
    genre: Optional[str] = Query(default=None, example="Action"),
    platform: Optional[str] = Query(default=None, example="PS4"),
    year_from: Optional[int] = Query(default=None, example=2000),
    year_to: Optional[int] = Query(default=None, example=2020),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = LeaderboardQuerySchema(
        metric=metric, genre=genre, platform=platform,
        year_from=year_from, year_to=year_to, limit=limit,
    )
    return AnalyticsService(db).get_leaderboard(query)


@router.get(
    "/verdict/game/{game_id}",
    summary="Verdict Machine -- game-level verdict by game_id (as returned by /api/games/search)",
)
def get_verdict_by_game_id(game_id: str, db: Session = Depends(get_db)):
    return AnalyticsService(db).get_verdict_by_game_id(game_id)


@router.get(
    "/verdict/{game_release_id}",
    summary="Verdict Machine -- classifies a game as All-Time Classic, Hidden Gem, Cult Classic etc.",
)
def get_verdict(game_release_id: str, db: Session = Depends(get_db)):
    return AnalyticsService(db).get_verdict(game_release_id)


@router.get(
    "/controversy",
    summary="Games where critics and players most disagreed",
)
def get_controversy(
    platform: Optional[str] = Query(default=None),
    year_from: Optional[int] = Query(default=None),
    year_to: Optional[int] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = LeaderboardQuerySchema(platform=platform, year_from=year_from, year_to=year_to, limit=limit)
    return AnalyticsService(db).get_controversy(query)


@router.get(
    "/hidden-gems",
    summary="High user scores but overlooked commercially",
)
def get_hidden_gems(
    platform: Optional[str] = Query(default=None),
    year_from: Optional[int] = Query(default=None),
    year_to: Optional[int] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = LeaderboardQuerySchema(platform=platform, year_from=year_from, year_to=year_to, limit=limit)
    return AnalyticsService(db).get_hidden_gems(query)


@router.get(
    "/decade-trends",
    summary="Gaming trends and stats grouped by decade",
)
def get_decade_trends(
    decade: Optional[int] = Query(default=None, example=2000),
    genre: Optional[str] = Query(default=None, example="Action"),
    db: Session = Depends(get_db),
):
    query = DecadeQuerySchema(decade=decade, genre=genre)
    return AnalyticsService(db).get_decade_trends(query)


@router.get(
    "/platform-dominance",
    summary="Which platforms dominated each gaming era",
)
def get_platform_dominance(
    decade: Optional[int] = Query(default=None, example=2000),
    db: Session = Depends(get_db),
):
    query = DecadeQuerySchema(decade=decade)
    return AnalyticsService(db).get_platform_dominance(query)


@router.get("/stats", summary="Database statistics")
def get_stats(db: Session = Depends(get_db)):
    from sqlalchemy import func
    from src.db.models import GameRelease
    total = db.query(func.count(GameRelease.id)).scalar()
    full = db.query(func.count(GameRelease.id)).filter(
        GameRelease.has_metacritic == True,
        GameRelease.has_vgchartz == True
    ).scalar()
    return {"total_releases": total, "with_full_data": full}