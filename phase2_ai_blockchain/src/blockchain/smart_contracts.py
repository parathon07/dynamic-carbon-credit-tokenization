"""
Token Smart Contract — Step 2.6
==================================
Simulates Solidity-like ERC-20 state logic.
Handles state modifiers for Minting, Burning, and Transferring
Dynamic Carbon Credits, strictly governed by DCMM inputs.
"""

from __future__ import annotations
import logging
from typing import Dict, Any

from src.blockchain.ledger import PoABlockchain

logger = logging.getLogger("blockchain.smart_contracts")

class CarbonERC20Contract:
    """
    Virtual Smart Contract deployed on top of the PoA Blockchain.
    Maintains authoritative state mappings outside of raw block search,
    simulating how Ethereum EVM state works.
    """
    
    def __init__(self, ledger: PoABlockchain, owner_address: str = "0xSystem_Regulator"):
        self._ledger = ledger
        self.owner = owner_address
        self._balances: Dict[str, float] = {}
        self.total_supply = 0.0
        
        # Pre-allocate if necessary or leave at 0
        self._balances[self.owner] = 0.0

    def _sync_state(self, address: str):
        """Helper to ensure address exists in mapping."""
        if address not in self._balances:
            self._balances[address] = 0.0

    def mint(self, facility_addr: str, amount: float, dcmm_validation: Dict[str, Any]) -> str:
        """
        Only System Regulator can mint.
        Mints tokens to a facility directly tied to the DCMM proof.
        """
        assert amount > 0, "Cannot mint 0 or negative tokens."
        # Require proof of emissions vs baseline based on DCMM (alpha, beta, gamma)
        if "ef_t" not in dcmm_validation:
            logger.error(f"Mint rejected for {facility_addr}: Invalid DCMM Proof")
            return "REJECTED"

        self._sync_state(facility_addr)
        self._balances[facility_addr] += amount
        self.total_supply += amount
        
        # Trigger blockchain transaction for immutability
        tx_hash = self._ledger.add_transaction(
            sender=self.owner, 
            receiver=facility_addr, 
            amount=amount, 
            data={"action": "MINT_ERC20", "proof": dcmm_validation}
        )
        logger.info(f"Minted {amount:.2f} tokens to {facility_addr}.")
        return tx_hash

    def transfer(self, sender: str, receiver: str, amount: float) -> str:
        """Standard ERC-20 Transfer."""
        self._sync_state(sender)
        self._sync_state(receiver)
        
        if self._balances[sender] < amount:
            logger.error(f"Transfer failed: {sender} has insufficient balance.")
            return "INSUFFICIENT_FUNDS"
            
        self._balances[sender] -= amount
        self._balances[receiver] += amount
        
        tx_hash = self._ledger.add_transaction(
            sender=sender,
            receiver=receiver,
            amount=amount,
            data={"action": "TRANSFER_ERC20"}
        )
        logger.info(f"Transferred {amount:.2f} from {sender} to {receiver}.")
        return tx_hash

    def burn(self, facility_addr: str, amount: float) -> str:
        """
        Burns tokens (e.g., when offsets are retired up against excess emissions).
        """
        self._sync_state(facility_addr)
        if self._balances[facility_addr] < amount:
            logger.error(f"Burn failed: {facility_addr} has insufficient balance.")
            return "INSUFFICIENT_FUNDS"

        self._balances[facility_addr] -= amount
        self.total_supply -= amount
        
        tx_hash = self._ledger.add_transaction(
            sender=facility_addr,
            receiver="0x0000000000000000000000000000000000000000", # Burn address
            amount=amount,
            data={"action": "BURN_ERC20"}
        )
        logger.info(f"Burned {amount:.2f} tokens from {facility_addr}.")
        return tx_hash

    def balance_of(self, address: str) -> float:
        """Fast state lookup for balances."""
        return self._balances.get(address, 0.0)
