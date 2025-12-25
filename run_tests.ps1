# PowerShell script to create venv, install deps and run tests (Windows)
Set-StrictMode -Version Latest
$venv = ".venv"
if (-Not (Test-Path $venv)) {
    python -m venv $venv
}
$activate = "$venv\Scripts\Activate.ps1"
. $activate
pip install --upgrade pip
pip install -r requirements.txt
pytest -q --maxfail=1 --disable-warnings
