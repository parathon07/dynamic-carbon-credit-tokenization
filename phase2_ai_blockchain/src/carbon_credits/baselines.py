"""
Emission Baselines — Step 2.4
==============================
Per-facility-type hourly emission baselines (kg CO₂e/hour).
Used as the reference point for carbon credit calculations.
"""

from __future__ import annotations

from src.config import EMISSION_BASELINES, FACILITY_TYPES


def get_baseline(facility_type: str) -> float:
    """Return the hourly emission baseline for a facility type (kg CO₂e/hour)."""
    if facility_type not in EMISSION_BASELINES:
        raise ValueError(
            f"Unknown facility type: {facility_type}. "
            f"Valid types: {FACILITY_TYPES}"
        )
    return EMISSION_BASELINES[facility_type]


def get_all_baselines() -> dict:
    """Return all baselines as a dict."""
    return dict(EMISSION_BASELINES)


def get_15s_baseline(facility_type: str) -> float:
    """
    Return the per-reading (15-second) baseline.
    Baselines are hourly → divide by 240 (3600/15).
    """
    return get_baseline(facility_type) / 240.0
