from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv

load_dotenv(".env.local")

try:
    import libsql
except ModuleNotFoundError:  # pragma: no cover - optional dependency in local dev
    libsql = None


_LOCAL_DB_PATH = Path(os.getenv("F1_LOCAL_DB_PATH", "/tmp/streamlit_endpoints_f1.db"))


def _safe_json(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _safe_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_safe_json(v) for v in obj]
    if hasattr(obj, "item") and type(obj).__module__.startswith("numpy"):
        return obj.item()
    if isinstance(obj, (pd.Timestamp,)):
        return obj.isoformat()
    if isinstance(obj, pd.Timedelta):
        return None if pd.isna(obj) else obj.total_seconds()
    if isinstance(obj, (float,)) and obj != obj:
        return None
    if pd.isna(obj):
        return None
    return obj


def df_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    return [_safe_json(row) for row in df.where(pd.notnull(df), None).to_dict(orient="records")]


def _env(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


@lru_cache(maxsize=1)
def get_connection():
    remote_url = _env("TURSO_DATABASE_URL")
    auth_token = _env("TURSO_AUTH_TOKEN")
    _LOCAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not remote_url or not auth_token:
        raise RuntimeError("Missing Turso credentials. Set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN.")
    if libsql is None:
        raise RuntimeError("libsql is not installed. Install requirements before starting the app.")

    conn = libsql.connect(
        str(_LOCAL_DB_PATH),
        sync_url=remote_url,
        auth_token=auth_token,
        _check_same_thread=False,
    )
    if hasattr(conn, "sync"):
        conn.sync()
    return conn


def _commit(conn) -> None:
    if hasattr(conn, "commit"):
        conn.commit()


def _sync(conn) -> None:
    if hasattr(conn, "sync"):
        conn.sync()


def _fetch_all(conn, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    cursor = conn.execute(sql, params)
    rows = cursor.fetchall()
    if not rows:
        return []

    columns = [col[0] for col in cursor.description or []]
    if not columns:
        return []

    return [dict(zip(columns, row)) for row in rows]


def _ensure_schema(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS event_schedule (
            year INTEGER NOT NULL,
            round_number INTEGER NOT NULL,
            event_name TEXT NOT NULL,
            country TEXT,
            event_date TEXT,
            PRIMARY KEY (year, round_number)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS session_data (
            year INTEGER NOT NULL,
            round_number INTEGER NOT NULL,
            session_code TEXT NOT NULL,
            laps_json TEXT NOT NULL,
            results_json TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (year, round_number, session_code)
        )
        """
    )
    _commit(conn)


def _upsert_schedule(conn, year: int, schedule: pd.DataFrame) -> None:
    rows = []
    for row in schedule.where(pd.notnull(schedule), None).to_dict(orient="records"):
        rows.append(
            (
                year,
                int(row["RoundNumber"]),
                row["EventName"],
                row.get("Country"),
                str(row.get("EventDate")),
            )
        )

    conn.executemany(
        """
        INSERT INTO event_schedule (year, round_number, event_name, country, event_date)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(year, round_number) DO UPDATE SET
            event_name = excluded.event_name,
            country = excluded.country,
            event_date = excluded.event_date
        """,
        rows,
    )
    _commit(conn)
    _sync(conn)


def _upsert_session(conn, year: int, round_num: int, session_code: str, laps: pd.DataFrame, results: pd.DataFrame) -> None:
    conn.execute(
        """
        INSERT INTO session_data (year, round_number, session_code, laps_json, results_json)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(year, round_number, session_code) DO UPDATE SET
            laps_json = excluded.laps_json,
            results_json = excluded.results_json,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            year,
            round_num,
            session_code,
            json.dumps(df_to_records(laps)),
            json.dumps(df_to_records(results)),
        ),
    )
    _commit(conn)
    _sync(conn)


def get_event_schedule(year: int) -> pd.DataFrame:
    conn = get_connection()
    _ensure_schema(conn)

    rows = _fetch_all(
        conn,
        """
        SELECT round_number AS RoundNumber, event_name AS EventName, country AS Country, event_date AS EventDate
        FROM event_schedule
        WHERE year = ?
        ORDER BY round_number
        """,
        (year,),
    )
    if not rows:
        raise LookupError(
            f"No schedule found for year {year}. Run scripts/migrate_f1_turso.py to populate Turso."
        )
    return pd.DataFrame(rows)


def get_session_bundle(year: int, round_num: int, session_code: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    conn = get_connection()
    _ensure_schema(conn)

    rows = _fetch_all(
        conn,
        """
        SELECT laps_json, results_json
        FROM session_data
        WHERE year = ? AND round_number = ? AND session_code = ?
        LIMIT 1
        """,
        (year, round_num, session_code),
    )
    if not rows:
        raise LookupError(
            f"No session found for year {year}, round {round_num}, session {session_code}. "
            "Run scripts/migrate_f1_turso.py to populate Turso."
        )
    stored = rows[0]
    laps = pd.DataFrame(json.loads(stored["laps_json"]))
    results = pd.DataFrame(json.loads(stored["results_json"]))
    return laps, results
