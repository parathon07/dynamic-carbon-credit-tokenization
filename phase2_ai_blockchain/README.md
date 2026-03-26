# Phase 2: AI + Blockchain + Tokenization
### Blockchain-Based Dynamic Carbon Credit Tokenisation System

Transforms Phase 1 raw IoT sensor data into verified emissions, AI predictions, anomaly detection, and blockchain-validated carbon credit tokens.

---

## Architecture

```
Raw Sensor Data (Phase 1)
    │
    ▼
┌──────────────────────────────────────────────────────────┐
│  DATA PREPROCESSING                                      │
│  cleaner.py → normalizer.py → synchronizer.py            │
│  (null removal, outlier clipping, min-max normalization,  │
│   timestamp grid alignment)                               │
└──────────────┬───────────────────────────────────────────┘
               ▼
┌──────────────────────────────────────────────────────────┐
│  AI ENGINE                                                │
│  emission_model.py:  Random Forest → CO₂e prediction      │
│  anomaly_detector.py: Isolation Forest → spike detection   │
│  Output: {co2e_emission, confidence_score, anomaly_flag}  │
└──────────────┬───────────────────────────────────────────┘
               ▼
┌──────────────────────────────────────────────────────────┐
│  CARBON CREDITS                                           │
│  credits = (baseline - actual) × conversion_factor        │
│  Reward for reduction, penalty for excess                 │
└──────────────┬───────────────────────────────────────────┘
               ▼
┌──────────────────────────────────────────────────────────┐
│  BLOCKCHAIN                                               │
│  SHA-256 hash chain → emission records → CCT token minting │
│  Smart contracts → P2P trading engine                     │
└──────────────┬───────────────────────────────────────────┘
               ▼
┌──────────────────────────────────────────────────────────┐
│  DASHBOARD                                                │
│  Real-time emissions, credits, anomalies, blockchain logs │
└──────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
phase2_ai_blockchain/
├── README.md
├── requirements.txt
├── pytest.ini
├── src/
│   ├── config.py                    # Emission factors, baselines, blockchain params
│   ├── preprocessing/
│   │   ├── cleaner.py               # Null/noise removal, outlier clipping
│   │   ├── normalizer.py            # Min-max & z-score normalization
│   │   └── synchronizer.py          # Timestamp grid alignment, gap detection
│   ├── ai_engine/
│   │   ├── emission_model.py        # Random Forest + Linear Regression CO₂e
│   │   ├── anomaly_detector.py      # Isolation Forest + z-score thresholds
│   │   ├── training.py              # Synthetic data → train → save models
│   │   └── inference.py             # Load models → real-time prediction
│   ├── carbon_credits/
│   │   ├── baselines.py             # Per-type emission baselines
│   │   └── calculator.py            # Reward/penalty credit computation
│   ├── blockchain/
│   │   ├── ledger.py                # SHA-256 hash chain with proof-of-work
│   │   ├── token_manager.py         # ERC-20 style CCT token operations
│   │   ├── smart_contracts.py       # Emission record, issuance, trading
│   │   └── trading.py              # P2P order book trading engine
│   ├── pipeline/
│   │   └── orchestrator.py          # Full IoT → AI → Blockchain pipeline
│   └── dashboard/
│       └── monitor.py               # Real-time stats and reporting
├── tests/
│   └── test_phase2.py               # 70+ comprehensive test cases
└── models/                          # Saved ML models (.pkl)
```

---

## Key Formulas

| Calculation | Formula |
|---|---|
| CO₂ equivalent | `CO₂e = CO₂_kg × 1.0 + CH₄_kg × 28.0 + NOₓ_kg × 265.0` |
| Net credits | `(baseline - actual) × 0.001` (1 credit = 1 tonne CO₂e) |
| Anomaly z-score | `z = (x - μ) / σ`, flag if `\|z\| > 3` |
| Block hash | `SHA-256(index + timestamp + data + prev_hash + nonce)` |

---

## Setup & Run

```bash
cd phase2_ai_blockchain
pip install -r requirements.txt
python -m pytest tests/test_phase2.py -v
```

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| ML Models | scikit-learn (Random Forest, Isolation Forest) |
| Data Processing | NumPy, pandas |
| Blockchain | Custom SHA-256 chain (no external node) |
| Tokens | ERC-20 style (in-process simulation) |
| Serialization | joblib (model persistence) |
| Testing | pytest |
