"""
Carbon Credit Trading Platform — FastAPI Application
======================================================

Production-ready backend wrapping Phase 1–4 logic into RESTful APIs.

Run:
    cd phase5_deployment/backend
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.core.config import settings
from app.core.monitoring import REQUEST_COUNT, REQUEST_LATENCY
from app.services.engine import engine

# ── Logging ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-25s | %(levelname)-7s | %(message)s",
)
logger = logging.getLogger("backend")


# ── Lifespan (startup / shutdown) ────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Carbon Credit Trading Platform...")
    engine.initialize()
    logger.info("Engine initialized. Server ready.")
    yield
    logger.info("Shutting down...")


# ── App ────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Production API for the Blockchain-Based Dynamic Carbon Credit "
        "Tokenisation and AI-Integrated P2P Trading Framework."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Middleware: request metrics ────────────────────────────────────────
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start

    endpoint = request.url.path
    method = request.method
    status = response.status_code

    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(elapsed)

    return response


# ── Routes ─────────────────────────────────────────────────────────────
from app.api.routes import auth, emissions, credits, trading, blockchain, analytics
from app.websocket.stream import router as ws_router

API_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(emissions.router, prefix=API_PREFIX)
app.include_router(credits.router, prefix=API_PREFIX)
app.include_router(trading.router, prefix=API_PREFIX)
app.include_router(blockchain.router, prefix=API_PREFIX)
app.include_router(analytics.router, prefix=API_PREFIX)
app.include_router(ws_router)

# ── Frontend Mounting ──────────────────────────────────────────────────
import os
from fastapi.staticfiles import StaticFiles
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "dist")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


# ── Health & Metrics ──────────────────────────────────────────────────
@app.get("/api/v1/health")
async def health():
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "uptime_seconds": round(engine.uptime, 1),
        "services": {
            "ai_engine": "active" if engine._initialized else "initializing",
            "blockchain": f"{engine.blockchain.length} blocks" if engine.blockchain else "offline",
            "token": f"{round(engine.token.total_supply, 4)} CCT" if engine.token else "offline",
        },
    }


@app.get("/metrics")
async def prometheus_metrics():
    from starlette.responses import Response
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ── Global exception handler ──────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": "Internal server error", "detail": str(exc)},
    )
