"""
Phase 3 — Centralised Configuration
======================================
Marketplace parameters, pricing model defaults, order book settings,
fraud detection thresholds, incentive tiers, and policy simulation defaults.
"""

from __future__ import annotations

import os
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── Facility Types (inherited from Phase 1/2) ────────────────────────────
FACILITY_TYPES = [
    "chemical_manufacturing",
    "power_generation",
    "cement_production",
    "steel_manufacturing",
    "petroleum_refining",
]

# ── Marketplace Parameters ───────────────────────────────────────────────
DEFAULT_CREDIT_PRICE = 25.0        # $/CCT starting price
MIN_LISTING_AMOUNT = 0.0001        # minimum CCT for a listing
LISTING_EXPIRY_HOURS = 72          # listings expire after 72h
MARKETPLACE_FEE_RATE = 0.01        # 1% transaction fee

# ── Dynamic Pricing Engine ───────────────────────────────────────────────
PRICING_LOOKBACK_WINDOW = 50       # number of past trades for price calc
SUPPLY_DEMAND_SENSITIVITY = 0.15   # price sensitivity to supply-demand ratio
ARIMA_ORDER = (2, 1, 2)            # (p, d, q) for ARIMA model
VOLATILITY_WINDOW = 20             # rolling window for volatility calc
BASE_PRICE_FLOOR = 5.0             # minimum price floor $/CCT
BASE_PRICE_CEILING = 200.0         # maximum price ceiling $/CCT

# ── Order Book / Trading ─────────────────────────────────────────────────
MAX_ORDER_SIZE = 10000.0           # max CCT per single order
ORDER_EXPIRY_SECONDS = 3600        # limit orders expire after 1h
PRICE_TICK_SIZE = 0.01             # minimum price increment

# ── Emission Optimization ────────────────────────────────────────────────
OPTIMIZATION_LOOKBACK = 100        # readings to analyse for recommendations
FUEL_REDUCTION_COST_PER_PCT = 500  # $/% cost to reduce fuel usage
ENERGY_SAVING_PER_KWH = 0.12      # $/kWh saving from efficiency

# ── Incentive & Penalty ──────────────────────────────────────────────────
INCENTIVE_TIERS = {
    "gold":   {"min_reduction_pct": 20.0, "bonus_multiplier": 1.5},
    "silver": {"min_reduction_pct": 10.0, "bonus_multiplier": 1.25},
    "bronze": {"min_reduction_pct": 5.0,  "bonus_multiplier": 1.1},
}
PENALTY_ESCALATION_RATE = 0.1      # additional 10% per consecutive violation
MAX_PENALTY_MULTIPLIER = 3.0       # cap on penalty escalation
EARLY_ADOPTER_BONUS = 1.15         # 15% bonus for first 10 participants

# ── Fraud Detection ──────────────────────────────────────────────────────
WASH_TRADE_WINDOW_SEC = 60         # time window to detect wash trading
WASH_TRADE_MIN_TRADES = 3          # min trades between same pair in window
HOARDING_THRESHOLD_PCT = 30.0      # % of total supply = hoarding
VELOCITY_SPIKE_ZSCORE = 3.0        # z-score threshold for velocity anomaly
MIN_TRADE_HISTORY = 5              # min trades before fraud analysis

# ── Policy Simulation ────────────────────────────────────────────────────
DEFAULT_CARBON_TAX_RATE = 50.0     # $/tonne CO₂e
TAX_RATE_RANGE = (10.0, 200.0)     # simulation range for carbon tax
CAP_AND_TRADE_DEFAULT_CAP = 1000.0 # total emission cap in tonnes
SUBSIDY_RATE_CLEAN_ENERGY = 0.20   # 20% subsidy for clean energy adoption

# ── Analytics ────────────────────────────────────────────────────────────
ANALYTICS_REPORT_TOP_N = 10        # top-N in leaderboards
FORECAST_HORIZON = 10              # periods ahead for price forecasting

# ── Sensor fields (shared) ──────────────────────────────────────────────
SENSOR_FIELDS = ["co2_ppm", "ch4_ppm", "nox_ppb", "fuel_rate", "energy_kwh"]
