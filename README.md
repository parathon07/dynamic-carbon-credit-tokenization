# Blockchain-Based Dynamic Carbon Credit Tokenisation System

An end-to-end AI and blockchain-integrated platform for **real-time carbon emission monitoring**, **credit tokenisation**, and **market-based trading**. Built across three phases — from IoT sensor simulation through AI inference and blockchain recording to a fully autonomous carbon credit marketplace.

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│                         DATA FLOW PIPELINE                             │
│                                                                        │
│  IoT Sensors ──→ Edge Gateway ──→ Backend ──→ AI Engine ──→ Carbon     │
│  (Phase 1)       (Kalman/SQLite)              (RF + IF)     Credits    │
│                                                              │         │
│                                         ┌────────────────────┘         │
│                                         ▼                              │
│            Blockchain Ledger ◄── Token Manager ──→ Marketplace         │
│            (SHA-256 PoW)         (ERC-20 CCT)      (Phase 3)           │
│                  │                                     │               │
│                  ▼                                     ▼               │
│            Immutable Record              ┌─────────────────────────┐   │
│                                          │ Dynamic Pricing (ARIMA) │   │
│                                          │ Order Book (P2P)        │   │
│                                          │ Fraud Detection         │   │
│                                          │ Policy Simulation       │   │
│                                          │ Emission Optimization   │   │
│                                          └─────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
Distributed_project/
├── run_demo.py                     # Combined demo (all 3 phases)
├── README.md
├── .gitignore
│
├── phase1_infrastructure/          # IoT + Edge + Backend
│   ├── src/
│   │   ├── sensors/
│   │   │   └── data_generator.py   # Multi-facility IoT simulator
│   │   └── edge/
│   │       ├── gateway.py          # Edge validation + SQLite buffer
│   │       └── kalman_filter.py    # 1-D Kalman noise filter
│   ├── tests/
│   └── requirements.txt
│
├── phase2_ai_blockchain/           # AI + Blockchain + Tokenisation
│   ├── src/
│   │   ├── preprocessing/
│   │   │   ├── cleaner.py          # NaN/outlier handling
│   │   │   ├── normalizer.py       # Min-max / z-score
│   │   │   └── synchronizer.py     # 15-sec grid alignment
│   │   ├── ai_engine/
│   │   │   ├── emission_model.py   # Random Forest CO₂e estimator
│   │   │   ├── anomaly_detector.py # Isolation Forest + z-score
│   │   │   └── training.py         # Synthetic data generation
│   │   ├── carbon_credits/
│   │   │   ├── calculator.py       # Credit / penalty computation
│   │   │   └── baselines.py        # Per-type emission baselines
│   │   ├── blockchain/
│   │   │   ├── ledger.py           # SHA-256 hash-chain (PoW)
│   │   │   ├── token_manager.py    # ERC-20 CCT token
│   │   │   ├── smart_contracts.py  # Validation, issuance, trading
│   │   │   └── trading.py          # Basic order matching
│   │   ├── pipeline/
│   │   │   └── orchestrator.py     # Phase 2 unified pipeline
│   │   └── dashboard/
│   │       └── monitor.py          # Real-time stats tracker
│   ├── tests/
│   └── requirements.txt
│
└── phase3_market_intelligence/     # Marketplace + AI Pricing + Risk
    ├── src/
    │   ├── config.py               # All Phase 3 parameters
    │   ├── marketplace/
    │   │   ├── marketplace.py      # P2P listings, bids, purchases
    │   │   └── wallet.py           # Per-participant wallet
    │   ├── pricing/
    │   │   ├── pricing_engine.py   # ARIMA + supply-demand pricing
    │   │   └── market_signals.py   # Signal aggregation
    │   ├── trading/
    │   │   └── order_book.py       # Price-time priority matching
    │   ├── optimization/
    │   │   └── optimizer.py        # Emission reduction recommender
    │   ├── incentives/
    │   │   └── incentive_engine.py # Tiered rewards + penalties
    │   ├── risk/
    │   │   └── fraud_detector.py   # Wash trade / manipulation detection
    │   ├── analytics/
    │   │   └── analytics.py        # Market reports + forecasting
    │   ├── policy/
    │   │   └── policy_simulator.py # Carbon tax / cap-and-trade sim
    │   └── pipeline/
    │       └── orchestrator.py     # Phase 3 integration pipeline
    ├── tests/
    └── requirements.txt
