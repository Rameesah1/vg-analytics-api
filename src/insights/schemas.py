from pydantic import BaseModel, Field
from typing import Optional


class LeaderboardQuerySchema(BaseModel):
    metric: str = Field(default="total_sales", example="meta_score")
    genre: Optional[str] = Field(default=None, example="Action")
    platform: Optional[str] = Field(default=None, example="PS4")
    year_from: Optional[int] = Field(default=None, example=2000)
    year_to: Optional[int] = Field(default=None, example=2020)
    limit: int = Field(default=10, ge=1, le=100, example=10)


class DecadeQuerySchema(BaseModel):
    decade: Optional[int] = Field(default=None, example=2000)
    genre: Optional[str] = Field(default=None, example="Action")