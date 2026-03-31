"""
PoA Blockchain Ledger Simulation — Step 2.5
=============================================
Replaces simplistic append-only hashing with a
Proof-of-Authority (PoA) consensus mechanism containing:
  - Memory Pool for unconfirmed transactions
  - Authorized Validator nodes
  - Cryptographic Block signing
"""

from __future__ import annotations

import hashlib
import json
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("blockchain.ledger")

@dataclass
class Transaction:
    sender: str
    receiver: str
    amount: float
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    tx_hash: str = field(init=False)

    def __post_init__(self):
        content = json.dumps({
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount,
            "data": self.data,
            "timestamp": self.timestamp
        }, sort_keys=True)
        self.tx_hash = hashlib.sha256(content.encode()).hexdigest()

    def to_dict(self):
        return {
            "tx_hash": self.tx_hash,
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount,
            "data": self.data,
            "timestamp": self.timestamp
        }


@dataclass
class Block:
    index: int
    timestamp: float
    transactions: List[Dict[str, Any]]
    previous_hash: str
    validator: str  # PoA signer
    hash: str = ""

    def compute_hash(self) -> str:
        content = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "validator": self.validator
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()


class ValidatorNode:
    """Represents an authorized signer in the PoA network."""
    def __init__(self, node_id: str):
        self.node_id = node_id

    def sign_block(self, block: Block) -> Block:
        block.validator = self.node_id
        block.hash = block.compute_hash()
        return block


class PoABlockchain:
    """
    Robust blockchain simulation using Proof of Authority.
    Separates transactions from blocks, using a tx_pool.
    """

    def __init__(self):
        self._chain: List[Block] = []
        self._tx_pool: List[Transaction] = []
        self._validators: List[ValidatorNode] = [
            ValidatorNode("Regulator_Authority_1"),
            ValidatorNode("Auditor_Authority_2"),
            ValidatorNode("Gov_Authority_3")
        ]
        self._validator_index = 0
        self._create_genesis_block()

    def _create_genesis_block(self):
        """Initializes blockchain state."""
        genesis = Block(
            index=0,
            timestamp=time.time(),
            transactions=[{"msg": "Genesis Block - Dynamic Tokenisation Network"}],
            previous_hash="0" * 64,
            validator="System"
        )
        genesis.hash = genesis.compute_hash()
        self._chain.append(genesis)

    def add_transaction(self, sender: str, receiver: str, amount: float, data: Dict[str, Any]) -> str:
        """Puts a transaction into the memory pool."""
        tx = Transaction(sender, receiver, amount, data)
        self._tx_pool.append(tx)
        logger.info(f"Transaction queued in pool: {tx.tx_hash[:8]}")
        return tx.tx_hash

    def get_pool_size(self):
        return len(self._tx_pool)

    def mine_pending_transactions(self) -> Optional[Block]:
        """
        PoA Consensus: Selected validator pulls transactions from pool,
        signs them into a block, and appends to ledger.
        """
        if not self._tx_pool:
            return None

        # PoA round-robin validator selection
        validator = self._validators[self._validator_index]
        self._validator_index = (self._validator_index + 1) % len(self._validators)

        # Take up to 100 txs per block
        txs_to_mine = [tx.to_dict() for tx in self._tx_pool[:100]]
        
        prev_block = self._chain[-1]
        new_block = Block(
            index=prev_block.index + 1,
            timestamp=time.time(),
            transactions=txs_to_mine,
            previous_hash=prev_block.hash,
            validator=validator.node_id
        )
        
        # Sign block
        new_block = validator.sign_block(new_block)
        
        self._chain.append(new_block)
        self._tx_pool = self._tx_pool[100:]  # Clear mined txs
        
        logger.info(f"Block #{new_block.index} minted by {validator.node_id} with {len(txs_to_mine)} TXs.")
        return new_block

    def is_valid(self) -> bool:
        """Verify structural integrity of the entire chain."""
        for i in range(1, len(self._chain)):
            current = self._chain[i]
            previous = self._chain[i - 1]
            if current.hash != current.compute_hash(): return False
            if current.previous_hash != previous.hash: return False
        return True

    def get_balance(self, address: str) -> float:
        """Calculates token balance directly from immutable ledger state."""
        balance = 0.0
        for block in self._chain:
            for tx in block.transactions:
                if "sender" in tx and "receiver" in tx:
                    if tx["sender"] == address:
                        balance -= tx["amount"]
                    if tx["receiver"] == address:
                        balance += tx["amount"]
        return balance
