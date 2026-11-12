import json
import sqlite3
from contextlib import closing
from io import BytesIO
from pathlib import Path
from urllib.error import URLError

from data_monitoring.cli import main
from data_monitoring.collectors import bajs

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "settings.example.toml"
SAMPLE = ROOT / "tests" / "fixtures" / "bajs-sample.json"


def test_import_status_and_invalid_response(tmp_path, capsys):
    database = tmp_path / "demo.sqlite3"
    options = ["--config", str(CONFIG), "--database", str(database)]
    assert main(["status", *options]) == 0
    assert json.loads(capsys.readouterr().out) == {"status": "no_snapshots"}
    assert not database.exists()

    collect = ["collect", *options, "--from-json", str(SAMPLE), "--captured-at"]
    assert main([*collect, "2026-11-06T09:00:00+01:00"]) == 0
    assert json.loads(capsys.readouterr().out)["saved_stations"] == 3
    assert main([*collect, "2026-11-06T08:00:00Z"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "already_stored"

    assert main([*collect, "2026-11-06T07:00:00Z"]) == 0
    capsys.readouterr()
    broken = tmp_path / "broken.json"
    broken.write_text('{"countries": []}', encoding="utf-8")
    assert main([
        "collect", *options, "--from-json", str(broken), "--captured-at", "2026-11-06T09:00:00Z"
    ]) == 1

    assert main(["status", *options]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "last_snapshot_utc": "2026-11-06T08:00:00.000000+00:00",
        "stations": 3,
        "active_stations": 2,
        "empty_active_stations": 1,
        "stations_in_maintenance": 1,
    }
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM station_snapshots").fetchone() == (6,)


def test_live_collect_uses_bajs_endpoint_and_preserves_snapshot_on_network_error(
    tmp_path, capsys, monkeypatch
):
    def download(url, *, timeout):
        assert url == bajs.BAJS_URL
        assert timeout == 15
        return BytesIO(SAMPLE.read_bytes())

    monkeypatch.setattr(bajs, "urlopen", download)
    options = ["--config", str(CONFIG), "--database", str(tmp_path / "live.sqlite3")]
    assert main(["collect", *options]) == 0
    saved = json.loads(capsys.readouterr().out)
    assert saved["saved_stations"] == 3

    def unavailable(*args, **kwargs):
        raise URLError("offline")

    monkeypatch.setattr(bajs, "urlopen", unavailable)
    assert main(["collect", *options]) == 1
    assert main(["status", *options]) == 0
    assert json.loads(capsys.readouterr().out)["last_snapshot_utc"] == saved["captured_at_utc"]
