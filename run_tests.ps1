# Run Tests Script
# Create and activate venv
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
pip install pytest

# Run tests
pytest tests/

# Print metrics
python -c "from data_pipeline.metrics import log_metrics; log_metrics()"