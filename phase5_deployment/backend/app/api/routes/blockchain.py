"""
Blockchain Routes — Chain status, block explorer, verification.
"""
from fastapi import APIRouter, Depends, Query

from app.core.security import get_current_user
from app.core.monitoring import BLOCKCHAIN_BLOCKS
from app.models.schemas import APIResponse
from app.services.engine import engine

router = APIRouter(prefix="/blockchain", tags=["Blockchain"])


@router.get("/status", response_model=APIResponse)
async def get_status(user=Depends(get_current_user)):
    """Get blockchain status — length, validity, latest hash."""
    status = engine.get_blockchain_status()
    BLOCKCHAIN_BLOCKS.set(status["chain_length"])
    return APIResponse(data=status)


@router.get("/blocks", response_model=APIResponse)
async def get_blocks(
    limit: int = Query(10, ge=1, le=100),
    user=Depends(get_current_user),
):
    """Get recent blocks from the chain."""
    return APIResponse(data=engine.get_recent_blocks(limit))


@router.get("/verify", response_model=APIResponse)
async def verify_chain(user=Depends(get_current_user)):
    """Perform full chain integrity verification."""
    return APIResponse(data=engine.verify_chain())
