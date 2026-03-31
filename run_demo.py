"""
========================================================================
  UNIFIED DEMO: Blockchain-Based Dynamic Carbon Credit System
========================================================================

    This script serves as the centralized orchestration and execution
    engine for the entire platform. It runs all core processes in
    sequence and finalizes by launching the full-stack UI interface.

    USAGE:
        python run_demo.py
"""

import io
import os
import sys
import time
import threading
import webbrowser

# Force UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── Paths ─────────────────────────────────────────────────────────────
DEMO_DIR = os.path.dirname(os.path.abspath(__file__))
P1_DIR = os.path.join(DEMO_DIR, "phase1_infrastructure")
P2_DIR = os.path.join(DEMO_DIR, "phase2_ai_blockchain")
P3_DIR = os.path.join(DEMO_DIR, "phase3_market_intelligence")
P4_DIR = os.path.join(DEMO_DIR, "phase4_evaluation")
P5_DIR = os.path.join(DEMO_DIR, "phase5_deployment", "backend")

# Ensure Phase 5 backend is the primary path to load app modules seamlessly
if P5_DIR not in sys.path:
    sys.path.insert(0, P5_DIR)


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
    print(f"\n{color}{'═' * 75}\n  {text}\n{'═' * 75}{RESET}\n")

def info(msg):
    print(f"  {GREEN}[INFO]{RESET} {msg}")

def explain(msg):
    print(f"    {DIM}├ {msg}{RESET}")


# ══════════════════════════════════════════════════════════════════════
#  MAIN EXECUTION ORCHESTRATION
# ══════════════════════════════════════════════════════════════════════

