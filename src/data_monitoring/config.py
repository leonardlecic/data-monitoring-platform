"""Load non-secret settings. KT1 validates the agreed configuration contract."""

import math
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    display_timezone: str
    database_path: Path
    timeout_seconds: int
    max_attempts: int
    weather_interval_minutes: int
    prices_interval_minutes: int
    latitude: float
    longitude: float
    prices_enabled: bool
    daily_request_budget: int


def _positive_int(table: dict, key: str) -> int:
    value = table[key]
    if type(value) is not int or value <= 0:
        raise ValueError(f"{key} must be a positive integer")
    return value


def _coordinate(table: dict, key: str, limit: int) -> float:
    value = table[key]
    if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > limit:
        raise ValueError(f"{key} must be a finite number between {-limit} and {limit}")
    return float(value)


def load_settings(path: Path) -> Settings:
    """Resolve relative database paths against the configuration directory's parent."""
    with path.open("rb") as stream:
        raw = tomllib.load(stream)
    try:
        app, collection, weather, prices = (
            raw["app"], raw["collection"], raw["weather"], raw["prices"]
        )
        if not all(isinstance(table, dict) for table in (app, collection, weather, prices)):
            raise ValueError("Settings sections must be TOML tables")
        if app["display_timezone"] != "Europe/Zagreb":
            raise ValueError("KT1 display_timezone must be Europe/Zagreb; storage will use UTC")
        database = app["database_path"]
        if not isinstance(database, str) or not database.strip():
            raise ValueError("database_path must be a non-empty string")
        if type(prices["enabled"]) is not bool:
            raise ValueError("prices.enabled must be a boolean")
        attempts = _positive_int(collection, "max_attempts")
        if attempts > 5:
            raise ValueError("max_attempts must not exceed 5")
        budget = _positive_int(prices, "daily_request_budget")
        if budget > 100:
            raise ValueError("KT1 conservative daily_request_budget must not exceed 100")
        database_path = Path(database)
        if not database_path.is_absolute():
            database_path = path.resolve().parent.parent / database_path
        return Settings(
            display_timezone=app["display_timezone"],
            database_path=database_path,
            timeout_seconds=_positive_int(collection, "timeout_seconds"),
            max_attempts=attempts,
            weather_interval_minutes=_positive_int(collection, "weather_interval_minutes"),
            prices_interval_minutes=_positive_int(collection, "prices_interval_minutes"),
            latitude=_coordinate(weather, "latitude", 90),
            longitude=_coordinate(weather, "longitude", 180),
            prices_enabled=prices["enabled"],
            daily_request_budget=budget,
        )
    except KeyError as exc:
        raise ValueError(f"Missing configuration key: {exc.args[0]}") from exc
