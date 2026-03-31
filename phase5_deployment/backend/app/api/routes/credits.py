"""
Credit Routes — Balance, history, calculations.
"""
from fastapi import APIRouter, Depends

from app.core.security import get_current_user, rate_limiter
from app.models.schemas import APIResponse
from app.services.engine import engine

router = APIRouter(prefix="/credits", tags=["Carbon Credits"])


@router.get("/balance/{facility_id}", response_model=APIResponse)
async def get_balance(facility_id: str, user=Depends(get_current_user)):
    """Get credit balance for a facility."""
    return APIResponse(data=engine.get_credit_balance(facility_id))


@router.get("/balances", response_model=APIResponse)
async def get_all_balances(user=Depends(get_current_user)):
    """Get all facility credit balances."""
    balances = engine.token.get_all_balances()
    data = [
        {"facility_id": fid, "balance": round(bal, 6)}
        for fid, bal in sorted(balances.items(), key=lambda x: -x[1])
    ]
    return APIResponse(data=data)


@router.get("/supply", response_model=APIResponse)
async def get_supply(user=Depends(get_current_user)):
    """Get total CCT token supply info."""
    return APIResponse(data={
        "total_supply": round(engine.token.total_supply, 6),
        "holders": len(engine.token.get_all_balances()),
        "symbol": engine.token.symbol,
        "name": engine.token.name,
    })


@router.get("/history", response_model=APIResponse)
async def get_credit_history(
    facility_id: str = None,
    user=Depends(get_current_user),
):
    """Get credit transaction history."""
    results = engine._results
    if facility_id:
        results = [r for r in results if r["facility_id"] == facility_id]
    history = [
        {
            "facility_id": r["facility_id"],
            "credits_earned": r["credits_earned"],
            "credits_penalty": r["credits_penalty"],
            "net": round(r["credits_earned"] - r["credits_penalty"], 6),
            "timestamp": r["timestamp"],
        }
        for r in results[-100:]
    ]
    return APIResponse(data=history)
