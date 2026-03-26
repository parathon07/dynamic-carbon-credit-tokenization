"""
MQTT Publisher — Simulated IoT Sensor Network
===============================================
Multi-threaded publisher that streams synthetic sensor data from
50 facilities to an MQTT broker, each on its own topic:

    /facility/{facility_id}/emissions

Each facility runs in its own thread, publishing one JSON reading
every 15 seconds (configurable via SAMPLING_INTERVAL_SEC).
Supports a speed multiplier for accelerated simulation.
"""

from __future__ import annotations

import json
import logging
import signal
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import paho.mqtt.client as mqtt

from src.config import (
    MQTT_BROKER_HOST,
    MQTT_BROKER_PORT,
    MQTT_QOS,
    NUM_FACILITIES,
    SAMPLING_INTERVAL_SEC,
    SIMULATION_SPEED_MULTIPLIER,
)
from src.sensors.data_generator import FacilitySimulator, create_all_simulators

logger = logging.getLogger("mqtt_publisher")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-18s  %(levelname)-7s  %(message)s",
)

# ── Graceful shutdown ────────────────────────────────────────────────────
_shutdown_event = threading.Event()


def _signal_handler(sig, frame):
    logger.info("Shutdown signal received — stopping all publishers …")
    _shutdown_event.set()


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


# ── MQTT Client Factory ─────────────────────────────────────────────────

def _create_mqtt_client(client_id: str) -> mqtt.Client:
    """Create a configured MQTT client with reconnect logic."""
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=client_id,
        protocol=mqtt.MQTTv311,
    )

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            logger.info("MQTT client '%s' connected to %s:%s",
                        client_id, MQTT_BROKER_HOST, MQTT_BROKER_PORT)
        else:
            logger.error("MQTT connect failed for '%s': %s", client_id, reason_code)

    def on_disconnect(client, userdata, flags, reason_code, properties):
        logger.warning("MQTT client '%s' disconnected (rc=%s)", client_id, reason_code)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.reconnect_delay_set(min_delay=1, max_delay=30)

    return client


# ── Per-facility publisher thread ────────────────────────────────────────

class FacilityPublisher(threading.Thread):
    """
    Daemon thread that:
      1. Connects to MQTT broker
      2. In a loop, generates one sensor reading via FacilitySimulator
      3. Publishes JSON payload to  /facility/{id}/emissions
      4. Sleeps for the configured interval (scaled by speed multiplier)
    """

    def __init__(
        self,
        simulator: FacilitySimulator,
        start_time: Optional[datetime] = None,
    ):
        super().__init__(daemon=True)
        self.sim = simulator
        self.name = f"pub-{simulator.facility_id}"
        self.topic = f"/facility/{simulator.facility_id}/emissions"
        self.current_time = start_time or datetime.now(timezone.utc)
        self._client: Optional[mqtt.Client] = None

    def run(self):
        self._client = _create_mqtt_client(f"pub_{self.sim.facility_id}")

        try:
            self._client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=60)
        except Exception as exc:
            logger.error("Could not connect '%s': %s", self.sim.facility_id, exc)
            return

        self._client.loop_start()

        interval = SAMPLING_INTERVAL_SEC / max(SIMULATION_SPEED_MULTIPLIER, 1)

        while not _shutdown_event.is_set():
            reading = self.sim.generate_reading(self.current_time)
            payload = json.dumps(reading.to_dict())

            info = self._client.publish(self.topic, payload, qos=MQTT_QOS)
            if info.rc != mqtt.MQTT_ERR_SUCCESS:
                logger.warning("Publish failed on %s (rc=%s)", self.topic, info.rc)

            self.current_time += timedelta(seconds=SAMPLING_INTERVAL_SEC)
            _shutdown_event.wait(timeout=interval)

        self._client.loop_stop()
        self._client.disconnect()
        logger.info("Publisher %s stopped.", self.sim.facility_id)


# ── Main entry point ─────────────────────────────────────────────────────

def run_publishers(num_facilities: int = NUM_FACILITIES):
    """Launch all facility publishers and block until shutdown."""
    simulators = create_all_simulators(num_facilities)
    start_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    logger.info(
        "Starting %d facility publishers (interval=%ds, speed=%dx) …",
        num_facilities,
        SAMPLING_INTERVAL_SEC,
        SIMULATION_SPEED_MULTIPLIER,
    )

    threads: list[FacilityPublisher] = []
    for sim in simulators:
        t = FacilityPublisher(sim, start_time=start_time)
        t.start()
        threads.append(t)

    # Block main thread until Ctrl-C
    try:
        while not _shutdown_event.is_set():
            _shutdown_event.wait(timeout=1.0)
    except KeyboardInterrupt:
        _shutdown_event.set()

    for t in threads:
        t.join(timeout=5)

    logger.info("All publishers stopped.")


if __name__ == "__main__":
    run_publishers()
