from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from fastapi import HTTPException, status
from src.db.models import Developer, GameReleaseDeveloper, GameRelease, Game, Platform
from src.developers.schemas import DeveloperQuerySchema


class DevelopersService:
    def __init__(self, db: Session):
        self.db = db

    def find_all(self, query: DeveloperQuerySchema):
        offset = (query.page - 1) * query.limit

        base = (
            self.db.query(
                Developer.id,
                Developer.name,
                Developer.country,
                func.count(GameReleaseDeveloper.game_release_id.distinct()).label("release_count"),
                func.round(func.avg(GameRelease.meta_score), 2).label("avg_meta_score"),
                func.round(func.avg(GameRelease.user_review), 2).label("avg_user_review"),
                func.round(func.sum(GameRelease.total_sales), 2).label("total_sales"),
            )
            .outerjoin(GameReleaseDeveloper, GameReleaseDeveloper.developer_id == Developer.id)
            .outerjoin(GameRelease, GameRelease.id == GameReleaseDeveloper.game_release_id)
            .group_by(Developer.id)
        )

        if query.name:
            base = base.filter(Developer.name.ilike(f"%{query.name}%"))

        rows = base.order_by(desc(func.sum(GameRelease.total_sales))).limit(query.limit).offset(offset).all()

        count_q = self.db.query(func.count()).select_from(Developer)
        if query.name:
            count_q = count_q.filter(Developer.name.ilike(f"%{query.name}%"))
        total = count_q.scalar()

        return {
            "data": [self._row_to_dict(r) for r in rows],
            "meta": {
                "total": total,
                "page": query.page,
                "limit": query.limit,
                "total_pages": -(-total // query.limit),
                "has_next_page": query.page * query.limit < total,
                "has_previous_page": query.page > 1,
            },
        }

    def find_one(self, developer_id: str):
        dev = self.db.query(Developer).filter(Developer.id == developer_id).first()
        if not dev:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Developer not found")

        # top 5 games by meta score
        top_games = (
            self.db.query(
                GameRelease.id,
                Game.canonical_title.label("title"),
                Platform.name.label("platform"),
                GameRelease.meta_score,
                GameRelease.user_review,
                GameRelease.total_sales,
                GameRelease.release_year,
            )
            .join(GameReleaseDeveloper, GameRelease.id == GameReleaseDeveloper.game_release_id)
            .join(Game, Game.id == GameRelease.game_id)
            .join(Platform, Platform.id == GameRelease.platform_id)
            .filter(GameReleaseDeveloper.developer_id == developer_id)
            .order_by(desc(GameRelease.meta_score))
            .limit(5)
            .all()
        )

        return {
            "id": dev.id,
            "name": dev.name,
            "country": dev.country,
            "release_count": 0,
            "avg_meta_score": None,
            "avg_user_review": None,
            "total_sales": None,
            "top_games": [
                {
                    "id": g.id,
                    "title": g.title,
                    "platform": g.platform,
                    "meta_score": float(g.meta_score) if g.meta_score else None,
                    "user_review": float(g.user_review) if g.user_review else None,
                    "total_sales": float(g.total_sales) if g.total_sales else None,
                    "release_year": g.release_year,
                }
                for g in top_games
            ],
        }

    def _row_to_dict(self, row) -> dict:
        return {
            "id": row.id,
            "name": row.name,
            "country": row.country,
            "release_count": row.release_count,
            "avg_meta_score": float(row.avg_meta_score) if row.avg_meta_score else None,
            "avg_user_review": float(row.avg_user_review) if row.avg_user_review else None,
            "total_sales": float(row.total_sales) if row.total_sales else None,
        }