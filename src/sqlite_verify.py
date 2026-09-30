from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd

from config import CLEAN_PATH, DB_PATH, METRICS_PATH


def verify_behavior_counts(frame: pd.DataFrame, db_path: Path) -> dict[str, int]:
    with sqlite3.connect(db_path) as connection:
        frame[["behavior"]].to_sql("events", connection, if_exists="replace", index=False)
        rows = connection.execute(
            "SELECT behavior, COUNT(*) AS events FROM events GROUP BY behavior ORDER BY behavior"
        ).fetchall()
    return {behavior: int(events) for behavior, events in rows}


def load_clean_events(clean_path: Path = CLEAN_PATH, db_path: Path = DB_PATH) -> None:
    if db_path.exists():
        db_path.unlink()
    with sqlite3.connect(db_path) as connection:
        for index, chunk in enumerate(pd.read_csv(clean_path, chunksize=200_000, parse_dates=["event_time"]), start=1):
            chunk.to_sql("events", connection, if_exists="append", index=False)
            print(f"sqlite_chunk={index}", flush=True)
        connection.executescript(
            """
            CREATE INDEX idx_events_behavior ON events(behavior);
            CREATE INDEX idx_events_user ON events(user_id);
            CREATE INDEX idx_events_date ON events(event_date);
            CREATE INDEX idx_events_category ON events(category_id);
            """
        )


def run_verification(db_path: Path = DB_PATH) -> dict:
    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    expected = metrics["basic"]["behavior_events"]
    with sqlite3.connect(db_path) as connection:
        actual = {
            row[0]: int(row[1])
            for row in connection.execute(
                "SELECT behavior, COUNT(*) FROM events GROUP BY behavior ORDER BY behavior"
            ).fetchall()
        }
        distinct_users = int(connection.execute("SELECT COUNT(DISTINCT user_id) FROM events").fetchone()[0])
        buyers = int(
            connection.execute("SELECT COUNT(DISTINCT user_id) FROM events WHERE behavior='buy'").fetchone()[0]
        )
    checks = {
        "behavior_counts_match": actual == expected,
        "distinct_users_match": distinct_users == metrics["basic"]["users"],
        "buyers_match": buyers == metrics["repeat_purchase"]["buyers"],
    }
    if not all(checks.values()):
        raise AssertionError(f"SQL verification failed: {checks}; actual={actual}; expected={expected}")
    return checks


def main() -> None:
    load_clean_events()
    checks = run_verification()
    for name, value in checks.items():
        print(f"{name}: {'PASS' if value else 'FAIL'}")


if __name__ == "__main__":
    main()
