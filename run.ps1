$ErrorActionPreference = "Stop"
$versionOutput = & python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Python ist noch nicht eingerichtet." -ForegroundColor Red
    Write-Host "Installiere Python 3.11+ inklusive Tcl/Tk oder konfiguriere pyenv und starte danach erneut."
    Write-Host $versionOutput
    exit 1
}
$env:PYTHONPATH = Join-Path $PSScriptRoot "src"
python -m timesheet.app
