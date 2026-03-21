from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID


class GameQuerySchema(BaseModel):
    page: int = Field(default=1, ge=1, example=1)
    limit: int = Field(default=20, ge=1, le=100, example=20)
    title: Optional[str] = Field(default=None, example="GTA")
    genre: Optional[str] = Field(default=None, example="Action")
    platform: Optional[str] = Field(default=None, example="PS4")
    year_from: Optional[int] = Field(default=None, example=2000)
    year_to: Optional[int] = Field(default=None, example=2020)
    sort_by: Optional[str] = Field(default="total_sales", example="meta_score")
    order: Optional[str] = Field(default="desc", example="desc")

class GameResponseSchema(BaseModel):
    id: UUID
    canonical_title: str
    release_year: Optional[int]
    platform: Optional[str]
    total_sales: Optional[float]
    meta_score: Optional[float]
    user_review: Optional[float]
    summary: Optional[str]
    match_confidence: Optional[float]
    has_vgchartz: bool
    has_metacritic: bool

    model_config = {"from_attributes": True}


class GameDetailSchema(GameResponseSchema):
    # extra fields only shown in the single game detail view
    release_date: Optional[str]
    na_sales: Optional[float]
    jp_sales: Optional[float]
    pal_sales: Optional[float]
    other_sales: Optional[float]
    vg_critic_score: Optional[float]
    match_strategy: Optional[str]


class PaginationMetaSchema(BaseModel):
    total: int
    page: int
    limit: int
    total_pages: int
    has_next_page: bool
    has_previous_page: bool


class PaginatedGameResponseSchema(BaseModel):
    data: list[GameResponseSchema]
    meta: PaginationMetaSchema