```

---

## Phase 1: IoT Sensor Infrastructure

**Purpose:** Simulate industrial IoT sensors, validate data at the edge, and prepare readings for AI processing.

| Component | Description |
|-----------|-------------|
| `data_generator.py` | Generates 15-second interval readings for 5 facility types (CO₂, CH₄, NOₓ, fuel rate, energy) |
| `gateway.py` | Edge validation with fault detection (-999 sentinel), range clipping, SQLite buffering |
| `kalman_filter.py` | 1-D Kalman filter for sensor noise reduction |

**Facility Types:** Chemical Manufacturing, Power Generation, Cement Production, Steel Manufacturing, Petroleum Refining

---

## Phase 2: AI + Blockchain Layer

**Purpose:** AI-based emission estimation, anomaly detection, carbon credit calculation, and immutable blockchain recording with ERC-20 tokenisation.

### AI Engine
| Model | Algorithm | Purpose |
|-------|-----------|---------|
| Emission Estimator | **Random Forest** (100 trees) | Predict CO₂e emissions from 5 sensor inputs |
| Anomaly Detector | **Isolation Forest** + z-score (σ > 3) | Classify normal / emission spike / sensor fault |

**CO₂e Formula:**
```
CO₂e = (CO₂_ppm × 0.044 × 1.0) + (CH₄_ppm × 0.016 × 28.0) + (NOₓ_ppb × 0.000046 × 265.0)
```

### Blockchain & Tokenisation
- **Ledger:** SHA-256 hash-chained blocks with configurable proof-of-work difficulty
- **Token (CCT):** ERC-20 style with mint, transfer, burn, approve, transferFrom
- **Double-counting prevention:** Unique `emission_hash` per reading ensures no duplicate minting
- **Smart Contracts:** Emission recording, credit issuance, and P2P trading validation

### Credit Calculation
```
net_credits = (baseline - actual) × conversion_factor
credits_earned  = max(0, net_credits) × reward_multiplier
credits_penalty = max(0, -net_credits) × penalty_multiplier
```

---

## Phase 3: Market Intelligence Layer

**Purpose:** Full-featured carbon credit marketplace with AI-driven pricing, smart trading, emission optimization, fraud detection, and policy simulation.

### 3.1 P2P Marketplace
- Participant wallet management (CCT balance, trade history)
- Credit listing & bidding system with automatic expiry
- Direct purchases with 1% marketplace fee
- All trades recorded on blockchain with unique `tx_hash`

### 3.2 Dynamic Pricing Engine
- **Supply-demand equilibrium:** Price adjusts inversely with supply/demand ratio
- **ARIMA forecasting:** Time-series prediction with (2,1,2) order (EMA fallback)
- **Volatility index:** Rolling standard deviation of price returns
- **Floor / Ceiling:** $5 – $200 per CCT

### 3.3 Smart Trading (Order Book)
- **Price-time priority** matching (like a stock exchange)
- **Limit orders:** Execute at specified price or better
- **Market orders:** Execute at best available price
- **Bid-ask spread** tracking
- All settlements via `CarbonToken.transfer()`

### 3.4 Emission Optimization
- Facility-level fuel usage and energy efficiency recommendations
- Trend analysis (increasing vs. decreasing emissions)
- Peer comparison against facility-type benchmarks
- Priority-ranked actionable recommendations

### 3.5 Incentive & Penalty System
| Tier | Reduction Required | Bonus Multiplier |
|------|--------------------|-------------------|
| 🥇 Gold | ≥ 20% | 1.5× |
| 🥈 Silver | ≥ 10% | 1.25× |
| 🥉 Bronze | ≥ 5% | 1.1× |

- **Escalating penalties** for consecutive violations (up to 3×)
- **Early adopter bonus:** 15% extra for first 10 participants
- Bonuses are minted, penalties are burned via `CarbonToken`

### 3.6 Fraud Detection
| Method | Detection |
|--------|-----------|
| Wash trading | Repeated trades between same pair in 60-sec window |
| Credit hoarding | Single participant holds > 30% of total supply |
| Velocity spike | Abnormal trade frequency (z-score > 3) |
| Price manipulation | Trades at prices > 3σ from market average |

### 3.7 Market Analytics
- Market overview (volume, value, participants)
- Price analytics with trend and volatility
- Credit flow tracking (mints, burns, trades)
- Participant leaderboard (top buyers / sellers)
- Exponential smoothing price forecast

### 3.8 Policy Simulation
| Policy | Effect |
|--------|--------|
| **Carbon tax** ($10–$200/tonne) | Higher tax → higher credit prices, lower emissions |
| **Cap-and-trade** (emission cap) | Tight cap → scarcity → price increase |
| **Clean energy subsidy** (up to 100%) | Faster adoption → lower emissions, moderate price drop |

Scenario comparison identifies best policy for emissions vs. price stability.

---

## Quick Start

### Prerequisites
- Python ≥ 3.10
- pip (package manager)

### Installation

```bash
# Clone the repository
git clone https://github.com/<your-username>/dynamic-carbon-credit-tokenization.git
cd dynamic-carbon-credit-tokenization

