from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from fastapi import HTTPException, status
from src.db.models import Squad, SquadItem, GameRelease, Game, Platform
from src.squads.schemas import CreateSquadSchema, UpdateSquadSchema, AddSquadItemSchema, SquadFilterSchema
import math

MIN_SQUAD_SIZE = 5
MAX_SQUAD_SIZE = 15


class SquadsService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: str, dto: CreateSquadSchema):
        squad = Squad(
            user_id=user_id,
            name=dto.name,
            description=dto.description,
            is_public=dto.is_public,
        )
        self.db.add(squad)
        self.db.commit()
        self.db.refresh(squad)
        return self._squad_to_dict(squad)

    def find_all_for_user(self, user_id: str, filter: SquadFilterSchema):
        offset = (filter.page - 1) * filter.limit

        base = (
            self.db.query(
                Squad.id,
                Squad.name,
                Squad.description,
                Squad.is_public,
                Squad.created_at,
                func.count(SquadItem.id).label("item_count"),
            )
            .outerjoin(SquadItem, SquadItem.squad_id == Squad.id)
            .filter(Squad.user_id == user_id)
            .group_by(Squad.id)
            .order_by(desc(Squad.created_at))
        )

        if filter.name:
            base = base.filter(Squad.name.ilike(f"%{filter.name}%"))

        rows = base.limit(filter.limit).offset(offset).all()

        count_q = self.db.query(func.count()).select_from(Squad).filter(Squad.user_id == user_id)
        if filter.name:
            count_q = count_q.filter(Squad.name.ilike(f"%{filter.name}%"))
        total = count_q.scalar()

        return {
            "data": [
                {
                    "id": r.id,
                    "name": r.name,
                    "description": r.description,
                    "is_public": r.is_public,
                    "created_at": r.created_at,
                    "item_count": r.item_count,
                }
                for r in rows
            ],
            "meta": {
                "total": total,
                "page": filter.page,
                "limit": filter.limit,
                "total_pages": -(-total // filter.limit),
                "has_next_page": filter.page * filter.limit < total,
                "has_previous_page": filter.page > 1,
            },
        }

    def find_one(self, squad_id: str, user_id: str):
        squad = self.db.query(Squad).filter(Squad.id == squad_id).first()

        if not squad:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Squad not found")
        if str(squad.user_id) != user_id and not squad.is_public:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this squad")

        # get squad items with full game details
        items = (
            self.db.query(
                SquadItem.id.label("item_id"),
                SquadItem.game_release_id,
                SquadItem.notes,
                SquadItem.added_at,
                Game.canonical_title.label("title"),
                Platform.name.label("platform"),
                GameRelease.release_year,
                GameRelease.meta_score,
                GameRelease.user_review,
                GameRelease.total_sales,
            )
            .join(GameRelease, GameRelease.id == SquadItem.game_release_id)
            .join(Game, Game.id == GameRelease.game_id)
            .join(Platform, Platform.id == GameRelease.platform_id)
            .filter(SquadItem.squad_id == squad_id)
            .all()
        )

        return {
            **self._squad_to_dict(squad),
            "items": [
                {
                    "item_id": i.item_id,
                    "game_release_id": i.game_release_id,
                    "notes": i.notes,
                    "added_at": i.added_at,
                    "title": i.title,
                    "platform": i.platform,
                    "release_year": i.release_year,
                    "meta_score": float(i.meta_score) if i.meta_score else None,
                    "user_review": float(i.user_review) if i.user_review else None,
                    "total_sales": float(i.total_sales) if i.total_sales else None,
                }
                for i in items
            ],
        }

    def update(self, squad_id: str, user_id: str, dto: UpdateSquadSchema):
        squad = self.db.query(Squad).filter(Squad.id == squad_id).first()

        if not squad:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Squad not found")
        if str(squad.user_id) != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this squad")

        if dto.name is not None:
            squad.name = dto.name
        if dto.description is not None:
            squad.description = dto.description
        if dto.is_public is not None:
            squad.is_public = dto.is_public

        self.db.commit()
        self.db.refresh(squad)
        return self._squad_to_dict(squad)

    def remove(self, squad_id: str, user_id: str):
        squad = self.db.query(Squad).filter(Squad.id == squad_id).first()

        if not squad:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Squad not found")
        if str(squad.user_id) != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this squad")

        self.db.delete(squad)
        self.db.commit()
        return {"message": "Squad deleted"}

    def add_item(self, squad_id: str, user_id: str, dto: AddSquadItemSchema):
        squad = self.db.query(Squad).filter(Squad.id == squad_id).first()

        if not squad:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Squad not found")
        if str(squad.user_id) != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this squad")

        # enforce squad size limit
        item_count = self.db.query(func.count()).select_from(SquadItem).filter(
            SquadItem.squad_id == squad_id
        ).scalar()

        if item_count >= MAX_SQUAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Squad cannot have more than {MAX_SQUAD_SIZE} games",
            )

        # check game release exists
        release = self.db.query(GameRelease).filter(GameRelease.id == dto.game_release_id).first()
        if not release:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game release not found")

        # check if already in squad
        existing = self.db.query(SquadItem).filter(
            and_(SquadItem.squad_id == squad_id, SquadItem.game_release_id == dto.game_release_id)
        ).first()

        if existing:
            return {"message": "Game already in squad"}

        item = SquadItem(
            squad_id=squad_id,
            game_release_id=dto.game_release_id,
            notes=dto.notes,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return {"item_id": item.id, "squad_id": item.squad_id, "game_release_id": item.game_release_id}

    def remove_item(self, squad_id: str, item_id: str, user_id: str):
        squad = self.db.query(Squad).filter(Squad.id == squad_id).first()

        if not squad:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Squad not found")
        if str(squad.user_id) != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this squad")

        item = self.db.query(SquadItem).filter(
            and_(SquadItem.id == item_id, SquadItem.squad_id == squad_id)
        ).first()

        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found in squad")

        self.db.delete(item)
        self.db.commit()
        return {"message": "Item removed from squad"}

    def get_squad_dna(self, squad_id: str, user_id: str):
        squad = self.db.query(Squad).filter(Squad.id == squad_id).first()

        if not squad:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Squad not found")
        if str(squad.user_id) != user_id and not squad.is_public:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this squad")

        items = (
            self.db.query(
                GameRelease.meta_score,
                GameRelease.user_review,
                GameRelease.total_sales,
            )
            .join(SquadItem, SquadItem.game_release_id == GameRelease.id)
            .filter(SquadItem.squad_id == squad_id)
            .all()
        )

        if len(items) < MIN_SQUAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Squad needs at least {MIN_SQUAD_SIZE} games for DNA analysis",
            )

        with_critic = [i for i in items if i.meta_score is not None]
        with_user = [i for i in items if i.user_review is not None]
        with_sales = [i for i in items if i.total_sales is not None]

        avg_critic = sum(float(i.meta_score) for i in with_critic) / len(with_critic) if with_critic else None
        avg_user = sum(float(i.user_review) for i in with_user) / len(with_user) if with_user else None
        avg_sales = sum(float(i.total_sales) for i in with_sales) / len(with_sales) if with_sales else None

        # log-normalise sales to 0-100 -- same approach as verdict machine
        max_sales = 20
        sales_score = min(
            (math.log10(1 + avg_sales) / math.log10(1 + max_sales)) * 100, 100
        ) if avg_sales is not None else None

        return {
            "squad_id": squad_id,
            "squad_name": squad.name,
            "item_count": len(items),
            "avg_critic_score": round(avg_critic, 2) if avg_critic else None,
            "avg_user_score": round(avg_user, 2) if avg_user else None,
            "avg_global_sales": round(avg_sales, 2) if avg_sales else None,
            "sales_score_100": round(sales_score, 2) if sales_score else None,
            "critic_coverage": f"{len(with_critic)}/{len(items)}",
            "user_coverage": f"{len(with_user)}/{len(items)}",
            "sales_coverage": f"{len(with_sales)}/{len(items)}",
        }

    def _squad_to_dict(self, squad) -> dict:
        return {
            "id": squad.id,
            "name": squad.name,
            "description": squad.description,
            "is_public": squad.is_public,
            "created_at": squad.created_at,
            "updated_at": squad.updated_at,
        }