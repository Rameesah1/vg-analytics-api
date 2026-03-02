from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from src.db.session import get_db
from src.developers.service import DevelopersService
from src.developers.schemas import DeveloperQuerySchema, PaginatedDeveloperResponseSchema, DeveloperDetailSchema

router = APIRouter(prefix="/api/developers", tags=["Developers"])


@router.get(
    "",
    summary="List developers with portfolio stats",
    response_model=PaginatedDeveloperResponseSchema,
)
def find_all(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    name: Optional[str] = Query(default=None, example="Rockstar"),
    db: Session = Depends(get_db),
):
    query = DeveloperQuerySchema(page=page, limit=limit, name=name)
    return DevelopersService(db).find_all(query)


@router.get(
    "/{developer_id}",
    summary="Get developer profile with top 5 games by Metacritic score",
    response_model=DeveloperDetailSchema,
    responses={404: {"description": "Developer not found"}},
)
def find_one(developer_id: str, db: Session = Depends(get_db)):
    return DevelopersService(db).find_one(developer_id)