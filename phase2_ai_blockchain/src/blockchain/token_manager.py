"""
Token Manager — Step 2.5/2.6
==============================
ERC-20 style carbon credit token: mint, transfer, burn, balance.
Prevents double-counting via emission hash tracking.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Set

from src.config import TOKEN_NAME, TOKEN_SYMBOL, TOKEN_DECIMALS

logger = logging.getLogger("blockchain.token_manager")


class CarbonToken:
    """
    ERC-20 style token for carbon credits.

    Properties:
      - Name: CarbonCreditToken
      - Symbol: CCT
      - Decimals: 4
      - Total supply tracked

    Anti-fraud:
      - Unique emission_hash per minting event
      - Prevents double-counting of the same emission reading
    """

    def __init__(self):
        self.name = TOKEN_NAME
        self.symbol = TOKEN_SYMBOL
        self.decimals = TOKEN_DECIMALS

        self._balances: Dict[str, float] = {}       # address → balance
        self._allowances: Dict[str, Dict[str, float]] = {}  # owner → {spender → amount}
        self._total_supply: float = 0.0
        self._minted_hashes: Set[str] = set()       # prevent double minting
        self._tx_log: List[Dict[str, Any]] = []     # transaction history

    # ── Core operations ──────────────────────────────────────────────────

    def mint(self, to: str, amount: float, emission_hash: str) -> Dict[str, Any]:
        """
        Mint new tokens to an address.

        Args:
            to: recipient address (facility_id)
            amount: tokens to mint
            emission_hash: unique hash of the emission reading

        Raises:
            ValueError: if emission_hash already used (double-counting)
        """
        if emission_hash in self._minted_hashes:
            raise ValueError(f"Double-counting prevented: {emission_hash} already minted")

        if amount <= 0:
            raise ValueError(f"Mint amount must be positive, got {amount}")

        self._balances[to] = self._balances.get(to, 0.0) + amount
        self._total_supply += amount
        self._minted_hashes.add(emission_hash)

        tx = {"type": "mint", "to": to, "amount": round(amount, self.decimals),
              "emission_hash": emission_hash}
        self._tx_log.append(tx)
        logger.debug("Minted %.4f %s to %s", amount, self.symbol, to)
        return tx

    def transfer(self, from_addr: str, to_addr: str, amount: float) -> Dict[str, Any]:
        """Transfer tokens between addresses."""
        if amount <= 0:
            raise ValueError("Transfer amount must be positive")
        if self._balances.get(from_addr, 0.0) < amount:
            raise ValueError(
                f"Insufficient balance: {from_addr} has "
                f"{self._balances.get(from_addr, 0)}, needs {amount}"
            )

        self._balances[from_addr] -= amount
        self._balances[to_addr] = self._balances.get(to_addr, 0.0) + amount

        tx = {"type": "transfer", "from": from_addr, "to": to_addr,
              "amount": round(amount, self.decimals)}
        self._tx_log.append(tx)
        return tx

    def burn(self, from_addr: str, amount: float) -> Dict[str, Any]:
        """Burn (retire) tokens from an address."""
        if amount <= 0:
            raise ValueError("Burn amount must be positive")
        if self._balances.get(from_addr, 0.0) < amount:
            raise ValueError(f"Insufficient balance to burn")

        self._balances[from_addr] -= amount
        self._total_supply -= amount

        tx = {"type": "burn", "from": from_addr, "amount": round(amount, self.decimals)}
        self._tx_log.append(tx)
        return tx

    # ── Allowance (ERC-20 approve/transferFrom) ──────────────────────────

    def approve(self, owner: str, spender: str, amount: float):
        """Approve spender to transfer up to `amount` from owner."""
        if owner not in self._allowances:
            self._allowances[owner] = {}
        self._allowances[owner][spender] = amount

    def allowance(self, owner: str, spender: str) -> float:
        return self._allowances.get(owner, {}).get(spender, 0.0)

    def transfer_from(self, spender: str, from_addr: str, to_addr: str, amount: float) -> Dict:
        """Transfer on behalf of owner using allowance."""
        allowed = self.allowance(from_addr, spender)
        if allowed < amount:
            raise ValueError(f"Allowance exceeded: {allowed} < {amount}")
        self._allowances[from_addr][spender] -= amount
        return self.transfer(from_addr, to_addr, amount)

    # ── Queries ──────────────────────────────────────────────────────────

    def balance_of(self, address: str) -> float:
        return round(self._balances.get(address, 0.0), self.decimals)

    @property
    def total_supply(self) -> float:
        return round(self._total_supply, self.decimals)

    def get_tx_log(self) -> List[Dict]:
        return list(self._tx_log)

    def get_all_balances(self) -> Dict[str, float]:
        return {k: round(v, self.decimals) for k, v in self._balances.items() if v > 0}

    @staticmethod
    def compute_emission_hash(reading: Dict[str, Any]) -> str:
        """Compute unique hash for an emission reading."""
        content = json.dumps({
            "facility_id": reading.get("facility_id"),
            "timestamp_utc": reading.get("timestamp_utc"),
            "co2e_emission": reading.get("co2e_emission"),
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
