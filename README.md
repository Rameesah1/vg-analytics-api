# Video Game Industry Analytics API

A REST + GraphQL API combining two Kaggle datasets for video game industry analytics, built for COMP3011 Web Services and Web Data.

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Framework | FastAPI |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy |
| Validation | Pydantic |
| Auth | JWT + RBAC |
| GraphQL | Strawberry |
| MCP Server | Python MCP SDK |
| Rate Limiting | slowapi |
| Testing | Pytest |
| Deployment | Render |

## Datasets

- **VGChartz 2024** — 63,575 game releases with global sales data
- **Metacritic 1995–2021** — 18k games with critic and user scores
- Joined via exact + fuzzy title matching — 10,461 records have both datasets
- `matchConfidence` and `matchStrategy` stored per record

## Setup

### Prerequisites
- Python 3.12+
- Docker + Docker Compose

### Run locally

```bash
# 1. Clone the repo
git clone https://github.com/Rameesah1/COMP3011-VideoGame-API
cd COMP3011-VideoGame-API

# 2. Copy env file and fill in your JWT secret
cp .env.example .env

# 3. Start PostgreSQL
docker compose up postgres -d

# 4. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 5. Install dependencies
pip install -r requirements.txt

# 6. Run migrations
alembic upgrade head

# 7. Seed the database (first time only)
python scripts/seed.py

# 8. Start the API
uvicorn main:app --reload
```

API runs at: http://localhost:8000
Swagger docs: http://localhost:8000/api/docs

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | /api/auth/register | Register a new user |
| POST | /api/auth/login | Login and receive JWT |
| GET | /api/auth/me | Get current user |
| GET | /api/games | List games (paginated, filterable) |
| GET | /api/games/:id | Get single game |
| GET | /api/developers | List developers with portfolio stats |
| GET | /api/developers/:id | Get developer with top games |
| GET | /api/analytics/verdict/:id | Verdict Machine classification |
| GET | /api/analytics/leaderboard | Top rated games |
| GET | /api/analytics/hidden-gems | Hidden gem games |
| GET | /api/analytics/controversy | Most controversial games |
| GET | /api/analytics/decade-trends | Sales and scores by decade |
| GET | /api/analytics/platform-dominance | Platform market share |
| POST/GET/PATCH/DELETE | /api/squads | Squad management |
| GET | /api/squads/:id/dna | Squad DNA analysis |
| POST/GET | /api/battles | Battle two squads |

## API Documentation

Full documentation available at `/api/docs` (Swagger UI) after running the API.
