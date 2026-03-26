"""
FastAPI Backend Server
=======================
Receives batches of processed sensor readings from the edge gateway,
inserts them into TimescaleDB, and exposes query endpoints.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field, validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database import async_engine, get_async_session
from src.backend.models import Base, EmissionReading

logger = logging.getLogger("backend.api")

# ── FastAPI app ──────────────────────────────────────────────────────────

app = FastAPI(
    title="Carbon Emission Monitor — Backend API",
    version="1.0.0",
    description=(
        "Phase 1 backend: ingests processed IoT emission readings, "
        "stores in TimescaleDB, and exposes query endpoints."
    ),
)


# ── Startup / shutdown ───────────────────────────────────────────────────

@app.on_event("startup")
async def on_startup():
    """Create tables if they don't exist (idempotent)."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        await conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM timescaledb_information.hypertables
                    WHERE hypertable_name = 'emission_readings'
                ) THEN
                    PERFORM create_hypertable(
                        'emission_readings',
                        'timestamp_utc',
                        if_not_exists => TRUE
                    );
                END IF;
            EXCEPTION WHEN undefined_function THEN
                RAISE NOTICE 'TimescaleDB not installed — using plain table';
            END $$;
        """))

    logger.info("Backend tables initialised.")


@app.on_event("shutdown")
async def on_shutdown():
    await async_engine.dispose()


# ── Pydantic schemas ─────────────────────────────────────────────────────

class SensorReadingIn(BaseModel):
    facility_id: str = Field(..., min_length=1, max_length=16)
    timestamp_utc: str
    co2_ppm: float
    ch4_ppm: float
    nox_ppb: float
    fuel_rate: float
    energy_kwh: float

    @validator("timestamp_utc")
    def parse_timestamp(cls, v):
        try:
            datetime.fromisoformat(v)
        except ValueError:
            raise ValueError(f"Invalid ISO 8601 timestamp: {v}")
        return v


class IngestBatch(BaseModel):
    readings: List[SensorReadingIn] = Field(..., min_length=1, max_length=1000)


class IngestResponse(BaseModel):
    status: str = "ok"
    inserted: int


class HealthResponse(BaseModel):
    status: str = "healthy"
    db_connected: bool
    readings_total: Optional[int] = None


class MLInferenceRequest(BaseModel):
    facility_id: str
    features: dict


class MLInferenceResponse(BaseModel):
    facility_id: str
    prediction: str = "placeholder"
    model_version: str = "stub-v0"


class BlockchainStubResponse(BaseModel):
    status: str = "stub"
    message: str = "Blockchain module not yet deployed — Phase 4"


# ── Ingest endpoint ─────────────────────────────────────────────────────

@app.post(
    "/api/v1/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Ingestion"],
    summary="Receive a batch of edge-processed sensor readings",
)
async def ingest_readings(
    batch: IngestBatch,
    session: AsyncSession = Depends(get_async_session),
):
    rows = []
    for r in batch.readings:
        rows.append(EmissionReading(
            facility_id=r.facility_id,
            timestamp_utc=datetime.fromisoformat(r.timestamp_utc),
            co2_ppm=r.co2_ppm,
            ch4_ppm=r.ch4_ppm,
            nox_ppb=r.nox_ppb,
            fuel_rate=r.fuel_rate,
            energy_kwh=r.energy_kwh,
        ))
    session.add_all(rows)
    await session.flush()
    return IngestResponse(inserted=len(rows))


# ── Query endpoints ──────────────────────────────────────────────────────

@app.get(
    "/api/v1/facilities/{facility_id}/readings",
    tags=["Query"],
    summary="Get recent readings for a facility",
)
async def get_readings(
    facility_id: str,
    limit: int = 100,
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        text("""
            SELECT id, facility_id, timestamp_utc,
                   co2_ppm, ch4_ppm, nox_ppb, fuel_rate, energy_kwh
            FROM emission_readings
            WHERE facility_id = :fid
            ORDER BY timestamp_utc DESC
            LIMIT :lim
        """),
        {"fid": facility_id, "lim": limit},
    )
    rows = result.mappings().all()
    return {"facility_id": facility_id, "count": len(rows), "readings": [dict(r) for r in rows]}


@app.get(
    "/api/v1/facilities/{facility_id}/stats",
    tags=["Query"],
    summary="Get aggregate stats for a facility",
)
async def get_facility_stats(
    facility_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(
        text("""
            SELECT
                COUNT(*) AS total_readings,
                MIN(timestamp_utc) AS first_reading,
                MAX(timestamp_utc) AS last_reading,
                AVG(co2_ppm)    AS avg_co2,
                AVG(ch4_ppm)    AS avg_ch4,
                AVG(nox_ppb)    AS avg_nox,
                AVG(fuel_rate)  AS avg_fuel,
                AVG(energy_kwh) AS avg_energy
            FROM emission_readings
            WHERE facility_id = :fid
        """),
        {"fid": facility_id},
    )
    row = result.mappings().first()
    return {"facility_id": facility_id, "stats": dict(row) if row else {}}


# ── Health check ─────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check(session: AsyncSession = Depends(get_async_session)):
    try:
        result = await session.execute(text("SELECT COUNT(*) FROM emission_readings"))
        count = result.scalar()
        return HealthResponse(db_connected=True, readings_total=count)
    except Exception:
        return HealthResponse(status="degraded", db_connected=False)


# ── Placeholder: ML inference ────────────────────────────────────────────

@app.post(
    "/api/v1/ml/predict",
    response_model=MLInferenceResponse,
    tags=["ML (Stub)"],
    summary="Placeholder for Phase 5 ML inference",
)
async def ml_predict(request: MLInferenceRequest):
    return MLInferenceResponse(facility_id=request.facility_id)


# ── Placeholder: Blockchain ──────────────────────────────────────────────

@app.get(
    "/api/v1/blockchain/status",
    response_model=BlockchainStubResponse,
    tags=["Blockchain (Stub)"],
    summary="Placeholder for Phase 4 blockchain integration",
)
async def blockchain_status():
    return BlockchainStubResponse()
