"""
P2P Trading Engine — Step 2.5
===============================
Order book for carbon credit trading with market/limit orders.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from src.blockchain.token_manager import CarbonToken
from src.blockchain.ledger import Blockchain


class Order:
    """A trading order."""

    def __init__(self, order_id: int, trader: str, side: str,
                 amount: float, price: float):
        self.order_id = order_id
        self.trader = trader
        self.side = side           # "buy" or "sell"
        self.amount = amount       # CCT amount
        self.price = price         # price per CCT
        self.timestamp = time.time()
        self.filled = 0.0
        self.status = "open"       # "open", "filled", "cancelled"

    @property
    def remaining(self) -> float:
        return self.amount - self.filled

    def to_dict(self) -> Dict:
        return {
            "order_id": self.order_id, "trader": self.trader,
            "side": self.side, "amount": self.amount,
            "price": self.price, "filled": self.filled,
            "status": self.status,
        }


class TradingEngine:
    """
    Order book engine for carbon credit P2P trading.

    Supports:
      - Limit orders (specific price)
      - Market orders (best available price)
      - Order matching and execution
    """

    def __init__(self, token: CarbonToken, blockchain: Blockchain):
        self._token = token
        self._chain = blockchain
        self._buy_orders: List[Order] = []    # sorted by price desc
        self._sell_orders: List[Order] = []   # sorted by price asc
        self._next_id = 1
        self._trades: List[Dict] = []

    def place_order(self, trader: str, side: str, amount: float,
                    price: float = 0.0) -> Dict[str, Any]:
        """Place a buy or sell order."""
        if side not in ("buy", "sell"):
            return {"status": "error", "reason": "side must be 'buy' or 'sell'"}
        if amount <= 0:
            return {"status": "error", "reason": "amount must be positive"}

        # Verify seller has enough tokens
        if side == "sell" and self._token.balance_of(trader) < amount:
            return {"status": "error", "reason": "insufficient balance"}

        order = Order(self._next_id, trader, side, amount, price)
        self._next_id += 1

        # Try to match
        matches = self._match_order(order)

        if order.remaining > 0:
            if side == "buy":
                self._buy_orders.append(order)
                self._buy_orders.sort(key=lambda o: -o.price)
            else:
                self._sell_orders.append(order)
                self._sell_orders.sort(key=lambda o: o.price)

        return {
            "status": "placed",
            "order_id": order.order_id,
            "filled": round(order.filled, 4),
            "remaining": round(order.remaining, 4),
            "matches": matches,
        }

    def _match_order(self, order: Order) -> List[Dict]:
        """Match an order against the opposite side of the book."""
        matches = []
        opposite = self._sell_orders if order.side == "buy" else self._buy_orders

        i = 0
        while i < len(opposite) and order.remaining > 0:
            counter = opposite[i]

            # Price compatibility check
            if order.side == "buy" and order.price > 0 and counter.price > order.price:
                break
            if order.side == "sell" and order.price > 0 and counter.price < order.price:
                break

            # Execute match
            fill_amount = min(order.remaining, counter.remaining)
            exec_price = counter.price if counter.price > 0 else order.price

            try:
                if order.side == "buy":
                    self._token.transfer(counter.trader, order.trader, fill_amount)
                else:
                    self._token.transfer(order.trader, counter.trader, fill_amount)

                order.filled += fill_amount
                counter.filled += fill_amount

                if counter.remaining <= 0:
                    counter.status = "filled"
                    opposite.pop(i)
                else:
                    i += 1

                trade = {
                    "buyer": order.trader if order.side == "buy" else counter.trader,
                    "seller": counter.trader if order.side == "buy" else order.trader,
                    "amount": round(fill_amount, 4),
                    "price": round(exec_price, 2),
                }
                self._trades.append(trade)
                matches.append(trade)

            except ValueError:
                i += 1

        if order.remaining <= 0:
            order.status = "filled"

        return matches

    def get_order_book(self) -> Dict[str, List[Dict]]:
        """Return current order book snapshot."""
        return {
            "buy_orders": [o.to_dict() for o in self._buy_orders if o.status == "open"],
            "sell_orders": [o.to_dict() for o in self._sell_orders if o.status == "open"],
        }

    def get_trade_history(self) -> List[Dict]:
        return list(self._trades)
