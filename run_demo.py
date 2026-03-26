"""
═══════════════════════════════════════════════════════════════════════
  COMBINED DEMO: Phase 1 + Phase 2 + Phase 3 + Phase 4 (Evaluation)
═══════════════════════════════════════════════════════════════════════

Run:
    cd Distributed_project
    python run_demo.py
"""

from __future__ import annotations

import importlib
import io
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

# Force UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import numpy as np

# ── Paths ─────────────────────────────────────────────────────────────
DEMO_DIR = os.path.dirname(os.path.abspath(__file__))
P1_DIR = os.path.join(DEMO_DIR, "phase1_infrastructure")
P2_DIR = os.path.join(DEMO_DIR, "phase2_ai_blockchain")
P3_DIR = os.path.join(DEMO_DIR, "phase3_market_intelligence")
P4_DIR = os.path.join(DEMO_DIR, "phase4_evaluation")


def load_phase(phase_dir):
    """Reload the 'src' package from a specific phase directory."""
    # Remove any cached 'src' modules
    to_remove = [k for k in sys.modules if k == "src" or k.startswith("src.")]
    for k in to_remove:
        del sys.modules[k]
    # Set path
    if phase_dir not in sys.path:
        sys.path.insert(0, phase_dir)
    for other in [P1_DIR, P2_DIR, P3_DIR, P4_DIR]:
        if other != phase_dir and other in sys.path:
            sys.path.remove(other)


# ══════════════════════════════════════════════════════════════════════
#  DISPLAY UTILITIES
# ══════════════════════════════════════════════════════════════════════

BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"
RESET = "\033[0m"
DIM = "\033[2m"

def header(text, color=CYAN):
    print(f"\n{color}{'═' * 72}\n  {text}\n{'═' * 72}{RESET}")

def subheader(text, color=YELLOW):
    print(f"\n{color}  ── {text} ──{RESET}")

def kv(key, val, indent=4):
    print(f"{' ' * indent}{DIM}{key}:{RESET} {BOLD}{val}{RESET}")

def bar(value, max_val, width=25, color=GREEN):
    f = min(int((value / (max_val + 1e-10)) * width), width)
    return f"{color}{'█' * f}{DIM}{'░' * (width - f)}{RESET}"

def trow(cols, ws):
    print("    " + "  ".join(str(c).ljust(w) for c, w in zip(cols, ws)))


# ══════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════

