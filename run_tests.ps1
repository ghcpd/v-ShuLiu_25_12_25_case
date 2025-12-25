# Run tests and show a few metrics
python -m venv .venv
.\.venv\Scripts\pip.exe install -r requirements.txt
.\.venv\Scripts\pytest.exe -q --maxfail=1 || exit 1


"nWrite-Host "Tests finished. You can inspect metrics via interactive python: 'from data_pipeline.metrics import metrics; print(metrics)'