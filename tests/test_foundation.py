"""Offline checks of invalid data boundaries and configuration failure modes."""

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from data_monitoring.cli import main
from data_monitoring.config import load_settings
from data_monitoring.domain import Measurement

EXAMPLE = Path(__file__).resolve().parents[1] / "config" / "settings.example.toml"


def measurement(**changes):
    fields = dict(
        source="synthetic", entity_key="product:001:store:001", metric="price",
        observed_at=datetime(2026, 10, 28, tzinfo=UTC),
        collected_at=datetime(2026, 10, 28, 12, tzinfo=UTC),
        value=Decimal("1.99"), unit="EUR",
    )
    return Measurement(**(fields | changes))


def test_decimal_price_preserves_precision():
    assert measurement().value + Decimal("0.01") == Decimal("2.00")


@pytest.mark.parametrize("changes", [
    {"value": Decimal("NaN")}, {"value": Decimal("Infinity")},
    {"value": Decimal("-0.01")}, {"value": 1.99}, {"unit": "USD"},
    {"observed_at": datetime(2026, 10, 28)}, {"collected_at": "2026-10-28"},
    {"entity_key": " "},
])
def test_invalid_measurements_are_rejected(changes):
    with pytest.raises(ValueError):
        measurement(**changes)


def test_negative_weather_temperature_is_valid():
    assert measurement(metric="temperature_2m", unit="degC", value=Decimal("-3")).value == -3


def test_example_and_relative_database_path():
    settings = load_settings(EXAMPLE)
    assert settings.database_path == EXAMPLE.parents[1] / "data" / "monitoring.sqlite3"
    assert not settings.prices_enabled


@pytest.mark.parametrize(("old", "new"), [
    ("timeout_seconds = 15", "timeout_seconds = 0"),
    ("max_attempts = 3", "max_attempts = true"),
    ("max_attempts = 3", "max_attempts = 6"),
    ("latitude = 45.8150", "latitude = 91"),
    ("longitude = 15.9819", "longitude = nan"),
    ("enabled = false", 'enabled = "false"'),
    ("daily_request_budget = 100", "daily_request_budget = 101"),
])
def test_invalid_settings_are_rejected(tmp_path, old, new):
    path = tmp_path / "bad.toml"
    path.write_text(EXAMPLE.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
    with pytest.raises(ValueError):
        load_settings(path)


def test_missing_key_has_actionable_error(tmp_path):
    path = tmp_path / "empty.toml"
    path.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="Missing configuration key: app"):
        load_settings(path)


def test_cli_success(capsys):
    assert main(["check-config", "--config", str(EXAMPLE)]) == 0
    assert json.loads(capsys.readouterr().out)["network_requests"] == 0


def test_cli_missing_file_returns_failure(tmp_path, capsys):
    assert main(["check-config", "--config", str(tmp_path / "missing.toml")]) == 2
    assert "Configuration error" in capsys.readouterr().err
