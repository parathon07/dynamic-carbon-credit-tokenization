"""
metrics.py
==========
Dynamic Metrics Extraction Module for the Carbon Credit Tokenisation System.
This module extracts real-time, non-hardcoded metrics directly from the production AI/Blockchain pipeline.

For Demo Presentation:
Each metric group contains a docstring explaining what it represents, how it is calculated,
and why it is important, ready to be explained during a technical interview.
"""
import json
import time
import os
import sys
from typing import Dict, Any

# Ensure backend path is in sys.path so we can import 'app' standalone
DEMO_DIR = os.path.dirname(os.path.abspath(__file__))
P5_DIR = os.path.join(DEMO_DIR, "phase5_deployment", "backend")
if P5_DIR not in sys.path:
    sys.path.insert(0, P5_DIR)

from app.services.engine import engine

def compute_emissions() -> Dict[str, Any]:
    """
    Environmental Metrics Extractor.
    [Demo Explanation]
      - Represents: The total amount of predicted CO2 equivalent escaping the simulated factories.
      - Calculated: By aggregating the continuous output of the Random Forest Regression model over time.
      - Importance: This is the raw baseline. Without tracking accurate cumulative emissions, the entire carbon credit system is invalid.
    """
    summary = engine.get_emission_summary()
    return {
        "total_emissions_co2e": summary.get("total_co2e", 0.0),
        "emission_rate_avg": summary.get("avg_co2e", 0.0),
        "active_sensors": summary.get("facilities", 0)
    }

def generate_predictions(new_reading: Dict[str, Any]) -> Dict[str, Any]:
    """
    AI/ML Metrics Extractor via Pipeline Processing.
    [Demo Explanation]
      - Represents: The real-time output of the AI pipeline upon receiving a single new telemetry reading.
      - Calculated: We pass raw data through a Pipeline (Cleaning -> Anomaly Isolation Forest -> Random Forest Regressor).
      - Importance: Proves the system is reacting intelligently to 'dirty' edge-device data and catching fraudulent sensor manipulation instantly.
    """
    # Push the reading through the actual engine pipeline.
    # This automatically triggers Phase 3 (Credits) and Phase 4 (Blockchain).
    result = engine.process_reading(new_reading)
    
    return {
        "facility_id": result.get("facility_id"),
        "predicted_co2e": result.get("co2e_emission", 0.0),
        "anomaly_flag": result.get("anomaly_flag", False),
        "severity_score": result.get("severity_score", 0.0),
    }

def calculate_carbon_credits() -> Dict[str, Any]:
    """
    Token/Financial Metrics Extractor.
    [Demo Explanation]
      - Represents: The dynamic valuation of how many emission credits have been 'saved' vs penalised.
      - Calculated: The AI compares 'predicted_co2e' vs 'facility_baseline'. Savings equal minted tokens.
      - Importance: This validates the financial incentive mechanics of the project.
    """
    overview = engine.get_dashboard_overview()
    return {
        "total_credits_generated": overview.get("total_credits_minted", 0.0),
        "total_marketplace_trades": overview.get("total_trades", 0),
        "current_token_price": overview.get("current_price", 0.0)
    }

def track_blockchain_transactions() -> Dict[str, Any]:
    """
    Blockchain Network Metrics.
    [Demo Explanation]
      - Represents: The state of the immutable ledger verifying our credits.
      - Calculated: We traverse the local cryptographic hash chain checking links and proof-of-work difficulty.
      - Importance: Guarantees that the emitted carbon credits are secure, tamper-proof, and cannot be double-spent.
    """
    status = engine.get_blockchain_status()
    blocks = engine.get_recent_blocks(limit=1)
    return {
        "transaction_count": status.get("total_transactions", 0),
        "chain_length": status.get("chain_length", 0),
        "chain_valid_integrity": status.get("is_valid", False),
        "latest_block_hash": blocks[0]["hash"] if blocks else "Genesis"
    }

def format_dashboard_json() -> str:
    """Aggregates all metrics into a clean, displayable JSON mapping."""
    metrics_payload = {
        "environment": compute_emissions(),
        "tokenomics": calculate_carbon_credits(),
        "blockchain": track_blockchain_transactions(),
        "system_status": "Running - Live Stream"
    }
    return json.dumps(metrics_payload, indent=2)

if __name__ == "__main__":
    engine.initialize()
    print("Initial Pipeline Extraction Metrics:")
    print(format_dashboard_json())
