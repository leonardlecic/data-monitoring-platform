"""Command-line entry point for the monitoring platform."""

import argparse
import json
import logging
import sqlite3
import sys
from datetime import UTC, datetime
from http.client import HTTPException
from pathlib import Path

from data_monitoring import __version__
from data_monitoring.collectors.bajs import fetch_stations, parse_stations
from data_monitoring.config import load_settings
from data_monitoring.storage.snapshots import latest_status, save_snapshot

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Data Monitoring Platform")
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check-config", help="Validate settings without network access")
    collect = subparsers.add_parser("collect", help="Save one Bajs station snapshot")
    status = subparsers.add_parser("status", help="Show the latest stored station counts")
    for command in (check, collect, status):
        command.add_argument("--config", type=Path, default=Path("config/settings.example.toml"))
    for command in (collect, status):
        command.add_argument("--database", type=Path, help="Override the configured SQLite path")
    collect.add_argument("--from-json", type=Path, help="Read a saved Nextbike response")
    collect.add_argument("--captured-at", help="Original ISO 8601 capture time with timezone")
    args = parser.parse_args(argv)
    if args.command == "collect":
        if (args.from_json is None) != (args.captured_at is None):
            collect.error("--from-json and --captured-at must be supplied together")
    try:
        settings = load_settings(args.config)
    except (OSError, ValueError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    if args.command != "check-config":
        database = args.database or settings.database_path
        try:
            if args.command == "status":
                summary = latest_status(database)
                print(json.dumps(summary or {"status": "no_snapshots"}, indent=2))
                return 0
            if args.from_json:
                captured_at = datetime.fromisoformat(args.captured_at)
                with args.from_json.open(encoding="utf-8-sig") as stream:
                    readings = parse_stations(json.load(stream))
            else:
                readings = fetch_stations(settings.timeout_seconds)
                captured_at = datetime.now(UTC)
            count = save_snapshot(database, captured_at, readings)
        except (OSError, ValueError, OverflowError, HTTPException, sqlite3.Error) as exc:
            logger.error("Bajs %s failed: %s", args.command, exc)
            return 1
        print(json.dumps({
            "status": "saved" if count else "already_stored",
            "saved_stations": count,
            "captured_at_utc": captured_at.astimezone(UTC).isoformat(timespec="microseconds"),
        }, indent=2))
        return 0
    print(json.dumps({
        "status": "ok",
        "stage": "KT1",
        "display_timezone": settings.display_timezone,
        "prices_enabled": settings.prices_enabled,
        "network_requests": 0,
    }, indent=2))
    return 0
