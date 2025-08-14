@'
<# 
.SYNOPSIS
  One-shot setup for the AI Pentest Harness (Windows/VS Code).
.DESCRIPTION
  - Temporarily bypasses execution policy for this session
  - Creates .venv (if missing)
  - Installs/updates pip + requirements
  - Runs tools\preflight.py inside the venv
#>

param(
  [string]$ProjectPath = "."
)

$ErrorActionPreference = "Stop"

function Write-Info($msg){ Write-Host "[i] $msg" -ForegroundColor Cyan }
function Write-Ok($msg){ Write-Host "[✓] $msg" -ForegroundColor Green }
function Write-Warn($msg){ Write-Host "[!] $msg" -ForegroundColor Yellow }
function Write-Err($msg){ Write-Host "[x] $msg" -ForegroundColor Red }

# Resolve path & cd
$Project = Resolve-Path $ProjectPath
Set-Location $Project

Write-Info "Process-scoped ExecutionPolicy → Bypass"
try {
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
} catch {
  Write-Warn "Could not set ExecutionPolicy (Process). Continuing..."
}

# Ensure requirements.txt exists
if (!(Test-Path ".\requirements.txt")) {
  Write-Err "requirements.txt not found in $Project"
  exit 1
}

# Create venv if missing
$venvPy = ".\.venv\Scripts\python.exe"
if (!(Test-Path $venvPy)) {
  Write-Info "Creating virtualenv at .\.venv"
  try {
    $py = (Get-Command py -ErrorAction SilentlyContinue)
    if ($py) {
      & py -3 -m venv .venv
    } else {
      & python -m venv .venv
    }
  } catch {
    Write-Err "Failed to create venv: $($_.Exception.Message)"
    exit 1
  }
} else {
  Write-Ok "Found existing venv (.venv)"
}

# Upgrade pip & install reqs using venv python
Write-Info "Upgrading pip in venv"
& $venvPy -m pip install --upgrade pip

Write-Info "Installing requirements"
& $venvPy -m pip install -r requirements.txt

# Run preflight inside venv
if (!(Test-Path ".\tools\preflight.py")) {
  Write-Warn "tools\preflight.py missing. Creating a minimal placeholder."
  @"
print("Preflight placeholder – no checks run.")
"@ | Out-File -Encoding utf8 ".\tools\preflight.py"
}

Write-Info "Running preflight checks (inside venv)"
& $venvPy ".\tools\preflight.py"

Write-Ok "Bootstrap complete."
Write-Host ""
Write-Host "Next:" -ForegroundColor Cyan
Write-Host "  # Passive healthcheck" -ForegroundColor Gray
Write-Host "  .\.venv\Scripts\python.exe harness.py https://example.com --max-pages 80 --timeout 12" -ForegroundColor Gray
Write-Host "  # Active (with plan & permission)" -ForegroundColor Gray
Write-Host "  .\.venv\Scripts\python.exe harness.py https://example.com --plan plans\active_plan.yaml --run-active --outdir out_client" -ForegroundColor Gray
'@ | Set-Content -Encoding UTF8 .\bootstrap.ps1
