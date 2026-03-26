"""
SQLite Buffer — Edge-side store-and-forward
=============================================
Stores processed (Kalman-filtered, validated) sensor readings locally
in SQLite so that no data is lost if the backend is temporarily
unreachable.  The forwarder periodically drains the buffer and POSTs
batches to the backend REST API.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from pathlib import Path
from typing import Optional

from src.config import EDGE_SQLITE_PATH

logger = logging.getLogger("edge.sqlite_buffer")


class SQLiteBuffer:
    """Thread-safe ring buffer backed by SQLite."""

    _CREATE_TABLE = """
    CREATE TABLE IF NOT EXISTS edge_buffer (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        facility_id TEXT    NOT NULL,
        payload     TEXT    NOT NULL,
        created_at  TEXT    NOT NULL DEFAULT (strftime('%%Y-%%m-%%dT%%H:%%M:%%fZ', 'now')),
        forwarded   INTEGER NOT NULL DEFAULT 0
    );
    """

    _CREATE_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_buffer_forwarded
    ON edge_buffer (forwarded, id);
    """

    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path or EDGE_SQLITE_PATH
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self):
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")
        self._conn.execute(self._CREATE_TABLE)
        self._conn.execute(self._CREATE_INDEX)
        self._conn.commit()
        logger.info("SQLite buffer initialised at %s", self._db_path)

    # ── Write path ───────────────────────────────────────────────────────

    def enqueue(self, facility_id: str, payload: dict):
        """Insert a processed reading into the buffer."""
        with self._lock:
            self._conn.execute(
                "INSERT INTO edge_buffer (facility_id, payload) VALUES (?, ?)",
                (facility_id, json.dumps(payload)),
            )
            self._conn.commit()

    def enqueue_batch(self, records: list[tuple[str, dict]]):
        """Bulk insert processed readings."""
        with self._lock:
            self._conn.executemany(
                "INSERT INTO edge_buffer (facility_id, payload) VALUES (?, ?)",
                [(fid, json.dumps(p)) for fid, p in records],
            )
            self._conn.commit()

    # ── Read path (for forwarder) ────────────────────────────────────────

    def dequeue(self, batch_size: int = 100) -> list[tuple[int, dict]]:
        """
        Retrieve up to *batch_size* un-forwarded records.
        Returns list of (row_id, payload_dict) tuples.
        """
        with self._lock:
            cur = self._conn.execute(
                "SELECT id, payload FROM edge_buffer "
                "WHERE forwarded = 0 ORDER BY id LIMIT ?",
                (batch_size,),
            )
            rows = cur.fetchall()
        return [(row_id, json.loads(payload)) for row_id, payload in rows]

    def mark_forwarded(self, row_ids: list[int]):
        """Mark rows as successfully forwarded."""
        if not row_ids:
            return
        with self._lock:
            placeholders = ",".join("?" for _ in row_ids)
            self._conn.execute(
                f"UPDATE edge_buffer SET forwarded = 1 WHERE id IN ({placeholders})",
                row_ids,
            )
            self._conn.commit()

    # ── Housekeeping ─────────────────────────────────────────────────────

    def purge_forwarded(self, keep_last: int = 10_000):
        """Delete old forwarded records to bound disk usage."""
        with self._lock:
            self._conn.execute(
                "DELETE FROM edge_buffer WHERE forwarded = 1 AND id NOT IN "
                "(SELECT id FROM edge_buffer WHERE forwarded = 1 "
                " ORDER BY id DESC LIMIT ?)",
                (keep_last,),
            )
            self._conn.commit()

    def pending_count(self) -> int:
        with self._lock:
            cur = self._conn.execute(
                "SELECT COUNT(*) FROM edge_buffer WHERE forwarded = 0"
            )
            return cur.fetchone()[0]

    def close(self):
        if self._conn:
            self._conn.close()
