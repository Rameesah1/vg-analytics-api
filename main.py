from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.auth.router import router as auth_router
from src.games.router import router as games_router
from src.developers.router import router as developers_router
from src.insights.router import router as analytics_router
from src.squads.router import router as squads_router
from src.battles.router import router as battles_router

# 60 requests per minute per IP — mirrors ThrottlerModule.forRoot([{ ttl: 60000, limit: 60 }])
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Video Game Analytics API starting up...")
    print("Swagger docs at http://localhost:8000/api/docs")
    yield
    print(" shutting down...")


app = FastAPI(
    title="Video Game Analytics API",
    description=(
        "COMP3011 Web Services and Web Data — Video Game Analytics API. "
        "Authenticate via /api/auth/login and use the returned JWT as Bearer token for protected routes."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# routers
app.include_router(auth_router)
app.include_router(games_router)
app.include_router(developers_router)
app.include_router(analytics_router)
app.include_router(squads_router) 
app.include_router(battles_router)

@app.get("/api/health", tags=["health"])
@limiter.exempt
def health():
    return {"status": "ok"}