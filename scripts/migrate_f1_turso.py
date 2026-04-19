#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

try:
    import pandas as pd
except ModuleNotFoundError as exc:  # pragma: no cover - environment setup
    raise SystemExit(
        "pandas is not installed. Run `pip install -r requirements.txt` before using the migration script."
    ) from exc

try:
    import fastf1
except ModuleNotFoundError as exc:  # pragma: no cover - environment setup
    raise SystemExit(
        "fastf1 is not installed. Run `pip install -r requirements.txt` before using the migration script."
    ) from exc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.f1_store import get_connection, _ensure_schema, _upsert_schedule, _upsert_session  # noqa: E402

DEFAULT_YEARS = [2023, 2024, 2025]
DEFAULT_SESSIONS = ["R", "Q"]

_FASTF1_CACHE_DIR = Path(os.getenv("FASTF1_CACHE_DIR", "/tmp/fastf1_cache"))
_FASTF1_CACHE_DIR.mkdir(parents=True, exist_ok=True)
fastf1.Cache.enable_cache(str(_FASTF1_CACHE_DIR))


def _load_live_schedule(year: int) -> pd.DataFrame:
    schedule = fastf1.get_event_schedule(year, include_testing=False)
    return (
        schedule[["RoundNumber", "EventName", "Country", "EventDate"]]
        .assign(EventDate=lambda df: df["EventDate"].astype(str))
        .sort_values("RoundNumber")
        .reset_index(drop=True)
    )


def _load_live_session(year: int, round_num: int, session_code: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    session = fastf1.get_session(year, round_num, session_code)
    session.load(telemetry=False, weather=False, messages=False)

    lap_cols = [
        c
        for c in ["Driver", "Team", "LapNumber", "LapTime", "Compound", "IsPersonalBest", "Position"]
        if c in session.laps.columns
    ]
    laps = session.laps[lap_cols].copy()
    laps["LapTimeSec"] = laps["LapTime"].dt.total_seconds()
    laps = laps.drop(columns=["LapTime"])

    result_cols = [
        c
        for c in [
            "Position",
            "Abbreviation",
            "FullName",
            "TeamName",
            "GridPosition",
            "Points",
            "Status",
            "Q1",
            "Q2",
            "Q3",
        ]
        if c in session.results.columns
    ]
    results = session.results[result_cols].copy()
    for col in ["Q1", "Q2", "Q3"]:
        if col in results.columns:
            results[col] = results[col].apply(lambda t: t.total_seconds() if hasattr(t, "total_seconds") and pd.notnull(t) else None)

    return laps, results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill F1 data into Turso-backed SQLite.")
    parser.add_argument(
        "--years",
        nargs="+",
        type=int,
        default=DEFAULT_YEARS,
        help="Season years to migrate.",
    )
    parser.add_argument(
        "--sessions",
        nargs="+",
        default=DEFAULT_SESSIONS,
        help="Session codes to migrate for each round (default: R Q).",
    )
    parser.add_argument(
        "--skip-live-load",
        action="store_true",
        help="Only create schema and refresh existing rows; do not call FastF1 for missing data.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    remote_url = os.getenv("TURSO_DATABASE_URL")
    auth_token = os.getenv("TURSO_AUTH_TOKEN")
    if not remote_url or not auth_token:
        print("Missing Turso credentials. Set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN.", file=sys.stderr)
        return 1

    conn = get_connection()
    _ensure_schema(conn)

    total_schedules = 0
    total_sessions = 0

    for year in args.years:
        print(f"[{year}] loading schedule")
        schedule = _load_live_schedule(year) if not args.skip_live_load else pd.DataFrame()
        if not schedule.empty:
            _upsert_schedule(conn, year, schedule)
            total_schedules += len(schedule)

        if schedule.empty:
            # If the schedule already exists in the DB, use that list of rounds.
            rows = conn.execute(
                """
                SELECT round_number AS RoundNumber, event_name AS EventName, country AS Country, event_date AS EventDate
                FROM event_schedule
                WHERE year = ?
                ORDER BY round_number
                """,
                (year,),
            ).fetchall()
            schedule = pd.DataFrame(rows, columns=["RoundNumber", "EventName", "Country", "EventDate"]) if rows else pd.DataFrame()

        if schedule.empty:
            print(f"[{year}] no rounds available, skipping")
            continue

        for round_num in schedule["RoundNumber"].tolist():
            for session_code in args.sessions:
                print(f"[{year} R{round_num} {session_code}] loading session")
                try:
                    laps, results = _load_live_session(year, int(round_num), session_code)
                except Exception as exc:
                    print(f"[{year} R{round_num} {session_code}] failed: {exc}", file=sys.stderr)
                    continue

                _upsert_session(conn, year, int(round_num), session_code, laps, results)
                total_sessions += 1

    if hasattr(conn, "sync"):
        conn.sync()

    print(json.dumps({"years": args.years, "sessions": args.sessions, "schedules_upserted": total_schedules, "sessions_upserted": total_sessions}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
