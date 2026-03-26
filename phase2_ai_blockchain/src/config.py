"""
Phase 2 — Centralised Configuration
=====================================
Emission factors, facility baselines, normalization ranges,
blockchain parameters, and dashboard settings.
"""

from __future__ import annotations

import os
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
MODELS_DIR.mkdir(exist_ok=True)

# ── Facility Types (inherited from Phase 1) ──────────────────────────────
FACILITY_TYPES = [
    "chemical_manufacturing",
    "power_generation",
    "cement_production",
    "steel_manufacturing",
    "petroleum_refining",
]

# ── Sensor Baseline Ranges (per facility type) ──────────────────────────
SENSOR_BASELINES = {
    "chemical_manufacturing": {
        "co2_ppm": (380, 520), "ch4_ppm": (1.5, 4.0),
        "nox_ppb": (30, 80), "fuel_rate": (100, 250), "energy_kwh": (2000, 5000),
    },
    "power_generation": {
        "co2_ppm": (400, 650), "ch4_ppm": (1.0, 3.0),
        "nox_ppb": (40, 120), "fuel_rate": (200, 500), "energy_kwh": (5000, 12000),
    },
    "cement_production": {
        "co2_ppm": (450, 700), "ch4_ppm": (0.8, 2.5),
        "nox_ppb": (50, 100), "fuel_rate": (150, 400), "energy_kwh": (3000, 8000),
    },
    "steel_manufacturing": {
        "co2_ppm": (420, 680), "ch4_ppm": (1.2, 3.5),
        "nox_ppb": (35, 90), "fuel_rate": (180, 450), "energy_kwh": (4000, 10000),
    },
    "petroleum_refining": {
        "co2_ppm": (500, 800), "ch4_ppm": (2.0, 6.0),
        "nox_ppb": (60, 150), "fuel_rate": (300, 700), "energy_kwh": (6000, 15000),
    },
}

# ── IPCC GWP-100 Emission Factors ────────────────────────────────────────
# Global Warming Potential relative to CO₂ (100-year horizon)
GWP_CO2 = 1.0       # CO₂ reference
GWP_CH4 = 28.0      # methane
GWP_N2O = 265.0     # nitrous oxide (NOₓ proxy)

# Conversion: ppm/ppb sensor reading → kg/hour emission estimate
# These are facility-scale conversion factors (ppm × volume_flow → mass)
EMISSION_CONVERSION = {
    "co2_ppm_to_kg":  0.044,   # molecular weight ratio × flow factor
    "ch4_ppm_to_kg":  0.016,   # CH₄ molecular weight factor
    "nox_ppb_to_kg":  0.000046,  # NOₓ ppb → kg (small quantities)
}

# ── Baseline Emissions (kg CO₂e per hour, per facility type) ─────────────
# Used for carbon credit calculation: credits = baseline - actual
EMISSION_BASELINES = {
    "chemical_manufacturing": 45.0,
    "power_generation":       72.0,
    "cement_production":      85.0,
    "steel_manufacturing":    68.0,
    "petroleum_refining":     95.0,
}

# ── Carbon Credit Parameters ────────────────────────────────────────────
CREDIT_CONVERSION_FACTOR = 0.001   # 1 credit = 1 tonne CO₂e = 1000 kg
CREDIT_REWARD_MULTIPLIER = 1.0     # reward multiplier for reductions
CREDIT_PENALTY_MULTIPLIER = 1.2    # higher penalty for excess emissions

# ── Normalization Ranges (for AI model input) ────────────────────────────
NORMALIZATION_RANGES = {
    "co2_ppm":    (300, 900),
    "ch4_ppm":    (0.5, 8.0),
    "nox_ppb":    (20, 200),
    "fuel_rate":  (50, 800),
    "energy_kwh": (1000, 18000),
}

# ── Valid Sensor Bounds (for cleaning) ───────────────────────────────────
VALID_SENSOR_BOUNDS = {
    "co2_ppm":    (0, 2000),
    "ch4_ppm":    (0, 50),
    "nox_ppb":    (0, 1000),
    "fuel_rate":  (0, 2000),
    "energy_kwh": (0, 50000),
}

# ── Anomaly Detection ───────────────────────────────────────────────────
ANOMALY_ZSCORE_THRESHOLD = 3.0     # z-score > 3 → anomaly
ISOLATION_FOREST_CONTAMINATION = 0.05  # expected 5% anomaly rate

# ── Blockchain ──────────────────────────────────────────────────────────
BLOCKCHAIN_DIFFICULTY = 2          # proof-of-work leading zeros
TOKEN_NAME = "CarbonCreditToken"
TOKEN_SYMBOL = "CCT"
TOKEN_DECIMALS = 4

# ── Sensor fields ───────────────────────────────────────────────────────
SENSOR_FIELDS = ["co2_ppm", "ch4_ppm", "nox_ppb", "fuel_rate", "energy_kwh"]
