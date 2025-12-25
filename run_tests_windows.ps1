# Run tests and show a few metrics (clean, robust PowerShell version)
python -m venv .venv
.venv\Scripts\pip.exe install -r requirements.txt
$env:PYTHONPATH = (Get-Location).Path
.venv\Scripts\pytest.exe -q --maxfail=1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Tests finished. You can inspect metrics via: python -c \"from data_pipeline.metrics import metrics; print(metrics)\""
