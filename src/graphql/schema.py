import strawberry
from typing import Optional
from uuid import UUID


@strawberry.type
class DeveloperType:
    id: UUID
    name: str
    country: Optional[str]


@strawberry.type
class VerdictType:
    classification: str
    explanation: str
    confidence: str
    critic: float
    user: float
    sales: float
    divergence: float


@strawberry.type
class GameType:
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

    # nested resolvers -- these are filled in by the resolver layer
    verdict: Optional[VerdictType] = strawberry.field(default=None)
    developers: Optional[list[DeveloperType]] = strawberry.field(default=None)


@strawberry.type
class GamePage:
    data: list[GameType]
    total: int
    page: int
    total_pages: int


@strawberry.type
class ControversyType:
    id: UUID
    title: str
    platform: str
    release_year: Optional[int]
    meta_score: Optional[float]
    user_review: Optional[float]
    divergence: float


@strawberry.type
class DecadeTrendType:
    decade: int
    release_count: int
    avg_meta_score: Optional[float]
    avg_user_review: Optional[float]
    total_sales: Optional[float]