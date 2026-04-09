from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple


def _utc_now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


class Storage:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    @contextmanager
    def _tx(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._tx() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS app_state (
                    k TEXT PRIMARY KEY,
                    v TEXT NOT NULL
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS host_prefs (
                    listing_id TEXT PRIMARY KEY,
                    prefs_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    action TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                """
            )

            # Defaults
            conn.execute(
                "INSERT OR IGNORE INTO app_state(k, v) VALUES(?, ?)",
                ("kill_switch", json.dumps(False)),
            )
            conn.execute(
                "INSERT OR IGNORE INTO app_state(k, v) VALUES(?, ?)",
                ("regional_override", json.dumps(None)),
            )

    def get_state(self) -> Dict[str, Any]:
        with self._tx() as conn:
            rows = conn.execute("SELECT k, v FROM app_state").fetchall()
        out: Dict[str, Any] = {}
        for r in rows:
            out[str(r["k"])] = json.loads(r["v"])
        return out

    def set_state(self, *, kill_switch: bool, regional_override: Optional[str]) -> None:
        with self._tx() as conn:
            conn.execute(
                "INSERT INTO app_state(k, v) VALUES(?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                ("kill_switch", json.dumps(bool(kill_switch))),
            )
            conn.execute(
                "INSERT INTO app_state(k, v) VALUES(?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                ("regional_override", json.dumps(regional_override)),
            )

    def append_audit(self, action: str, payload: Dict[str, Any]) -> None:
        with self._tx() as conn:
            conn.execute(
                "INSERT INTO audit_log(ts, action, payload_json) VALUES(?, ?, ?)",
                (_utc_now_iso(), action, json.dumps(payload)),
            )

    def recent_audit(self, limit: int = 20) -> List[Dict[str, Any]]:
        limit = min(max(int(limit), 1), 200)
        with self._tx() as conn:
            rows = conn.execute(
                "SELECT ts, action, payload_json FROM audit_log ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            payload = json.loads(r["payload_json"])
            out.append({"ts": r["ts"], "action": r["action"], **payload})
        out.reverse()
        return out

    def get_host_prefs(self, listing_id: str) -> Optional[Dict[str, Any]]:
        with self._tx() as conn:
            row = conn.execute(
                "SELECT prefs_json FROM host_prefs WHERE listing_id = ?",
                (str(listing_id),),
            ).fetchone()
        if not row:
            return None
        return json.loads(row["prefs_json"])

    def set_host_prefs(self, listing_id: str, prefs: Dict[str, Any]) -> Dict[str, Any]:
        payload = json.dumps(prefs)
        with self._tx() as conn:
            conn.execute(
                """
                INSERT INTO host_prefs(listing_id, prefs_json, updated_at)
                VALUES(?, ?, ?)
                ON CONFLICT(listing_id) DO UPDATE SET
                  prefs_json=excluded.prefs_json,
                  updated_at=excluded.updated_at
                """,
                (str(listing_id), payload, _utc_now_iso()),
            )
        return prefs


def default_storage(root: Path) -> Storage:
    # Allow override (useful if you want to bind-mount in containers)
    p = os.environ.get("SMART_PRICING_DB_PATH", str(root / "backend" / "app.db"))
    return Storage(Path(p))

