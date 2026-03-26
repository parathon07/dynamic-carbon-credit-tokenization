"""
Phase 4 — System Validation & Evaluation
==========================================
Central configuration for all evaluation parameters, thresholds,
benchmark values, and output directories.
"""

from __future__ import annotations

import os
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────
PHASE4_ROOT = Path(os.path.dirname(os.path.abspath(__file__))).parent
OUTPUT_DIR = PHASE4_ROOT / "output"
FIGURES_DIR = OUTPUT_DIR / "figures"
TABLES_DIR = OUTPUT_DIR / "tables"

for d in (OUTPUT_DIR, FIGURES_DIR, TABLES_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ── Dataset Validation ─────────────────────────────────────────────────
# EPA / IPCC benchmark ranges per facility type (kg CO₂e / reading)
BENCHMARK_EMISSION_RANGES = {
    "chemical_manufacturing": (15.0, 35.0),
    "power_generation":      (18.0, 40.0),
    "cement_production":     (20.0, 45.0),
    "steel_manufacturing":   (20.0, 42.0),
    "petroleum_refining":    (22.0, 50.0),
}

# Sensor value realistic ranges (used for data validation)
SENSOR_REALISTIC_RANGES = {
    "co2_ppm":    (300.0, 800.0),
    "ch4_ppm":    (1.0, 10.0),
    "nox_ppb":    (10.0, 200.0),
    "fuel_rate":  (50.0, 500.0),
    "energy_kwh": (500.0, 10000.0),
}

VALIDATION_MIN_SAMPLES = 50
SHAPIRO_ALPHA = 0.05        # Normality test significance level
CORRELATION_THRESHOLD = 0.3  # Minimum expected sensor correlation

# ── AI Evaluation ──────────────────────────────────────────────────────
TRAIN_TEST_SPLIT = 0.2
CV_FOLDS = 5
RANDOM_STATE = 42

# Anomaly injection rates for F1 evaluation
ANOMALY_INJECTION_RATE = 0.05
ANOMALY_TYPES = ["emission_spike", "sensor_malfunction", "pattern_anomaly"]

# Acceptable thresholds for passing evaluation
MIN_R2_SCORE = 0.95
MAX_MAE_THRESHOLD = 2.0     # kg CO₂e
MIN_F1_SCORE = 0.70

# ── Blockchain Evaluation ──────────────────────────────────────────────
BENCH_BATCH_SIZES = [10, 50, 100, 200, 500, 1000]
DIFFICULTY_LEVELS = [1, 2, 3, 4]
LATENCY_PERCENTILES = [50, 75, 90, 95, 99]

# Simulated gas cost model (Wei per operation)
GAS_COST_PER_BLOCK = 21000
GAS_PRICE_GWEI = 20

# ── Scalability ────────────────────────────────────────────────────────
SCALE_FACILITY_COUNTS = [10, 25, 50, 100, 200, 500]
SCALE_READING_COUNTS = [100, 500, 1000, 2500, 5000, 10000]
SCALE_TRADE_COUNTS = [1, 5, 10, 25, 50, 100]

# ── Comparative Analysis ──────────────────────────────────────────────
COMPARISON_DIMENSIONS = [
    "transparency",
    "real_time_capability",
    "pricing_accuracy",
    "fraud_detection",
    "scalability",
    "cost_efficiency",
]

# Scores (0–10) for traditional ETS and static credit models
TRADITIONAL_ETS_SCORES = {
    "transparency": 4, "real_time_capability": 2, "pricing_accuracy": 5,
    "fraud_detection": 3, "scalability": 4, "cost_efficiency": 5,
}
STATIC_MODEL_SCORES = {
    "transparency": 2, "real_time_capability": 1, "pricing_accuracy": 3,
    "fraud_detection": 1, "scalability": 6, "cost_efficiency": 7,
}

# ── Case Studies ───────────────────────────────────────────────────────
INDUSTRIAL_PLANT_FACILITIES = 5
INDUSTRIAL_PLANT_READINGS = 500
SMART_CITY_FACILITIES = 50
SMART_CITY_READINGS = 200

# ── Visualization ──────────────────────────────────────────────────────
FIGURE_DPI = 300
FIGURE_FORMAT = "png"
FIGURE_STYLE = "seaborn-v0_8-whitegrid"
COLOR_PALETTE = ["#2196F3", "#4CAF50", "#FF9800", "#E91E63", "#9C27B0", "#00BCD4"]

# ── Report ─────────────────────────────────────────────────────────────
REPORT_TITLE = "Phase 4: System Validation & Performance Evaluation Report"
