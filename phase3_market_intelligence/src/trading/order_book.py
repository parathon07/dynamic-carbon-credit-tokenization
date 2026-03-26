"""
Advanced Order Book — Step 3.3
================================
Price-time priority order matching engine for carbon credit trading.
Supports limit orders, market orders, and auto-execution.
Records all trades on the blockchain.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import numpy as np

from src.config import MAX_ORDER_SIZE, ORDER_EXPIRY_SECONDS, PRICE_TICK_SIZE


class OrderEntry:
    """A single order in the order book."""

    def __init__(self, order_id: int, trader: str, side: str,
                 amount: float, price: float, order_type: str = "limit"):
        self.order_id = order_id
        self.trader = trader
        self.side = side               # "buy" or "sell"
        self.amount = amount
        self.price = price             # 0 = market order
        self.order_type = order_type   # "limit" or "market"
        self.timestamp = time.time()
        self.filled = 0.0
        self.status = "open"           # open, filled, partial, cancelled, expired

    @property
    def remaining(self) -> float:
        return self.amount - self.filled

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.timestamp) > ORDER_EXPIRY_SECONDS and self.status == "open"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "trader": self.trader,
            "side": self.side,
            "amount": round(self.amount, 4),
            "price": round(self.price, 2),
            "filled": round(self.filled, 4),
            "remaining": round(self.remaining, 4),
            "order_type": self.order_type,
            "status": self.status,
            "timestamp": self.timestamp,
        }


class AdvancedOrderBook:
    """
    Price-time priority order matching engine.

    Features:
      - Limit orders: execute at specified price or better
      - Market orders: execute at best available price
      - Price-time priority matching (best price first, then earliest)
      - Auto-execution on match
      - Blockchain-recorded settlements
      - Order expiry
    """

    def __init__(self, token_manager, blockchain, pricing_engine=None):
        """
        Args:
            token_manager: CarbonToken for balance/transfer.
            blockchain: Blockchain for recording trades.
            pricing_engine: Optional DynamicPricingEngine for price tracking.
        """
        self._token = token_manager
        self._chain = blockchain
        self._pricing = pricing_engine

        self._buy_orders: List[OrderEntry] = []     # sorted: highest price first, then earliest
        self._sell_orders: List[OrderEntry] = []    # sorted: lowest price first, then earliest
        self._next_id = 1
        self._trades: List[Dict[str, Any]] = []
        self._all_orders: Dict[int, OrderEntry] = {}

    def place_order(self, trader: str, side: str, amount: float,
                    price: float = 0.0, order_type: str = "limit") -> Dict[str, Any]:
        """
        Place a buy or sell order.

        Args:
            trader: Participant ID.
            side: 'buy' or 'sell'.
            amount: CCT amount.
            price: Price per CCT (0 for market orders).
            order_type: 'limit' or 'market'.
        """
        # Validation
        if side not in ("buy", "sell"):
            return {"status": "error", "reason": "side must be 'buy' or 'sell'"}
        if amount <= 0 or amount > MAX_ORDER_SIZE:
            return {"status": "error", "reason": f"amount must be 0 < x <= {MAX_ORDER_SIZE}"}
        if order_type == "limit" and price <= 0:
            return {"status": "error", "reason": "limit orders require positive price"}
        if order_type == "market":
            price = 0.0

        # Verify seller balance
        if side == "sell" and self._token.balance_of(trader) < amount:
            return {"status": "error", "reason": "insufficient balance"}

        # Clean expired orders
        self._clean_expired()

        order = OrderEntry(self._next_id, trader, side, amount, price, order_type)
        self._next_id += 1
        self._all_orders[order.order_id] = order

        # Attempt matching
        matches = self._match(order)

        # Add remainder to book
        if order.remaining > 0.001:
            if order_type == "limit":
                if side == "buy":
                    self._buy_orders.append(order)
                    self._buy_orders.sort(key=lambda o: (-o.price, o.timestamp))
                else:
                    self._sell_orders.append(order)
                    self._sell_orders.sort(key=lambda o: (o.price, o.timestamp))
                if order.filled > 0:
                    order.status = "partial"
            else:
                # Market orders don't rest in the book
                if order.filled > 0:
                    order.status = "partial"
                else:
                    order.status = "cancelled"
        else:
            order.status = "filled"

        return {
            "status": "placed" if order.status in ("open", "partial") else order.status,
            "order_id": order.order_id,
            "filled": round(order.filled, 4),
            "remaining": round(order.remaining, 4),
            "matches": matches,
        }

    def cancel_order(self, order_id: int, trader: str) -> Dict[str, Any]:
        """Cancel an open order."""
        order = self._all_orders.get(order_id)
        if not order:
            return {"status": "error", "reason": "order not found"}
        if order.trader != trader:
            return {"status": "error", "reason": "not order owner"}
        if order.status not in ("open", "partial"):
            return {"status": "error", "reason": f"order is {order.status}"}

        order.status = "cancelled"
        if order.side == "buy":
            self._buy_orders = [o for o in self._buy_orders if o.order_id != order_id]
        else:
            self._sell_orders = [o for o in self._sell_orders if o.order_id != order_id]

        return {"status": "cancelled", "order_id": order_id}

    def _match(self, order: OrderEntry) -> List[Dict[str, Any]]:
        """Match order against the opposite side using price-time priority."""
        matches = []
        opposite = self._sell_orders if order.side == "buy" else self._buy_orders

        i = 0
        while i < len(opposite) and order.remaining > 0.001:
            counter = opposite[i]

            # Skip expired
            if counter.is_expired:
                counter.status = "expired"
                opposite.pop(i)
                continue

            # Price compatibility
            if order.order_type == "limit":
                if order.side == "buy" and counter.price > order.price:
                    break  # sell price too high
                if order.side == "sell" and counter.price < order.price:
                    break  # buy price too low
            # Market orders match any price

            # Execute fill
            fill_amount = min(order.remaining, counter.remaining)
            exec_price = counter.price if counter.price > 0 else order.price

            if exec_price <= 0:
                i += 1
                continue

            try:
                seller = order.trader if order.side == "sell" else counter.trader
                buyer = order.trader if order.side == "buy" else counter.trader
                self._token.transfer(seller, buyer, fill_amount)

                order.filled += fill_amount
                counter.filled += fill_amount

                # Record trade
                trade = {
                    "trade_id": len(self._trades) + 1,
                    "buyer": buyer,
                    "seller": seller,
                    "amount": round(fill_amount, 4),
                    "price": round(exec_price, 2),
                    "total_value": round(fill_amount * exec_price, 2),
                    "buy_order_id": order.order_id if order.side == "buy" else counter.order_id,
                    "sell_order_id": counter.order_id if order.side == "buy" else order.order_id,
                    "timestamp": time.time(),
                }

                # Record on blockchain
                block = self._chain.add_block({
                    "type": "order_book_trade",
                    **trade,
                })
                trade["block_hash"] = block.hash
                self._trades.append(trade)
                matches.append(trade)

                # Update pricing engine
                if self._pricing:
                    self._pricing.record_trade(exec_price, fill_amount)

                # Remove filled counter orders
                if counter.remaining <= 0.001:
                    counter.status = "filled"
                    opposite.pop(i)
                else:
                    counter.status = "partial"
                    i += 1

            except ValueError:
                i += 1

        return matches

    def _clean_expired(self):
        """Remove expired orders from both sides."""
        self._buy_orders = [o for o in self._buy_orders if not o.is_expired]
        self._sell_orders = [o for o in self._sell_orders if not o.is_expired]

    # ── Queries ──────────────────────────────────────────────────────────

    def get_order_book(self) -> Dict[str, List[Dict]]:
        self._clean_expired()
        return {
            "buy_orders": [o.to_dict() for o in self._buy_orders if o.status in ("open", "partial")],
            "sell_orders": [o.to_dict() for o in self._sell_orders if o.status in ("open", "partial")],
        }

    def get_trade_history(self, limit: int = 100) -> List[Dict]:
        return self._trades[-limit:]

    def get_best_bid(self) -> Optional[float]:
        """Best (highest) buy price."""
        active = [o for o in self._buy_orders if o.status in ("open", "partial")]
        return active[0].price if active else None

    def get_best_ask(self) -> Optional[float]:
        """Best (lowest) sell price."""
        active = [o for o in self._sell_orders if o.status in ("open", "partial")]
        return active[0].price if active else None

    def get_spread(self) -> Optional[float]:
        """Bid-ask spread."""
        bid = self.get_best_bid()
        ask = self.get_best_ask()
        if bid is not None and ask is not None:
            return round(ask - bid, 2)
        return None

    def get_summary(self) -> Dict[str, Any]:
        book = self.get_order_book()
        return {
            "total_orders": len(self._all_orders),
            "open_buy_orders": len(book["buy_orders"]),
            "open_sell_orders": len(book["sell_orders"]),
            "total_trades": len(self._trades),
            "total_volume": round(sum(t["amount"] for t in self._trades), 4),
            "best_bid": self.get_best_bid(),
            "best_ask": self.get_best_ask(),
            "spread": self.get_spread(),
        }
