"""Read station availability from the Bajs Nextbike feed."""

import json
from typing import NamedTuple
from urllib.request import urlopen

CITY_ID = 1172
BAJS_URL = (
    "https://maps.nextbike.net/maps/nextbike-live.json"
    f"?city={CITY_ID}&domains=hd&list_cities=0&bikes=0"
)


class StationReading(NamedTuple):
    station_id: int
    name: str
    available_bikes: int
    free_racks: int | None
    maintenance: bool


def fetch_stations(timeout_seconds: int) -> list[StationReading]:
    with urlopen(BAJS_URL, timeout=timeout_seconds) as response:
        return parse_stations(json.load(response))


def parse_stations(payload: object) -> list[StationReading]:
    try:
        places = next(
            city["places"]
            for country in payload["countries"]
            for city in country["cities"]
            if city["uid"] == CITY_ID
        )
    except (KeyError, TypeError, StopIteration) as exc:
        raise ValueError("Expected a Nextbike response with Bajs city 1172") from exc
    if not isinstance(places, list):
        raise ValueError("Bajs places must be a list")

    readings = []
    station_ids = set()
    for place in places:
        if not isinstance(place, dict):
            raise ValueError("Bajs place must be an object")
        if place.get("spot") is False:
            continue
        station_id = place.get("uid")
        name = place.get("name")
        available_bikes = place.get("bikes_available_to_rent")
        free_racks = place.get("free_racks")
        maintenance = place.get("maintenance")
        if type(station_id) is not int or station_id <= 0:
            raise ValueError("Bajs station uid must be a positive integer")
        if station_id in station_ids:
            raise ValueError(f"Bajs response contains duplicate station {station_id}")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Bajs station {station_id} has no name")
        if type(available_bikes) is not int or available_bikes < 0:
            raise ValueError(f"Bajs station {station_id} has an invalid rentable-bike count")
        if free_racks is not None and type(free_racks) is not int:
            raise ValueError(f"Bajs station {station_id} has an invalid free-rack count")
        if type(maintenance) is not bool:
            raise ValueError(f"Bajs station {station_id} has an invalid maintenance flag")

        station_ids.add(station_id)
        readings.append(
            StationReading(station_id, name.strip(), available_bikes, free_racks, maintenance)
        )

    if not readings:
        raise ValueError("Bajs response contains no stations")
    return readings
