"""
Edge Gateway Processor
=======================
The central edge-device process that:

  1. Subscribes to MQTT topics  /facility/+/emissions
  2. Validates incoming sensor data
  3. Applies Kalman filtering per facility × per sensor
  4. Stores filtered readings in the local SQLite buffer
  5. Runs a background forwarder thread that drains the buffer
     and POSTs batches to the backend REST API
  6. Implements store-and-forward with exponential backoff on failure

Simulates the behaviour of a Raspberry Pi 4B / Jetson Nano edge gateway.
"""

from __future__ import annotations

import json
import logging
import signal
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
import paho.mqtt.client as mqtt

from src.config import (
    EDGE_FORWARD_INTERVAL_SEC,
    EDGE_FORWARD_URL,
    EDGE_MAX_RETRY,
    MQTT_BROKER_HOST,
    MQTT_BROKER_PORT,
    MQTT_QOS,
    NUM_FACILITIES,
)
from src.edge.kalman_filter import create_filters_for_facility
from src.edge.sqlite_buffer import SQLiteBuffer

logger = logging.getLogger("edge.gateway")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-18s  %(levelname)-7s  %(message)s",
)

# Graceful shutdown
_shutdown = threading.Event()


def _signal_handler(sig, frame):
    logger.info("Edge gateway shutting down …")
    _shutdown.set()


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


# ── Data validation ──────────────────────────────────────────────────────

VALID_RANGES = {
    "co2_ppm":    (0, 5000),
    "ch4_ppm":    (0, 100),
    "nox_ppb":    (0, 2000),
    "fuel_rate":  (0, 5000),
    "energy_kwh": (0, 100_000),
}


def validate_reading(data: dict) -> tuple[bool, Optional[str]]:
    """
    Returns (is_valid, rejection_reason).
    Checks required keys, types, and sane ranges.
    Readings with anomaly_flag == 'fault' (sensor fault sentinel -999)
    are marked as invalid.
    """
    required = ["facility_id", "timestamp_utc", "co2_ppm", "ch4_ppm",
                 "nox_ppb", "fuel_rate", "energy_kwh"]
    for key in required:
        if key not in data:
            return False, f"missing key: {key}"

    for sensor, (lo, hi) in VALID_RANGES.items():
        val = data.get(sensor)
        if val is None:
            return False, f"{sensor} is null"
        if not isinstance(val, (int, float)):
            return False, f"{sensor} not numeric"
        if val < lo or val > hi:
            return False, f"{sensor}={val} out of range [{lo}, {hi}]"

    return True, None


# ── Edge Gateway ─────────────────────────────────────────────────────────

