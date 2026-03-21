import json
import hashlib
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc, text, and_
from fastapi import HTTPException, status
from src.db.models import GameRelease, Game, Platform
from src.insights.schemas import LeaderboardQuerySchema, DecadeQuerySchema

# try to import redis , if it's not running we fall back to no cache gracefully
try:
    import redis
    _redis = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    _redis.ping()
    CACHE_AVAILABLE = True
except Exception:
    _redis = None
    CACHE_AVAILABLE = False

# cache TTL in seconds - analytics data doesn't change often so 5 minutes is fine
CACHE_TTL = 300


def _cache_get(key: str):
    if not CACHE_AVAILABLE:
        return None
    try:
        val = _redis.get(key)
        return json.loads(val) if val else None
    except Exception:
        return None


def _cache_set(key: str, value: dict):
    if not CACHE_AVAILABLE:
        return
    try:
        _redis.setex(key, CACHE_TTL, json.dumps(value))
    except Exception:
        pass


def _make_cache_key(prefix: str, **kwargs) -> str:
    # build a deterministic cache key from the query params
    content = json.dumps(kwargs, sort_keys=True)
    digest = hashlib.md5(content.encode()).hexdigest()[:8]
    return f"vg:{prefix}:{digest}"


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    # Leaderboard

    def get_leaderboard(self, query: LeaderboardQuerySchema):
        # cache leaderboard results - same filters always return same data
        cache_key = _make_cache_key("leaderboard",
            metric=query.metric, genre=query.genre,
            platform=query.platform, year_from=query.year_from,
            year_to=query.year_to, limit=query.limit)

        cached = _cache_get(cache_key)
        if cached:
            return {**cached, "cached": True}

        # map the metric param to the actual db column
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

        result = {
            "metric": query.metric,
            "filters": {
                "genre": query.genre,
                "platform": query.platform,
                "year_from": query.year_from,
                "year_to": query.year_to,
            },
            "leaders": [self._game_row_to_dict(r) for r in rows],
            "cached": False,
        }

        _cache_set(cache_key, result)
        return result

    # classification verdict

    def get_verdict(self, game_release_id: str):
        # verdict is deterministic per game so we can cache it indefinitely
        cache_key = f"vg:verdict:{game_release_id}"
        cached = _cache_get(cache_key)
        if cached:
            return {**cached, "cached": True}

        row = (
            self.db.query(
                GameRelease.id,
                GameRelease.game_id,
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

        # aggregate across all platform releases using sales-weighted averaging
        # releases with higher sales contribute more — the version most players
        # experienced matters most. falls back to simple avg for F2P/missing sales
        agg = (
            self.db.query(
                func.sum(GameRelease.total_sales).label("total_sales"),
                func.avg(GameRelease.meta_score).label("avg_meta"),
                func.avg(GameRelease.user_review).label("avg_user"),
                func.sum(GameRelease.meta_score * GameRelease.total_sales).label("weighted_meta"),
                func.sum(GameRelease.user_review * GameRelease.total_sales).label("weighted_user"),
            )
            .filter(GameRelease.game_id == row.game_id)
            .first()
        )

        total_sales = float(agg.total_sales) if agg and agg.total_sales else None
        if total_sales:
            meta = float(agg.weighted_meta) / total_sales if agg.weighted_meta else None
            user = float(agg.weighted_user) / total_sales if agg.weighted_user else None
        else:
            meta = float(agg.avg_meta) if agg and agg.avg_meta else None
            user = float(agg.avg_user) if agg and agg.avg_user else None

        verdict = self._compute_verdict(meta, user, total_sales)

        result = {**self._game_row_to_dict(row), **verdict, "cached": False}
        _cache_set(cache_key, result)
        return result

    def get_verdict_by_game_id(self, game_id: str):
        """Verdict for a game_id directly — as returned by /api/games/search."""
        cache_key = f"vg:verdict:game:{game_id}"
        cached = _cache_get(cache_key)
        if cached:
            return {**cached, "cached": True}

        game = self.db.query(Game).filter(Game.id == game_id).first()
        if not game:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")

        agg = (
            self.db.query(
                func.sum(GameRelease.total_sales).label("total_sales"),
                func.avg(GameRelease.meta_score).label("avg_meta"),
                func.avg(GameRelease.user_review).label("avg_user"),
                func.sum(GameRelease.meta_score * GameRelease.total_sales).label("weighted_meta"),
                func.sum(GameRelease.user_review * GameRelease.total_sales).label("weighted_user"),
                func.min(GameRelease.release_year).label("release_year"),
            )
            .filter(GameRelease.game_id == game_id)
            .first()
        )

        total_sales = float(agg.total_sales) if agg and agg.total_sales else None
        if total_sales:
            meta = float(agg.weighted_meta) / total_sales if agg.weighted_meta else None
            user = float(agg.weighted_user) / total_sales if agg.weighted_user else None
        else:
            meta = float(agg.avg_meta) if agg and agg.avg_meta else None
            user = float(agg.avg_user) if agg and agg.avg_user else None

        verdict = self._compute_verdict(meta, user, total_sales)

        result = {
            "id": str(game_id),
            "title": game.canonical_title,
            "release_year": int(agg.release_year) if agg and agg.release_year else None,
            "total_sales": total_sales,
            **verdict,
            "cached": False,
        }
        _cache_set(cache_key, result)
        return result

    def _compute_verdict(self, meta_score, user_review, total_sales):
        # scale everything to 0-100 for fair comparison across three dimensions
        critic = meta_score or 0
        user = (user_review or 0) * 10
        # log normalise sales - cap at 20M = 100, prevents blockbusters dominating
        sales = min((total_sales or 0) / 20 * 100, 100)
        has_sales = total_sales is not None and total_sales > 0
        has_data = meta_score is not None and user_review is not None
        divergence = abs(critic - user)

        # confidence tells the consumer how much to trust this verdict
        if has_data and has_sales:
            confidence = "high"
        elif has_data:
            confidence = "medium"
        else:
            confidence = "low"

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
            "confidence": confidence,
            "scores": {
                "critic": critic,
                "user": user,
                "sales": round(sales),
                "divergence": round(divergence),
            },
        }

    # controversy and hidden gems

    def get_controversy(self, query: LeaderboardQuerySchema):
        # games where the gap between critic score and user score is largest
        cache_key = _make_cache_key("controversy",
            platform=query.platform, year_from=query.year_from,
            year_to=query.year_to, limit=query.limit)

        cached = _cache_get(cache_key)
        if cached:
            return {**cached, "cached": True}

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

        result = {
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
            "cached": False,
        }

        _cache_set(cache_key, result)
        return result

    def get_hidden_gems(self, query: LeaderboardQuerySchema):
        # high user score + low commercial visibility = hidden gem
        cache_key = _make_cache_key("gems",
            platform=query.platform, year_from=query.year_from,
            year_to=query.year_to, limit=query.limit)

        cached = _cache_get(cache_key)
        if cached:
            return {**cached, "cached": True}

        conditions = [
            GameRelease.user_review.isnot(None),
            GameRelease.user_review >= 8.0,
        ]
        conditions = self._apply_filters(conditions, query.platform, query.year_from, query.year_to)

        # penalise for sales- the less it sold, the more "hidden" it is
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

        result = {
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
            "cached": False,
        }

        _cache_set(cache_key, result)
        return result

    # Decade trends

    def get_decade_trends(self, query: DecadeQuerySchema):
     
        cache_key = _make_cache_key("decade", decade=query.decade, genre=query.genre)
        cached = _cache_get(cache_key)
        if cached:
            return {**cached, "cached": True}

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

        result = {
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
            "cached": False,
        }

        _cache_set(cache_key, result)
        return result

    # platform dominance

    def get_platform_dominance(self, query: DecadeQuerySchema):
        # same as decade trends -- group by on large table, cache it
        cache_key = _make_cache_key("platform_dom", decade=query.decade)
        cached = _cache_get(cache_key)
        if cached:
            return {**cached, "cached": True}

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

        result = {
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
            "cached": False,
        }

        _cache_set(cache_key, result)
        return result

    # shared helpers

    def _apply_filters(self, conditions, platform, year_from, year_to):
        if platform:
            conditions.append(Platform.name.ilike(f"%{platform}%"))
        if year_from:
            conditions.append(GameRelease.release_year >= year_from)
        if year_to:
            conditions.append(GameRelease.release_year <= year_to)
        return conditions

    def _genre_subquery(self, genre: str):
        # genre is many-to-many so needs a subquery rather than a simple join
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