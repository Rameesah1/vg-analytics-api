import os
import sys
import json
import math

# add project root to path so we can import src modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()

from mcp.server.fastmcp import FastMCP
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func
from src.db.session import SessionLocal
from src.db.models import GameRelease, Game, Platform, Developer, GameReleaseDeveloper

mcp = FastMCP("vg-analytics-mcp")


def get_db() -> Session:
    return SessionLocal()


@mcp.tool()
def search_games(
    title: str = None,
    platform: str = None,
    genre: str = None,
    limit: int = 10,
) -> str:
    """Search for game releases by title, platform or genre.
    Returns paginated results with sales and review scores."""
    db = get_db()
    try:
        query = (
            db.query(
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
        )

        if title:
            query = query.filter(Game.canonical_title.ilike(f"%{title}%"))
        if platform:
            query = query.filter(Platform.name.ilike(f"%{platform}%"))

        results = query.order_by(desc(GameRelease.total_sales).nullslast()).limit(limit).all()

        games = [
            {
                "id": str(r.id),
                "title": r.title,
                "platform": r.platform,
                "release_year": r.release_year,
                "meta_score": float(r.meta_score) if r.meta_score else None,
                "user_review": float(r.user_review) if r.user_review else None,
                "total_sales": float(r.total_sales) if r.total_sales else None,
            }
            for r in results
        ]
        return json.dumps({"results": games, "count": len(games)})
    finally:
        db.close()


@mcp.tool()
def get_verdict(game_release_id: str) -> str:
    """Get the Verdict Machine classification for a specific game release.
    Classifications: All-Time Classic, Cult Classic, Hidden Gem, Overhyped,
    Commercial Hit, Critic Darling, Divisive, Great Game, Solid Title, Unrated."""
    db = get_db()
    try:
        row = (
            db.query(
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
            return json.dumps({"error": "Game not found"})

        critic = float(row.meta_score) if row.meta_score else 0
        user = (float(row.user_review) if row.user_review else 0) * 10
        sales_raw = float(row.total_sales) if row.total_sales else 0
        sales = min((sales_raw / 20) * 100, 100)
        divergence = abs(critic - user)
        has_data = row.meta_score is not None and row.user_review is not None
        has_sales = sales_raw > 0

        if not has_data:
            verdict = "Unrated"
        elif critic >= 90 and user >= 85:
            verdict = "All-Time Classic"
        elif user >= 80 and critic < 70 and divergence >= 20:
            verdict = "Cult Classic"
        elif critic >= 80 and user < 60 and divergence >= 20:
            verdict = "Critic Darling"
        elif has_sales and sales >= 50 and critic < 70 and user < 70:
            verdict = "Overhyped"
        elif user >= 75 and (not has_sales or sales < 15):
            verdict = "Hidden Gem"
        elif has_sales and sales >= 40 and critic >= 70:
            verdict = "Commercial Hit"
        elif divergence >= 25:
            verdict = "Divisive"
        elif critic >= 80 and user >= 75:
            verdict = "Great Game"
        else:
            verdict = "Solid Title"

        return json.dumps({
            "id": str(row.id),
            "title": row.title,
            "platform": row.platform,
            "verdict": verdict,
            "scores": {
                "critic": round(critic, 1),
                "user": round(user, 1),
                "sales": round(sales, 1),
                "divergence": round(divergence, 1),
            },
        })
    finally:
        db.close()


@mcp.tool()
def get_controversy(limit: int = 10) -> str:
    """Get games where critics and players most disagreed.
    Returns games ranked by the divergence between critic score and user score."""
    db = get_db()
    try:
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

        results = [
            {
                "id": str(r.id),
                "title": r.title,
                "platform": r.platform,
                "release_year": r.release_year,
                "meta_score": float(r.meta_score),
                "user_review": float(r.user_review),
                "divergence": float(r.divergence),
            }
            for r in rows
        ]
        return json.dumps({"description": "Games where critics and users most disagreed", "results": results})
    finally:
        db.close()


@mcp.tool()
def get_hidden_gems(limit: int = 10) -> str:
    """Get games with high user scores that were overlooked commercially.
    These are games players loved but that didn't sell well."""
    db = get_db()
    try:
        gem_score = (
            GameRelease.user_review * 10
            - func.coalesce(GameRelease.total_sales, 0) * 2
        )

        rows = (
            db.query(
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
            .filter(
                GameRelease.user_review.isnot(None),
                GameRelease.user_review >= 8.0,
            )
            .order_by(desc(gem_score))
            .limit(limit)
            .all()
        )

        results = [
            {
                "id": str(r.id),
                "title": r.title,
                "platform": r.platform,
                "release_year": r.release_year,
                "meta_score": float(r.meta_score) if r.meta_score else None,
                "user_review": float(r.user_review),
                "total_sales": float(r.total_sales) if r.total_sales else None,
            }
            for r in rows
        ]
        return json.dumps({"description": "High user scores but overlooked commercially", "results": results})
    finally:
        db.close()


@mcp.tool()
def get_leaderboard(
    metric: str = "total_sales",
    limit: int = 10,
    platform: str = None,
    year_from: int = None,
    year_to: int = None,
) -> str:
    """Get top games ranked by a specific metric.
    metric options: meta_score, user_review, total_sales"""
    db = get_db()
    try:
        metric_map = {
            "meta_score": GameRelease.meta_score,
            "user_review": GameRelease.user_review,
            "total_sales": GameRelease.total_sales,
        }
        sort_col = metric_map.get(metric, GameRelease.total_sales)

        conditions = [sort_col.isnot(None)]
        if platform:
            conditions.append(Platform.name.ilike(f"%{platform}%"))
        if year_from:
            conditions.append(GameRelease.release_year >= year_from)
        if year_to:
            conditions.append(GameRelease.release_year <= year_to)

        rows = (
            db.query(
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
            .limit(limit)
            .all()
        )

        results = [
            {
                "id": str(r.id),
                "title": r.title,
                "platform": r.platform,
                "release_year": r.release_year,
                "meta_score": float(r.meta_score) if r.meta_score else None,
                "user_review": float(r.user_review) if r.user_review else None,
                "total_sales": float(r.total_sales) if r.total_sales else None,
            }
            for r in rows
        ]
        return json.dumps({"metric": metric, "leaders": results})
    finally:
        db.close()


if __name__ == "__main__":
    mcp.run()