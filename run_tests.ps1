# One-click test script for Windows PowerShell
# Sets up venv, installs dependencies, runs tests, displays metrics

param(
    [string]$pythonPath = "python",
    [string]$venvPath = "venv",
    [switch]$skipVenv = $false
)

# Colors for output
$successColor = "Green"
$warningColor = "Yellow"
$errorColor = "Red"
$infoColor = "Cyan"

function Write-Header {
    param([string]$text)
    Write-Host "`n=== $text ===" -ForegroundColor $infoColor
}

function Write-Success {
    param([string]$text)
    Write-Host $text -ForegroundColor $successColor
}

function Write-Error {
    param([string]$text)
    Write-Host $text -ForegroundColor $errorColor
}

function Write-Warning {
    param([string]$text)
    Write-Host $text -ForegroundColor $warningColor
}

# Start
Write-Host "Train Data Pipeline - Test Suite" -ForegroundColor Cyan
Write-Host "Platform: Windows PowerShell" -ForegroundColor Cyan
Write-Host "Date: $(Get-Date)" -ForegroundColor Cyan

# Check Python installation
Write-Header "Checking Python Installation"
try {
    $pythonVersion = & $pythonPath --version 2>&1
    Write-Success "Found Python: $pythonVersion"
} catch {
    Write-Error "Python not found at '$pythonPath'"
    exit 1
}

# Create virtual environment
Write-Header "Setting Up Virtual Environment"
if ($skipVenv) {
    Write-Warning "Skipping venv creation"
} else {
    if (Test-Path $venvPath) {
        Write-Warning "Virtual environment already exists at '$venvPath'"
    } else {
        Write-Host "Creating virtual environment..."
        & $pythonPath -m venv $venvPath
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Virtual environment created"
        } else {
            Write-Error "Failed to create virtual environment"
            exit 1
        }
    }
}

# Activate virtual environment
Write-Header "Activating Virtual Environment"
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    & $activateScript
    Write-Success "Virtual environment activated"
} else {
    Write-Warning "Could not find activation script at $activateScript"
}

# Install dependencies
Write-Header "Installing Dependencies"
$requirementsPath = Join-Path (Get-Location) "requirements.txt"
if (Test-Path $requirementsPath) {
    Write-Host "Installing from requirements.txt..."
    & pip install -r requirements.txt --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Dependencies installed successfully"
    } else {
        Write-Error "Failed to install dependencies"
        exit 1
    }
} else {
    Write-Warning "requirements.txt not found at $requirementsPath"
}

# Run tests
Write-Header "Running Tests"
Write-Host "Executing test suite..."
$testStart = Get-Date

try {
    # Try pytest first
    & python -m pytest tests/test_pipeline.py -v --tb=short
    $testExitCode = $LASTEXITCODE
} catch {
    # Fallback to unittest
    Write-Warning "pytest not available, using unittest"
    & python tests/test_pipeline.py
    $testExitCode = $LASTEXITCODE
}

$testEnd = Get-Date
$testDuration = ($testEnd - $testStart).TotalSeconds

if ($testExitCode -eq 0) {
    Write-Success "All tests passed! (Duration: $testDuration seconds)"
} else {
    Write-Error "Some tests failed (Exit code: $testExitCode)"
}

# Display metrics
Write-Header "Cache & Performance Metrics"

$metricsScript = @"
try:
    from compat import initialize, get_cache, get_metrics
    from data_pipeline.metrics import MetricsCollector
    
    initialize(config_dir="data")
    
    collector = MetricsCollector.get_instance()
    metrics_dict = collector.to_dict()
    
    print("\nCache Metrics:")
    print(f"  Total Hits: {metrics_dict['cache']['total_hits']}")
    print(f"  Total Misses: {metrics_dict['cache']['total_misses']}")
    print(f"  Total Evictions: {metrics_dict['cache']['total_evictions']}")
    print(f"  Hit Rate: {metrics_dict['cache']['hit_rate']:.2%}")
    print(f"  TTL Expirations: {metrics_dict['cache']['ttl_expired']}")
    
    if metrics_dict['cache']['namespace_hit_rates']:
        print("\nNamespace Hit Rates:")
        for ns, rate in metrics_dict['cache']['namespace_hit_rates'].items():
            print(f"  {ns}: {rate:.2%}")
    
    if metrics_dict['cache']['top_10_keys']:
        print("\nTop 10 Most Accessed Keys:")
        for i, (key, count) in enumerate(list(metrics_dict['cache']['top_10_keys'].items())[:10], 1):
            print(f"  {i}. {key}: {count} accesses")
    
    if metrics_dict['performance']:
        print("\nPerformance Metrics:")
        for op, stats in metrics_dict['performance'].items():
            print(f"  {op}:")
            print(f"    Avg: {stats['avg_ms']:.2f}ms")
            print(f"    P95: {stats['p95_ms']:.2f}ms")
            print(f"    P99: {stats['p99_ms']:.2f}ms")
    
except ImportError as e:
    print(f"Warning: Could not import modules for metrics: {e}")
    print("Metrics display requires successful module imports")
except Exception as e:
    print(f"Warning: Error displaying metrics: {e}")
"@

Write-Host "Collecting metrics..."
& python -c $metricsScript

# Summary
Write-Header "Test Summary"
Write-Host "Test Duration: $testDuration seconds"

if ($testExitCode -eq 0) {
    Write-Success "✓ All tests completed successfully"
    Write-Host "Next steps:"
    Write-Host "  1. Review README.md for usage examples"
    Write-Host "  2. Check tests/test_pipeline.py for test patterns"
    Write-Host "  3. Use compat module for legacy API compatibility"
    exit 0
} else {
    Write-Error "✗ Tests failed with exit code $testExitCode"
    Write-Host "Review test output above for details"
    exit 1
}
