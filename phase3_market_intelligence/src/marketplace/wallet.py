"""
Wallet — Step 3.1
===================
Participant wallet wrapper around CarbonToken.
Tracks CCT balance, trade history, and pending orders.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional


class Wallet:
    """
    Participant wallet for carbon credit marketplace.

    Wraps token balance operations and maintains a local
    ledger of all wallet-level activity (trades, listings, rewards).
    """

    def __init__(self, participant_id: str, participant_type: str = "facility"):
        """
        Args:
            participant_id: Unique identifier (e.g. facility_id).
            participant_type: 'facility', 'broker', or 'regulator'.
        """
        self.participant_id = participant_id
        self.participant_type = participant_type
        self._activity_log: List[Dict[str, Any]] = []
        self._pending_listings: List[str] = []       # listing_ids
        self._pending_orders: List[int] = []          # order_ids
        self._total_traded_volume: float = 0.0
        self._total_fees_paid: float = 0.0
        self._created_at: float = time.time()

    def record_activity(self, activity_type: str, details: Dict[str, Any]):
        """Log a wallet activity."""
        entry = {
            "type": activity_type,
            "timestamp": time.time(),
            **details,
        }
        self._activity_log.append(entry)

        if activity_type in ("buy", "sell"):
            self._total_traded_volume += details.get("amount", 0.0)
            self._total_fees_paid += details.get("fee", 0.0)

    def add_pending_listing(self, listing_id: str):
        self._pending_listings.append(listing_id)

    def remove_pending_listing(self, listing_id: str):
        if listing_id in self._pending_listings:
            self._pending_listings.remove(listing_id)

    def add_pending_order(self, order_id: int):
        self._pending_orders.append(order_id)

    def remove_pending_order(self, order_id: int):
        if order_id in self._pending_orders:
            self._pending_orders.remove(order_id)

    def get_activity_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._activity_log[-limit:]

    def get_summary(self) -> Dict[str, Any]:
        return {
            "participant_id": self.participant_id,
            "participant_type": self.participant_type,
            "total_activities": len(self._activity_log),
            "total_traded_volume": round(self._total_traded_volume, 4),
            "total_fees_paid": round(self._total_fees_paid, 4),
            "pending_listings": len(self._pending_listings),
            "pending_orders": len(self._pending_orders),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "participant_id": self.participant_id,
            "participant_type": self.participant_type,
            "created_at": self._created_at,
            "summary": self.get_summary(),
        }
