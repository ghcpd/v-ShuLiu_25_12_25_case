<# One‑click test runner for Windows PowerShell: creates venv, installs, runs pytest, prints metrics. #>
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $root

if (-Not (Test-Path -Path .venv)) {
    python -m venv .venv
}

# Activate (PowerShell)
. .\.venv\Scripts\Activate.ps1

pip install --upgrade pip
pip install -r requirements.txt

# run tests with a concise report
pytest -q --maxfail=1

if ($LASTEXITCODE -ne 0) {
    Write-Host "Some tests failed (exit code $LASTEXITCODE)" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "All tests passed ✅" -ForegroundColor Green
