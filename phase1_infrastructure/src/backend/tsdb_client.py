"""
Time-Series Database Client — Step 1.3 (Advanced)
===================================================
Robust persistent storage layer simulating a true Time-Series Database
(like TimescaleDB/InfluxDB) using heavily indexed SQLite.
"""

import sqlite3
import json
import logging
from typing import Dict, List, Any
import os

logger = logging.getLogger("tsdb_client")

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "timeseries.db")

class TSDBClient:
    """
    Simulates a Time-Series Database using SQLite with
    optimizations for massive time-indexed querying.
    """
    def __init__(self, db_path: str = DB_PATH):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sensor_metrics (
                    timestamp_utc TEXT NOT NULL,
                    facility_id TEXT NOT NULL,
                    co2_ppm REAL,
                    ch4_ppm REAL,
                    nox_ppb REAL,
                    fuel_rate REAL,
                    energy_kwh REAL,
                    anomaly_flag TEXT,
                    PRIMARY KEY (timestamp_utc, facility_id)
                )
            ''')
            # Create indexing for time-series querying
            conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON sensor_metrics(timestamp_utc DESC)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_facility ON sensor_metrics(facility_id)')
            conn.commit()

    def insert_batch(self, readings: List[Dict[str, Any]]):
        """Insert a large batch of sensor readings optimally."""
        if not readings:
            return
            
        # extract values
        values = []
        for r in readings:
            values.append((
                r["timestamp_utc"],
                r["facility_id"],
                r.get("co2_ppm", 0.0),
                r.get("ch4_ppm", 0.0),
                r.get("nox_ppb", 0.0),
                r.get("fuel_rate", 0.0),
                r.get("energy_kwh", 0.0),
                r.get("anomaly_flag", None)
            ))
            
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany('''
                INSERT OR IGNORE INTO sensor_metrics 
                (timestamp_utc, facility_id, co2_ppm, ch4_ppm, nox_ppb, fuel_rate, energy_kwh, anomaly_flag)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', values)
            conn.commit()

    def query_time_range(self, start_time: str, end_time: str, facility_id: str = None) -> List[Dict[str, Any]]:
        """Query metrics by time range and optional facility."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if facility_id:
                cursor = conn.execute('''
                    SELECT * FROM sensor_metrics 
                    WHERE facility_id = ? AND timestamp_utc >= ? AND timestamp_utc <= ?
                    ORDER BY timestamp_utc ASC
                ''', (facility_id, start_time, end_time))
            else:
                cursor = conn.execute('''
                    SELECT * FROM sensor_metrics 
                    WHERE timestamp_utc >= ? AND timestamp_utc <= ?
                    ORDER BY timestamp_utc ASC
                ''', (start_time, end_time))
            
            return [dict(row) for row in cursor.fetchall()]
