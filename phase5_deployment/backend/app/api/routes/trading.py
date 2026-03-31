"""
Trading Routes — Order placement, order book, trade history, price.
"""
from fastapi import APIRouter, Depends

from app.core.security import get_current_user, require_role, rate_limiter
from app.core.monitoring import TRADES_EXECUTED
from app.models.schemas import OrderRequest, APIResponse
from app.services.engine import engine

router = APIRouter(prefix="/trading", tags=["Trading"])


@router.post("/orders", response_model=APIResponse)
async def place_order(
    order: OrderRequest,
    user=Depends(require_role("admin", "operator")),
    _=Depends(rate_limiter),
):
    """Place a buy or sell order on the carbon credit market."""
    result = engine.place_order(order.model_dump())
    TRADES_EXECUTED.inc()
    return APIResponse(success=True, message="Order placed", data=result)


@router.get("/orderbook", response_model=APIResponse)
async def get_orderbook(user=Depends(get_current_user)):
    """View current order book (bids and asks)."""
    return APIResponse(data=engine.get_order_book())


@router.get("/history", response_model=APIResponse)
async def get_trade_history(user=Depends(get_current_user)):
    """Get recent trade history."""
    return APIResponse(data=engine.get_trade_history())


@router.get("/price", response_model=APIResponse)
async def get_price(user=Depends(get_current_user)):
    """Get current carbon credit price and market info."""
    price = engine.get_current_price()
    return APIResponse(data={
        "current_price": round(price, 2),
        "currency": "USD",
        "symbol": "CCT",
        "change_24h_pct": round(0.5, 2),
        "volume_24h": len(engine._trades),
    })
