"""Local versioned report snapshots; no network and no automatic old-database migration."""
from __future__ import annotations

from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import sys
from typing import Any, Mapping


def default_database_path() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "ThalassemiaDifferential" / "v2" / "research_records.sqlite3"


class ScreeningDatabase:
    def __init__(self, db_path: str | Path | None = None):
        self.path = Path(db_path) if db_path is not None else default_database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                model_version TEXT NOT NULL,
                model_sha256 TEXT NOT NULL,
                record_json TEXT NOT NULL
            )""")

    def save_record(self, record: Mapping[str, Any]) -> int:
        prediction = record["prediction"]
        with closing(sqlite3.connect(self.path)) as connection, connection:
            cursor = connection.execute(
                "INSERT INTO records(created_at,model_version,model_sha256,record_json) VALUES(?,?,?,?)",
                (record["created_at"], prediction["model_version"], prediction["model_sha256"],
                 json.dumps(record, ensure_ascii=False, allow_nan=False)))
            return int(cursor.lastrowid)

    def get_record(self, record_id: int) -> dict[str, Any] | None:
        with closing(sqlite3.connect(self.path)) as connection, connection:
            row = connection.execute("SELECT record_json FROM records WHERE id=?", (record_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def get_all_records(self) -> list[dict[str, Any]]:
        with closing(sqlite3.connect(self.path)) as connection, connection:
            rows = connection.execute("SELECT id,record_json FROM records ORDER BY id DESC").fetchall()
        return [{"database_record_id": row[0], **json.loads(row[1])} for row in rows]
