"""
Emission Routes — Submit readings, query records, facility info.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from app.core.security import get_current_user, require_role, rate_limiter
from app.core.monitoring import EMISSIONS_PROCESSED
from app.models.schemas import (
    SensorReading, EmissionResult, EmissionSummary, FacilityInfo, APIResponse,
)
from app.services.engine import engine

router = APIRouter(prefix="/emissions", tags=["Emissions"])


@router.post("/readings", response_model=APIResponse)
async def submit_reading(
    reading: SensorReading,
    user=Depends(require_role("admin", "operator")),
    _=Depends(rate_limiter),
):
    """Submit a sensor reading for processing through the AI pipeline."""
    result = engine.process_reading(reading.model_dump())
    EMISSIONS_PROCESSED.inc()
    return APIResponse(success=True, message="Reading processed", data=result)


@router.post("/readings/batch", response_model=APIResponse)
async def submit_batch(
    readings: List[SensorReading],
    user=Depends(require_role("admin", "operator")),
):
    """Submit multiple readings at once."""
    results = []
    for r in readings[:100]:  # Cap at 100
        result = engine.process_reading(r.model_dump())
        EMISSIONS_PROCESSED.inc()
        results.append(result)
    return APIResponse(
        success=True,
        message=f"Processed {len(results)} readings",
        data=results,
    )


@router.get("/readings", response_model=APIResponse)
async def get_readings(
    facility_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    user=Depends(get_current_user),
):
    """Query processed emission records."""
    results = engine._results
    if facility_id:
        results = [r for r in results if r["facility_id"] == facility_id]
    return APIResponse(data=results[-limit:])


@router.get("/summary", response_model=APIResponse)
async def get_summary(user=Depends(get_current_user)):
    """Get aggregated emission statistics."""
    return APIResponse(data=engine.get_emission_summary())


@router.get("/facilities", response_model=APIResponse)
async def get_facilities(user=Depends(get_current_user)):
    """List all facilities with emission stats."""
    return APIResponse(data=engine.get_facilities())
