"""Command-line entry point for the monitoring platform."""

import argparse
import json
import logging
import sqlite3
import sys
from datetime import UTC, datetime
from http.client import HTTPException
from logging.handlers import RotatingFileHandler
from pathlib import Path
from time import monotonic, sleep

from data_monitoring import __version__
from data_monitoring.collectors.bajs import fetch_stations, parse_stations
from data_monitoring.config import load_settings
from data_monitoring.storage.snapshots import latest_status, save_snapshot
from data_monitoring.windows_power import keep_awake

logger = logging.getLogger(__name__)
COLLECTION_ERRORS = (OSError, ValueError, OverflowError, HTTPException, sqlite3.Error)


def _collect_live(database: Path, timeout_seconds: int) -> tuple[datetime, int]:
    readings = fetch_stations(timeout_seconds)
    captured_at = datetime.now(UTC)
    return captured_at, save_snapshot(database, captured_at, readings)


def _watch(database: Path, timeout_seconds: int, interval_minutes: int) -> None:
    interval_seconds = interval_minutes * 60
    logger.info("Collecting Bajs snapshots every %d minutes", interval_minutes)
    while True:
        started = monotonic()
        try:
            captured_at, count = _collect_live(database, timeout_seconds)
            logger.info("Saved %d Bajs station readings at %s", count, captured_at.isoformat())
        except COLLECTION_ERRORS as exc:
            logger.error("Bajs collection failed: %s", exc)
        sleep(max(0, interval_seconds - (monotonic() - started)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Data Monitoring Platform")
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check-config", help="Validate settings without network access")
    collect = subparsers.add_parser("collect", help="Save one Bajs station snapshot")
    status = subparsers.add_parser("status", help="Show the latest stored station counts")
    watch = subparsers.add_parser("watch", help="Collect Bajs snapshots at the configured interval")
    for command in (check, collect, status, watch):
        command.add_argument("--config", type=Path, default=Path("config/settings.example.toml"))
    for command in (collect, status, watch):
        command.add_argument("--database", type=Path, help="Override the configured SQLite path")
    collect.add_argument("--from-json", type=Path, help="Read a saved Nextbike response")
    collect.add_argument("--captured-at", help="Original ISO 8601 capture time with timezone")
    watch.add_argument("--log-file", type=Path, help="Write to a rotating log file")
    watch.add_argument("--keep-awake", action="store_true", help="Prevent idle sleep on Windows")
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
            if args.command == "watch":
                log_options = {}
                if args.log_file is not None:
                    if args.log_file.resolve() == database.resolve():
                        raise ValueError("Log file and SQLite database must use different paths")
                    args.log_file.parent.mkdir(parents=True, exist_ok=True)
                    log_options["handlers"] = [
                        RotatingFileHandler(
                            args.log_file, maxBytes=1_000_000, backupCount=2, encoding="utf-8"
                        )
                    ]
                logging.basicConfig(
                    level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s",
                    **log_options,
                )
                try:
                    with keep_awake(args.keep_awake):
                        _watch(database, settings.timeout_seconds, settings.bajs_interval_minutes)
                except KeyboardInterrupt:
                    logger.info("Bajs collector stopped")
                return 0
            if args.from_json:
                captured_at = datetime.fromisoformat(args.captured_at)
                with args.from_json.open(encoding="utf-8-sig") as stream:
                    readings = parse_stations(json.load(stream))
                count = save_snapshot(database, captured_at, readings)
            else:
                captured_at, count = _collect_live(database, settings.timeout_seconds)
        except COLLECTION_ERRORS as exc:
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
