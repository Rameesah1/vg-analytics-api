import strawberry
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, asc
from fastapi import Depends
from strawberry.types import Info

from src.db.session import get_db
from src.db.models import GameRelease, Game, Platform, Developer, GameReleaseDeveloper
from src.graphql.schema import (
    GameType, GamePage, VerdictType, DeveloperType,
    ControversyType, DecadeTrendType,
)


def _compute_verdict(meta_score, user_review, total_sales) -> VerdictType:
    critic = float(meta_score) if meta_score else 0
    user = (float(user_review) if user_review else 0) * 10
    sales = min((float(total_sales) if total_sales else 0) / 20 * 100, 100)
    has_data = meta_score is not None and user_review is not None
    has_sales = total_sales is not None and float(total_sales) > 0
    divergence = abs(critic - user)

    if has_data and has_sales:
        confidence = "high"
    elif has_data:
        confidence = "medium"
    else:
        confidence = "low"

    if not has_data:
        classification, explanation = "Unrated", "Insufficient review data to classify this game."
    elif critic >= 90 and user >= 85:
        classification, explanation = "All-Time Classic", "Critically acclaimed and beloved by players."
    elif user >= 80 and critic < 70 and divergence >= 20:
        classification, explanation = "Cult Classic", "Critics dismissed it but players discovered something special."
    elif critic >= 80 and user < 60 and divergence >= 20:
        classification, explanation = "Critic Darling", "The press loved it but players were left cold."
    elif has_sales and sales >= 50 and critic < 70 and user < 70:
        classification, explanation = "Overhyped", "Massive commercial success that failed to impress."
    elif user >= 75 and (not has_sales or sales < 15):
        classification, explanation = "Hidden Gem", "Fans loved it but it flew under the radar commercially."
    elif has_sales and sales >= 40 and critic >= 70:
        classification, explanation = "Commercial Hit", "Strong sales backed by solid critical reception."
    elif divergence >= 25:
        classification, explanation = "Divisive", "Critics and players fundamentally disagreed on this one."
    elif critic >= 80 and user >= 75:
        classification, explanation = "Great Game", "Strong scores across the board."
    else:
        classification, explanation = "Solid Title", "A well-rounded game without any standout extremes."

    return VerdictType(
        classification=classification,
        explanation=explanation,
        confidence=confidence,
        critic=round(critic, 1),
        user=round(user, 1),
        sales=round(sales, 1),
        divergence=round(divergence, 1),
    )


def _get_developers_for_release(db: Session, release_id) -> list[DeveloperType]:
    devs = (
        db.query(Developer.id, Developer.name, Developer.country)
        .join(GameReleaseDeveloper, GameReleaseDeveloper.developer_id == Developer.id)
        .filter(GameReleaseDeveloper.game_release_id == release_id)
        .all()
    )
    return [DeveloperType(id=d.id, name=d.name, country=d.country) for d in devs]


def _row_to_game_type(row, db: Session, include_verdict=False, include_developers=False) -> GameType:
    game = GameType(
        id=row.id,
        canonical_title=row.canonical_title,
        release_year=row.release_year,
        platform=row.platform,
        total_sales=float(row.total_sales) if row.total_sales else None,
        meta_score=float(row.meta_score) if row.meta_score else None,
        user_review=float(row.user_review) if row.user_review else None,
        summary=row.summary,
        match_confidence=float(row.match_confidence) if row.match_confidence else None,
        has_vgchartz=row.has_vgchartz,
        has_metacritic=row.has_metacritic,
    )

    # only resolve nested fields if explicitly requested in the query
    # this avoids the N+1 problem -- we only hit the DB when the client asks for it
    if include_verdict:
        game.verdict = _compute_verdict(row.meta_score, row.user_review, row.total_sales)
    if include_developers:
        game.developers = _get_developers_for_release(db, row.id)

    return game


