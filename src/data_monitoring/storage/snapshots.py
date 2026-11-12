"""Store complete station snapshots and summarize the latest one."""

import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from data_monitoring.collectors.bajs import StationReading

CREATE_SNAPSHOTS = """
CREATE TABLE IF NOT EXISTS station_snapshots (
    captured_at_utc TEXT NOT NULL,
    station_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    available_bikes INTEGER NOT NULL CHECK (available_bikes >= 0),
    free_racks INTEGER,
    maintenance INTEGER NOT NULL CHECK (maintenance IN (0, 1)),
    PRIMARY KEY (captured_at_utc, station_id)
)
"""


def save_snapshot(
    database: Path, captured_at: datetime, readings: list[StationReading]
) -> int:
    if captured_at.utcoffset() is None:
        raise ValueError("Snapshot time must include a timezone")
    timestamp = captured_at.astimezone(UTC).isoformat(timespec="microseconds")
    database.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute(CREATE_SNAPSHOTS)
        connection.execute("BEGIN IMMEDIATE")
        if connection.execute(
            "SELECT 1 FROM station_snapshots WHERE captured_at_utc = ? LIMIT 1", (timestamp,)
        ).fetchone():
            return 0
        connection.executemany(
            """
            INSERT INTO station_snapshots (
                captured_at_utc, station_id, name, available_bikes, free_racks, maintenance
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            ((timestamp, *reading) for reading in readings),
        )
    return len(readings)


def latest_status(database: Path) -> dict[str, str | int] | None:
    if not database.exists():
        return None
    with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT captured_at_utc AS last_snapshot_utc,
                   COUNT(*) AS stations,
                   COUNT(*) FILTER (WHERE maintenance = 0) AS active_stations,
                   COUNT(*) FILTER (WHERE maintenance = 0 AND available_bikes = 0)
                       AS empty_active_stations,
                   COUNT(*) FILTER (WHERE maintenance = 1) AS stations_in_maintenance
            FROM station_snapshots
            WHERE captured_at_utc = (SELECT MAX(captured_at_utc) FROM station_snapshots)
            GROUP BY captured_at_utc
            """
        ).fetchone()
    return dict(row) if row else None
