# AI Model Training and Evaluation Guide

## Overview

This document outlines the methodology, architecture, and evaluation processes for the AI models integrated into the Blockchain-Based Dynamic Carbon Credit Tokenisation System. The models are pivotal for predicting greenhouse gas emissions securely and for flagging anomalous or fraudulent sensor readings.

## Model Summary

The project utilizes two primary machine learning models designed to operate robustly on IoT-generated sensor data:

1.  **Emission Estimator (Regression Approach)**
    *   **Algorithm:** Random Forest Regressor & Linear Regression (for baseline comparison).
    *   **Purpose:** Predict $CO_2e$ emissions based on multispectral sensor inputs.
    *   **Features:** `co2_ppm`, `ch4_ppm`, `nox_ppb`, `fuel_rate`, `energy_kwh`.
    *   **Evaluation Metrics:** $R^2$ Score, MAE (Mean Absolute Error), RMSE, MAPE.
2.  **Anomaly Detector (Unsupervised Learning Approach)**
    *   **Algorithm:** Isolation Forest paired with Statistical Z-score validations.
    *   **Purpose:** Detect outliers, potential fraud attempts, or sensor malfunctions in real-time.
    *   **Features:** Time-series patterns of identical IoT sensor features.
    *   **Evaluation Metrics:** Precision, Recall, F1-Score.

## 1. Data Generation and Preprocessing

Since real-time industrial carbon emission data is sensitive, a highly advanced synthetic data generation approach is utilized (`src/ai_engine/training.py`).

### Data Synthesis Methodology
*   **Generative Simulation:** Sensors generate values within context-aware baselines defined for distinct industry types (Chemical, Steel, Power Generation, etc.).
*   **Noise and Variance:** Gaussian noise is injected to realistically model transient anomalies and fluctuating fuel/energy consumption patterns.
*   **Kalman Filtering:** Simulated edge devices use a Kalman Filter to suppress high-frequency noise, ensuring clean signal integrity before reaching the AI pipelines.

### Preprocessing Pipeline
1.  **Cleaning:** Erroneous Nulls or unphysical negative values are excluded or imputed.
2.  **Time-Synchronization:** Ensures timestamps are rigorously aligned using interpolation to correct intermittent transmission delays.
3.  **Feature Extraction:** Translating physical fields into standardized input vectors.

## 2. Emission Estimator Training Process

### Training Steps
1.  **Dataset Construction:** Using the phase 2 synthetic generator to create a robust dataset covering 30+ virtual facilities spanning several months.
2.  **Train-Test Split:** Conducted temporally (handling potential time-series dependencies) with an 80/20 standard split.
3.  **Random Forest Configuration:**
    *   `n_estimators=100`: Balance between computational complexity and variance reduction.
    *   `random_state=42`: Ensuring reproducibility.
4.  **Ground Truth Computation:** The ground truth label ($Y$) is computed using established GHG physical equations applying Global Warming Potential (GWP) coefficients for $CH_4$ ($\times28$) and $NO_x$ ($\times298$).

### Model Performance
The Random Forest typically yields high predictive stability on simulated industrial metrics with $R^2$ scores usually over **0.95**, far exceeding linear modeling capabilities which struggle with non-linear multi-gas volatility.

## 3. Anomaly Detector Training Process

### Fit Phase
*   The Isolation Forest is trained exclusively on standard, 'normal' operating conditions across various facilities to understand the natural multi-variate distribution.
*   The model dynamically adapts branching trees to isolate instances which deviate substantially from the core sample density.

### Detection Phase
During production inference, incoming data points receive an anomaly score. By applying an empirically chosen threshold factor, readings are flagged as `True` (Anomaly) or `False` (Normal). Further validation checks if $\sigma > 3$ on specific gas features.

## 4. Retraining & Continuous Learning Strategy

As part of the deployment (Phase 5), model decay is a recognized risk.
*   **Feedback Loops:** Periodic ground-truth audits (e.g. quarterly meter readings) are planned to be ingested for continual fine-tuning.
*   **Version Control:** Newly trained models will be containerized and swapped via blue-green deployment strategies to ensure zero downtime.
*   **Monitoring Dashboards:** Using Phase 4 utilities, system administrators monitor model drift through integrated model evaluation endpoints.

---
*Created by Antigravity AI — Documentation Auto-Generated.*
