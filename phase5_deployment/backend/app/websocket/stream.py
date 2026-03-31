"""
WebSocket — Real-time emission data streaming.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.engine import engine

logger = logging.getLogger("backend.websocket")
router = APIRouter()

# Active connections
_connections: Set[WebSocket] = set()


@router.websocket("/ws/emissions")
async def emission_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time emission updates.

    Clients connect and receive new emission results as they are processed.
    Sends data every 2 seconds with latest system stats.
    """
    await websocket.accept()
    _connections.add(websocket)
    logger.info("WebSocket client connected. Total: %d", len(_connections))

    try:
        last_count = len(engine._results)
        while True:
            await asyncio.sleep(2)

            current_count = len(engine._results)

            # Send new results since last check
            if current_count > last_count:
                new_results = engine._results[last_count:current_count]
                for r in new_results:
                    await websocket.send_json({
                        "type": "emission",
                        "data": r,
                    })
                last_count = current_count

            # Always send heartbeat with system stats
            await websocket.send_json({
                "type": "heartbeat",
                "data": {
                    "total_readings": len(engine._results),
                    "blockchain_blocks": engine.blockchain.length if engine.blockchain else 0,
                    "token_supply": round(engine.token.total_supply, 6) if engine.token else 0,
                    "active_connections": len(_connections),
                    "timestamp": time.time(),
                },
            })

    except WebSocketDisconnect:
        _connections.discard(websocket)
        logger.info("WebSocket client disconnected. Total: %d", len(_connections))
    except Exception as e:
        _connections.discard(websocket)
        logger.error("WebSocket error: %s", e)
