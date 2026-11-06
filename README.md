# Data Monitoring Platform

Projekt za kolegij Skriptni jezici. Python aplikacija dohvaća stanje
zagrebačkih Bajs stanica i gradi povijest u SQLiteu. Iz te povijesti
planiran je pregled stanica koje najčešće ostaju bez bicikala.

## Pokretanje

Iz korijena repozitorija, u PowerShellu s instaliranim Pythonom 3.12 ili novijim.

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -e ".[dev]"
./.venv/Scripts/python.exe -m data_monitoring collect
./.venv/Scripts/python.exe -m data_monitoring status
```

`collect` sprema jednu snimku u `data/monitoring.sqlite3`. `status`
prikazuje vrijeme zadnje snimke u UTC-u te broj aktivnih stanica, aktivnih
stanica bez dostupnih bicikala i stanica na održavanju. Neuspjeli dohvat
ostavlja zadnju snimku dostupnom za pregled.

## Provjera bez mreže

```powershell
./.venv/Scripts/python.exe -m data_monitoring collect --from-json tests/fixtures/bajs-sample.json --captured-at 2026-11-06T08:00:00Z --database data/bajs-demo.sqlite3
./.venv/Scripts/python.exe -m data_monitoring status --database data/bajs-demo.sqlite3
./.venv/Scripts/python.exe -m pytest
```

Testni primjer daje dvije aktivne stanice, od kojih je jedna prazna, te
jednu stanicu na održavanju. Ponovni uvoz s istim vremenom snimke vraća
`already_stored`.

## Struktura repozitorija

- `src/data_monitoring/` sadrži CLI, Bajs adapter i SQLite pohranu.
- `config/` sadrži primjer konfiguracije.
- `tests/` sadrži automatizirane provjere i sintetički Bajs odgovor.
- `scripts/` sadrži PowerShell naredbu za provjere projekta.
- `reports/` sadrži PDF izvješća i pripadajuće LaTeX izvore.
- `data/` sadrži lokalne baze koje Git ignorira.
- `notes/` služi za lokalne nacrte, radne bilješke i alate.
