from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc, text, and_
from fastapi import HTTPException, status
from src.db.models import GameRelease, Game, Platform
from src.insights.schemas import LeaderboardQuerySchema, DecadeQuerySchema


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    # --- LEADERBOARD ---

    def get_leaderboard(self, query: LeaderboardQuerySchema):
        # map the metric param to the actual column
        metric_map = {
            "meta_score": GameRelease.meta_score,
            "user_review": GameRelease.user_review,
            "total_sales": GameRelease.total_sales,
        }
        sort_col = metric_map.get(query.metric, GameRelease.total_sales)

        conditions = [sort_col.isnot(None)]
        conditions = self._apply_filters(conditions, query.platform, query.year_from, query.year_to)

        if query.genre:
            conditions.append(self._genre_subquery(query.genre))

        rows = (
            self.db.query(
                GameRelease.id,
                Game.canonical_title.label("title"),
                Platform.name.label("platform"),
                GameRelease.release_year,
                GameRelease.meta_score,
                GameRelease.user_review,
                GameRelease.total_sales,
            )
            .join(Game, GameRelease.game_id == Game.id)
            .join(Platform, GameRelease.platform_id == Platform.id)
            .filter(and_(*conditions))
            .order_by(desc(sort_col).nullslast())
            .limit(query.limit)
            .all()
        )

        return {
            "metric": query.metric,
            "filters": {
                "genre": query.genre,
                "platform": query.platform,
                "year_from": query.year_from,
                "year_to": query.year_to,
            },
            "leaders": [self._game_row_to_dict(r) for r in rows],
        }

    # --- VERDICT MACHINE (signature feature) ---

    def get_verdict(self, game_release_id: str):
        row = (
            self.db.query(
                GameRelease.id,
                Game.canonical_title.label("title"),
                Platform.name.label("platform"),
                GameRelease.release_year,
                GameRelease.meta_score,
                GameRelease.user_review,
                GameRelease.total_sales,
            )
            .join(Game, GameRelease.game_id == Game.id)
            .join(Platform, GameRelease.platform_id == Platform.id)
            .filter(GameRelease.id == game_release_id)
            .first()
        )

        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")

        verdict = self._compute_verdict(
            float(row.meta_score) if row.meta_score else None,
            float(row.user_review) if row.user_review else None,
            float(row.total_sales) if row.total_sales else None,
        )

        return {**self._game_row_to_dict(row), **verdict}

    def _compute_verdict(self, meta_score, user_review, total_sales):
        # scale everything to 0-100 for fair comparison
        critic = meta_score or 0
        user = (user_review or 0) * 10
        # log-normalise sales -- cap at 20M = 100, prevents blockbusters dominating
        sales = min((total_sales or 0) / 20 * 100, 100)
        has_sales = total_sales is not None and total_sales > 0
        has_data = meta_score is not None and user_review is not None
        divergence = abs(critic - user)

        if not has_data:
            classification = "Unrated"
            explanation = "Insufficient review data to classify this game."
        elif critic >= 90 and user >= 85:
            classification = "All-Time Classic"
            explanation = "Critically acclaimed and beloved by players -- a genuine classic."
        elif user >= 80 and critic < 70 and divergence >= 20:
            classification = "Cult Classic"
            explanation = "Critics dismissed it but players discovered something special."
        elif critic >= 80 and user < 60 and divergence >= 20:
            classification = "Critic Darling"
            explanation = "The press loved it but players were left cold."
        elif has_sales and sales >= 50 and critic < 70 and user < 70:
            classification = "Overhyped"
            explanation = "Massive commercial success that failed to impress critics or players."
        elif user >= 75 and (not has_sales or sales < 15):
            classification = "Hidden Gem"
            explanation = "Fans loved it but it flew under the radar commercially."
        elif has_sales and sales >= 40 and critic >= 70:
            classification = "Commercial Hit"
            explanation = "Strong sales backed by solid critical reception."
        elif divergence >= 25:
            classification = "Divisive"
            explanation = "Critics and players fundamentally disagreed on this one."
        elif critic >= 80 and user >= 75:
            classification = "Great Game"
            explanation = "Strong scores across the board -- a genuinely good game."
        else:
            classification = "Solid Title"
            explanation = "A well-rounded game without any standout extremes."

        return {
            "verdict": classification,
            "explanation": explanation,
            "scores": {
                "critic": critic,
                "user": user,
                "sales": round(sales),
                "divergence": round(divergence),
            },
        }

    # --- CONTROVERSY INDEX ---

    def get_controversy(self, query: LeaderboardQuerySchema):
        # games where the gap between critic score and user score is largest
        conditions = [
            GameRelease.meta_score.isnot(None),
            GameRelease.user_review.isnot(None),
        ]
        conditions = self._apply_filters(conditions, query.platform, query.year_from, query.year_to)

        divergence_expr = func.abs(
            GameRelease.meta_score - (GameRelease.user_review * 10)
        )

        rows = (
            self.db.query(
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
            .filter(and_(*conditions))
            .order_by(desc(divergence_expr))
            .limit(query.limit)
            .all()
        )

        return {
            "description": "Games where critics and users most disagreed",
            "results": [
                {
                    "id": r.id,
                    "title": r.title,
                    "platform": r.platform,
                    "release_year": r.release_year,
                    "meta_score": float(r.meta_score) if r.meta_score else None,
                    "user_review": float(r.user_review) if r.user_review else None,
                    "divergence": float(r.divergence) if r.divergence else None,
                }
                for r in rows
            ],
        }

    # --- HIDDEN GEMS ---

    def get_hidden_gems(self, query: LeaderboardQuerySchema):
        # high user score + low commercial visibility = hidden gem
        conditions = [
            GameRelease.user_review.isnot(None),
            GameRelease.user_review >= 8.0,
        ]
        conditions = self._apply_filters(conditions, query.platform, query.year_from, query.year_to)

        # penalise for sales -- the less it sold, the more "hidden" it is
        gem_score = (
            GameRelease.user_review * 10
            - func.coalesce(GameRelease.total_sales, 0) * 2
        )

        rows = (
            self.db.query(
                GameRelease.id,
                Game.canonical_title.label("title"),
                Platform.name.label("platform"),
                GameRelease.release_year,
                GameRelease.meta_score,
                GameRelease.user_review,
                GameRelease.total_sales,
                func.round(gem_score, 2).label("hidden_gem_score"),
            )
            .join(Game, GameRelease.game_id == Game.id)
            .join(Platform, GameRelease.platform_id == Platform.id)
            .filter(and_(*conditions))
            .order_by(desc(gem_score))
            .limit(query.limit)
            .all()
        )

        return {
            "description": "High user scores but overlooked commercially",
            "results": [
                {
                    "id": r.id,
                    "title": r.title,
                    "platform": r.platform,
                    "release_year": r.release_year,
                    "meta_score": float(r.meta_score) if r.meta_score else None,
                    "user_review": float(r.user_review) if r.user_review else None,
                    "total_sales": float(r.total_sales) if r.total_sales else None,
                    "hidden_gem_score": float(r.hidden_gem_score) if r.hidden_gem_score else None,
                }
                for r in rows
            ],
        }

    # --- DECADE TRENDS ---

    def get_decade_trends(self, query: DecadeQuerySchema):
        decade_expr = func.floor(GameRelease.release_year / 10) * 10

        conditions = []
        if query.decade:
            conditions.append(GameRelease.release_year >= query.decade)
            conditions.append(GameRelease.release_year <= query.decade + 9)
        if query.genre:
            conditions.append(self._genre_subquery(query.genre))

        base = (
            self.db.query(
                decade_expr.label("decade"),
                func.count().label("release_count"),
                func.round(func.avg(GameRelease.meta_score), 2).label("avg_meta_score"),
                func.round(func.avg(GameRelease.user_review), 2).label("avg_user_review"),
                func.round(func.sum(GameRelease.total_sales), 2).label("total_sales"),
            )
            .join(Game, GameRelease.game_id == Game.id)
            .join(Platform, GameRelease.platform_id == Platform.id)
            .group_by(decade_expr)
            .order_by(asc(decade_expr))
        )

        if conditions:
            base = base.filter(and_(*conditions))

        rows = base.all()

        return {
            "description": "Gaming trends by decade",
            "decades": [
                {
                    "decade": int(r.decade) if r.decade else None,
                    "release_count": r.release_count,
                    "avg_meta_score": float(r.avg_meta_score) if r.avg_meta_score else None,
                    "avg_user_review": float(r.avg_user_review) if r.avg_user_review else None,
                    "total_sales": float(r.total_sales) if r.total_sales else None,
                }
                for r in rows
            ],
        }

    # --- PLATFORM DOMINANCE ---

    def get_platform_dominance(self, query: DecadeQuerySchema):
        decade_expr = func.floor(GameRelease.release_year / 10) * 10

        conditions = [GameRelease.release_year.isnot(None)]
        if query.decade:
            conditions.append(GameRelease.release_year >= query.decade)
            conditions.append(GameRelease.release_year <= query.decade + 9)

        rows = (
            self.db.query(
                Platform.name.label("platform"),
                decade_expr.label("decade"),
                func.count().label("release_count"),
                func.round(func.sum(GameRelease.total_sales), 2).label("total_sales"),
                func.round(func.avg(GameRelease.meta_score), 2).label("avg_meta_score"),
            )
            .join(Platform, GameRelease.platform_id == Platform.id)
            .filter(and_(*conditions))
            .group_by(Platform.name, decade_expr)
            .order_by(asc(decade_expr), desc(func.sum(GameRelease.total_sales)))
            .all()
        )

        return {
            "description": "Platform dominance by decade",
            "platforms": [
                {
                    "platform": r.platform,
                    "decade": int(r.decade) if r.decade else None,
                    "release_count": r.release_count,
                    "total_sales": float(r.total_sales) if r.total_sales else None,
                    "avg_meta_score": float(r.avg_meta_score) if r.avg_meta_score else None,
                }
                for r in rows
            ],
        }

    # --- SHARED HELPERS ---

    def _apply_filters(self, conditions, platform, year_from, year_to):
        if platform:
            conditions.append(Platform.name.ilike(f"%{platform}%"))
        if year_from:
            conditions.append(GameRelease.release_year >= year_from)
        if year_to:
            conditions.append(GameRelease.release_year <= year_to)
        return conditions

    def _genre_subquery(self, genre: str):
        # genre is many-to-many so needs a subquery
        return text(f"""
            EXISTS (
                SELECT 1 FROM game_release_genre grg
                INNER JOIN genre g ON g.id = grg.genre_id
                WHERE grg.game_release_id = game_release.id
                AND g.name ILIKE '%{genre}%'
            )
        """)

    def _game_row_to_dict(self, row) -> dict:
        return {
            "id": row.id,
            "title": row.title,
            "platform": row.platform,
            "release_year": row.release_year,
            "meta_score": float(row.meta_score) if row.meta_score else None,
            "user_review": float(row.user_review) if row.user_review else None,
            "total_sales": float(row.total_sales) if row.total_sales else None,
        }