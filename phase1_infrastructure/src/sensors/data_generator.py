"""
Synthetic IoT Sensor Data Generator
====================================
Generates realistic industrial emission data for 50 facilities with:
  - Baseline ranges per facility type
  - Day/night and weekly temporal patterns
  - Inter-sensor correlations (fuel ↔ CO₂, energy ↔ NOₓ)
  - Gaussian noise
  - Anomaly injection (spikes, sensor faults, downtime)

Each call to `generate_reading()` returns one 15-second sample for
one facility.  The `FacilitySimulator` class maintains internal state
so readings have temporal continuity.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import numpy as np

from src.config import FACILITY_TYPES, SENSOR_BASELINES


# ── Anomaly configuration ────────────────────────────────────────────────
ANOMALY_SPIKE_PROB = 0.002        # 0.2 % chance per reading
SENSOR_FAULT_PROB = 0.001         # 0.1 % chance per reading
DOWNTIME_PROB = 0.0005            # 0.05 % chance per reading
DOWNTIME_DURATION_RANGE = (4, 48) # readings (1–12 minutes of downtime)


@dataclass
class SensorReading:
    """Single 15-second sample from one facility."""
    facility_id: str
    timestamp_utc: str
    co2_ppm: float
    ch4_ppm: float
    nox_ppb: float
    fuel_rate: float
    energy_kwh: float
    anomaly_flag: Optional[str] = None   # None | "spike" | "fault" | "downtime"

    def to_dict(self) -> dict:
        d = {
            "facility_id": self.facility_id,
            "timestamp_utc": self.timestamp_utc,
            "co2_ppm": round(self.co2_ppm, 2),
            "ch4_ppm": round(self.ch4_ppm, 4),
            "nox_ppb": round(self.nox_ppb, 2),
            "fuel_rate": round(self.fuel_rate, 2),
            "energy_kwh": round(self.energy_kwh, 2),
        }
        if self.anomaly_flag:
            d["anomaly_flag"] = self.anomaly_flag
        return d


class FacilitySimulator:
    """
    Stateful simulator for a single industrial facility.

    Maintains smooth temporal evolution by applying autoregressive drift
    on top of deterministic diurnal and weekly patterns.
    """

    def __init__(self, facility_index: int, rng_seed: Optional[int] = None):
        self.index = facility_index
        self.facility_id = f"FAC_{facility_index + 1:03d}"
        self.facility_type = FACILITY_TYPES[facility_index % len(FACILITY_TYPES)]
        self.baselines = SENSOR_BASELINES[self.facility_type]

        import time
        seed = rng_seed if rng_seed is not None else (time.time_ns() + facility_index) % (2**32)
        self.rng = np.random.default_rng(seed)

        # Autoregressive state for each sensor (starts at mid-range)
        self._state: dict[str, float] = {}
        for key, (lo, hi) in self.baselines.items():
            self._state[key] = (lo + hi) / 2.0

        # Downtime counter (>0 means facility is in simulated downtime)
        self._downtime_remaining: int = 0

        # Random phase offsets so facilities don't all peak at the same time
        self._phase_offset_hours = self.rng.uniform(0, 6)

    # ── Temporal modulation ──────────────────────────────────────────────

    @staticmethod
    def _diurnal_factor(hour: float) -> float:
        """
        Sinusoidal day/night cycle.
        Peak at ~14:00, trough at ~02:00.
        Returns a multiplier in [0.65, 1.15].
        """
        return 0.90 + 0.25 * math.sin((hour - 8) * math.pi / 12)

    @staticmethod
    def _weekly_factor(weekday: int) -> float:
        """
        Industrial weekly pattern:
        Mon–Fri = full operation, Sat = 70 %, Sun = 50 %.
        """
        if weekday < 5:
            return 1.0
        elif weekday == 5:
            return 0.70
        else:
            return 0.50

    # ── Core generation ──────────────────────────────────────────────────

    def generate_reading(self, current_time: datetime) -> SensorReading:
        """
        Produce one sensor reading for *current_time*.

        Algorithm
        ---------
        1. Compute temporal multiplier (diurnal × weekly).
        2. For each sensor, apply AR(1) drift toward the temporally-
           modulated baseline, then add Gaussian noise.
        3. Enforce inter-sensor correlations:
           fuel ↑  →  co2 ↑  (combustion equation)
           energy ↑ → nox ↑  (thermal NOₓ formation)
        4. With small probability, inject anomalies (spike / fault / downtime).
        """
        # ── Handle ongoing downtime ──────────────────────────────────────
        if self._downtime_remaining > 0:
            self._downtime_remaining -= 1
            return SensorReading(
                facility_id=self.facility_id,
                timestamp_utc=current_time.isoformat(),
                co2_ppm=0.0,
                ch4_ppm=0.0,
                nox_ppb=0.0,
                fuel_rate=0.0,
                energy_kwh=0.0,
                anomaly_flag="downtime",
            )

        # ── Temporal modulation ──────────────────────────────────────────
        hour = current_time.hour + current_time.minute / 60.0 + self._phase_offset_hours
        hour = hour % 24
        weekday = current_time.weekday()

        tempo = self._diurnal_factor(hour) * self._weekly_factor(weekday)

        # ── AR(1) drift with noise ───────────────────────────────────────
        alpha = 0.95  # autoregressive coefficient (high = smooth)
        values: dict[str, float] = {}

        for key, (lo, hi) in self.baselines.items():
            target = lo + (hi - lo) * tempo
            noise_scale = (hi - lo) * 0.03  # 3 % of range
            innovation = self.rng.normal(0, noise_scale)
            new_val = alpha * self._state[key] + (1 - alpha) * target + innovation
            new_val = max(lo * 0.5, min(hi * 1.5, new_val))  # soft clamp
            self._state[key] = new_val
            values[key] = new_val

        # ── Inter-sensor correlations ────────────────────────────────────
        fuel_lo, fuel_hi = self.baselines["fuel_rate"]
        fuel_norm = (values["fuel_rate"] - fuel_lo) / max(fuel_hi - fuel_lo, 1)

        co2_lo, co2_hi = self.baselines["co2_ppm"]
        values["co2_ppm"] += (co2_hi - co2_lo) * 0.3 * (fuel_norm - 0.5)

        energy_lo, energy_hi = self.baselines["energy_kwh"]
        energy_norm = (values["energy_kwh"] - energy_lo) / max(energy_hi - energy_lo, 1)

        nox_lo, nox_hi = self.baselines["nox_ppb"]
        values["nox_ppb"] += (nox_hi - nox_lo) * 0.25 * (energy_norm - 0.5)

        # ── Anomaly injection ────────────────────────────────────────────
        anomaly_flag = None
        roll = self.rng.random()

        if roll < ANOMALY_SPIKE_PROB:
            # Sudden emission spike: 2–5× overshoot on a random sensor
            spike_key = self.rng.choice(list(self.baselines.keys()))
            spike_mult = self.rng.uniform(2.0, 5.0)
            values[spike_key] *= spike_mult
            anomaly_flag = "spike"

        elif roll < ANOMALY_SPIKE_PROB + SENSOR_FAULT_PROB:
            # Sensor fault: one sensor reads a fixed impossible value
            fault_key = self.rng.choice(list(self.baselines.keys()))
            values[fault_key] = -999.0  # sentinel for "sensor fault"
            anomaly_flag = "fault"

        elif roll < ANOMALY_SPIKE_PROB + SENSOR_FAULT_PROB + DOWNTIME_PROB:
            # Facility downtime: all sensors read zero for N readings
            self._downtime_remaining = int(
                self.rng.integers(*DOWNTIME_DURATION_RANGE)
            )
            return SensorReading(
                facility_id=self.facility_id,
                timestamp_utc=current_time.isoformat(),
                co2_ppm=0.0,
                ch4_ppm=0.0,
                nox_ppb=0.0,
                fuel_rate=0.0,
                energy_kwh=0.0,
                anomaly_flag="downtime",
            )

        return SensorReading(
            facility_id=self.facility_id,
            timestamp_utc=current_time.isoformat(),
            co2_ppm=values["co2_ppm"],
            ch4_ppm=values["ch4_ppm"],
            nox_ppb=values["nox_ppb"],
            fuel_rate=values["fuel_rate"],
            energy_kwh=values["energy_kwh"],
            anomaly_flag=anomaly_flag,
        )


# ── Convenience factory ──────────────────────────────────────────────────

def create_all_simulators(num_facilities: int = 50) -> list[FacilitySimulator]:
    """Create simulator instances for all facilities."""
    return [FacilitySimulator(i) for i in range(num_facilities)]
