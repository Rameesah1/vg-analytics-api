from pydantic import BaseModel, Field, model_validator
from typing import Optional


class CustomWeightsSchema(BaseModel):
    critic: float = Field(..., ge=0, le=1, example=0.40, description="Weight for critic score (0-1)")
    user: float = Field(..., ge=0, le=1, example=0.35, description="Weight for user score (0-1)")
    sales: float = Field(..., ge=0, le=1, example=0.25, description="Weight for sales score (0-1)")

    @model_validator(mode="after")
    def weights_must_sum_to_one(self):
        total = self.critic + self.user + self.sales
        if abs(total - 1.0) > 0.01:
            raise ValueError("Custom weights must sum to 1.0")
        return self


class CreateBattleSchema(BaseModel):
    squad_a_id: str = Field(..., example="d2ca1130-55d4-477b-bee1-eea493750591")
    squad_b_id: str = Field(..., example="e5fe298a-e48e-4ec7-9126-e477f9bf5d8f")
    preset: Optional[str] = Field(
        default="BALANCED",
        example="BALANCED",
        description="BALANCED, CRITICAL_ACCLAIM, PEOPLES_CHOICE, COMMERCIAL_TITANS",
    )
    custom_weights: Optional[CustomWeightsSchema] = Field(
        default=None,
        description="Custom weights -- must sum to 1.0. Overrides preset if provided.",
    )