"""
Carbon Credit Marketplace — Step 3.1
=======================================
Peer-to-peer marketplace for carbon credit trading.
Manages participant wallets, credit listings, bids, and trade history.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, List, Optional

from src.marketplace.wallet import Wallet
from src.config import (
    DEFAULT_CREDIT_PRICE, MIN_LISTING_AMOUNT,
    LISTING_EXPIRY_HOURS, MARKETPLACE_FEE_RATE,
)


class Listing:
    """A credit listing on the marketplace."""

    def __init__(self, listing_id: str, seller_id: str, amount: float,
                 price_per_credit: float, expiry_hours: float = LISTING_EXPIRY_HOURS):
        self.listing_id = listing_id
        self.seller_id = seller_id
        self.amount = amount
        self.price_per_credit = price_per_credit
        self.created_at = time.time()
        self.expires_at = self.created_at + (expiry_hours * 3600)
        self.status = "active"            # active, sold, cancelled, expired
        self.filled_amount = 0.0
        self.bids: List[Dict[str, Any]] = []

    @property
    def remaining(self) -> float:
        return self.amount - self.filled_amount

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at and self.status == "active"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "listing_id": self.listing_id,
            "seller_id": self.seller_id,
            "amount": self.amount,
            "remaining": round(self.remaining, 4),
            "price_per_credit": self.price_per_credit,
            "status": self.status,
            "bids_count": len(self.bids),
            "created_at": self.created_at,
        }


class CarbonMarketplace:
    """
    Peer-to-peer carbon credit marketplace.

    Features:
      - Participant wallet management
      - Credit listing with bidding
      - Direct buy / accept-bid execution
      - Transaction history with fee tracking
      - Integration with CarbonToken for settlement
    """

    def __init__(self, token_manager, blockchain, fee_rate: float = MARKETPLACE_FEE_RATE):
        """
        Args:
            token_manager: CarbonToken instance for balance/transfer ops.
            blockchain: Blockchain instance for recording transactions.
            fee_rate: Marketplace fee as fraction (e.g. 0.01 = 1%).
        """
        self._token = token_manager
        self._chain = blockchain
        self._fee_rate = fee_rate

        self._wallets: Dict[str, Wallet] = {}
        self._listings: Dict[str, Listing] = {}
        self._trade_history: List[Dict[str, Any]] = []
        self._next_listing_id = 1
        self._total_fees_collected = 0.0

    # ── Wallet Management ────────────────────────────────────────────────

    def register_participant(self, participant_id: str,
                              participant_type: str = "facility") -> Dict[str, Any]:
        """Register a new marketplace participant."""
        if participant_id in self._wallets:
            return {"status": "exists", "participant_id": participant_id}

        wallet = Wallet(participant_id, participant_type)
        self._wallets[participant_id] = wallet
        return {
            "status": "registered",
            "participant_id": participant_id,
            "participant_type": participant_type,
        }

    def get_wallet(self, participant_id: str) -> Optional[Wallet]:
        return self._wallets.get(participant_id)

    def get_balance(self, participant_id: str) -> float:
        return self._token.balance_of(participant_id)

    # ── Listings ─────────────────────────────────────────────────────────

    def create_listing(self, seller_id: str, amount: float,
                       price_per_credit: float = DEFAULT_CREDIT_PRICE) -> Dict[str, Any]:
        """Create a new credit listing."""
        if amount < MIN_LISTING_AMOUNT:
            return {"status": "error", "reason": f"amount below minimum {MIN_LISTING_AMOUNT}"}

        balance = self._token.balance_of(seller_id)
        if balance < amount:
            return {"status": "error", "reason": f"insufficient balance: {balance:.4f} < {amount:.4f}"}

        listing_id = f"LST_{self._next_listing_id:06d}"
        self._next_listing_id += 1

        listing = Listing(listing_id, seller_id, amount, price_per_credit)
        self._listings[listing_id] = listing

        # Track in wallet
        if seller_id in self._wallets:
            self._wallets[seller_id].add_pending_listing(listing_id)
            self._wallets[seller_id].record_activity("listing_created", {
                "listing_id": listing_id, "amount": amount,
                "price_per_credit": price_per_credit,
            })

        return {
            "status": "listed",
            "listing_id": listing_id,
            "amount": amount,
            "price_per_credit": price_per_credit,
        }

    def place_bid(self, listing_id: str, buyer_id: str,
                  bid_amount: float, bid_price: float) -> Dict[str, Any]:
        """Place a bid on an existing listing."""
        listing = self._listings.get(listing_id)
        if not listing:
            return {"status": "error", "reason": "listing not found"}
        if listing.status != "active":
            return {"status": "error", "reason": f"listing is {listing.status}"}
        if listing.is_expired:
            listing.status = "expired"
            return {"status": "error", "reason": "listing expired"}
        if bid_amount > listing.remaining:
            return {"status": "error", "reason": "bid exceeds available amount"}

        bid = {
            "buyer_id": buyer_id,
            "amount": bid_amount,
            "price": bid_price,
            "timestamp": time.time(),
            "status": "pending",
        }
        listing.bids.append(bid)

        if buyer_id in self._wallets:
            self._wallets[buyer_id].record_activity("bid_placed", {
                "listing_id": listing_id, "amount": bid_amount, "price": bid_price,
            })

        return {"status": "bid_placed", "listing_id": listing_id, "bid_index": len(listing.bids) - 1}

    def execute_purchase(self, listing_id: str, buyer_id: str,
                         amount: float) -> Dict[str, Any]:
        """
        Direct purchase from a listing at the listed price.
        Handles token transfer, fee deduction, and blockchain recording.
        """
        listing = self._listings.get(listing_id)
        if not listing:
            return {"status": "error", "reason": "listing not found"}
        if listing.status != "active":
            return {"status": "error", "reason": f"listing is {listing.status}"}
        if listing.is_expired:
            listing.status = "expired"
            return {"status": "error", "reason": "listing expired"}
        if amount > listing.remaining:
            return {"status": "error", "reason": "amount exceeds available"}

        seller_id = listing.seller_id
        price = listing.price_per_credit
        fee = round(amount * price * self._fee_rate, 4)
        total_value = round(amount * price, 4)

        # Execute token transfer
        try:
            self._token.transfer(seller_id, buyer_id, amount)
        except ValueError as e:
            return {"status": "error", "reason": str(e)}

        # Update listing
        listing.filled_amount += amount
        if listing.remaining <= 0.0001:
            listing.status = "sold"
            if seller_id in self._wallets:
                self._wallets[seller_id].remove_pending_listing(listing_id)

        # Generate transaction hash
        tx_data = {
            "type": "marketplace_trade",
            "seller_id": seller_id,
            "buyer_id": buyer_id,
            "credits_traded": round(amount, 4),
            "price_per_credit": price,
            "total_value": total_value,
            "fee": fee,
            "listing_id": listing_id,
        }
        tx_hash = hashlib.sha256(
            json.dumps(tx_data, sort_keys=True).encode()
        ).hexdigest()[:16]

        # Record on blockchain
        block = self._chain.add_block(tx_data)
        self._total_fees_collected += fee

        trade_record = {
            **tx_data,
            "tx_hash": tx_hash,
            "block_hash": block.hash,
            "timestamp": time.time(),
        }
        self._trade_history.append(trade_record)

        # Update wallets
        for pid, activity_type in [(seller_id, "sell"), (buyer_id, "buy")]:
            if pid in self._wallets:
                self._wallets[pid].record_activity(activity_type, {
                    "amount": amount, "price": price, "fee": fee if activity_type == "sell" else 0,
                    "counterparty": buyer_id if activity_type == "sell" else seller_id,
                    "tx_hash": tx_hash,
                })

        return {
            "status": "executed",
            "tx_hash": tx_hash,
            "block_hash": block.hash,
            "seller_id": seller_id,
            "buyer_id": buyer_id,
            "credits_traded": round(amount, 4),
            "price_per_credit": price,
            "total_value": total_value,
            "fee": fee,
            "seller_balance": self._token.balance_of(seller_id),
            "buyer_balance": self._token.balance_of(buyer_id),
        }

    def cancel_listing(self, listing_id: str, seller_id: str) -> Dict[str, Any]:
        """Cancel an active listing."""
        listing = self._listings.get(listing_id)
        if not listing:
            return {"status": "error", "reason": "listing not found"}
        if listing.seller_id != seller_id:
            return {"status": "error", "reason": "not the listing owner"}
        if listing.status != "active":
            return {"status": "error", "reason": f"listing is {listing.status}"}

        listing.status = "cancelled"
        if seller_id in self._wallets:
            self._wallets[seller_id].remove_pending_listing(listing_id)
            self._wallets[seller_id].record_activity("listing_cancelled", {
                "listing_id": listing_id,
            })
        return {"status": "cancelled", "listing_id": listing_id}

    # ── Queries ──────────────────────────────────────────────────────────

    def get_active_listings(self) -> List[Dict[str, Any]]:
        """Return all active listings."""
        active = []
        for lst in self._listings.values():
            if lst.is_expired:
                lst.status = "expired"
            if lst.status == "active":
                active.append(lst.to_dict())
        return sorted(active, key=lambda x: x["price_per_credit"])

    def get_trade_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self._trade_history[-limit:]

    def get_participant_trades(self, participant_id: str) -> List[Dict[str, Any]]:
        return [
            t for t in self._trade_history
            if t["seller_id"] == participant_id or t["buyer_id"] == participant_id
        ]

    def get_market_summary(self) -> Dict[str, Any]:
        active = self.get_active_listings()
        return {
            "total_listings": len(self._listings),
            "active_listings": len(active),
            "total_trades": len(self._trade_history),
            "total_volume": round(
                sum(t["credits_traded"] for t in self._trade_history), 4
            ),
            "total_value": round(
                sum(t["total_value"] for t in self._trade_history), 2
            ),
            "total_fees_collected": round(self._total_fees_collected, 4),
            "registered_participants": len(self._wallets),
            "avg_price": round(
                sum(t["price_per_credit"] for t in self._trade_history) / max(len(self._trade_history), 1), 2
            ),
        }
