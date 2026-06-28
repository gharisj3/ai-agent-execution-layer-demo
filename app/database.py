from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

from app.config import settings


def _sqlite_path_from_url(database_url: str) -> Path:
    if database_url.startswith("sqlite:///"):
        return Path(database_url.replace("sqlite:///", "", 1)).resolve()
    parsed = urlparse(database_url)
    if parsed.scheme == "sqlite":
        return Path(parsed.path).resolve()
    raise ValueError("This demo supports SQLite by default. Configure a sqlite:/// URL.")


DB_PATH = _sqlite_path_from_url(settings.database_url)


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                event_id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                request_payload TEXT NOT NULL,
                extracted_intent TEXT NOT NULL,
                validation_result TEXT NOT NULL,
                decision TEXT NOT NULL,
                approval_status TEXT NOT NULL,
                final_erp_response TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.commit()


def insert_audit_event(record: dict[str, object]) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO audit_events (
                event_id,
                request_id,
                event_type,
                request_payload,
                extracted_intent,
                validation_result,
                decision,
                approval_status,
                final_erp_response,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["event_id"],
                record["request_id"],
                record["event_type"],
                json.dumps(record["request_payload"]),
                json.dumps(record["extracted_intent"]),
                json.dumps(record["validation_result"]),
                record["decision"],
                record["approval_status"],
                json.dumps(record["final_erp_response"]),
                record["created_at"],
            ),
        )
        connection.commit()


def list_audit_events() -> list[dict[str, object]]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM audit_events ORDER BY created_at DESC"
        ).fetchall()
    events: list[dict[str, object]] = []
    for row in rows:
        events.append(
            {
                "event_id": row["event_id"],
                "request_id": row["request_id"],
                "event_type": row["event_type"],
                "request_payload": json.loads(row["request_payload"]),
                "extracted_intent": json.loads(row["extracted_intent"]),
                "validation_result": json.loads(row["validation_result"]),
                "decision": row["decision"],
                "approval_status": row["approval_status"],
                "final_erp_response": json.loads(row["final_erp_response"]),
                "created_at": row["created_at"],
            }
        )
    return events

