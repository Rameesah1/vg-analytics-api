from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.db.models import User
from src.auth.dependencies import get_current_user
from src.battles.service import BattlesService
from src.battles.schemas import CreateBattleSchema

router = APIRouter(prefix="/api/battles", tags=["Battles"])


@router.post(
    "",
    status_code=201,
    summary="Battle two squads head to head using weighted scoring",
    responses={
        400: {"description": "Squads too small or invalid weights"},
        403: {"description": "You do not own Squad A"},
        404: {"description": "Squad not found"},
    },
)
def create(
    dto: CreateBattleSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return BattlesService(db).create(str(current_user.id), dto)


@router.get("", summary="List your battle history")
def find_all(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return BattlesService(db).find_all_for_user(str(current_user.id))


@router.get(
    "/{battle_id}",
    summary="Get full battle details with DNA snapshots and weights",
    responses={404: {"description": "Battle not found"}},
)
def find_one(
    battle_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return BattlesService(db).find_one(battle_id, str(current_user.id))