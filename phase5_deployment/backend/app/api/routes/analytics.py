"""
Analytics Routes — Dashboard overview, price forecast, system comparison.
"""
from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.models.schemas import APIResponse
from app.services.engine import engine

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview", response_model=APIResponse)
async def dashboard_overview(user=Depends(get_current_user)):
    """Get system-wide dashboard statistics."""
    return APIResponse(data=engine.get_dashboard_overview())


@router.get("/forecast", response_model=APIResponse)
async def price_forecast(user=Depends(get_current_user)):
    """Get ARIMA-based credit price forecast."""
    return APIResponse(data=engine.get_price_forecast())


@router.get("/comparison", response_model=APIResponse)
async def system_comparison(user=Depends(get_current_user)):
    """Get comparative analysis data (radar chart)."""
    return APIResponse(data=engine.get_comparison_data())


@router.get("/emissions/trend", response_model=APIResponse)
async def emission_trend(user=Depends(get_current_user)):
    """Get emission trend data for charts."""
    results = engine._results[-200:]
    data = [
        {"timestamp": r["timestamp"], "co2e": r["co2e_emission"],
         "facility": r["facility_id"]}
        for r in results
    ]
    return APIResponse(data=data)