# Install dependencies for all phases
pip install -r phase1_infrastructure/requirements.txt
pip install -r phase2_ai_blockchain/requirements.txt
pip install -r phase3_market_intelligence/requirements.txt
```

### Run the Full Demo

```bash
python run_demo.py
```

This executes all 3 phases end-to-end:
1. **Stage 1:** IoT sensor data generation (50 facilities × 20 readings)
2. **Stage 2:** AI model training (Random Forest + Isolation Forest)
3. **Stage 3:** Pipeline processing (clean → predict → detect → credit → blockchain)
4. **Stage 4:** Results summary (emissions, anomalies, credits, tokens)
5. **Stage 5:** P2P credit trading demo
6. **Stage 6:** Market intelligence (pricing, optimization, incentives, fraud, policy)

### Run Tests

```bash
# Phase 1 (100+ tests)
cd phase1_infrastructure
python -m pytest tests/ -v

# Phase 2 (70+ tests)
cd phase2_ai_blockchain
python -m pytest tests/ -v

# Phase 3 (79 tests)
cd phase3_market_intelligence
python -m pytest tests/ -v
```

---

## Key Dependencies

| Phase | Package | Purpose |
|-------|---------|---------|
| 1 | `fastapi`, `uvicorn` | Backend REST API |
| 1 | `psycopg2`, `sqlalchemy` | TimescaleDB integration |
| 1 | `paho-mqtt` | MQTT broker for sensors |
| 2 | `scikit-learn` | Random Forest, Isolation Forest |
| 2 | `numpy`, `pandas` | Data processing |
| 3 | `statsmodels` | ARIMA time-series forecasting |
| 3 | `scipy` | Statistical analysis |

---

## Test Coverage Summary

| Phase | Tests | Coverage |
|-------|-------|----------|
| Phase 1: IoT Infrastructure | 100+ | Sensor generation, edge validation, Kalman filter, gateway |
| Phase 2: AI + Blockchain | 70+ | Preprocessing, AI models, credits, blockchain, tokens, contracts, pipeline |
| Phase 3: Market Intelligence | 79 | Marketplace, pricing, order book, optimizer, incentives, fraud, analytics, policy, integration |
| **Total** | **250+** | **End-to-end validated** |

---

## Performance Benchmarks (Demo Run)

| Metric | Value |
|--------|-------|
| Facilities simulated | 50 |
| Sensor readings | 1,000 |
| AI model R² score | 0.9994 |
| Anomaly detection rate | ~5% |
| Blockchain blocks | ~2,700 |
| Pipeline throughput | ~67 readings/sec |
| Credit price (dynamic) | $23.50 |
| Incentive tiers | 10 Gold, 10 Silver, 27 Bronze |
| Total execution time | ~21 seconds |

---

## License

This project is developed as part of academic research. Contact the authors for usage and licensing information.
