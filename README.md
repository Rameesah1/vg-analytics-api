# Video Game Industry Analytics API

A REST and GraphQL API combining two public datasets to surface meaningful analytics about the video game industry. Built for COMP3011 Web Services and Web Data at the University of Leeds.

The core idea is that critic scores, player reviews and commercial sales data each tell a different part of the story, but no single tool brings them together. This API does exactly that, with a Verdict Machine that classifies any game using all three signals at once.

**Live API:** https://vg-analytics-api.onrender.com
**Swagger Docs:** https://vg-analytics-api.onrender.com/api/docs
**API Documentation PDF:** [api-docs.pdf](api-docs.pdf)
**Frontend Dashboard:** served at the root URL

---

## Tech Stack

| Layer | Technology | Justification |
|---|---|---|
| Language | Python 3.12 | Best ecosystem for data analytics and the Anthropic/MCP SDKs are Python-first |
| Framework | FastAPI | Async, automatic Swagger docs, Pydantic validation built in |
| Database | PostgreSQL 16 | Relational model suits a 13-table schema with complex joins |
| ORM | SQLAlchemy | SQL transparency for analytics queries; raw text() blocks where needed |
| Validation | Pydantic | Runtime type checking on all inputs and outputs |
| Auth | JWT + RBAC | Stateless authentication with two roles: USER and ADMIN |
| GraphQL | Strawberry | Eliminates N+1 round trips for nested game/verdict/developer queries |
| MCP Server | Python MCP SDK | Exposes the API as a tool source for LLM clients |
| Caching | Redis | 5-minute TTL on expensive analytics endpoints, graceful fallback if unavailable |
| Rate Limiting | slowapi | 60 requests per minute per IP |
| Testing | Pytest | 72 tests across unit, integration and system layers |
| Deployment | Render | Docker-based cloud deployment with GitHub Actions CI/CD |

---

## Datasets

- **VGChartz 2024** - game releases across all major platforms with global and regional sales data
- **Metacritic 1995-2021** - critic scores and user reviews covering releases up to 2021
- The two datasets are joined using exact normalised title matching followed by fuzzy matching for titles that do not align exactly
- Every record stores a `match_confidence` score and `match_strategy` field so consumers can filter by data quality

---

## Key Features

- **Verdict Machine** -- classifies any game across 10 categories (All-Time Classic, Hidden Gem, Cult Classic, Overhyped and more) using sales-weighted averaging across all platform releases, with a confidence rating reflecting data completeness
- **Squad Battles** -- build curated collections of games and battle them head to head using 4 weighted scoring presets or custom weights
- **GraphQL layer** -- a single query fetches game, verdict and developer data, replacing 3 separate REST calls
- **MCP Server** -- 5 tools let LLM clients query the database directly in natural language
- **Ask AI** -- a chat endpoint that routes natural language questions through Claude, which autonomously calls the MCP tools and synthesises a response
- **Redis caching** -- the five most expensive analytics endpoints are cached with a graceful fallback to PostgreSQL if Redis is unavailable

---

## Project Structure

```
vg-analytics-api/
├── main.py                 # FastAPI app entry point
├── src/
│   ├── auth/               # JWT auth and RBAC
│   ├── games/              # Game releases CRUD
│   ├── developers/         # Developer portfolio analytics
│   ├── insights/           # Verdict Machine and analytics endpoints
│   ├── squads/             # Squad management
│   ├── battles/            # Battle scoring engine
│   ├── graphql/            # Strawberry GraphQL schema and resolvers
│   ├── mcp/                # MCP server with 5 tools
│   ├── ask/                # AI natural language endpoint
│   └── db/                 # SQLAlchemy models and session
├── tests/                  # Pytest unit, integration and system tests
├── scripts/                # Data normalisation and seeding scripts
├── static/                 # Frontend dashboard (single HTML file)
└── docker-compose.yml      # PostgreSQL, Redis and API
```

---

## Local Setup

### Prerequisites
- Python 3.12+
- Docker and Docker Compose
- An Anthropic API key (only needed for the Ask AI feature)

### Steps

