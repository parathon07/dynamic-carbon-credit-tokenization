# Phase-Wise System Execution Workflow

This document provides a detailed, step-by-step breakdown of how the **Blockchain-Based Dynamic Carbon Credit Tokenisation** framework functions internally, corresponding directly with the orchestrations instantiated by the unified `run_demo.py` launcher.

---

## 🏗️ Phase 1: Infrastructure Setup
**What is happening:** 
The system establishes its baseline operational parameters by spinning up non-deterministic IoT sensor nodes (`FacilitySimulator`) acting as distinct industrial power plants and manufacturing centers.

**Why it is important:** 
Without real-world emission data (which is confidential and hard to access), securing a highly realistic synthetic ecosystem ensures our AI and Blockchain logic can be thoroughly tested against robust variance.

**How it is implemented:** 
In `phase1_infrastructure/src/sensors/data_generator.py`, the code dynamically generates timestamp-seeded multi-variate metrics ($CO_2$, $CH_4$, $NO_x$, fuel rate, energy usage) shaped by diurnal (day/night) operations and simulated downtime incidents. Before data proceeds down the pipeline, an Edge-based **Kalman Filter** suppresses raw noise, pushing clean matrices into Phase 2.

---

## 🧹 Phase 2: Data Processing
**What is happening:** 
Raw telematic signals undergo rapid cleaning, validation, and feature translation.

**Why it is important:** 
Garbage in equals garbage out. Machine Learning models require clean tensors to make accurate regression predictions. Data ingestion pipelines must standardize anomalous missing values natively before attempting to estimate underlying carbon equivalency ($CO_2e$).

**How it is implemented:** 
`phase2_ai_blockchain/src/preprocessing/cleaner.py` evaluates boundaries and missing fields. `TimestampSynchronizer` corrects minor signal latencies to unify readings, ultimately converting IoT maps into standardized `np.ndarray` vectors for AI consumption.

---

## 🧠 Phase 3: AI/ML Integration
**What is happening:** 
The pipeline activates pre-trained Machine Learning inference models dynamically to approximate emissions and flag structural fraud.

**Why it is important:** 
Rather than trusting raw sensor metrics, the **Emission Estimator** reconstructs accurate GHG baselines utilizing feature correlation, while the **Anomaly Detector** identifies malicious tampering. This enforces zero-trust architectures prior to issuing financial carbon tokens.

**How it is implemented:** 
During initialization (`engine.initialize()`), `phase2_ai_blockchain/src/ai_engine/training.py` invokes a **Random Forest Regressor** to learn $CO_2e$ patterns. Real-time inference tests new data arrays against this model (`estimator.predict()`). An **Isolation Forest** evaluates if the reading falls outside a $3\sigma$ standard density, explicitly labeling `anomaly_flag: True/False`. Emission reductions calculate carbon credits organically (`CarbonCreditCalculator`).

---

## 🔗 Phase 4: Blockchain Integration
**What is happening:** 
Evaluated multi-gas metrics are permanently codified onto a distributed ledger, and earned credits manifest as minted $CCT$ (Carbon Credit Tokens).

**Why it is important:** 
Blockchain guarantees immutable transparency, fulfilling standard regulatory compliance models that prevent "double-counting" in carbon offsets. 

**How it is implemented:** 
`phase2_ai_blockchain/src/blockchain/ledger.py` packages valid readings into cryptographic blocks containing SHA-256 `emission_hashes` alongside the `facility_id`. Concurrently, `token_manager.py` manages a simulated ERC-20 token contract interface, allocating minted `$CCT` credits into digital wallets assigned to adhering facilities.

---

## 📊 Phase 5: Interface & Visualization
**What is happening:** 
The frontend visualization environment securely binds to the backend processing architecture.

**Why it is important:** 
Deployments require an intuitive interface for stakeholders (facility managers, regulators, traders) to monitor live carbon burns and active peer-to-peer (P2P) token order-book bids inside the marketplace.

**How it is implemented:** 
Using Python's `FastAPI`, the system mounts `phase5_deployment/frontend/index.html` natively to standard HTTP routes (`/`). Background data streams via `app/services/engine.py` supply live data endpoints mapping anomaly rates, credit balances, and block hashing metrics directly to dashboard DOM elements.

---

## 🚀 Phase 6: Deployment Simulation
**What is happening:** 
The system finalizes by transitioning from sequential setup procedures into a continuous, active service deployment state processing HTTP traffic.

**Why it is important:** 
Mimics authentic production behavior (where servers continuously listen for ingestion requests and web application calls), completing the project as a comprehensive monolithic stack.

**How it is implemented:** 
In `run_demo.py`, Python orchestrates a concurrent `uvicorn.run()` logic block that halts linear execution, bindings localhost ports (`127.0.0.1:8000`), forcing the default web browser to pop the live GUI while internal metrics process natively over REST loops.
