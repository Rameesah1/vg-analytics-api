from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from src.db.session import get_db
from src.games.service import GamesService
from src.games.schemas import GameQuerySchema, PaginatedGameResponseSchema, GameDetailSchema

router = APIRouter(prefix="/api/games", tags=["Games"])


@router.get(
    "",
    summary="Browse and search game releases with filters",
    response_model=PaginatedGameResponseSchema,
)
def find_all(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    title: Optional[str] = Query(default=None, example="GTA"),
    genre: Optional[str] = Query(default=None, example="Action"),
    platform: Optional[str] = Query(default=None, example="PS4"),
    year_from: Optional[int] = Query(default=None, example=2000),
    year_to: Optional[int] = Query(default=None, example=2020),
    sort_by: Optional[str] = Query(default="total_sales"),
    order: Optional[str] = Query(default="desc"),
    db: Session = Depends(get_db),
):
    query = GameQuerySchema(
        page=page,
        limit=limit,
        title=title,
        genre=genre,
        platform=platform,
        year_from=year_from,
        year_to=year_to,
        sort_by=sort_by,
        order=order,
    )
    return GamesService(db).find_all(query)


@router.get(
    "/search",
    summary="Search games by title — one result per game, not per release",
)
def search(
    title: str = Query(...),
    limit: int = Query(default=8, ge=1, le=20),
    db: Session = Depends(get_db),
):
    return GamesService(db).search_by_title(title, limit)


@router.get(
    "/{release_id}",
    summary="Get full details for a single game release",
    response_model=GameDetailSchema,
    responses={404: {"description": "Game not found"}},
)
def find_one(release_id: str, db: Session = Depends(get_db)):
    game = GamesService(db).find_one(release_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game