```bash
# 1. Clone the repo
git clone https://github.com/Rameesah1/vg-analytics-api
cd vg-analytics-api

# 2. Copy the env file and fill in your values
cp .env.example .env

# 3. Start PostgreSQL and Redis
docker compose up postgres redis -d

# 4. Create a virtual environment and install dependencies
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

Register and login to receive a JWT token:

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

Pass the returned `access_token` as a Bearer token in the Authorization header on protected routes.

---

## API Endpoints

### Auth
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | /api/auth/register | No | Register a new user |
| POST | /api/auth/login | No | Login and receive JWT |
| GET | /api/auth/me | Yes | Get current user profile |

### Games
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | /api/games | No | List games with filters and pagination |
| GET | /api/games/search | No | Search by title, returns one result per game not per release |
| GET | /api/games/:id | No | Get a single game release with full detail |
| POST | /api/games | Admin | Create a game release |
| PATCH | /api/games/:id | Admin | Update a game release |
| DELETE | /api/games/:id | Admin | Delete a game release |

### Analytics
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | /api/analytics/verdict/game/:game_id | No | Verdict Machine classification aggregated across all platform releases |
| GET | /api/analytics/verdict/:release_id | No | Verdict Machine classification for a single release |
| GET | /api/analytics/leaderboard | No | Top games by metric |
| GET | /api/analytics/hidden-gems | No | High user scores with low commercial visibility |
| GET | /api/analytics/controversy | No | Games where critics and players disagreed most |
| GET | /api/analytics/decade-trends | No | Sales and scores grouped by decade |
| GET | /api/analytics/platform-dominance | No | Platform market share by era |
| GET | /api/analytics/stats | No | Database statistics |

### Squads and Battles
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST/GET | /api/squads | Yes | Create and list squads |
| GET/PATCH/DELETE | /api/squads/:id | Yes | Manage a squad |
| POST/DELETE | /api/squads/:id/items | Yes | Add or remove games from a squad |
| GET | /api/squads/:id/dna | Yes | Squad DNA analysis |
| POST/GET | /api/battles | Yes | Battle two squads head to head |

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
| 400 | Bad request -- validation error or business rule violation |
| 401 | Unauthorised -- missing or invalid JWT token |
| 403 | Forbidden -- insufficient permissions |
| 404 | Not found -- resource does not exist |
| 409 | Conflict -- duplicate resource such as a username already taken |
| 422 | Unprocessable entity -- request body failed Pydantic validation |
| 429 | Too many requests -- rate limit exceeded (60 per minute) |
| 500 | Internal server error |

---

## Running Tests

The test suite is split across three layers. Unit tests instantiate services directly with no database needed, so they run fast and in isolation. Integration tests run against the live seeded database. System tests bring up the full application and verify routing and API contracts end to end.

```bash
# Run everything
pytest tests/ -v

# Unit tests only (no database required)
pytest tests/test_verdict.py tests/test_battles.py -v

# Integration tests
pytest tests/test_auth.py tests/test_games.py tests/test_analytics.py tests/test_squads.py -v

# System tests
pytest tests/test_system.py -v
```

72 tests passing. Unit tests cover all 10 Verdict Machine classification branches and all 4 battle scoring presets including custom weight validation. Integration tests cover authentication flows, game filtering and sorting, all analytics endpoints, and the full squads and battles lifecycle including error cases.

---

## CI/CD

A GitHub Actions pipeline runs automatically on every push to `main` and `develop`. It provisions a PostgreSQL instance, runs the unit and system test suites, and only proceeds if everything passes. Deployment to Render triggers automatically on a successful push to `main`, rebuilding from the Docker image with no manual steps required.

---

## GenAI Declaration

Claude (Anthropic) was used throughout this project as a research partner, debugging assistant and deployed runtime component. Technology stack decisions were stress-tested by prompting Claude to argue against them, architectural choices like the GraphQL dual-API approach were explored through directed conversation, and specific failures like the Strawberry/Pydantic version conflict and the passlib/Python 3.12 incompatibility were diagnosed with its help. All design decisions were made independently. The most interesting use of AI here is the Ask AI feature, where Claude runs at runtime as a deployed component rather than a development tool, autonomously calling MCP tools to answer natural language questions against the live database. Conversation logs are included as an appendix in the technical report.
