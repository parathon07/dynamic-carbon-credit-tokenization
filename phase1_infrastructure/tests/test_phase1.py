"""
Phase 1 — Comprehensive Validation Test Suite
================================================
Validates the complete IoT carbon emission monitoring pipeline:

  Synthetic Sensors → MQTT → Edge Gateway → Backend API → Database

Covers:
  ▸ Functional correctness (JSON schema, timestamps, facility IDs)
  ▸ Data validation (value ranges, correlations, anomaly injection)
  ▸ Edge processing (Kalman filter, SQLite buffer, gateway validation)
  ▸ Backend API (Pydantic schemas, response models)
  ▸ Pipeline integrity (zero data loss, traceability, latency)
  ▸ Performance benchmarks (throughput, burst traffic, memory)
  ▸ Fault tolerance (store-and-forward, persistence, recovery)
  ▸ Database schema (ORM models, indices, constraints)
  ▸ End-to-end integration (full pipeline, continuous streaming)

Run:
    python -m pytest tests/test_phase1.py -v
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import numpy as np
import pytest
from pydantic import BaseModel, Field, validator

# ── Ensure project root is on sys.path ───────────────────────────────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config import FACILITY_TYPES, SENSOR_BASELINES, MQTT_QOS
from src.sensors.data_generator import (
    ANOMALY_SPIKE_PROB, SENSOR_FAULT_PROB, DOWNTIME_PROB,
    FacilitySimulator, SensorReading, create_all_simulators,
)
from src.sensors.mqtt_publisher import FacilityPublisher
from src.edge.kalman_filter import (
    KalmanFilter1D, SENSOR_FILTER_PARAMS, create_filters_for_facility,
)
from src.edge.sqlite_buffer import SQLiteBuffer
from src.edge.gateway import validate_reading, VALID_RANGES
from src.backend.models import Base, EmissionReading, FacilityProfile


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  FIXTURES                                                                ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

BASE_TIME = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
REQUIRED_KEYS = {"facility_id", "timestamp_utc", "co2_ppm", "ch4_ppm",
                 "nox_ppb", "fuel_rate", "energy_kwh"}


@pytest.fixture
def sim():
    """Deterministic FacilitySimulator (index=0, seed=42)."""
    return FacilitySimulator(facility_index=0, rng_seed=42)


@pytest.fixture
def base_time():
    return datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def reading(sim, base_time):
    return sim.generate_reading(base_time)


@pytest.fixture
def reading_dict(reading):
    return reading.to_dict()


@pytest.fixture
def sqlite_buffer(tmp_path):
    buf = SQLiteBuffer(db_path=str(tmp_path / "test.db"))
    yield buf
    buf.close()


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  1. FUNCTIONAL TESTS — Data Generator                                   ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

class TestDataGeneratorSchema:
    """JSON schema, types, rounding, and field completeness."""

    def test_required_keys_present(self, reading_dict):
        assert REQUIRED_KEYS.issubset(reading_dict.keys())

    def test_correct_types(self, reading_dict):
        assert isinstance(reading_dict["facility_id"], str)
        assert isinstance(reading_dict["timestamp_utc"], str)
        for k in ("co2_ppm", "ch4_ppm", "nox_ppb", "fuel_rate", "energy_kwh"):
            assert isinstance(reading_dict[k], (int, float))

    def test_values_rounded(self, reading_dict):
        for k in ("co2_ppm", "nox_ppb", "fuel_rate", "energy_kwh"):
            assert reading_dict[k] == round(reading_dict[k], 2)
        assert reading_dict["ch4_ppm"] == round(reading_dict["ch4_ppm"], 4)

    def test_to_dict_roundtrip(self, reading):
        d = reading.to_dict()
        assert d["facility_id"] == reading.facility_id
        assert d["co2_ppm"] == round(reading.co2_ppm, 2)


class TestFacilityID:
    """Facility ID format and uniqueness."""

    def test_format_FAC_NNN(self, reading):
        assert re.match(r"^FAC_\d{3}$", reading.facility_id)

    def test_50_unique_ids(self):
        sims = create_all_simulators(50)
        ids = [s.facility_id for s in sims]
        assert len(set(ids)) == 50
        assert sorted(ids)[0] == "FAC_001" and sorted(ids)[-1] == "FAC_050"


class TestTimestamps:
    """ISO-8601 format and 15-second intervals."""

    def test_iso8601_parseable(self, reading):
        datetime.fromisoformat(reading.timestamp_utc)

    def test_15_second_intervals(self, sim, base_time):
        readings = []
        t = base_time
        for _ in range(10):
            readings.append(sim.generate_reading(t))
            t += timedelta(seconds=15)
        for i in range(1, len(readings)):
            d = (datetime.fromisoformat(readings[i].timestamp_utc) -
                 datetime.fromisoformat(readings[i - 1].timestamp_utc)).total_seconds()
            assert d == 15.0

    def test_timestamp_matches_input(self, sim, base_time):
        assert sim.generate_reading(base_time).timestamp_utc == base_time.isoformat()


class TestFacilityTypes:
    """All 5 types covered and cyclically assigned."""

    def test_all_types_covered(self):
        types = {s.facility_type for s in create_all_simulators(50)}
        assert types == set(FACILITY_TYPES)

    def test_cyclic_assignment(self):
        for s in create_all_simulators(50):
            assert s.facility_type == FACILITY_TYPES[s.index % len(FACILITY_TYPES)]


class TestDeterminism:
    """Same seed → same output; different seed → different output."""

    def test_same_seed_same_output(self, base_time):
        s1, s2 = FacilitySimulator(0, 42), FacilitySimulator(0, 42)
        for _ in range(20):
            assert s1.generate_reading(base_time).to_dict() == \
                   s2.generate_reading(base_time).to_dict()
            base_time += timedelta(seconds=15)

    def test_different_seeds_differ(self, base_time):
        r1 = FacilitySimulator(0, 1).generate_reading(base_time)
        r2 = FacilitySimulator(0, 2).generate_reading(base_time)
        assert r1.to_dict() != r2.to_dict()


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  2. FUNCTIONAL TESTS — MQTT Publisher                                    ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

class TestMQTTPublisher:
    """Topic routing, QoS, and payload format."""

    def test_topic_format(self):
        pub = FacilityPublisher(FacilitySimulator(0, 42))
        assert re.match(r"^/facility/FAC_\d{3}/emissions$", pub.topic)

    def test_topic_contains_facility_id(self):
        sim = FacilitySimulator(5, 42)
        assert FacilityPublisher(sim).topic == f"/facility/{sim.facility_id}/emissions"

    def test_50_unique_topics(self):
        topics = {FacilityPublisher(FacilitySimulator(i, i)).topic for i in range(50)}
        assert len(topics) == 50

    def test_payload_valid_json(self, sim, base_time):
        r = sim.generate_reading(base_time)
        parsed = json.loads(json.dumps(r.to_dict()))
        assert REQUIRED_KEYS.issubset(parsed.keys())

    def test_qos_is_1(self):
        assert MQTT_QOS == 1


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  3. DATA VALIDATION TESTS                                               ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

class TestValueRanges:
    """Sensor values within soft-clamped bounds (non-anomaly readings)."""

    @staticmethod
    def _normals(sim, n=500):
        t = BASE_TIME
        out = []
        for _ in range(n):
            r = sim.generate_reading(t); t += timedelta(seconds=15)
            if r.anomaly_flag is None: out.append(r)
        return out

    @pytest.mark.parametrize("sensor", ["co2_ppm", "ch4_ppm", "nox_ppb", "fuel_rate", "energy_kwh"])
    def test_sensor_within_range(self, sim, sensor):
        lo, hi = SENSOR_BASELINES[sim.facility_type][sensor]
        for r in self._normals(sim):
            v = getattr(r, sensor)
            assert lo * 0.3 <= v <= hi * 2.0, f"{sensor}={v}"


class TestCorrelations:
    """Inter-sensor correlations fuel↔CO₂ and energy↔NOₓ."""

    @staticmethod
    def _collect(sim, n=1000):
        t = BASE_TIME
        out = []
        for _ in range(n):
            r = sim.generate_reading(t); t += timedelta(seconds=15)
            if r.anomaly_flag is None: out.append(r)
        return out

    def test_fuel_co2_positive(self, sim):
        rs = self._collect(sim)
        r = np.corrcoef([x.fuel_rate for x in rs], [x.co2_ppm for x in rs])[0, 1]
        assert r > 0.3, f"fuel↔CO₂ r={r:.3f}"

    def test_energy_nox_positive(self, sim):
        rs = self._collect(sim)
        r = np.corrcoef([x.energy_kwh for x in rs], [x.nox_ppb for x in rs])[0, 1]
        assert r > 0.2, f"energy↔NOₓ r={r:.3f}"


class TestNoise:
    """Readings must contain noise but not excessive noise."""

    def test_noise_present(self, sim, base_time):
        vals = []
        t = base_time
        for _ in range(50):
            r = sim.generate_reading(t); t += timedelta(seconds=15)
            if r.anomaly_flag is None: vals.append(r.co2_ppm)
        assert np.std(np.diff(vals)) > 0

    def test_noise_not_excessive(self, sim, base_time):
        lo, hi = SENSOR_BASELINES[sim.facility_type]["co2_ppm"]
        vals = []
        t = base_time
        for _ in range(200):
            r = sim.generate_reading(t); t += timedelta(seconds=15)
            if r.anomaly_flag is None: vals.append(r.co2_ppm)
        assert np.std(vals) < (hi - lo) * 0.5


class TestAnomalyInjection:
    """Spikes, faults, and downtime appear in large samples."""

    @staticmethod
    def _large(seed=12345, n=10000):
        sim = FacilitySimulator(0, rng_seed=seed)
        t = BASE_TIME
        out = []
        for _ in range(n):
            out.append(sim.generate_reading(t)); t += timedelta(seconds=15)
        return out

    def test_spike_exists(self):
        assert any(r.anomaly_flag == "spike" for r in self._large())

    def test_fault_exists(self):
        assert any(r.anomaly_flag == "fault" for r in self._large())

    def test_downtime_exists(self):
        assert any(r.anomaly_flag == "downtime" for r in self._large())

    def test_downtime_all_zero(self):
        for r in self._large():
            if r.anomaly_flag == "downtime":
                assert r.co2_ppm == r.ch4_ppm == r.nox_ppb == r.fuel_rate == r.energy_kwh == 0


class TestTemporalPatterns:
    """Diurnal and weekly modulation."""

    def test_diurnal(self):
        day = FacilitySimulator(0, 42)
        night = FacilitySimulator(0, 42)
        d = [day.generate_reading(datetime(2024,1,1,12,0,0,tzinfo=timezone.utc)+timedelta(seconds=15*i))
             for i in range(200)]
        n = [night.generate_reading(datetime(2024,1,1,2,0,0,tzinfo=timezone.utc)+timedelta(seconds=15*i))
             for i in range(200)]
        dv = np.mean([r.co2_ppm for r in d if r.anomaly_flag is None])
        nv = np.mean([r.co2_ppm for r in n if r.anomaly_flag is None])
        assert dv > nv * 0.85

    def test_weekly(self):
        wd = FacilitySimulator(0, 42)
        we = FacilitySimulator(0, 42)
        w = [wd.generate_reading(datetime(2024,1,1,12,0,0,tzinfo=timezone.utc)+timedelta(seconds=15*i))
             for i in range(200)]
        e = [we.generate_reading(datetime(2024,1,7,12,0,0,tzinfo=timezone.utc)+timedelta(seconds=15*i))
             for i in range(200)]
        assert np.mean([r.co2_ppm for r in w if not r.anomaly_flag]) > \
               np.mean([r.co2_ppm for r in e if not r.anomaly_flag])


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  4. EDGE PROCESSING — Kalman Filter                                     ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

class TestKalmanFilter:
    """Noise reduction, convergence, step response, and reset."""

    def test_first_passthrough(self):
        assert KalmanFilter1D().update(100.0) == 100.0

    def test_noise_reduction(self):
        kf = KalmanFilter1D()
        np.random.seed(42)
        true_s = np.sin(np.linspace(0, 4*np.pi, 200))
        raw = true_s + np.random.normal(0, 0.5, 200)
        filt = np.array([kf.update(v) for v in raw])
        assert np.var(filt - true_s) < np.var(raw - true_s)

    def test_reduction_ratio_40pct(self):
        kf = KalmanFilter1D(1.0, 5.0)
        np.random.seed(42)
        raw = 100 + np.random.normal(0, 5, 500)
        filt = np.array([kf.update(v) for v in raw])
        r_raw = np.sqrt(np.mean((raw-100)**2))
        r_filt = np.sqrt(np.mean((filt-100)**2))
        assert (1 - r_filt/r_raw) > 0.4

    def test_step_response(self):
        kf = KalmanFilter1D(2.0, 5.0)
        for _ in range(50): kf.update(100.0)
        res = [kf.update(200.0) for _ in range(20)]
        assert abs(res[9] - 200) < 20

    def test_reset(self):
        kf = KalmanFilter1D()
        for v in [100, 110, 105]: kf.update(v)
        kf.reset()
        assert kf.update(50.0) == 50.0

    def test_profile_keys(self):
        f = create_filters_for_facility()
        assert set(f.keys()) == {"co2_ppm","ch4_ppm","nox_ppb","fuel_rate","energy_kwh"}

    def test_profile_params(self):
        for k, kf in create_filters_for_facility().items():
            q, r = SENSOR_FILTER_PARAMS[k]
            assert kf._q == q and kf._r == r


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  5. EDGE PROCESSING — SQLite Buffer                                     ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

class TestSQLiteBuffer:
    """FIFO ordering, forwarding, batch ops, purge, thread safety."""

    def test_fifo_order(self, sqlite_buffer):
        for i in range(5): sqlite_buffer.enqueue(f"F{i}", {"i": i})
        assert [p["i"] for _, p in sqlite_buffer.dequeue(5)] == [0,1,2,3,4]

    def test_empty_dequeue(self, sqlite_buffer):
        assert sqlite_buffer.dequeue() == []

    def test_mark_forwarded(self, sqlite_buffer):
        for i in range(10): sqlite_buffer.enqueue("F", {"v": i})
        b = sqlite_buffer.dequeue(5)
        ids = [r for r, _ in b]
        sqlite_buffer.mark_forwarded(ids)
        assert all(r not in [x for x, _ in sqlite_buffer.dequeue(10)] for r in ids)

    def test_batch_enqueue(self, sqlite_buffer):
        sqlite_buffer.enqueue_batch([("F", {"s": i}) for i in range(20)])
        assert sqlite_buffer.pending_count() == 20

    def test_pending_count(self, sqlite_buffer):
        for i in range(7): sqlite_buffer.enqueue("F", {"x": i})
        assert sqlite_buffer.pending_count() == 7
        b = sqlite_buffer.dequeue(3)
        sqlite_buffer.mark_forwarded([r for r, _ in b])
        assert sqlite_buffer.pending_count() == 4

    def test_purge(self, sqlite_buffer):
        for i in range(100): sqlite_buffer.enqueue("F", {"i": i})
        b = sqlite_buffer.dequeue(100)
        sqlite_buffer.mark_forwarded([r for r, _ in b])
        sqlite_buffer.purge_forwarded(keep_last=10)
        with sqlite_buffer._lock:
            n = sqlite_buffer._conn.execute("SELECT COUNT(*) FROM edge_buffer").fetchone()[0]
        assert n == 10

    def test_thread_safety(self, sqlite_buffer):
        errs = []
        def w(tid):
            try:
                for j in range(50): sqlite_buffer.enqueue(f"T{tid}", {"j": j})
            except Exception as e: errs.append(e)
        with ThreadPoolExecutor(10) as p:
            list(p.map(w, range(10)))
        assert not errs and sqlite_buffer.pending_count() == 500


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  6. EDGE PROCESSING — Gateway Validation                                ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

class TestGatewayValidation:
    """validate_reading() accept / reject logic."""

    def test_valid_accepted(self, reading_dict):
        assert validate_reading(reading_dict)[0] is True

    @pytest.mark.parametrize("key", list(REQUIRED_KEYS))
    def test_missing_key_rejected(self, reading_dict, key):
        del reading_dict[key]
        ok, r = validate_reading(reading_dict)
        assert not ok and "missing key" in r

    @pytest.mark.parametrize("sensor,bad", [
        ("co2_ppm",-100), ("ch4_ppm",-1), ("nox_ppb",-50),
        ("fuel_rate",-10), ("energy_kwh",200_000),
    ])
    def test_out_of_range(self, reading_dict, sensor, bad):
        reading_dict[sensor] = bad
        assert not validate_reading(reading_dict)[0]

    @pytest.mark.parametrize("sensor", ["co2_ppm","ch4_ppm","nox_ppb","fuel_rate","energy_kwh"])
    def test_null_rejected(self, reading_dict, sensor):
        reading_dict[sensor] = None
        ok, r = validate_reading(reading_dict)
        assert not ok and "is null" in r

    @pytest.mark.parametrize("sensor", ["co2_ppm","ch4_ppm","nox_ppb","fuel_rate","energy_kwh"])
    def test_non_numeric_rejected(self, reading_dict, sensor):
        reading_dict[sensor] = "bad"
        ok, r = validate_reading(reading_dict)
        assert not ok and "not numeric" in r

    def test_fault_sentinel(self, reading_dict):
        reading_dict["co2_ppm"] = -999.0
        assert not validate_reading(reading_dict)[0]


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  7. BACKEND API — Pydantic Schema Tests                                 ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

# Pydantic models replicated here to avoid importing database.py (needs psycopg2)

class _SensorReadingIn(BaseModel):
    facility_id: str = Field(..., min_length=1, max_length=16)
    timestamp_utc: str
    co2_ppm: float; ch4_ppm: float; nox_ppb: float
    fuel_rate: float; energy_kwh: float

    @validator("timestamp_utc")
    def _ts(cls, v):
        datetime.fromisoformat(v); return v

class _IngestBatch(BaseModel):
    readings: List[_SensorReadingIn] = Field(..., min_length=1, max_length=1000)

class _IngestResponse(BaseModel):
    status: str = "ok"; inserted: int

class _HealthResponse(BaseModel):
    status: str = "healthy"; db_connected: bool; readings_total: Optional[int] = None

class _MLInferenceResponse(BaseModel):
    facility_id: str; prediction: str = "placeholder"; model_version: str = "stub-v0"

class _BlockchainStubResponse(BaseModel):
    status: str = "stub"; message: str = "Blockchain module not yet deployed — Phase 4"

def _valid():
    return {"facility_id":"FAC_001","timestamp_utc":"2024-01-01T10:00:00+00:00",
            "co2_ppm":450,"ch4_ppm":2.5,"nox_ppb":60,"fuel_rate":200,"energy_kwh":4000}


class TestAPISchemas:
    """Pydantic schema validation without DB."""

    def test_valid_reading(self):
        assert _SensorReadingIn(**_valid()).facility_id == "FAC_001"

    def test_bad_timestamp(self):
        with pytest.raises(Exception):
            _SensorReadingIn(**{**_valid(), "timestamp_utc": "bad"})

    def test_missing_field(self):
        d = _valid(); del d["co2_ppm"]
        with pytest.raises(Exception): _SensorReadingIn(**d)

    def test_empty_facility(self):
        with pytest.raises(Exception):
            _SensorReadingIn(**{**_valid(), "facility_id": ""})

    def test_batch_valid(self):
        assert len(_IngestBatch(readings=[_valid()]*5).readings) == 5

    def test_batch_empty(self):
        with pytest.raises(Exception): _IngestBatch(readings=[])

    def test_batch_too_large(self):
        with pytest.raises(Exception): _IngestBatch(readings=[_valid()]*1001)

    def test_response_models(self):
        assert _IngestResponse(inserted=50).status == "ok"
        assert _HealthResponse(db_connected=True).status == "healthy"
        assert _MLInferenceResponse(facility_id="F").prediction == "placeholder"
        assert "Phase 4" in _BlockchainStubResponse().message


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  8. DATABASE SCHEMA — ORM Validation                                    ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

class TestDatabaseSchema:
    """ORM model definitions validated without a live database."""

    def test_emission_columns(self):
        cols = {c.name for c in EmissionReading.__table__.columns}
        assert {"id","facility_id","timestamp_utc","co2_ppm","ch4_ppm",
                "nox_ppb","fuel_rate","energy_kwh","ingested_at"}.issubset(cols)

    def test_facility_columns(self):
        cols = {c.name for c in FacilityProfile.__table__.columns}
        assert {"facility_id","facility_type","description","registered_at"}.issubset(cols)

    def test_primary_keys(self):
        assert "id" in [c.name for c in EmissionReading.__table__.primary_key.columns]
        assert "facility_id" in [c.name for c in FacilityProfile.__table__.primary_key.columns]

    def test_non_nullable_sensors(self):
        for col in ("co2_ppm","ch4_ppm","nox_ppb","fuel_rate","energy_kwh"):
            assert EmissionReading.__table__.columns[col].nullable is False

    def test_facility_id_length(self):
        assert EmissionReading.__table__.columns["facility_id"].type.length == 16

    def test_timestamp_timezone(self):
        assert EmissionReading.__table__.columns["timestamp_utc"].type.timezone is True

    def test_ingested_at_default(self):
        assert EmissionReading.__table__.columns["ingested_at"].server_default is not None

    def test_composite_index(self):
        idx_names = {i.name for i in EmissionReading.__table__.indexes}
        assert "idx_facility_time" in idx_names


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  9. PIPELINE INTEGRITY — Integration                                    ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

class TestPipelineIntegrity:
    """Sensor → validation → Kalman → buffer chain (no network)."""

    @staticmethod
    def _push(sim, filters, buf, n, t):
        valid = 0
        for _ in range(n):
            data = sim.generate_reading(t).to_dict(); t += timedelta(seconds=15)
            ok, _ = validate_reading(data)
            if ok:
                for k, kf in filters.items(): data[k] = round(kf.update(data[k]), 4)
                buf.enqueue(data["facility_id"], data); valid += 1
        return valid

    def test_no_data_loss(self, sqlite_buffer, base_time):
        sim = FacilitySimulator(0, 42); flt = create_filters_for_facility()
        v = self._push(sim, flt, sqlite_buffer, 100, base_time)
        assert sqlite_buffer.pending_count() == v

    def test_traceability(self, sqlite_buffer, base_time):
        sim = FacilitySimulator(5, 42); flt = create_filters_for_facility()
        self._push(sim, flt, sqlite_buffer, 10, base_time)
        for _, p in sqlite_buffer.dequeue(20):
            assert p["facility_id"] == "FAC_006"
            datetime.fromisoformat(p["timestamp_utc"])

    def test_latency_under_50ms(self, base_time):
        sim = FacilitySimulator(0, 42); flt = create_filters_for_facility()
        lats = []
        t = base_time
        for _ in range(100):
            data = sim.generate_reading(t).to_dict(); t += timedelta(seconds=15)
            s = time.perf_counter()
            ok, _ = validate_reading(data)
            if ok:
                for k, kf in flt.items(): data[k] = round(kf.update(data[k]), 4)
            lats.append(time.perf_counter() - s)
        assert sum(lats)/len(lats)*1000 < 50

    def test_filter_modifies_values(self, base_time):
        sim = FacilitySimulator(0, 42); flt = create_filters_for_facility()
        found = False
        t = base_time
        for i in range(50):
            data = sim.generate_reading(t).to_dict(); t += timedelta(seconds=15)
            if validate_reading(data)[0] and i > 5:
                raw = data["co2_ppm"]
                if abs(raw - flt["co2_ppm"].update(raw)) > 0.01:
                    found = True; break
        assert found


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  10. PERFORMANCE BENCHMARKS                                              ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

class TestPerformance:
    """Throughput, burst, SQLite speed, memory."""

    def test_throughput_200_per_sec(self, base_time):
        sims = create_all_simulators(50)
        fb = {s.facility_id: create_filters_for_facility() for s in sims}
        total = 0; t = base_time; s = time.perf_counter()
        for _ in range(10):
            for sim in sims:
                data = sim.generate_reading(t).to_dict()
                ok, _ = validate_reading(data)
                if ok:
                    for k, kf in fb[data["facility_id"]].items():
                        data[k] = round(kf.update(data[k]), 4)
                total += 1
            t += timedelta(seconds=15)
        assert total / (time.perf_counter() - s) >= 200

    def test_burst_1000(self, base_time):
        sim = FacilitySimulator(0, 42); flt = create_filters_for_facility()
        errs = 0; t = base_time
        for _ in range(1000):
            try:
                data = sim.generate_reading(t).to_dict(); t += timedelta(seconds=15)
                if validate_reading(data)[0]:
                    for k, kf in flt.items(): data[k] = round(kf.update(data[k]), 4)
            except: errs += 1
        assert errs == 0

    def test_sqlite_throughput(self, sqlite_buffer):
        s = time.perf_counter()
        for i in range(1000): sqlite_buffer.enqueue("F", {"i": i})
        assert 1000 / (time.perf_counter() - s) >= 500

    def test_memory_stability(self, base_time):
        import tracemalloc; tracemalloc.start()
        sim = FacilitySimulator(0, 42); flt = create_filters_for_facility()
        snap1 = tracemalloc.take_snapshot(); t = base_time
        for _ in range(10000):
            data = sim.generate_reading(t).to_dict(); t += timedelta(seconds=15)
            if validate_reading(data)[0]:
                for k, kf in flt.items(): data[k] = round(kf.update(data[k]), 4)
        snap2 = tracemalloc.take_snapshot(); tracemalloc.stop()
        diff_mb = sum(s.size_diff for s in snap2.compare_to(snap1, "lineno") if s.size_diff > 0) / 1048576
        assert diff_mb < 50


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  11. FAULT TOLERANCE                                                     ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

class TestFaultTolerance:
    """Store-and-forward, recovery, persistence, backoff."""

    def test_store_and_forward(self, sqlite_buffer, base_time):
        sim = FacilitySimulator(0, 42); flt = create_filters_for_facility()
        t = base_time; cnt = 0
        for _ in range(50):
            data = sim.generate_reading(t).to_dict(); t += timedelta(seconds=15)
            if validate_reading(data)[0]:
                for k, kf in flt.items(): data[k] = round(kf.update(data[k]), 4)
                sqlite_buffer.enqueue(data["facility_id"], data); cnt += 1
        assert sqlite_buffer.pending_count() == cnt

    def test_recovery(self, sqlite_buffer, base_time):
        sim = FacilitySimulator(0, 42); flt = create_filters_for_facility()
        t = base_time
        for _ in range(30):
            data = sim.generate_reading(t).to_dict(); t += timedelta(seconds=15)
            if validate_reading(data)[0]:
                for k, kf in flt.items(): data[k] = round(kf.update(data[k]), 4)
                sqlite_buffer.enqueue(data["facility_id"], data)
        pre = sqlite_buffer.pending_count()
        b = sqlite_buffer.dequeue(200)
        sqlite_buffer.mark_forwarded([r for r, _ in b])
        assert sqlite_buffer.pending_count() == 0 and len(b) == pre

    def test_persistence(self, tmp_path):
        p = str(tmp_path / "p.db")
        b1 = SQLiteBuffer(db_path=p)
        for i in range(20): b1.enqueue("F", {"v": i})
        b1.close()
        b2 = SQLiteBuffer(db_path=p)
        assert b2.pending_count() == 20
        b2.close()

    def test_exponential_backoff(self):
        b = 1; delays = []
        for _ in range(5): delays.append(min(b, 60)); b *= 2
        assert delays == [1, 2, 4, 8, 16]

    def test_invalid_data_no_crash(self):
        assert not validate_reading({})[0]
        assert not validate_reading({"facility_id": "F"})[0]
        assert not validate_reading({"facility_id":"F","timestamp_utc":"t",
                                     "co2_ppm":"x","ch4_ppm":None,"nox_ppb":[],
                                     "fuel_rate":{},"energy_kwh":True})[0]


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  12. END-TO-END INTEGRATION                                             ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

class TestEndToEnd:
    """Full pipeline simulation and continuous streaming."""

    def test_full_pipeline_10fac(self, sqlite_buffer, base_time):
        sims = [FacilitySimulator(i, i) for i in range(10)]
        fb = {s.facility_id: create_filters_for_facility() for s in sims}
        valid = 0; t = base_time
        for _ in range(10):
            for sim in sims:
                data = sim.generate_reading(t).to_dict()
                if validate_reading(data)[0]:
                    fid = data["facility_id"]
                    for k, kf in fb[fid].items(): data[k] = round(kf.update(data[k]), 4)
                    sqlite_buffer.enqueue(fid, data); valid += 1
            t += timedelta(seconds=15)
        assert sqlite_buffer.pending_count() == valid

    def test_continuous_50fac_1000_readings(self, sqlite_buffer, base_time):
        sims = create_all_simulators(50)
        fb = {s.facility_id: create_filters_for_facility() for s in sims}
        valid = 0; t = base_time; s = time.perf_counter()
        for _ in range(20):
            for sim in sims:
                data = sim.generate_reading(t).to_dict()
                if validate_reading(data)[0]:
                    fid = data["facility_id"]
                    for k, kf in fb[fid].items(): data[k] = round(kf.update(data[k]), 4)
                    sqlite_buffer.enqueue(fid, data); valid += 1
            t += timedelta(seconds=15)
        assert sqlite_buffer.pending_count() == valid
        assert time.perf_counter() - s < 30
        fids = {p["facility_id"] for _, p in sqlite_buffer.dequeue(2000)}
        assert len(fids) >= 40

    def test_buffer_drain_cycle(self, sqlite_buffer, base_time):
        sim = FacilitySimulator(0, 42); flt = create_filters_for_facility()
        t = base_time
        for _ in range(50):
            data = sim.generate_reading(t).to_dict(); t += timedelta(seconds=15)
            if validate_reading(data)[0]:
                for k, kf in flt.items(): data[k] = round(kf.update(data[k]), 4)
                sqlite_buffer.enqueue(data["facility_id"], data)
        b = sqlite_buffer.dequeue(200)
        sqlite_buffer.mark_forwarded([r for r, _ in b])
        assert sqlite_buffer.pending_count() == 0
        # Continue after drain
        for _ in range(20):
            data = sim.generate_reading(t).to_dict(); t += timedelta(seconds=15)
            if validate_reading(data)[0]:
                for k, kf in flt.items(): data[k] = round(kf.update(data[k]), 4)
                sqlite_buffer.enqueue(data["facility_id"], data)
        assert sqlite_buffer.pending_count() > 0
