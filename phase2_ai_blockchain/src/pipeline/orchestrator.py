"""
Pipeline Orchestrator — Step 2.7
==================================
Chains all Phase 2 components into a unified data pipeline:

  raw_reading → clean → normalize → estimate_co2e → detect_anomalies
             → calculate_credits → record_on_blockchain → mint_tokens
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from src.preprocessing.cleaner import DataCleaner
from src.preprocessing.normalizer import SensorNormalizer
from src.preprocessing.synchronizer import TimestampSynchronizer
from src.ai_engine.emission_model import EmissionEstimator, compute_co2e_ground_truth, extract_features
from src.ai_engine.anomaly_detector import AnomalyDetector
from src.ai_engine.training import generate_synthetic_data
from src.carbon_credits.calculator import CarbonCreditCalculator
from src.blockchain.ledger import Blockchain
from src.blockchain.token_manager import CarbonToken
from src.blockchain.smart_contracts import (
    EmissionRecordContract, CreditIssuanceContract, TradingContract,
)

logger = logging.getLogger("pipeline.orchestrator")


class Phase2Pipeline:
    """
    Unified pipeline orchestrating the full Phase 2 data flow.

    Components:
      - DataCleaner           (preprocessing)
      - SensorNormalizer       (preprocessing)
      - TimestampSynchronizer  (preprocessing)
      - EmissionEstimator      (AI — CO₂e prediction)
      - AnomalyDetector        (AI — anomaly classification)
      - CarbonCreditCalculator (credit computation)
      - Blockchain             (immutable ledger)
      - CarbonToken            (ERC-20 token)
      - Smart Contracts        (validation, issuance, trading)
    """

    def __init__(self):
        # Preprocessing
        self.cleaner = DataCleaner()
        self.normalizer = SensorNormalizer(mode="minmax")
        self.synchronizer = TimestampSynchronizer()

        # AI
        self.estimator = EmissionEstimator()
        self.detector = AnomalyDetector()

        # Carbon Credits
        self.calculator = CarbonCreditCalculator()

        # Blockchain
        self.blockchain = Blockchain()
        self.token = CarbonToken()

        # Smart Contracts
        self.emission_contract = EmissionRecordContract(self.blockchain)
        self.issuance_contract = CreditIssuanceContract(
            self.blockchain, self.token, self.calculator,
        )
        self.trading_contract = TradingContract(self.blockchain, self.token)

        # Stats
        self._processed = 0
        self._errors = 0
        self._trained = False

    def train_models(self, n_facilities: int = 50,
                     readings_per_facility: int = 200, seed: int = 42):
        """Train AI models on synthetic data."""
        import numpy as np

        readings, X, y = generate_synthetic_data(
            n_facilities, readings_per_facility, seed,
        )

        # Train estimator
        self.estimator.train(X, y)

        # Train anomaly detector
        self.detector.fit(X)

        self._trained = True
        logger.info("Pipeline models trained on %d samples", len(readings))

    def process_reading(self, raw_reading: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a single reading through the full pipeline.

        Returns enriched result dict or None if rejected.
        """
        if not self._trained:
            raise RuntimeError("Models not trained — call train_models() first")

        start = time.perf_counter()

        # Step 1: Clean
        cleaned = self.cleaner.clean_reading(raw_reading)
        if cleaned is None:
            self._errors += 1
            return None

        # Step 2: Synchronize timestamp
        synced = self.synchronizer.synchronize_reading(cleaned)

        # Step 3: AI — Emission estimation
        emission = self.estimator.predict(synced)
        synced["co2e_emission"] = emission["co2e_emission"]
        synced["confidence_score"] = emission["confidence_score"]
        synced["model_version"] = emission["model_version"]

        # Step 4: AI — Anomaly detection
        anomaly = self.detector.detect(synced)
        synced["anomaly_flag"] = anomaly["anomaly_flag"]
        synced["anomaly_type"] = anomaly["anomaly_type"]
        synced["severity_score"] = anomaly["severity_score"]

        # Step 5: Record on blockchain (skip anomalies)
        record_result = self.emission_contract.record(synced)
        synced["blockchain_status"] = record_result["status"]
        if record_result.get("block_hash"):
            synced["block_hash"] = record_result["block_hash"]

        # Step 6: Calculate credits and mint tokens
        if not synced["anomaly_flag"] and "facility_type" in synced:
            issuance_result = self.issuance_contract.process(synced)
            synced["credits"] = issuance_result["credits"]
            synced["token_minted"] = issuance_result["token_minted"]
        else:
            synced["credits"] = None
            synced["token_minted"] = False

        synced["processing_time_ms"] = round(
            (time.perf_counter() - start) * 1000, 2,
        )
        self._processed += 1
        return synced

    def process_batch(self, readings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a batch of readings through the pipeline."""
        results = []
        for r in readings:
            result = self.process_reading(r)
            if result is not None:
                results.append(result)
        return results

    def get_summary(self) -> Dict[str, Any]:
        """Return pipeline summary statistics."""
        return {
            "processed": self._processed,
            "errors": self._errors,
            "blockchain_length": self.blockchain.length,
            "blockchain_valid": self.blockchain.is_valid(),
            "token_supply": self.token.total_supply,
            "token_balances": self.token.get_all_balances(),
            "credit_summary": self.calculator.get_summary(),
            "cleaner_stats": self.cleaner.get_stats(),
        }