class EdgeGateway:
    """MQTT subscriber → validation → Kalman → SQLite → REST forwarder."""

    def __init__(self):
        # Per-facility Kalman filter banks: { facility_id: {sensor: filter} }
        self._filters: dict[str, dict] = {}
        self._buffer = SQLiteBuffer()
        self._stats = {"received": 0, "valid": 0, "invalid": 0, "forwarded": 0}

    # ── MQTT callbacks ───────────────────────────────────────────────────

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            client.subscribe("/facility/+/emissions", qos=MQTT_QOS)
            logger.info("Edge subscribed to /facility/+/emissions")
        else:
            logger.error("Edge connect failed: %s", reason_code)

    def _on_message(self, client, userdata, msg):
        """Handle one incoming sensor reading."""
        self._stats["received"] += 1
        try:
            data = json.loads(msg.payload)
        except json.JSONDecodeError as exc:
            self._stats["invalid"] += 1
            logger.warning("Bad JSON on %s: %s", msg.topic, exc)
            return

        # ── Validate ─────────────────────────────────────────────────────
        ok, reason = validate_reading(data)
        if not ok:
            self._stats["invalid"] += 1
            if self._stats["invalid"] % 100 == 1:
                logger.debug("Invalid reading from %s: %s",
                             data.get("facility_id", "?"), reason)
            return

        self._stats["valid"] += 1
        fid = data["facility_id"]

        # ── Kalman filter ────────────────────────────────────────────────
        if fid not in self._filters:
            self._filters[fid] = create_filters_for_facility()

        filters = self._filters[fid]
        for sensor_key, kf in filters.items():
            data[sensor_key] = round(kf.update(data[sensor_key]), 4)

        # ── Temporal alignment (all readings snapped to 15-s grid) ──────
        try:
            ts = datetime.fromisoformat(data["timestamp_utc"])
            # Snap to nearest 15-second boundary
            seconds = ts.second
            snap = round(seconds / 15) * 15
            aligned = ts.replace(second=snap % 60, microsecond=0)
            if snap == 60:
                aligned = aligned.replace(second=0) + timedelta(minutes=1)
            data["timestamp_utc"] = aligned.isoformat()
        except (ValueError, KeyError):
            pass  # keep original if parsing fails

        # ── Buffer ───────────────────────────────────────────────────────
        self._buffer.enqueue(fid, data)

    # ── Forwarder (runs in background thread) ────────────────────────────

    def _forwarder_loop(self):
        """Drain the SQLite buffer and POST batches to the backend."""
        backoff = 1
        client = httpx.Client(timeout=10)

        while not _shutdown.is_set():
            batch = self._buffer.dequeue(batch_size=200)
            if not batch:
                _shutdown.wait(timeout=EDGE_FORWARD_INTERVAL_SEC)
                continue

            row_ids = [rid for rid, _ in batch]
            payloads = [payload for _, payload in batch]

            success = False
            for attempt in range(EDGE_MAX_RETRY):
                try:
                    resp = client.post(
                        EDGE_FORWARD_URL,
                        json={"readings": payloads},
                        headers={"Content-Type": "application/json"},
                    )
                    if resp.status_code in (200, 201, 202):
                        self._buffer.mark_forwarded(row_ids)
                        self._stats["forwarded"] += len(row_ids)
                        backoff = 1
                        success = True
                        break
                    else:
                        logger.warning(
                            "Backend returned %s (attempt %d/%d)",
                            resp.status_code, attempt + 1, EDGE_MAX_RETRY,
                        )
                except httpx.RequestError as exc:
                    logger.warning(
                        "Backend unreachable (attempt %d/%d): %s",
                        attempt + 1, EDGE_MAX_RETRY, exc,
                    )
                time.sleep(min(backoff, 60))
                backoff *= 2

            if not success:
                logger.error(
                    "Failed to forward batch of %d records — "
                    "will retry next cycle (store-and-forward).",
                    len(row_ids),
                )

            _shutdown.wait(timeout=EDGE_FORWARD_INTERVAL_SEC)

        client.close()
        logger.info(
            "Forwarder stopped. Stats: %s",
            json.dumps(self._stats),
        )

    # ── Start / stop ─────────────────────────────────────────────────────

    def start(self):
        """Launch MQTT subscriber and forwarder thread."""
        # MQTT client
        self._mqtt = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id="edge_gateway",
        )
        self._mqtt.on_connect = self._on_connect
        self._mqtt.on_message = self._on_message
        self._mqtt.reconnect_delay_set(min_delay=1, max_delay=30)

        try:
            self._mqtt.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=60)
        except Exception as exc:
            logger.error("Edge cannot connect to MQTT broker: %s", exc)
            raise

        self._mqtt.loop_start()

        # Forwarder thread
        self._forwarder_thread = threading.Thread(
            target=self._forwarder_loop, daemon=True, name="forwarder"
        )
        self._forwarder_thread.start()

        logger.info("Edge gateway running.")

        # Block until shutdown
        try:
            while not _shutdown.is_set():
                pending = self._buffer.pending_count()
                logger.info(
                    "Edge stats | recv=%d  valid=%d  invalid=%d  fwd=%d  pending=%d",
                    self._stats["received"],
                    self._stats["valid"],
                    self._stats["invalid"],
                    self._stats["forwarded"],
                    pending,
                )
                _shutdown.wait(timeout=30)
        except KeyboardInterrupt:
            _shutdown.set()

        self._mqtt.loop_stop()
        self._mqtt.disconnect()
        self._buffer.close()
        logger.info("Edge gateway stopped.")


if __name__ == "__main__":
    gw = EdgeGateway()
    gw.start()