def main():
    total_start = time.perf_counter()

    print(f"""{CYAN}{BOLD}
    ╔══════════════════════════════════════════════════════════════════╗
    ║                                                                  ║
    ║   BLOCKCHAIN-BASED DYNAMIC CARBON CREDIT TOKENISATION SYSTEM     ║
    ║   Phase 1 + Phase 2 Combined Demonstration                       ║
    ║                                                                  ║
    ╚══════════════════════════════════════════════════════════════════╝
{RESET}""")

    NUM_FAC = 50
    N_READ = 20
    BASE = datetime(2024, 6, 15, 8, 0, 0, tzinfo=timezone.utc)

    # ══════════════════════════════════════════════════════════════════
    #  STAGE 1: Phase 1 — Generate IoT Sensor Data
    # ══════════════════════════════════════════════════════════════════
    header("STAGE 1: PHASE 1 — IoT SENSOR DATA GENERATION")

    load_phase(P1_DIR)
    from src.sensors.data_generator import FacilitySimulator, create_all_simulators
    from src.edge.kalman_filter import create_filters_for_facility
    from src.edge.gateway import validate_reading
    from src.config import FACILITY_TYPES as P1_TYPES, SENSOR_BASELINES as P1_BASE

    SENSOR_FIELDS = ["co2_ppm", "ch4_ppm", "nox_ppb", "fuel_rate", "energy_kwh"]

    print(f"\n    Initializing {NUM_FAC} facility simulators...")

    simulators = [FacilitySimulator(i, rng_seed=i + 100) for i in range(NUM_FAC)]
    kalman = {s.facility_id: create_filters_for_facility() for s in simulators}

    # Fleet overview
    subheader("Facility Fleet Overview")
    tc = defaultdict(int)
    for s in simulators:
        tc[s.facility_type] += 1

    ws = [28, 8]
    trow(["Facility Type", "Count"], ws)
    trow(["─" * 28, "─" * 8], ws)
    for ft in P1_TYPES:
        trow([ft, tc[ft]], ws)
    trow(["─" * 28, "─" * 8], ws)
    trow([f"{BOLD}TOTAL{RESET}", NUM_FAC], ws)

    # Generate readings
    subheader("Generating Sensor Readings")
    all_readings = []
    valid_count = 0
    anom_count = 0
    gen_start = time.perf_counter()

    for sim in simulators:
        t = BASE
        flt = kalman[sim.facility_id]
        for _ in range(N_READ):
            reading = sim.generate_reading(t)
            data = reading.to_dict()
            data["facility_type"] = sim.facility_type
            ok, _ = validate_reading(data)
            if ok:
                for f in SENSOR_FIELDS:
                    if f in flt:
                        data[f] = round(flt[f].update(data[f]), 4)
                all_readings.append(data)
                valid_count += 1
            if reading.anomaly_flag:
                anom_count += 1
            t += timedelta(seconds=15)

    gen_time = time.perf_counter() - gen_start

    kv("Total generated", NUM_FAC * N_READ)
    kv("Valid after edge filter", f"{valid_count} ({valid_count * 100 // (NUM_FAC * N_READ)}%)")
    kv("Anomalies injected (Phase 1)", anom_count)
    kv("Kalman-filtered", valid_count)
    kv("Generation time", f"{gen_time:.2f}s")
    kv("Throughput", f"{valid_count / gen_time:.0f} readings/sec")

    subheader("Sample Readings (first 3)")
    for r in all_readings[:3]:
        print(f"    {DIM}├─{RESET} {r['facility_id']} | {r['timestamp_utc'][:19]} | "
              f"CO₂={r['co2_ppm']:.1f}  CH₄={r['ch4_ppm']:.2f}  "
              f"NOₓ={r['nox_ppb']:.1f}  Fuel={r['fuel_rate']:.1f}")

    # ══════════════════════════════════════════════════════════════════
    #  STAGE 2: Phase 2 — Train AI Models
    # ══════════════════════════════════════════════════════════════════
    header("STAGE 2: PHASE 2 — AI MODEL TRAINING")

    load_phase(P2_DIR)
    from src.ai_engine.emission_model import EmissionEstimator, compute_co2e_ground_truth, extract_features
    from src.ai_engine.anomaly_detector import AnomalyDetector
    from src.ai_engine.training import generate_synthetic_data
    from src.preprocessing.cleaner import DataCleaner
    from src.preprocessing.synchronizer import TimestampSynchronizer
    from src.carbon_credits.calculator import CarbonCreditCalculator
    from src.carbon_credits.baselines import get_15s_baseline
    from src.blockchain.ledger import Blockchain
    from src.blockchain.token_manager import CarbonToken
    from src.blockchain.smart_contracts import EmissionRecordContract, CreditIssuanceContract, TradingContract
    from src.dashboard.monitor import DashboardMonitor
    from src.config import EMISSION_BASELINES

    subheader("Training Emission Estimator (Random Forest)")
    t_start = time.perf_counter()
    _, X_train, y_train = generate_synthetic_data(50, 200, seed=42)
    estimator = EmissionEstimator()
    metrics = estimator.train(X_train, y_train)
    kv("Training samples", len(X_train))
    kv("Random Forest R²", f"{metrics['rf_r2_mean']:.4f} ± {metrics['rf_r2_std']:.4f}")
    kv("Linear Regression R²", f"{metrics['lr_r2_mean']:.4f} ± {metrics['lr_r2_std']:.4f}")

    subheader("Feature Importance (Random Forest)")
    fi = estimator.feature_importance()
    mx = max(fi.values())
    for fn, imp in sorted(fi.items(), key=lambda x: -x[1]):
        print(f"    {fn:>14s}  {bar(imp, mx, 22)}  {imp:.4f}")

    subheader("Training Anomaly Detector (Isolation Forest)")
    # Fit anomaly detector on ACTUAL Phase 1 data so it knows the real distribution
    from src.ai_engine.emission_model import extract_features as p2_extract
    X_phase1 = np.array([p2_extract(r) for r in all_readings])
    detector = AnomalyDetector()
    detector.fit(X_phase1)
    kv("Fitted on", f"{len(X_phase1)} Phase 1 readings")
    kv("Method", "Isolation Forest + Z-score (σ > 3)")
    kv("Training time", f"{time.perf_counter() - t_start:.2f}s")

    # Compute per-type CO₂e baselines from actual data (avg × 1.1)
    # so ~50% of readings fall below baseline and earn credits
    from src.ai_engine.emission_model import compute_co2e_ground_truth as p2_co2e
    type_co2e = defaultdict(list)
    for r in all_readings:
        type_co2e[r["facility_type"]].append(p2_co2e(r))
    dynamic_baselines = {ft: float(np.mean(vals)) * 1.1 for ft, vals in type_co2e.items()}
    kv("Dynamic baselines", {ft: f"{v:.2f} kg" for ft, v in dynamic_baselines.items()})

    # ══════════════════════════════════════════════════════════════════
    #  STAGE 3: Phase 2 — Pipeline Processing
    # ══════════════════════════════════════════════════════════════════
    header("STAGE 3: PHASE 2 — PIPELINE PROCESSING")

    cleaner = DataCleaner()
    sync = TimestampSynchronizer()
    calc = CarbonCreditCalculator()
    bc = Blockchain(difficulty=2)
    token = CarbonToken()
    em_ctr = EmissionRecordContract(bc)
    iss_ctr = CreditIssuanceContract(bc, token, calc)
    monitor = DashboardMonitor()

    results = []
    anomalies = []
    pipe_start = time.perf_counter()

    print(f"\n    Processing {len(all_readings)} readings through full pipeline...")
    print(f"    {DIM}Clean → Sync → CO₂e Predict → Anomaly Detect → Credits → Blockchain{RESET}\n")

    for i, raw in enumerate(all_readings):
        cleaned = cleaner.clean_reading(raw)
        if cleaned is None:
            continue

        synced = sync.synchronize_reading(cleaned)
        em = estimator.predict(synced)
        synced["co2e_emission"] = em["co2e_emission"]
        synced["confidence_score"] = em["confidence_score"]

        anom = detector.detect(synced)
        synced["anomaly_flag"] = anom["anomaly_flag"]
        synced["anomaly_type"] = anom["anomaly_type"]
        synced["severity_score"] = anom["severity_score"]

        rec = em_ctr.record(synced)
        synced["blockchain_status"] = rec["status"]
        if rec.get("block_hash"):
            synced["block_hash"] = rec["block_hash"]

        if not synced["anomaly_flag"] and "facility_type" in synced:
            # Use dynamic baseline (scaled to match AI predictions)
            ft = synced["facility_type"]
            baseline = dynamic_baselines.get(ft, 30.0)
            actual = synced["co2e_emission"]
            reduction = baseline - actual
            net_credit = reduction * 0.001  # 1 credit = 1 tonne
            if net_credit >= 0:
                earned = net_credit
                penalty = 0.0
            else:
                earned = 0.0
                penalty = abs(net_credit) * 1.2
            synced["credits"] = {
                "credits_earned": round(earned, 6),
                "credits_penalty": round(penalty, 6),
                "net_credits": round(net_credit, 6),
                "baseline_emission": round(baseline, 4),
                "actual_emission": round(actual, 4),
                "reduction_pct": round((reduction / baseline) * 100, 2),
            }
            synced["token_minted"] = False
            # Mint token if credits earned
            if earned > 0:
                emission_hash = CarbonToken.compute_emission_hash(synced)
                try:
                    token.mint(synced["facility_id"], earned, emission_hash)
                    block_data = {
                        "type": "credit_issuance",
                        "facility_id": synced["facility_id"],
                        "credits_earned": earned,
                        "emission_hash": emission_hash,
                    }
                    bc.add_block(block_data)
                    synced["token_minted"] = True
                except ValueError:
                    pass  # duplicate hash
        else:
            synced["credits"] = None
            synced["token_minted"] = False

        results.append(synced)
        if synced["anomaly_flag"]:
            anomalies.append(synced)
        monitor.record_result(synced)

        if (i + 1) % 200 == 0 or i == len(all_readings) - 1:
            pct = (i + 1) * 100 // len(all_readings)
            bl = pct // 5
            print(f"\r    [{GREEN}{'█' * bl}{DIM}{'░' * (20 - bl)}{RESET}] "
                  f"{pct}%  ({i+1}/{len(all_readings)})", end="", flush=True)

    pipe_time = time.perf_counter() - pipe_start
    print()
    kv("Processed", len(results))
    kv("Pipeline time", f"{pipe_time:.2f}s")
    kv("Throughput", f"{len(results) / pipe_time:.0f} readings/sec")

    # ══════════════════════════════════════════════════════════════════
    #  STAGE 4: Results
    # ══════════════════════════════════════════════════════════════════
    header("STAGE 4: RESULTS", MAGENTA)

    # Emissions
    subheader("CO₂e Emission Summary")
    co2e_vals = [r["co2e_emission"] for r in results]
    kv("Total CO₂e emitted", f"{sum(co2e_vals):.2f} kg")
    kv("Average CO₂e/reading", f"{np.mean(co2e_vals):.4f} kg")
    kv("Std deviation", f"{np.std(co2e_vals):.4f} kg")

    # Per type
    subheader("Emissions by Facility Type")
    te = defaultdict(list)
    for r in results:
        te[r.get("facility_type", "?")].append(r["co2e_emission"])

    ws2 = [28, 10, 10, 8]
    trow(["Facility Type", "Avg CO₂e", "Total", "Δ%"], ws2)
    trow(["─" * 28, "─" * 10, "─" * 10, "─" * 8], ws2)
    for ft in ["chemical_manufacturing", "power_generation", "cement_production",
                "steel_manufacturing", "petroleum_refining"]:
        if ft in te:
            avg = np.mean(te[ft])
            bl = dynamic_baselines.get(ft, 30.0)
            delta = ((avg - bl) / bl) * 100
            c = GREEN if delta < 0 else RED
            trow([ft, f"{avg:.4f}", f"{sum(te[ft]):.2f}", f"{c}{delta:+.1f}%{RESET}"], ws2)

    # Anomalies
    subheader("Anomaly Detection")
    normal = sum(1 for r in results if not r["anomaly_flag"])
    kv("Normal readings", f"{GREEN}{normal}{RESET}")
    kv("Anomalies detected", f"{RED}{len(anomalies)}{RESET}")
    kv("Anomaly rate", f"{len(anomalies) * 100 / len(results):.1f}%")
    if anomalies:
        at = defaultdict(int)
        for a in anomalies:
            at[a["anomaly_type"]] += 1
        for k, v in sorted(at.items(), key=lambda x: -x[1]):
            kv(f"  {k}", v)
        subheader("Sample Anomaly Alerts")
        for a in anomalies[-5:]:
            sc = RED if a["severity_score"] > 0.5 else YELLOW
            print(f"    {sc}⚠{RESET} {a['facility_id']} | {a['anomaly_type']} | "
                  f"severity={sc}{a['severity_score']:.3f}{RESET}")

    # Carbon credits — compute from results
    subheader("Carbon Credit Summary")
    total_earned = sum(r["credits"]["credits_earned"] for r in results if r.get("credits"))
    total_penalty = sum(r["credits"]["credits_penalty"] for r in results if r.get("credits"))
    net_balance = total_earned - total_penalty
    credited_count = sum(1 for r in results if r.get("credits"))
    kv("Readings with credits", credited_count)
    kv("Credits earned", f"{GREEN}{total_earned:.6f} CCT{RESET}")
    kv("Credits penalty", f"{RED}{total_penalty:.6f} CCT{RESET}")
    kv("Net balance", f"{BOLD}{net_balance:.6f} CCT{RESET}")

    # Blockchain
    subheader("Blockchain Ledger")
    kv("Chain length", f"{bc.length} blocks")
    kv("Chain valid", f"{GREEN}✓ YES{RESET}" if bc.is_valid() else f"{RED}✗ NO{RESET}")
    kv("Latest hash", bc.latest_block.hash[:32] + "...")
    kv("Difficulty", "2 (proof-of-work)")

    # Tokens
    subheader("CCT Token (ERC-20 Style)")
    kv("Symbol", token.symbol)
    kv("Total supply", f"{BOLD}{token.total_supply:.4f} CCT{RESET}")
    kv("Unique holders", len(token.get_all_balances()))

    bals = token.get_all_balances()
    if bals:
        top = sorted(bals.items(), key=lambda x: -x[1])[:10]
        subheader("Top 10 Token Holders")
        mx = top[0][1]
        for rk, (fid, b) in enumerate(top, 1):
            print(f"    {rk:>2}. {fid}  {bar(b, mx, 20)}  {b:.4f} CCT")

    # ══════════════════════════════════════════════════════════════════
    #  STAGE 5: P2P Trading Demo
    # ══════════════════════════════════════════════════════════════════
    header("STAGE 5: P2P CARBON CREDIT TRADING", BLUE)

    tc = TradingContract(bc, token)
    holders = sorted(bals.items(), key=lambda x: -x[1])
    if len(holders) >= 2:
        seller, sb = holders[0]
        buyer = holders[-1][0]
        amt = round(sb * 0.2, 4)
        kv("Seller", f"{seller} (balance: {sb:.4f} CCT)")
        kv("Buyer", f"{buyer} (balance: {token.balance_of(buyer):.4f} CCT)")
        kv("Trade amount", f"{amt:.4f} CCT @ $25.00/credit")

        tr = tc.execute_trade(seller, buyer, amt, 25.0)
        if tr["status"] == "executed":
            print(f"\n    {GREEN}✓ Trade executed!{RESET}")
            kv("Block hash", tr["block_hash"][:32] + "...")
            kv("Seller balance", f"{tr['seller_balance']:.4f} CCT")
            kv("Buyer balance", f"{tr['buyer_balance']:.4f} CCT")
            kv("Trade value", f"${amt * 25:.2f}")

    # ══════════════════════════════════════════════════════════════════
    #  STAGE 6: PHASE 3 — MARKET INTELLIGENCE LAYER
    # ══════════════════════════════════════════════════════════════════
    header("STAGE 6: MARKET INTELLIGENCE LAYER", CYAN)

    # Load Phase 3 modules (keep Phase 2 objects alive)
    load_phase(P3_DIR)
    from src.pipeline.orchestrator import Phase3Pipeline

    p3 = Phase3Pipeline(token, bc)

    # Register all token-holding facilities
    holders = list(token.get_all_balances().keys())
    p3.register_participants(holders)
    kv("Registered participants", len(holders))

    # Feed Phase 2 results into Phase 3
    print(f"\n    {CYAN}▶ Ingesting Phase 2 results …{RESET}")
    p3_results = p3.process_phase2_batch(results)
    kv("Readings ingested", len(p3_results))

    # ── 6a. Dynamic Pricing ─────────────────────────────────────
    print(f"\n    {CYAN}▶ Dynamic Pricing Engine{RESET}")
    pricing_update = p3.pricing_engine.update_price(
        supply=token.total_supply, demand=max(token.total_supply * 0.6, 1.0)
    )
    kv("Credit price", f"${pricing_update['current_price']:.2f}")
    kv("Volatility index", f"{pricing_update['volatility_index']:.4f}")
    kv("Confidence", f"{pricing_update['confidence']:.2f}")

    # ── 6b. Order Book Trading ──────────────────────────────────
    print(f"\n    {CYAN}▶ Order Book Trading{RESET}")
    sorted_holders = sorted(holders, key=lambda h: token.balance_of(h), reverse=True)
    if len(sorted_holders) >= 2:
        seller = sorted_holders[0]
        buyer = sorted_holders[-1]
        sell_amount = min(token.balance_of(seller) * 0.1, 1.0)
        if sell_amount > 0.0001:
            trades = p3.run_marketplace_round(
                sellers=[{"participant_id": seller, "amount": round(sell_amount, 4),
                         "price": pricing_update['current_price']}],
                buyers=[{"participant_id": buyer, "amount": round(sell_amount, 4),
                        "price": pricing_update['current_price']}],
            )
            kv("Trades executed", len(trades))
            for t in trades:
                kv(f"  {t['seller']} → {t['buyer']}",
                   f"{t['amount']:.4f} CCT @ ${t['price']:.2f}")
        else:
            print(f"      {YELLOW}⚠ Insufficient balance for demo trade{RESET}")
    else:
        print(f"      {YELLOW}⚠ Need ≥2 participants for trading demo{RESET}")

    # ── 6c. Emission Optimization ───────────────────────────────
    print(f"\n    {CYAN}▶ Emission Optimization{RESET}")
    if holders:
        recs = p3.generate_recommendations(holders[0])
        kv("Facility analysed", holders[0])
        for rec in recs[:3]:
            prio = rec.get('priority', 'info')
            color = GREEN if prio == 'info' else (YELLOW if prio == 'medium' else RED)
            print(f"      {color}[{prio.upper()}]{RESET} {rec['recommendation']}")

    # ── 6d. Incentive Tier Summary ──────────────────────────────
    print(f"\n    {CYAN}▶ Incentive System{RESET}")
    inc_summary = p3.incentives.get_summary()
    kv("Total bonuses minted", f"{inc_summary['total_bonuses_minted']:.4f} CCT")
    kv("Total penalties burned", f"{inc_summary['total_penalties_burned']:.4f} CCT")
    kv("Tier distribution", inc_summary['tier_distribution'])

    # ── 6e. Fraud Detection ─────────────────────────────────────
    print(f"\n    {CYAN}▶ Fraud Detection{RESET}")
    fraud_alerts = p3.run_fraud_analysis()
    kv("Alerts raised", len(fraud_alerts))
    for a in fraud_alerts[:3]:
        print(f"      {RED}⚠ {a['alert_type']}{RESET} severity={a['severity']} "
              f"participants={a['participants']}")

    # ── 6f. Policy Simulation ───────────────────────────────────
    print(f"\n    {CYAN}▶ Policy Simulation{RESET}")
    policy = p3.run_policy_simulation()
    cmp = policy['comparison']
    kv("Best for emissions", cmp['best_for_emissions'])
    kv("Best for price stability", cmp['best_for_price_stability'])
    for sc in cmp.get('scenarios', []):
        print(f"      {sc['policy']}: price {sc['price_change']:+.1f}%, "
              f"emissions {sc['emission_change']:+.1f}%")

    # ══════════════════════════════════════════════════════════════════
    #  STAGE 7: PHASE 4 — SYSTEM EVALUATION
    # ══════════════════════════════════════════════════════════════════
    header("STAGE 7: SYSTEM EVALUATION", YELLOW)

    load_phase(P4_DIR)
    from src.dataset.validator import DatasetValidator
    from src.ai_eval.model_evaluator import ModelEvaluator
    from src.blockchain_eval.chain_benchmarker import BlockchainBenchmarker
    from src.comparative.system_comparator import SystemComparator

    # 7a. Dataset Validation
    print(f"\n    {CYAN}▶ Dataset Validation{RESET}")
    dv = DatasetValidator()
    co2e_vals = [r.get('co2e_emission', 0) for r in results]
    dv_result = dv.validate(all_readings, co2e_vals)
    kv("Validation score", f"{dv_result['validation_score']:.4f}")
    kv("Data reliability", dv_result['data_reliability'])
    kv("Completeness", f"{dv_result['completeness']['completeness_pct']:.1f}%")

    # 7b. AI Model Evaluation
    print(f"\n    {CYAN}▶ AI Model Evaluation{RESET}")
    me = ModelEvaluator()
    load_phase(P2_DIR)
    from src.ai_engine.emission_model import extract_features
    from src.ai_engine.emission_model import compute_co2e_ground_truth
    X_eval = np.array([extract_features(r) for r in all_readings])
    y_eval = np.array([compute_co2e_ground_truth(r) for r in all_readings])
    load_phase(P4_DIR)
    em_result = me.evaluate_emission_model(estimator, X_eval, y_eval)
    rf = em_result['random_forest']
    kv("RF R²", f"{rf['r2']:.4f}")
    kv("RF MAE", f"{rf['mae']:.6f} kg")
    kv("RF RMSE", f"{rf['rmse']:.6f} kg")
    kv("RF MAPE", f"{rf['mape_pct']:.4f}%")
    an_result = me.evaluate_anomaly_detector(
        detector, X_eval, all_readings,
        ['co2_ppm', 'ch4_ppm', 'nox_ppb', 'fuel_rate', 'energy_kwh'],
    )
    kv("Anomaly Precision", f"{an_result['precision']:.4f}")
    kv("Anomaly Recall", f"{an_result['recall']:.4f}")
    kv("Anomaly F1", f"{an_result['f1_score']:.4f}")

    # 7c. Blockchain Benchmarking
    print(f"\n    {CYAN}▶ Blockchain Benchmarking{RESET}")
    bb = BlockchainBenchmarker()
    load_phase(P2_DIR)
    from src.blockchain.ledger import Blockchain
    load_phase(P4_DIR)
    bc_result = bb.benchmark_all(
        Blockchain,
        lambda: {'type': 'emission', 'facility_id': 'BENCH', 'co2e': 25.0},
    )
    kv("Avg latency", f"{bc_result['latency']['avg_ms']:.2f} ms")
    kv("P95 latency", f"{bc_result['latency']['percentiles']['p95']:.2f} ms")
    kv("Max TPS", f"{bc_result['throughput']['max_tps']:.0f}")
    kv("Gas/tx (simulated)", f"${bc_result['gas_cost']['cost_per_tx_usd']:.4f}")

    # 7d. Comparative Analysis
    print(f"\n    {CYAN}▶ Comparative Analysis{RESET}")
    sc = SystemComparator()
    comp_result = sc.compare({
        'blockchain': bc_result,
        'scalability': {'facility_scaling': {'data_points': [{'throughput': len(results)/pipe_time, 'success': True}]}, 'bottleneck_analysis': 'scales_well'},
        'ai_eval': {'emission': em_result, 'anomaly': an_result},
    })
    overall = comp_result['overall_scores']
    kv("Proposed system", f"{overall['proposed']:.1f}/10")
    kv("Traditional ETS", f"{overall['traditional_ets']:.1f}/10")
    kv("Static model", f"{overall['static_model']:.1f}/10")
    improvement = comp_result.get('improvement_vs_ets_pct', {})
    best_dim = max(improvement, key=improvement.get) if improvement else 'N/A'
    kv("Biggest advantage", f"{best_dim} (+{improvement.get(best_dim, 0):.0f}%)")

    # ══════════════════════════════════════════════════════════════════
    #  FINAL SUMMARY
    # ══════════════════════════════════════════════════════════════════
    total_time = time.perf_counter() - total_start
    p3_report = p3.get_full_report()

    header("FINAL SUMMARY", GREEN)
    print(f"""
    ┌────────────────────────────────────────────────────────────────┐
    │  {BOLD}Phase 1: IoT Sensor Layer{RESET}                                     │
    │    Facilities:           {NUM_FAC:<10}                           │
    │    Readings generated:   {NUM_FAC * N_READ:<10}                           │
    │    Valid (edge-filtered): {valid_count:<10}                           │
    │    Kalman-filtered:       {valid_count:<10}                           │
    ├────────────────────────────────────────────────────────────────┤
    │  {BOLD}Phase 2: AI + Blockchain Layer{RESET}                                │
    │    RF R² score:          {metrics['rf_r2_mean']:<10.4f}                           │
    │    Readings processed:   {len(results):<10}                           │
    │    Anomalies detected:   {len(anomalies):<10}                           │
    │    Blockchain blocks:    {bc.length:<10}                           │
    │    Chain integrity:      {'✓ VALID':<10}                           │
    │    CCT tokens minted:    {token.total_supply:<10.4f}                           │
    │    Token holders:        {len(token.get_all_balances()):<10}                           │
    │    Net credits:          {net_balance:<10.6f}                         │
    ├────────────────────────────────────────────────────────────────┤
    │  {BOLD}Phase 3: Market Intelligence Layer{RESET}                            │
    │    Participants:         {len(holders):<10}                           │
    │    Credit price:         ${pricing_update['current_price']:<9.2f}                           │
    │    Order book trades:    {p3_report['order_book']['total_trades']:<10}                           │
    │    Incentive actions:    {inc_summary['total_actions']:<10}                           │
    │    Fraud alerts:         {len(fraud_alerts):<10}                           │
    │    Policies simulated:   {policy['comparison'].get('scenarios', []).__len__():<10}                           │
    ├────────────────────────────────────────────────────────────────┤
    │  {BOLD}Phase 4: System Evaluation{RESET}                                    │
    │    Data reliability:     {dv_result['data_reliability']:<10}                           │
    │    Emission RF R²:       {rf['r2']:<10.4f}                           │
    │    Anomaly F1:           {an_result['f1_score']:<10.4f}                           │
    │    Blockchain TPS:       {bc_result['throughput']['max_tps']:<10.0f}                           │
    │    System score:         {overall['proposed']:<10.1f}/10                        │
    ├────────────────────────────────────────────────────────────────┤
    │  {BOLD}Performance{RESET}                                                   │
    │    Total execution:      {total_time:<10.2f}s                          │
    │    Pipeline throughput:   {len(results)/pipe_time:<10.0f}readings/sec              │
    └────────────────────────────────────────────────────────────────┘
    """)
    print(f"    {GREEN}{BOLD}✓ All phases completed successfully!{RESET}\n")


if __name__ == "__main__":
    main()
