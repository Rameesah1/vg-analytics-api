from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


# 60 requests per minute per IP — mirrors ThrottlerModule.forRoot([{ ttl: 60000, limit: 60 }])
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🎮 Video Game Analytics API starting up...")
    print("📚 Swagger docs at http://localhost:8000/api/docs")
    yield
    print("🎮 shutting down...")


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

# attach rate limiter to app state so slowapi can find it
app.state.limiter = limiter

# return 429 with a clear message when rate limit is exceeded
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# open CORS for development — tighten in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["health"])
@limiter.exempt  # health checks shouldn't count against the rate limit
def health():
    return {"status": "ok"}