from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, asc, desc, text
from src.db.models import Game, GameRelease, Platform
from src.games.schemas import GameQuerySchema


# maps query param names to SQLAlchemy columns
SORT_MAP = {
    "total_sales": GameRelease.total_sales,
    "meta_score": GameRelease.meta_score,
    "user_review": GameRelease.user_review,
    "release_year": GameRelease.release_year,
    "title": Game.canonical_title,
}


class GamesService:
    def __init__(self, db: Session):
        self.db = db

    def find_all(self, query: GameQuerySchema):
        offset = (query.page - 1) * query.limit
        sort_col = SORT_MAP.get(query.sort_by, GameRelease.total_sales)
        order_fn = asc if query.order == "asc" else desc

        # build dynamic conditions from query params
        conditions = []
        if query.title:
            conditions.append(Game.canonical_title.ilike(f"%{query.title}%"))
        if query.platform:
            conditions.append(Platform.name.ilike(f"%{query.platform}%"))
        if query.year_from:
            conditions.append(GameRelease.release_year >= query.year_from)
        if query.year_to:
            conditions.append(GameRelease.release_year <= query.year_to)

        # genre uses a raw subquery — many-to-many join
        if query.genre:
            conditions.append(
                text(f"""EXISTS (
                    SELECT 1 FROM game_release_genre grg
                    INNER JOIN genre g ON g.id = grg.genre_id
                    WHERE grg.game_release_id = game_release.id
                    AND g.name ILIKE '%{query.genre}%'
                )""")
            )

        where = and_(*conditions) if conditions else None

        # main data query
        base = (
            self.db.query(
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

        if where is not None:
            base = base.filter(where)

        rows = base.order_by(order_fn(sort_col).nullslast()).limit(query.limit).offset(offset).all()

        # separate count query for pagination meta
        count_q = (
            self.db.query(func.count())
            .select_from(GameRelease)
            .join(Game, GameRelease.game_id == Game.id)
            .join(Platform, GameRelease.platform_id == Platform.id)
        )
        if where is not None:
            count_q = count_q.filter(where)
        total = count_q.scalar()

        return {
            "data": [self._row_to_dict(r) for r in rows],
            "meta": {
                "total": total,
                "page": query.page,
                "limit": query.limit,
                "total_pages": -(-total // query.limit),  # ceiling division
                "has_next_page": query.page * query.limit < total,
                "has_previous_page": query.page > 1,
            },
        }

    def search_by_title(self, title: str, limit: int = 8):
        """One result per game (not per release) — returns game_id as id."""
        rows = (
            self.db.query(
                Game.id,
                Game.canonical_title,
                func.min(GameRelease.release_year).label("release_year"),
                func.round(func.avg(GameRelease.meta_score), 1).label("meta_score"),
            )
            .join(GameRelease, GameRelease.game_id == Game.id)
            .filter(
                Game.canonical_title.ilike(f"%{title}%"),
                GameRelease.meta_score.isnot(None),
            )
            .group_by(Game.id, Game.canonical_title)
            .order_by(desc(func.avg(GameRelease.meta_score)).nullslast())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": str(r.id),
                "canonical_title": r.canonical_title,
                "release_year": r.release_year,
                "meta_score": float(r.meta_score) if r.meta_score else None,
            }
            for r in rows
        ]

    def find_one(self, release_id: str):
        # full detail view including all sales breakdowns and provenance fields
        row = (
            self.db.query(
                GameRelease.id,
                GameRelease.game_id,
                Game.canonical_title,
                GameRelease.release_year,
                GameRelease.release_date,
                Platform.name.label("platform"),
                GameRelease.total_sales,
                GameRelease.na_sales,
                GameRelease.jp_sales,
                GameRelease.pal_sales,
                GameRelease.other_sales,
                GameRelease.vg_critic_score,
                GameRelease.meta_score,
                GameRelease.user_review,
                GameRelease.summary,
                GameRelease.match_confidence,
                GameRelease.match_strategy,
                GameRelease.has_vgchartz,
                GameRelease.has_metacritic,
            )
            .join(Game, GameRelease.game_id == Game.id)
            .join(Platform, GameRelease.platform_id == Platform.id)
            .filter(GameRelease.id == release_id)
            .first()
        )
        return self._row_to_detail_dict(row) if row else None

    def _row_to_dict(self, row) -> dict:
        return {
            "id": row.id,
            "canonical_title": row.canonical_title,
            "release_year": row.release_year,
            "platform": row.platform,
            "total_sales": float(row.total_sales) if row.total_sales else None,
            "meta_score": float(row.meta_score) if row.meta_score else None,
            "user_review": float(row.user_review) if row.user_review else None,
            "summary": row.summary,
            "match_confidence": float(row.match_confidence) if row.match_confidence else None,
            "has_vgchartz": row.has_vgchartz,
            "has_metacritic": row.has_metacritic,
        }

    def _row_to_detail_dict(self, row) -> dict:
        return {
            **self._row_to_dict(row),
            "game_id": str(row.game_id),
            "release_date": row.release_date,
            "na_sales": float(row.na_sales) if row.na_sales else None,
            "jp_sales": float(row.jp_sales) if row.jp_sales else None,
            "pal_sales": float(row.pal_sales) if row.pal_sales else None,
            "other_sales": float(row.other_sales) if row.other_sales else None,
            "vg_critic_score": float(row.vg_critic_score) if row.vg_critic_score else None,
            "match_strategy": row.match_strategy,
        }