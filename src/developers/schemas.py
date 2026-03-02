from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID


# --- query params ---

class DeveloperQuerySchema(BaseModel):
    page: int = Field(default=1, ge=1, example=1)
    limit: int = Field(default=20, ge=1, le=100, example=20)
    name: Optional[str] = Field(default=None, example="Rockstar")


# --- response bodies ---

class DeveloperResponseSchema(BaseModel):
    id: UUID
    name: str
    country: Optional[str]
    release_count: int
    avg_meta_score: Optional[float]
    avg_user_review: Optional[float]
    total_sales: Optional[float]

    model_config = {"from_attributes": True}


class TopGameSchema(BaseModel):
    id: UUID
    title: str
    platform: str
    meta_score: Optional[float]
    user_review: Optional[float]
    total_sales: Optional[float]
    release_year: Optional[int]

    model_config = {"from_attributes": True}


class DeveloperDetailSchema(DeveloperResponseSchema):
    top_games: list[TopGameSchema]


class PaginationMetaSchema(BaseModel):
    total: int
    page: int
    limit: int
    total_pages: int
    has_next_page: bool
    has_previous_page: bool


class PaginatedDeveloperResponseSchema(BaseModel):
    data: list[DeveloperResponseSchema]
    meta: PaginationMetaSchema