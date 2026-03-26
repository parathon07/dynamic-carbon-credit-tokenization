"""
Smart Contracts — Step 2.6
============================
Automated validation, credit issuance, and trading contracts.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.blockchain.ledger import Blockchain
from src.blockchain.token_manager import CarbonToken
from src.carbon_credits.calculator import CarbonCreditCalculator

logger = logging.getLogger("blockchain.smart_contracts")


class EmissionRecordContract:
    """
    Smart contract for recording verified emissions on-chain.

    Validates emission data before recording:
      - facility_id must be present
      - co2e_emission must be ≥ 0
      - anomaly_flag must be False (anomalous data excluded)
    """

    def __init__(self, blockchain: Blockchain):
        self._chain = blockchain
        self._records = 0

    def record(self, emission_data: Dict[str, Any]) -> Optional[Dict]:
        """Validate and record emission on blockchain."""
        # Validation rules
        if not emission_data.get("facility_id"):
            return {"status": "rejected", "reason": "missing facility_id"}

        co2e = emission_data.get("co2e_emission", -1)
        if co2e < 0:
            return {"status": "rejected", "reason": "negative co2e_emission"}

        if emission_data.get("anomaly_flag", False):
            return {"status": "rejected", "reason": "anomalous data excluded"}

        # Record on chain
        block_data = {
            "type": "emission_record",
            "facility_id": emission_data["facility_id"],
            "timestamp_utc": emission_data.get("timestamp_utc"),
            "co2e_emission": co2e,
            "confidence_score": emission_data.get("confidence_score", 0),
        }
        block = self._chain.add_block(block_data)
        self._records += 1

        return {
            "status": "recorded",
            "block_index": block.index,
            "block_hash": block.hash,
        }

    @property
    def total_records(self) -> int:
        return self._records


class CreditIssuanceContract:
    """
    Smart contract that auto-mints CCT tokens when credits are earned.
    """

    def __init__(self, blockchain: Blockchain, token: CarbonToken,
                 calculator: CarbonCreditCalculator):
        self._chain = blockchain
        self._token = token
        self._calculator = calculator
        self._issued = 0

    def process(self, reading: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate credits and mint tokens if earned.

        Args:
            reading: Must have facility_id, facility_type, co2e_emission.
        """
        credit_result = self._calculator.calculate(reading)

        result = {
            "credits": credit_result,
            "token_minted": False,
            "block_hash": None,
        }

        if credit_result["credits_earned"] > 0:
            # Create unique emission hash
            emission_hash = CarbonToken.compute_emission_hash(reading)

            try:
                # Mint tokens
                self._token.mint(
                    to=reading["facility_id"],
                    amount=credit_result["credits_earned"],
                    emission_hash=emission_hash,
                )

                # Record on blockchain
                block_data = {
                    "type": "credit_issuance",
                    "facility_id": reading["facility_id"],
                    "credits_earned": credit_result["credits_earned"],
                    "emission_hash": emission_hash,
                }
                block = self._chain.add_block(block_data)

                result["token_minted"] = True
                result["block_hash"] = block.hash
                self._issued += 1
            except ValueError as e:
                result["error"] = str(e)

        return result

    @property
    def total_issued(self) -> int:
        return self._issued


class TradingContract:
    """
    Smart contract for peer-to-peer carbon credit trading.
    Records all trades on the blockchain.
    """

    def __init__(self, blockchain: Blockchain, token: CarbonToken):
        self._chain = blockchain
        self._token = token
        self._trades = 0

    def execute_trade(self, seller: str, buyer: str, amount: float,
                      price_per_credit: float = 0.0) -> Dict[str, Any]:
        """
        Execute a P2P trade: transfer CCT from seller to buyer.
        """
        if amount <= 0:
            return {"status": "rejected", "reason": "amount must be positive"}

        seller_balance = self._token.balance_of(seller)
        if seller_balance < amount:
            return {
                "status": "rejected",
                "reason": f"insufficient balance: {seller} has {seller_balance}",
            }

        try:
            self._token.transfer(seller, buyer, amount)

            block_data = {
                "type": "credit_trade",
                "seller": seller, "buyer": buyer,
                "amount": round(amount, 4),
                "price_per_credit": price_per_credit,
                "total_value": round(amount * price_per_credit, 2),
            }
            block = self._chain.add_block(block_data)
            self._trades += 1

            return {
                "status": "executed",
                "block_hash": block.hash,
                "seller_balance": self._token.balance_of(seller),
                "buyer_balance": self._token.balance_of(buyer),
            }
        except ValueError as e:
            return {"status": "rejected", "reason": str(e)}

    @property
    def total_trades(self) -> int:
        return self._trades
