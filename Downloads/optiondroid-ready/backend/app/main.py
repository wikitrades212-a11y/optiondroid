"""
Options Analytics API — FastAPI entrypoint.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.routers import options_router, calculator_router
from app.providers import provider, get_provider_status

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# Cached at startup; refreshed on each call to /api/provider/status
_provider_status: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm up provider session and log readiness on startup."""
    global _provider_status
    logger.info(f"Starting with provider: {settings.data_provider}")
    _provider_status = await get_provider_status()
    readiness = _provider_status.get("readiness", "unknown")
    message   = _provider_status.get("message", "")
    if readiness in ("live", "delayed"):
        logger.info(f"Provider ready — {readiness}: {message}")
    else:
        logger.warning(f"Provider NOT ready — {readiness}: {message}")
    yield
    logger.info("Shutting down.")


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.rate_limit}/minute"],
)

app = FastAPI(
    title="Options Analytics API",
    description="Production-grade options flow analysis.",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(options_router)
app.include_router(calculator_router)


@app.get("/health", tags=["meta"])
async def health():
    return {
        "status": "ok",
        "provider": settings.data_provider,
        "readiness": _provider_status.get("readiness", "unknown"),
    }


@app.get("/api/provider/status", tags=["meta"])
async def provider_status():
    """
    Returns real-time provider readiness state.

    Readiness values:
      live             — health check passed, real-time data
      delayed          — health check passed, data is delayed (Polygon free tier)
      pending_approval — credentials set but broker API access not confirmed
      misconfigured    — required env vars missing
      unavailable      — health check failed
    """
    status = await get_provider_status()
    return status


@app.get("/", tags=["meta"])
async def root():
    return {
        "name": "Options Analytics API",
        "version": "1.0.0",
        "docs": "/docs",
        "provider": settings.data_provider,
        "readiness": _provider_status.get("readiness", "unknown"),
    }
