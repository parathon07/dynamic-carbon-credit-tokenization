"""
Centralised configuration loaded from environment variables.
All subsystems import settings from this module.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent   # phase1_infrastructure/
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# ── MQTT ─────────────────────────────────────────────────────────────────
MQTT_BROKER_HOST: str = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT: int = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_QOS: int = int(os.getenv("MQTT_QOS", "1"))

# ── PostgreSQL / TimescaleDB ─────────────────────────────────────────────
POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB: str = os.getenv("POSTGRES_DB", "carbon_emissions")
POSTGRES_USER: str = os.getenv("POSTGRES_USER", "carbon_admin")
POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "changeme_in_production")

DATABASE_URL: str = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)
ASYNC_DATABASE_URL: str = (
    f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# ── FastAPI ──────────────────────────────────────────────────────────────
BACKEND_HOST: str = os.getenv("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))

# ── Edge Gateway ─────────────────────────────────────────────────────────
EDGE_SQLITE_PATH: str = os.getenv("EDGE_SQLITE_PATH", str(DATA_DIR / "edge_buffer.db"))
EDGE_FORWARD_URL: str = os.getenv("EDGE_FORWARD_URL", "http://localhost:8000/api/v1/ingest")
EDGE_FORWARD_INTERVAL_SEC: int = int(os.getenv("EDGE_FORWARD_INTERVAL_SEC", "5"))
EDGE_MAX_RETRY: int = int(os.getenv("EDGE_MAX_RETRY", "5"))

# ── Simulation ───────────────────────────────────────────────────────────
NUM_FACILITIES: int = int(os.getenv("NUM_FACILITIES", "50"))
SAMPLING_INTERVAL_SEC: int = int(os.getenv("SAMPLING_INTERVAL_SEC", "15"))
SIMULATION_SPEED_MULTIPLIER: int = int(os.getenv("SIMULATION_SPEED_MULTIPLIER", "1"))

# ── Sensor Baseline Ranges (per facility type) ──────────────────────────
FACILITY_TYPES = [
    "chemical_manufacturing",
    "power_generation",
    "cement_production",
    "steel_manufacturing",
    "petroleum_refining",
]

SENSOR_BASELINES = {
    "chemical_manufacturing": {
        "co2_ppm": (380, 520),
        "ch4_ppm": (1.5, 4.0),
        "nox_ppb": (30, 80),
        "fuel_rate": (100, 250),
        "energy_kwh": (2000, 5000),
    },
    "power_generation": {
        "co2_ppm": (400, 650),
        "ch4_ppm": (1.0, 3.0),
        "nox_ppb": (40, 120),
        "fuel_rate": (200, 500),
        "energy_kwh": (5000, 12000),
    },
    "cement_production": {
        "co2_ppm": (450, 700),
        "ch4_ppm": (0.8, 2.5),
        "nox_ppb": (50, 100),
        "fuel_rate": (150, 400),
        "energy_kwh": (3000, 8000),
    },
    "steel_manufacturing": {
        "co2_ppm": (420, 680),
        "ch4_ppm": (1.2, 3.5),
        "nox_ppb": (35, 90),
        "fuel_rate": (180, 450),
        "energy_kwh": (4000, 10000),
    },
    "petroleum_refining": {
        "co2_ppm": (500, 800),
        "ch4_ppm": (2.0, 6.0),
        "nox_ppb": (60, 150),
        "fuel_rate": (300, 700),
        "energy_kwh": (6000, 15000),
    },
}