def main():
    print(f"""{CYAN}{BOLD}
    ╔══════════════════════════════════════════════════════════════════╗
    ║                                                                  ║
    ║   BLOCKCHAIN-BASED DYNAMIC CARBON CREDIT TOKENISATION SYSTEM     ║
    ║   Unified Orchestration and UI Launcher                          ║
    ║                                                                  ║
    ╚══════════════════════════════════════════════════════════════════╝
{RESET}""")

    # Import the singleton Phase 5 engine, which already bundles Phase 1–4
    from app.services.engine import engine

    # ────────────────────────────────────────────────────────────────
    # PHASE 1 & 2: Infrastructure & AI Models
    # ────────────────────────────────────────────────────────────────
    header("PHASE 1 & 2: DATA INFRASTRUCTURE & AI MODEL INITIALIZATION", color=YELLOW)
    info("Initializing core system components...")
    info("Executing Synthetic Data Generation (Phase 1)...")
    explain("Generating non-deterministic IoT sensor baselines across 30+ virtual facilities.")
    explain("Adding dynamic environmental noise and Kalman filtering to raw signals.")
    
    info("Loading & Training AI Engines (Phase 2)...")
    explain("Using synthetic data to train Random Forest Emission Estimators (Extracting Features -> Output CO2e).")
    explain("Training Isolation Forest Anomaly Detectors on 'normal' baseline conditions.")
    
    t_start = time.time()
    # This automatically trains models using dynamic data generation 
    # (as implemented in training.py) and caches system objects
    engine.initialize()
    duration = time.time() - t_start
    info(f"Phase 1 & 2 Completed Successfully (Took {duration:.2f}s). Models loaded in memory.")

    # ────────────────────────────────────────────────────────────────
    # PHASE 3: Data Processing & Inference Pipeline
    # ────────────────────────────────────────────────────────────────
    header("PHASE 3: PIPELINE PROCESSING & INFERENCE", color=MAGENTA)
    info("Feeding telemetry data into the pipeline...")
    explain("Synchronizing timestamps and pushing clean matrices into the Emission Estimator.")
    explain("Calculating Carbon Credits dynamically vs the generated physical baselines.")
    
    # Process some mock baseline telemetry readings dynamically via the engine
    import random
    facility_pool = ["FAC_001", "FAC_002", "FAC_003", "FAC_004"]
    for _ in range(50):
        dummy_reading = {
            "facility_id": random.choice(facility_pool),
            "facility_type": "power_generation" if random.random() > 0.5 else "chemical_manufacturing",
            "co2_ppm": random.uniform(390.0, 480.0),
            "ch4_ppm": random.uniform(1.0, 5.0),
            "nox_ppb": random.uniform(5.0, 30.0),
            "fuel_rate": random.uniform(80.0, 200.0),
            "energy_kwh": random.uniform(1000.0, 3500.0),
        }
        engine.process_reading(dummy_reading)
    info(f"Pipeline Processed 50 new telemetry samples dynamically.")

    # ────────────────────────────────────────────────────────────────
    # PHASE 4: Blockchain Tokenization & Smart Contracts
    # ────────────────────────────────────────────────────────────────
    header("PHASE 4: BLOCKCHAIN INTEGRATION", color=BLUE)
    info("Simulating Distributed Ledger Integrity...")
    explain("Hashing processed emission evaluations via SHA-256.")
    explain("Appending immutable block structures for verified credits.")
    explain("Executing Smart contract P2P Token matching (Credit Issuance).")
    
    # Force a mock Order entry to populate the UI order book
    engine.place_order({
        "participant_id": "FAC_001", "side": "sell", "quantity": 15.5, "price": 24.50
    })
    engine.place_order({
        "participant_id": "FAC_002", "side": "buy", "quantity": 10.0, "price": 25.00
    })
    
    bc_status = engine.get_blockchain_status()
    info(f"Ledger initialized. Chain verified: {bc_status['is_valid']}. Blocks: {bc_status['chain_length']}")


    # ────────────────────────────────────────────────────────────────
    # PHASE 5 & 6: Interface Orchestration & System Deployment
    # ────────────────────────────────────────────────────────────────
    header("PHASE 5 & 6: INTERFACE ORCHESTRATION & DEPLOYMENT", color=GREEN)
    info("System Orchestrated to Operational Status.")
    explain("Binding Phase 1->4 APIs dynamically to ASGI endpoint via FastAPI.")
    explain("Serving Frontend DOM via StaticFiles middleware.")
    
    import subprocess
    frontend_dir = os.path.join(DEMO_DIR, "phase5_deployment", "frontend")
    dist_dir = os.path.join(frontend_dir, "dist")
    if not os.path.exists(dist_dir) and os.path.exists(os.path.join(frontend_dir, "package.json")):
        info("Building frontend UI assets (Vite React)... This may take a minute.")
        try:
            subprocess.check_call("npm install", cwd=frontend_dir, shell=True)
            subprocess.check_call("npm run build", cwd=frontend_dir, shell=True)
            info("Frontend UI built successfully.")
        except Exception as e:
            print(f"  {RED}[ERROR] Failed to build frontend UI: {e}{RESET}")

    import uvicorn
    from app.main import app
    
    port = 8000
    host = "127.0.0.1"
    url = f"http://{host}:{port}"
    
    # Thread logic to automatically pop browser
    def open_browser():
        time.sleep(2)  # Give uvicorn a second to bind
        info(f"Opening User Dashboard Interface at {url}")
        webbrowser.open(url)
        
    threading.Thread(target=open_browser, daemon=True).start()

    # Streaming Metrics Output Thread (For Live Demo Presentation)
    try:
        from metrics import generate_predictions, format_dashboard_json
        import random
        
        def simulate_streaming_metrics():
            facility_pool = ["FAC_001", "FAC_002", "FAC_003", "FAC_004"]
            while True:
                time.sleep(15)  # Update metrics every 15 seconds
                dummy_reading = {
                    "facility_id": random.choice(facility_pool),
                    "facility_type": "chemical_manufacturing",
                    "co2_ppm": random.uniform(390.0, 480.0),
                    "ch4_ppm": random.uniform(1.0, 5.0),
                    "nox_ppb": random.uniform(5.0, 30.0),
                    "fuel_rate": random.uniform(80.0, 200.0),
                    "energy_kwh": random.uniform(1000.0, 3500.0),
                }
                # Pushing this through generate_predictions computes it via the engine
                generate_predictions(dummy_reading)
                
                print(f"\n{YELLOW}===[ LIVE METRICS STREAM - RUNTIME EXTRACTION ]==={RESET}")
                print(format_dashboard_json())
                print(f"{YELLOW}=================================================={RESET}\n")

        threading.Thread(target=simulate_streaming_metrics, daemon=True).start()
    except ImportError as e:
        pass

    info("Deploying ASGI Uvicorn Subprocess. Terminal intercepting local traffic...")
    print(f"\n{BOLD}[Ctrl+C to Terminate]{RESET}\n")
    
    # Run server locally. This blocks and acts as our deployment simulation.
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
