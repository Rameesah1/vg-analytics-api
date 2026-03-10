from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.auth.router import router as auth_router
from src.games.router import router as games_router
from src.developers.router import router as developers_router
from src.insights.router import router as analytics_router
from src.squads.router import router as squads_router
from src.battles.router import router as battles_router
from src.graphql.router import router as graphql_router

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Video Game Analytics API starting up...")
    print("Swagger docs at http://localhost:8000/api/docs")
    print("GraphQL playground at http://localhost:8000/api/graphql")
    yield
    print("shutting down...")


app = FastAPI(
    title="Video Game Analytics API",
    description=(
        "COMP3011 Web Services and Web Data -- Video Game Analytics API. "
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
    allow_headers=["*"],
    allow_methods=["*"],
)

app.include_router(auth_router)
app.include_router(games_router)
app.include_router(developers_router)
app.include_router(analytics_router)
app.include_router(squads_router)
app.include_router(battles_router)
app.include_router(graphql_router)

# serve frontend at root
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", include_in_schema=False)
def frontend():
    return FileResponse("static/index.html")


@app.get("/api/health", tags=["health"])
@limiter.exempt
def health():
    return {"status": "ok"}