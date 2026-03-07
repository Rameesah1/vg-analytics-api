import json
import math
from sqlalchemy.orm import Session
from sqlalchemy import desc, text
from fastapi import HTTPException, status
from src.db.models import Battle, Squad, SquadItem, GameRelease
from src.battles.schemas import CreateBattleSchema

MIN_SQUAD_SIZE = 5
DRAW_THRESHOLD = 0.5

# weight presets -- different ways to judge which squad is better
PRESETS = {
    "BALANCED":         {"critic": 0.40, "user": 0.35, "sales": 0.25},
    "CRITICAL_ACCLAIM": {"critic": 0.60, "user": 0.25, "sales": 0.15},
    "PEOPLES_CHOICE":   {"critic": 0.25, "user": 0.60, "sales": 0.15},
    "COMMERCIAL_TITANS":{"critic": 0.20, "user": 0.20, "sales": 0.60},
}


class BattlesService:
    def __init__(self, db: Session):
        self.db = db

    def _compute_squad_dna(self, squad_id: str) -> dict:
        # pull raw scores for every game in the squad
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
                detail=f"Squad needs at least {MIN_SQUAD_SIZE} games to battle",
            )

        with_critic = [i for i in items if i.meta_score is not None]
        with_user = [i for i in items if i.user_review is not None]
        with_sales = [i for i in items if i.total_sales is not None]

        avg_critic = sum(float(i.meta_score) for i in with_critic) / len(with_critic) if with_critic else 0
        avg_user = sum(float(i.user_review) for i in with_user) / len(with_user) if with_user else 0
        avg_sales = sum(float(i.total_sales) for i in with_sales) / len(with_sales) if with_sales else 0

        # log-normalise sales to 0-100 -- same scale as verdict machine
        max_sales = 20
        sales_score = min(
            (math.log10(1 + avg_sales) / math.log10(1 + max_sales)) * 100, 100
        )

        return {
            "item_count": len(items),
            "avg_critic": round(avg_critic, 2),
            "avg_user_100": round(avg_user * 10, 2),   # scale 0-10 to 0-100
            "sales_score_100": round(sales_score, 2),
            "critic_coverage": f"{len(with_critic)}/{len(items)}",
            "user_coverage": f"{len(with_user)}/{len(items)}",
            "sales_coverage": f"{len(with_sales)}/{len(items)}",
        }

    def _compute_score(self, dna: dict, weights: dict) -> float:
        return (
            weights["critic"] * dna["avg_critic"]
            + weights["user"] * dna["avg_user_100"]
            + weights["sales"] * dna["sales_score_100"]
        )

    def create(self, user_id: str, dto: CreateBattleSchema):
        if dto.squad_a_id == dto.squad_b_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot battle a squad against itself",
            )

        squad_a = self.db.query(Squad).filter(Squad.id == dto.squad_a_id).first()
        squad_b = self.db.query(Squad).filter(Squad.id == dto.squad_b_id).first()

        if not squad_a:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Squad A not found")
        if not squad_b:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Squad B not found")
        if str(squad_a.user_id) != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own Squad A")

        # custom weights override the preset if provided
        if dto.custom_weights:
            weights = {
                "critic": dto.custom_weights.critic,
                "user": dto.custom_weights.user,
                "sales": dto.custom_weights.sales,
            }
        else:
            weights = PRESETS.get(dto.preset or "BALANCED", PRESETS["BALANCED"])

        # compute DNA snapshots for both squads
        dna_a = self._compute_squad_dna(dto.squad_a_id)
        dna_b = self._compute_squad_dna(dto.squad_b_id)

        score_a = self._compute_score(dna_a, weights)
        score_b = self._compute_score(dna_b, weights)
        score_diff = abs(score_a - score_b)

        # draw if scores are within the threshold
        winner_squad_id = None
        if score_diff >= DRAW_THRESHOLD:
            winner_squad_id = dto.squad_a_id if score_a > score_b else dto.squad_b_id

        battle = Battle(
            user_id=user_id,
            squad_a_id=dto.squad_a_id,
            squad_b_id=dto.squad_b_id,
            winner_squad_id=winner_squad_id,
            score_a=round(score_a, 3),
            score_b=round(score_b, 3),
            score_diff=round(score_diff, 3),
            weights_json=json.dumps(weights),
            dna_a_json=json.dumps(dna_a),
            dna_b_json=json.dumps(dna_b),
        )
        self.db.add(battle)
        self.db.commit()
        self.db.refresh(battle)

        winner_name = (
            (squad_a.name if winner_squad_id == dto.squad_a_id else squad_b.name)
            if winner_squad_id else "Draw"
        )

        return {
            "id": battle.id,
            "squad_a_name": squad_a.name,
            "squad_b_name": squad_b.name,
            "score_a": float(battle.score_a),
            "score_b": float(battle.score_b),
            "score_diff": float(battle.score_diff),
            "winner_name": winner_name,
            "weights": weights,
            "dna_a": dna_a,
            "dna_b": dna_b,
            "created_at": battle.created_at,
        }

    def find_all_for_user(self, user_id: str):
        rows = (
            self.db.query(Battle)
            .filter(Battle.user_id == user_id)
            .order_by(desc(Battle.created_at))
            .all()
        )

        return {
            "data": [
                {
                    "id": r.id,
                    "squad_a_id": r.squad_a_id,
                    "squad_b_id": r.squad_b_id,
                    "winner_squad_id": r.winner_squad_id,
                    "score_a": float(r.score_a) if r.score_a else None,
                    "score_b": float(r.score_b) if r.score_b else None,
                    "score_diff": float(r.score_diff) if r.score_diff else None,
                    "created_at": r.created_at,
                }
                for r in rows
            ],
            "total": len(rows),
        }

    def find_one(self, battle_id: str, user_id: str):
        battle = self.db.query(Battle).filter(Battle.id == battle_id).first()

        if not battle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Battle not found")
        if str(battle.user_id) != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not own this battle")

        return {
            "id": battle.id,
            "squad_a_id": battle.squad_a_id,
            "squad_b_id": battle.squad_b_id,
            "winner_squad_id": battle.winner_squad_id,
            "score_a": float(battle.score_a) if battle.score_a else None,
            "score_b": float(battle.score_b) if battle.score_b else None,
            "score_diff": float(battle.score_diff) if battle.score_diff else None,
            "weights": json.loads(battle.weights_json) if battle.weights_json else {},
            "dna_a": json.loads(battle.dna_a_json) if battle.dna_a_json else {},
            "dna_b": json.loads(battle.dna_b_json) if battle.dna_b_json else {},
            "created_at": battle.created_at,
        }