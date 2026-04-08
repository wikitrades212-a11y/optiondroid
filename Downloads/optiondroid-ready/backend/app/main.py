"""
Options Analytics API — FastAPI entrypoint.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.routers import options_router, calculator_router
from app.providers import provider

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm up provider session on startup."""
    logger.info(f"Starting with provider: {settings.data_provider}")
    try:
        ok = await provider.health_check()
        if ok:
            logger.info("Provider health check passed.")
        else:
            logger.warning("Provider health check failed — check credentials.")
    except Exception as exc:
        logger.warning(f"Provider warmup error (non-fatal): {exc}")
    yield
    logger.info("Shutting down.")


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.rate_limit}/minute"],
)

app = FastAPI(
    title="Options Analytics API",
    description="Production-grade options flow analysis powered by Robinhood.",
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
    return {"status": "ok", "provider": settings.data_provider}


@app.get("/", tags=["meta"])
async def root():
    return {
        "name": "Options Analytics API",
        "version": "1.0.0",
        "docs": "/docs",
    }
