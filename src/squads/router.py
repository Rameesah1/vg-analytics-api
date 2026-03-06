from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from src.db.session import get_db
from src.db.models import User
from src.auth.dependencies import get_current_user
from src.squads.service import SquadsService
from src.squads.schemas import CreateSquadSchema, UpdateSquadSchema, AddSquadItemSchema, SquadFilterSchema

router = APIRouter(prefix="/api/squads", tags=["Squads"])


@router.post("", status_code=201, summary="Create a new squad")
def create(
    dto: CreateSquadSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return SquadsService(db).create(str(current_user.id), dto)


@router.get("", summary="List your squads")
def find_all(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    name: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    filter = SquadFilterSchema(page=page, limit=limit, name=name)
    return SquadsService(db).find_all_for_user(str(current_user.id), filter)


@router.get("/{squad_id}", summary="Get squad with all games")
def find_one(
    squad_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return SquadsService(db).find_one(squad_id, str(current_user.id))


@router.patch("/{squad_id}", summary="Update squad name or description")
def update(
    squad_id: str,
    dto: UpdateSquadSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return SquadsService(db).update(squad_id, str(current_user.id), dto)


@router.delete("/{squad_id}", summary="Delete a squad")
def remove(
    squad_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return SquadsService(db).remove(squad_id, str(current_user.id))


@router.post("/{squad_id}/items", status_code=201, summary="Add a game to your squad")
def add_item(
    squad_id: str,
    dto: AddSquadItemSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return SquadsService(db).add_item(squad_id, str(current_user.id), dto)


@router.delete("/{squad_id}/items/{item_id}", summary="Remove a game from your squad")
def remove_item(
    squad_id: str,
    item_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return SquadsService(db).remove_item(squad_id, item_id, str(current_user.id))


@router.get("/{squad_id}/dna", summary="Squad DNA -- average scores and coverage across all games")
def get_squad_dna(
    squad_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return SquadsService(db).get_squad_dna(squad_id, str(current_user.id))