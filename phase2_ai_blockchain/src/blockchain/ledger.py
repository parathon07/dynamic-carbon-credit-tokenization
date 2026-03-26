"""
Blockchain Ledger — Step 2.5
==============================
SHA-256 hash-chained immutable ledger with proof-of-work.
Fully self-contained — no external blockchain node required.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.config import BLOCKCHAIN_DIFFICULTY


@dataclass
class Block:
    """Single block in the blockchain."""
    index: int
    timestamp: float
    data: Dict[str, Any]
    previous_hash: str
    nonce: int = 0
    hash: str = ""

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of this block's contents."""
        content = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()


class Blockchain:
    """
    Immutable append-only SHA-256 hash chain with proof-of-work.

    Features:
      - Genesis block auto-created
      - Configurable mining difficulty
      - Full chain validation
      - Transaction query by facility_id
    """

    def __init__(self, difficulty: int = BLOCKCHAIN_DIFFICULTY):
        self._chain: List[Block] = []
        self._difficulty = difficulty
        self._create_genesis_block()

    def _create_genesis_block(self):
        genesis = Block(
            index=0, timestamp=time.time(),
            data={"type": "genesis", "message": "Phase 2 Carbon Credit Blockchain"},
            previous_hash="0" * 64,
        )
        genesis.hash = self._mine_block(genesis)
        self._chain.append(genesis)

    def _mine_block(self, block: Block) -> str:
        """Proof-of-work: find nonce such that hash starts with `difficulty` zeros."""
        prefix = "0" * self._difficulty
        while True:
            hash_val = block.compute_hash()
            if hash_val.startswith(prefix):
                return hash_val
            block.nonce += 1

    def add_block(self, data: Dict[str, Any]) -> Block:
        """Mine and append a new block with the given data."""
        prev = self._chain[-1]
        new_block = Block(
            index=prev.index + 1,
            timestamp=time.time(),
            data=data,
            previous_hash=prev.hash,
        )
        new_block.hash = self._mine_block(new_block)
        self._chain.append(new_block)
        return new_block

    def is_valid(self) -> bool:
        """Validate the entire chain integrity."""
        prefix = "0" * self._difficulty
        for i in range(1, len(self._chain)):
            current = self._chain[i]
            previous = self._chain[i - 1]

            # Verify hash
            if current.hash != current.compute_hash():
                return False
            # Verify chain link
            if current.previous_hash != previous.hash:
                return False
            # Verify proof-of-work
            if not current.hash.startswith(prefix):
                return False
        return True

    def get_chain(self) -> List[Dict[str, Any]]:
        """Return chain as list of dicts."""
        return [
            {
                "index": b.index, "timestamp": b.timestamp,
                "data": b.data, "hash": b.hash,
                "previous_hash": b.previous_hash, "nonce": b.nonce,
            }
            for b in self._chain
        ]

    def get_block(self, index: int) -> Optional[Block]:
        """Get block by index."""
        if 0 <= index < len(self._chain):
            return self._chain[index]
        return None

    @property
    def length(self) -> int:
        return len(self._chain)

    @property
    def latest_block(self) -> Block:
        return self._chain[-1]

    def query_by_facility(self, facility_id: str) -> List[Dict]:
        """Return all blocks containing data for a specific facility."""
        return [
            {"index": b.index, "data": b.data, "hash": b.hash}
            for b in self._chain
            if b.data.get("facility_id") == facility_id
        ]
