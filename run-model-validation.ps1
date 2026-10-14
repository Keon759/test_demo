param([string]$Model, [string]$Output)
$ErrorActionPreference = "Stop"
$demoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$demoPython = Join-Path $demoRoot "backend\.venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $demoPython)) { throw "Create backend/.venv and install backend/requirements.txt first." }
$previousKey = $env:OPENAI_API_KEY
$previousModel = $env:OPENAI_MODEL
$secretInput = $null
$resultCode = 2
Push-Location $demoRoot
try {
    if (-not $Model) { $Model = $env:OPENAI_MODEL }
    if ([string]::IsNullOrWhiteSpace($Model)) { $Model = "gpt-6-astra" }
    $env:OPENAI_MODEL = $Model.Trim()
    if ($env:OPENAI_MODEL -match '^sk-' -or -not ($env:OPENAI_MODEL -match '^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$')) {
        throw "The model field must contain a model ID, not an API key. Run without -Model to use the default."
    }
    Write-Host "Model configured automatically. Only paste the API key at the hidden prompt below."
    if (-not $env:OPENAI_API_KEY) {
        $secretInput = Read-Host "Paste your OpenAI API key (input is hidden; not saved)" -AsSecureString
        $keyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secretInput)
        try { $env:OPENAI_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPointer) }
        finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPointer) }
    }
    if (-not $env:OPENAI_API_KEY) { throw "An API key is required." }
    Write-Host "One model API request will be sent and may incur API charges. Results stay in artifacts/."
    if ($Output) { & $demoPython scripts/validate_model.py --output $Output }
    else { & $demoPython scripts/validate_model.py }
    $resultCode = $LASTEXITCODE
} finally {
    $env:OPENAI_API_KEY = $previousKey
    $env:OPENAI_MODEL = $previousModel
    if ($secretInput) { $secretInput.Dispose() }
    Pop-Location
}
exit $resultCode
