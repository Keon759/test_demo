$ErrorActionPreference = "Stop"
$demoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$demoPython = Join-Path $demoRoot "backend\.venv\Scripts\python.exe"
Push-Location $demoRoot
try {
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw "Install Node.js 20.19+ or 22.12+ first." }
    if (-not (Test-Path -LiteralPath $demoPython)) {
        python -m venv backend/.venv
        if ($LASTEXITCODE -ne 0) { throw "Could not create Python environment." }
    }
    & $demoPython -m pip install -r backend/requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "Backend dependency installation failed." }
    npm.cmd --prefix frontend ci
    if ($LASTEXITCODE -ne 0) { throw "Frontend dependency installation failed." }
    & $demoPython scripts/start_demo.py
} finally { Pop-Location }
