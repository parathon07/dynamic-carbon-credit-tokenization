"""
Pydantic Schemas — Request / Response models for all API endpoints.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════
#  AUTH
# ═══════════════════════════════════════════════════════════════════════

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    full_name: str = ""
    role: str = Field(default="viewer", pattern="^(admin|operator|viewer)$")

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    username: str
    role: str
    full_name: str


# ═══════════════════════════════════════════════════════════════════════
#  EMISSIONS
# ═══════════════════════════════════════════════════════════════════════

class SensorReading(BaseModel):
    facility_id: str
    facility_type: str = "chemical_manufacturing"
    co2_ppm: float = Field(..., ge=0, le=10000)
    ch4_ppm: float = Field(..., ge=0, le=500)
    nox_ppb: float = Field(..., ge=0, le=5000)
    fuel_rate: float = Field(..., ge=0)
    energy_kwh: float = Field(..., ge=0)
    timestamp_utc: Optional[str] = None

class EmissionResult(BaseModel):
    facility_id: str
    facility_type: str
    co2e_emission: float
    anomaly_flag: bool
    anomaly_type: str
    severity_score: float
    credits_earned: float
    credits_penalty: float
    blockchain_hash: str
    timestamp: str

class EmissionSummary(BaseModel):
    total_readings: int
    total_co2e: float
    avg_co2e: float
    anomalies_detected: int
    facilities: int
    by_facility_type: Dict[str, Any]

class FacilityInfo(BaseModel):
    facility_id: str
    facility_type: str
    total_readings: int
    total_co2e: float
    avg_co2e: float
    credit_balance: float


# ═══════════════════════════════════════════════════════════════════════
#  CREDITS
# ═══════════════════════════════════════════════════════════════════════

class CreditBalance(BaseModel):
    facility_id: str
    balance: float
    total_earned: float
    total_penalties: float
    net_credits: float

class CreditTransaction(BaseModel):
    tx_id: str
    facility_id: str
    amount: float
    tx_type: str  # "mint" | "burn" | "transfer"
    timestamp: str


# ═══════════════════════════════════════════════════════════════════════
#  TRADING
# ═══════════════════════════════════════════════════════════════════════

class OrderRequest(BaseModel):
    participant_id: str
    side: str = Field(..., pattern="^(buy|sell)$")
    quantity: float = Field(..., gt=0)
    price: Optional[float] = Field(default=None, gt=0)
    order_type: str = Field(default="limit", pattern="^(limit|market)$")

class OrderResponse(BaseModel):
    order_id: str
    status: str
    participant_id: str
    side: str
    quantity: float
    price: Optional[float]

class TradeRecord(BaseModel):
    trade_id: str
    buyer: str
    seller: str
    quantity: float
    price: float
    timestamp: str

class OrderBookView(BaseModel):
    bids: List[Dict[str, Any]]
    asks: List[Dict[str, Any]]
    spread: Optional[float]
    last_price: Optional[float]

class PriceInfo(BaseModel):
    current_price: float
    change_24h: float
    high_24h: float
    low_24h: float
    volume_24h: float
    volatility_index: float


# ═══════════════════════════════════════════════════════════════════════
#  BLOCKCHAIN
# ═══════════════════════════════════════════════════════════════════════

class BlockchainStatus(BaseModel):
    chain_length: int
    is_valid: bool
    latest_hash: str
    difficulty: int
    total_transactions: int

class BlockInfo(BaseModel):
    index: int
    timestamp: str
    data_type: str
    hash: str
    previous_hash: str


# ═══════════════════════════════════════════════════════════════════════
#  ANALYTICS
# ═══════════════════════════════════════════════════════════════════════

class DashboardOverview(BaseModel):
    total_emissions: float
    total_credits_minted: float
    total_trades: int
    active_facilities: int
    blockchain_blocks: int
    current_price: float
    system_score: float
    anomaly_rate: float

class ForecastResponse(BaseModel):
    forecast_prices: List[float]
    confidence_interval: Dict[str, List[float]]
    trend: str

class ComparisonResponse(BaseModel):
    dimensions: List[str]
    proposed: Dict[str, float]
    traditional_ets: Dict[str, float]
    static_model: Dict[str, float]
    overall_scores: Dict[str, float]


# ═══════════════════════════════════════════════════════════════════════
#  GENERIC
# ═══════════════════════════════════════════════════════════════════════

class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str
    uptime_seconds: float
    services: Dict[str, str]

class APIResponse(BaseModel):
    success: bool = True
    message: str = ""
    data: Any = None
