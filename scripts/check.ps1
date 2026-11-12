param([string]$Python = "python")
$ErrorActionPreference = "Stop"
Push-Location (Join-Path $PSScriptRoot "..")
try {
    & $Python -m ruff check .
    if ($LASTEXITCODE -ne 0) { throw "Ruff failed." }
    & $Python -m pytest
    if ($LASTEXITCODE -ne 0) { throw "Tests failed." }
    & $Python -m data_monitoring check-config --config config/settings.example.toml
    if ($LASTEXITCODE -ne 0) { throw "Configuration validation failed." }
} finally {
    Pop-Location
}