@strawberry.type
class Query:

    @strawberry.field(description="Get a single game release by ID, with optional nested verdict and developers")
    def game(
        self,
        id: str,
        include_verdict: bool = False,
        include_developers: bool = False,
        info: Info = None,
    ) -> Optional[GameType]:
        db: Session = info.context["db"]
        row = (
            db.query(
                GameRelease.id,
                Game.canonical_title,
                GameRelease.release_year,
                Platform.name.label("platform"),
                GameRelease.total_sales,
                GameRelease.meta_score,
                GameRelease.user_review,
                GameRelease.summary,
                GameRelease.match_confidence,
                GameRelease.has_vgchartz,
                GameRelease.has_metacritic,
            )
            .join(Game, GameRelease.game_id == Game.id)
            .join(Platform, GameRelease.platform_id == Platform.id)
            .filter(GameRelease.id == id)
            .first()
        )
        if not row:
            return None
        return _row_to_game_type(row, db, include_verdict, include_developers)

    @strawberry.field(description="Search and filter game releases. Supports title, platform, genre, year range and pagination")
    def games(
        self,
        title: Optional[str] = None,
        platform: Optional[str] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        page: int = 1,
        limit: int = 20,
        info: Info = None,
    ) -> GamePage:
        db: Session = info.context["db"]
        offset = (page - 1) * limit

        conditions = []
        if title:
            conditions.append(Game.canonical_title.ilike(f"%{title}%"))
        if platform:
            conditions.append(Platform.name.ilike(f"%{platform}%"))
        if year_from:
            conditions.append(GameRelease.release_year >= year_from)
        if year_to:
            conditions.append(GameRelease.release_year <= year_to)

        base = (
            db.query(
                GameRelease.id,
                Game.canonical_title,
                GameRelease.release_year,
                Platform.name.label("platform"),
                GameRelease.total_sales,
                GameRelease.meta_score,
                GameRelease.user_review,
                GameRelease.summary,
                GameRelease.match_confidence,
                GameRelease.has_vgchartz,
                GameRelease.has_metacritic,
            )
            .join(Game, GameRelease.game_id == Game.id)
            .join(Platform, GameRelease.platform_id == Platform.id)
        )

        if conditions:
            base = base.filter(and_(*conditions))

        rows = base.order_by(desc(GameRelease.total_sales).nullslast()).limit(limit).offset(offset).all()
        total = base.count()

        return GamePage(
            data=[_row_to_game_type(r, db) for r in rows],
            total=total,
            page=page,
            total_pages=-(-total // limit),
        )

    @strawberry.field(description="Get the Verdict Machine classification for a game release")
    def verdict(self, id: str, info: Info = None) -> Optional[VerdictType]:
        db: Session = info.context["db"]
        row = (
            db.query(
                GameRelease.meta_score,
                GameRelease.user_review,
                GameRelease.total_sales,
            )
            .filter(GameRelease.id == id)
            .first()
        )
        if not row:
            return None
        return _compute_verdict(row.meta_score, row.user_review, row.total_sales)

    @strawberry.field(description="Games where critics and players most disagreed -- ranked by divergence score")
    def controversy(self, limit: int = 10, info: Info = None) -> list[ControversyType]:
        db: Session = info.context["db"]
        divergence_expr = func.abs(
            GameRelease.meta_score - (GameRelease.user_review * 10)
        )

        rows = (
            db.query(
                GameRelease.id,
                Game.canonical_title.label("title"),
                Platform.name.label("platform"),
                GameRelease.release_year,
                GameRelease.meta_score,
                GameRelease.user_review,
                func.round(divergence_expr, 2).label("divergence"),
            )
            .join(Game, GameRelease.game_id == Game.id)
            .join(Platform, GameRelease.platform_id == Platform.id)
            .filter(
                GameRelease.meta_score.isnot(None),
                GameRelease.user_review.isnot(None),
            )
            .order_by(desc(divergence_expr))
            .limit(limit)
            .all()
        )

        return [
            ControversyType(
                id=r.id,
                title=r.title,
                platform=r.platform,
                release_year=r.release_year,
                meta_score=float(r.meta_score) if r.meta_score else None,
                user_review=float(r.user_review) if r.user_review else None,
                divergence=float(r.divergence),
            )
            for r in rows
        ]

    @strawberry.field(description="Gaming trends grouped by decade -- release counts, average scores and total sales")
    def decade_trends(self, info: Info = None) -> list[DecadeTrendType]:
        db: Session = info.context["db"]
        decade_expr = func.floor(GameRelease.release_year / 10) * 10

        rows = (
            db.query(
                decade_expr.label("decade"),
                func.count().label("release_count"),
                func.round(func.avg(GameRelease.meta_score), 2).label("avg_meta_score"),
                func.round(func.avg(GameRelease.user_review), 2).label("avg_user_review"),
                func.round(func.sum(GameRelease.total_sales), 2).label("total_sales"),
            )
            .filter(GameRelease.release_year.isnot(None))
            .group_by(decade_expr)
            .order_by(asc(decade_expr))
            .all()
        )

        return [
            DecadeTrendType(
                decade=int(r.decade),
                release_count=r.release_count,
                avg_meta_score=float(r.avg_meta_score) if r.avg_meta_score else None,
                avg_user_review=float(r.avg_user_review) if r.avg_user_review else None,
                total_sales=float(r.total_sales) if r.total_sales else None,
            )
            for r in rows
        ]


schema = strawberry.Schema(query=Query)