# Video Game Industry Analytics API

A REST + GraphQL API combining two public Kaggle datasets to provide video game industry analytics. Built for COMP3011 Web Services and Web Data at the University of Leeds.

**Live API:** https://vg-analytics-api.onrender.com (coming soon)  
**Swagger Docs:** https://vg-analytics-api.onrender.com/api/docs  
**API Documentation PDF:** [docs/api-docs.pdf](docs/api-docs.pdf)  
**Frontend Dashboard:** served at the root URL  

---

## Tech Stack

| Layer | Technology | Justification |
|---|---|---|
| Language | Python 3.12 | De facto language for data analytics workloads |
| Framework | FastAPI | Async, automatic Swagger, Pydantic validation — explicitly listed in brief |
| Database | PostgreSQL 16 | Relational model suits 13-table schema with complex joins |
| ORM | SQLAlchemy | SQL transparency for complex analytics queries |
| Validation | Pydantic | Runtime type validation on all request/response models |
| Auth | JWT + RBAC | Stateless authentication with role-based access control |
| GraphQL | Strawberry | Eliminates N+1 problem for nested game/verdict/developer queries |
| MCP Server | Python MCP SDK | Exposes API as LLM tool source via Anthropic MCP protocol |
| Caching | Redis | 5-minute TTL on expensive analytics aggregations |
| Rate Limiting | slowapi | 60 requests/minute per IP |
| Testing | Pytest | Unit + integration test suite covering 67 test cases |
| Deployment | Render | Cloud deployment via Docker |

---

## Datasets

- **VGChartz 2024** — 63,575 game releases with global, NA, JP, PAL and other regional sales data
- **Metacritic 1995–2021** — 18,000 games with critic scores and user reviews
- Joined via exact + fuzzy title matching — 10,461 records have data from both sources
- `match_confidence` and `match_strategy` stored per record for data provenance

---

## Key Features

- **Verdict Machine** — classifies any game across 10 categories (All-Time Classic, Hidden Gem, Cult Classic, Overhyped etc.) using weighted critic, user and sales scores with a confidence rating
- **Squad Battles** — build squads of games and battle them head to head using 4 configurable scoring presets
- **GraphQL layer** — single query fetches game + verdict + developer, eliminating 3 REST calls
- **MCP Server** — exposes 5 tools for LLM clients to query the database in natural language
- **Ask AI** — natural language interface powered by Claude using the MCP tool loop
- **Redis caching** — analytics endpoints cached with graceful fallback if Redis unavailable

---

## Project Structure

```
vg-analytics-api/
├── main.py                 # FastAPI app entry point
├── src/
│   ├── auth/               # JWT auth + RBAC
│   ├── games/              # Game releases CRUD
│   ├── developers/         # Developer portfolio analytics
│   ├── insights/           # Verdict Machine + analytics endpoints
│   ├── squads/             # Squad management
│   ├── battles/            # Battle scoring engine
│   ├── graphql/            # Strawberry GraphQL schema + resolvers
│   ├── mcp/                # MCP server with 5 tools
│   ├── ask/                # AI natural language endpoint
│   └── db/                 # SQLAlchemy models + session
├── tests/                  # Pytest unit + integration tests
├── scripts/                # Data seeding scripts
├── static/                 # Frontend dashboard
└── docker-compose.yml      # PostgreSQL + Redis + API
```

---

## Local Setup

### Prerequisites
- Python 3.12+
- Docker + Docker Compose
- An Anthropic API key (for the Ask AI feature)

### Steps

```bash
# 1. Clone the repo
git clone https://github.com/Rameesah1/vg-analytics-api
cd vg-analytics-api

# 2. Copy env file and fill in values
cp .env.example .env

# 3. Start PostgreSQL and Redis
docker compose up postgres redis -d

# 4. Create virtual environment and install dependencies
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# 5. Run database migrations
alembic upgrade head

# 6. Seed the database (first time only -- takes a few minutes)
python scripts/seed.py

# 7. Start the API
uvicorn main:app --reload
```

| URL | Description |
|---|---|
| http://localhost:8000 | Frontend dashboard |
| http://localhost:8000/api/docs | Swagger UI |
| http://localhost:8000/api/graphql | GraphQL playground |
| http://localhost:8000/api/health | Health check |

---

## Authentication

Register and login to get a JWT token:

```bash
# Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "email": "you@example.com", "password": "yourpassword"}'

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "yourpassword"}'
```

Use the returned `access_token` as a Bearer token in the Authorization header for protected routes.

---

## API Endpoints

### Auth
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | /api/auth/register | No | Register a new user |
| POST | /api/auth/login | No | Login and receive JWT |
| GET | /api/auth/me | Yes | Get current user |

### Games
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | /api/games | No | List games with filters and pagination |
| GET | /api/games/:id | No | Get single game with full detail |
| POST | /api/games | Admin | Create a game release |
| PATCH | /api/games/:id | Admin | Update a game release |
| DELETE | /api/games/:id | Admin | Delete a game release |

### Analytics
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | /api/analytics/verdict/:id | No | Verdict Machine classification |
| GET | /api/analytics/leaderboard | No | Top games by metric |
| GET | /api/analytics/hidden-gems | No | High user score, low commercial visibility |
| GET | /api/analytics/controversy | No | Biggest critic vs player disagreements |
| GET | /api/analytics/decade-trends | No | Sales and scores grouped by decade |
| GET | /api/analytics/platform-dominance | No | Platform market share by era |

### Squads & Battles
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST/GET | /api/squads | Yes | Create and list squads |
| GET/PATCH/DELETE | /api/squads/:id | Yes | Manage a squad |
| POST/DELETE | /api/squads/:id/items | Yes | Add/remove games from squad |
| GET | /api/squads/:id/dna | Yes | Squad DNA analysis |
| POST/GET | /api/battles | Yes | Battle two squads |

### Other
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | /api/ask | No | Natural language AI interface |
| GET | /api/developers | No | Developer portfolio analytics |
| POST | /api/graphql | No | GraphQL endpoint |
| GET | /api/health | No | Health check |

---

## Error Codes

| Code | Meaning |
|---|---|
| 400 | Bad request — validation error or business rule violation |
| 401 | Unauthorised — missing or invalid JWT token |
| 403 | Forbidden — insufficient permissions (e.g. non-admin on admin route) |
| 404 | Not found — resource does not exist |
| 409 | Conflict — duplicate resource (e.g. username already taken) |
| 422 | Unprocessable entity — request body failed Pydantic validation |
| 429 | Too many requests — rate limit exceeded (60/min) |
| 500 | Internal server error |

---

## Running Tests

```bash
# All tests
pytest tests/ -v

# Unit tests only (no database needed)
pytest tests/test_verdict.py tests/test_battles.py -v

# Integration tests
pytest tests/test_auth.py tests/test_games.py tests/test_analytics.py tests/test_squads.py -v
```

67 tests across unit and integration layers. Unit tests cover all 10 Verdict Machine classifications and all 4 battle scoring presets. Integration tests validate endpoint behaviour, auth guards and error responses.

---

## GenAI Declaration

Claude (Anthropic) was used throughout this project as a development assistant for implementation guidance, debugging, and exploring architectural alternatives. All design decisions — including the dataset choice, Verdict Machine algorithm, fuzzy matching approach, Squads/Battles concept, and technology stack - were made independently. Conversation logs are included as an appendix in the technical report.