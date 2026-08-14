$ErrorActionPreference = "Stop"
$versionOutput = & python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Python ist noch nicht eingerichtet." -ForegroundColor Red
    Write-Host "Installiere Python 3.11+ oder konfiguriere pyenv und starte danach erneut."
    Write-Host $versionOutput
    exit 1
}
python -m pip install --upgrade pip
python -m pip install -e $PSScriptRoot
