"""
Prometheus Monitoring — Custom metrics for the carbon credit platform.
"""
from __future__ import annotations

from prometheus_client import Counter, Histogram, Gauge, Info


# ── Request metrics ───────────────────────────────────────────────────
REQUEST_COUNT = Counter(
    "carbon_request_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "carbon_request_latency_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# ── Business metrics ─────────────────────────────────────────────────
EMISSIONS_PROCESSED = Counter(
    "carbon_emissions_processed_total",
    "Total emission readings processed",
)

CREDITS_MINTED = Counter(
    "carbon_credits_minted_total",
    "Total carbon credits minted",
)

CREDITS_BURNED = Counter(
    "carbon_credits_burned_total",
    "Total carbon credits burned",
)

TRADES_EXECUTED = Counter(
    "carbon_trades_executed_total",
    "Total trades executed",
)

BLOCKCHAIN_BLOCKS = Gauge(
    "carbon_blockchain_blocks",
    "Current blockchain length",
)

ACTIVE_USERS = Gauge(
    "carbon_active_users",
    "Number of currently active users",
)

CREDIT_PRICE = Gauge(
    "carbon_credit_price_usd",
    "Current carbon credit price in USD",
)

# ── System info ──────────────────────────────────────────────────────
SYSTEM_INFO = Info(
    "carbon_system",
    "System metadata",
)
SYSTEM_INFO.info({
    "version": "1.0.0",
    "framework": "fastapi",
    "blockchain": "sha256_pow",
    "ai_model": "random_forest",
})
