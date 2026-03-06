from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


# --- query params ---

class SquadFilterSchema(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    name: Optional[str] = Field(default=None, example="My Rockstar Squad")


# --- request bodies ---

class CreateSquadSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, example="Rockstar Legends")
    description: Optional[str] = Field(default=None, max_length=200, example="My all time favourite Rockstar games")
    is_public: bool = Field(default=False)


class UpdateSquadSchema(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    description: Optional[str] = Field(default=None, max_length=200)
    is_public: Optional[bool] = Field(default=None)


class AddSquadItemSchema(BaseModel):
    game_release_id: str = Field(..., example="2fb6a848-8874-4e97-b735-dff6c5dbb417")
    notes: Optional[str] = Field(default=None, example="My favourite game of all time")