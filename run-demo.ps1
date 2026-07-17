$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$backendVenv = Join-Path $backend ".venv"
$backendPython = Join-Path $backendVenv "Scripts\python.exe"
$frontendNodeModules = Join-Path $frontend "node_modules"

function Start-Window {
    param(
        [string]$Command
    )

    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-Command", $Command
    ) -WindowStyle Normal
}

if (-not (Test-Path $backendVenv)) {
    Write-Host "正在创建后端虚拟环境..."
    python -m venv $backendVenv
}

Write-Host "正在确保后端依赖可用..."
& $backendPython -m pip install -r (Join-Path $backend "requirements.txt")

$backendCommand = "Set-Location '$backend'; & '$backendPython' app.py"
Start-Window -Command $backendCommand

if (Get-Command npm -ErrorAction SilentlyContinue) {
    if (-not (Test-Path $frontendNodeModules)) {
        Write-Host "正在安装前端依赖..."
        Push-Location $frontend
        npm install
        Pop-Location
    }

    $frontendCommand = "Set-Location '$frontend'; npm run dev"
    Start-Window -Command $frontendCommand
    Start-Sleep -Seconds 5
    Start-Process "http://127.0.0.1:5173/"
}
else {
    Write-Host "未检测到 npm，已只启动后端页面。"
    Start-Process "http://127.0.0.1:5000/"
}
