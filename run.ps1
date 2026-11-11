<#
CampusBite: set up (if needed) and start the backend and frontend.

  .\run.ps1              Backend in a Python venv + frontend   (no Docker needed)
  .\run.ps1 -Docker      Backend in Docker + frontend
  .\run.ps1 -Reset       Delete the database first, so demo data is recreated
  .\run.ps1 -NoBrowser   Don't open the browser at the end

Safe to run every time. It only installs packages when requirements.txt or
package-lock.json changed, and skips anything that is already running.
Stop everything with .\stop.ps1
#>
param(
    [switch]$Docker,
    [switch]$Reset,
    [switch]$NoBrowser
)

# Native tools (python, npm, docker) write normal messages to stderr, so we check
# exit codes ourselves instead of letting PowerShell treat stderr as an error.
$ErrorActionPreference = 'Continue'

$Root     = $PSScriptRoot
$Backend  = Join-Path $Root 'backend'
$Frontend = Join-Path $Root 'frontend'
$ApiUrl   = 'http://localhost:8000'
$WebUrl   = 'http://localhost:5173'

# ---------- Helpers ----------
function Step($msg) { Write-Host ''; Write-Host "==> $msg" -ForegroundColor Cyan }
function Ok($msg)   { Write-Host "    $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "    $msg" -ForegroundColor Yellow }
function Fail($msg) {
    Write-Host ''
    Write-Host "ERROR: $msg" -ForegroundColor Red
    Write-Host ''
    exit 1
}

function Test-Url($url) {
    try {
        Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Wait-Url($url, $seconds) {
    $deadline = (Get-Date).AddSeconds($seconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-Url $url) { return $true }
        Start-Sleep -Seconds 2
    }
    return $false
}

function Get-Hash($path) { (Get-FileHash -Path $path -Algorithm SHA256).Hash }

# True when the stamp file is missing or holds a different hash than the source file
function Test-NeedsInstall($source, $stamp) {
    if (-not (Test-Path $stamp)) { return $true }
    return ((Get-Content $stamp -Raw).Trim() -ne (Get-Hash $source))
}

# Write text files without a BOM so Python reads them cleanly
function Write-Utf8NoBom($path, $lines) {
    [System.IO.File]::WriteAllLines($path, [string[]]$lines, (New-Object System.Text.UTF8Encoding($false)))
}

# Opens a new PowerShell window that runs a command and stays open to show logs
function Start-Window($title, $folder, $command) {
    $full = "`$Host.UI.RawUI.WindowTitle = '$title'; Set-Location '$folder'; $command"
    Start-Process powershell -WorkingDirectory $folder -ArgumentList @('-NoExit', '-ExecutionPolicy', 'Bypass', '-Command', $full) | Out-Null
}

Write-Host ''
Write-Host 'CampusBite' -ForegroundColor White
if ($Docker) { Write-Host 'Mode: backend in Docker' } else { Write-Host 'Mode: backend in local Python venv' }

# ---------- 1. Check tools ----------
Step 'Checking installed tools'

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Fail 'Node.js was not found. Install Node.js 24 from https://nodejs.org, then open a new PowerShell window.'
}
$nodeVersion = [version]((node --version).Trim().TrimStart('v'))
if ($nodeVersion -lt [version]'22.12.0') { Fail "Node.js $nodeVersion is too old. Install Node.js 24." }
Ok "Node.js $nodeVersion"

$PyExe = $null
$PyArgs = @()
if ($Docker) {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Fail 'Docker was not found. Install Docker Desktop, or run .\run.ps1 without -Docker.'
    }
    docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        Fail 'Docker Desktop is not running. Start it, wait until it shows "Engine running", then run this again.'
    }
    Ok 'Docker Desktop is running'
} else {
    # Prefer the Python launcher with 3.14, fall back to "python"
    if (Get-Command py -ErrorAction SilentlyContinue) {
        py -3.14 --version *> $null
        if ($LASTEXITCODE -eq 0) { $PyExe = 'py'; $PyArgs = @('-3.14') }
    }
    if (-not $PyExe -and (Get-Command python -ErrorAction SilentlyContinue)) { $PyExe = 'python' }
    if (-not $PyExe) { Fail 'Python was not found. Install Python 3.14 from https://www.python.org and tick "Add python.exe to PATH".' }

    $pyVersionText = (& $PyExe @PyArgs --version 2>&1 | Out-String).Trim()
    if ($pyVersionText -notmatch 'Python (\d+)\.(\d+)') {
        Fail "Could not read the Python version ($pyVersionText). Install Python 3.14 from https://www.python.org."
    }
    $pyMinor = [int]$Matches[2]
    if ([int]$Matches[1] -ne 3 -or $pyMinor -lt 11) { Fail "$pyVersionText is too old. Install Python 3.14." }
    if ($pyMinor -ne 14) { Warn "$pyVersionText found. The project targets Python 3.14 but should still work." }
    Ok $pyVersionText
}

# ---------- 2. Environment files ----------
Step 'Checking .env files'

$envFile = Join-Path $Backend '.env'
if (-not (Test-Path $envFile)) {
    Copy-Item (Join-Path $Backend '.env.example') $envFile
    Ok 'Created backend\.env from .env.example'
}

$envLines = @(Get-Content $envFile)
$hasSecret = $envLines | Where-Object { $_ -match '^JWT_SECRET_KEY=\S+' -and $_ -notmatch '^JWT_SECRET_KEY=change-me\s*$' }
if (-not $hasSecret) {
    $bytes = New-Object byte[] 48
    (New-Object System.Security.Cryptography.RNGCryptoServiceProvider).GetBytes($bytes)
    $secret = [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
    $envLines = @($envLines | Where-Object { $_ -notmatch '^JWT_SECRET_KEY=' }) + "JWT_SECRET_KEY=$secret"
    Write-Utf8NoBom $envFile $envLines
    Ok 'Generated a new JWT secret in backend\.env'
} else {
    Ok 'backend\.env has a JWT secret'
}

if (-not ($envLines | Where-Object { $_ -match '^OPENAI_API_KEY=\S+' })) {
    Warn 'OPENAI_API_KEY is empty in backend\.env. The app works, but AI insights will show "AI is not set up".'
} else {
    Ok 'backend\.env has an OpenAI key'
}

$frontendEnv = Join-Path $Frontend '.env'
if (-not (Test-Path $frontendEnv)) {
    Copy-Item (Join-Path $Frontend '.env.example') $frontendEnv
    Ok 'Created frontend\.env from .env.example'
} else {
    Ok 'frontend\.env exists'
}

# ---------- 3. Backend ----------
$backendRunning = Test-Url $ApiUrl

if ($Reset) {
    Step 'Resetting the database'
    if ($backendRunning -and -not $Docker) { Fail 'The backend is running. Run .\stop.ps1 first, then .\run.ps1 -Reset' }
    if ($Docker) {
        Push-Location $Root
        docker compose down -v
        Pop-Location
        $backendRunning = Test-Url $ApiUrl
        Ok 'Docker container and database volume removed'
    } else {
        $dbFile = Join-Path $Backend 'campusbite.db'
        if (Test-Path $dbFile) { Remove-Item $dbFile -Force; Ok 'Deleted backend\campusbite.db' } else { Ok 'No database file to delete' }
    }
}

if ($Docker) {
    Step 'Building and starting the backend container'
    if ($backendRunning) {
        Ok "Something is already answering on $ApiUrl, so it was left as is. Run .\stop.ps1 first to switch modes."
    } else {
        Push-Location $Root
        docker compose up --build -d
        $code = $LASTEXITCODE
        Pop-Location
        if ($code -ne 0) { Fail 'docker compose failed. Read the error above.' }
        Start-Window 'CampusBite backend logs' $Root 'docker compose logs -f backend'
        Ok 'Container started. Logs are in the "CampusBite backend logs" window.'
    }
} else {
    $venvPython = Join-Path $Backend 'venv\Scripts\python.exe'
    if (-not (Test-Path $venvPython)) {
        Step 'Creating the Python virtual environment'
        Push-Location $Backend
        & $PyExe @PyArgs -m venv venv
        Pop-Location
        if (-not (Test-Path $venvPython)) { Fail 'Could not create backend\venv. Read the error above.' }
        Ok 'Created backend\venv'
    }

    $requirements = Join-Path $Backend 'requirements.txt'
    $reqStamp = Join-Path $Backend 'venv\.requirements.sha256'
    if (Test-NeedsInstall $requirements $reqStamp) {
        Step 'Installing backend packages (takes a minute the first time)'
        & $venvPython -m pip install --disable-pip-version-check -r $requirements
        if ($LASTEXITCODE -ne 0) { Fail 'pip install failed. Read the error above.' }
        Set-Content -Path $reqStamp -Value (Get-Hash $requirements)
        Ok 'Backend packages installed'
    } else {
        Step 'Backend packages'
        Ok 'Up to date'
    }

    Step 'Starting the backend'
    if ($backendRunning) {
        Ok "Already running at $ApiUrl"
    } else {
        Start-Window 'CampusBite backend' $Backend "& '.\venv\Scripts\python.exe' -m uvicorn main:app --reload --reload-dir app --port 8000"
        Ok 'Started in the "CampusBite backend" window'
    }
}

# ---------- 4. Frontend ----------
$lockFile = Join-Path $Frontend 'package-lock.json'
$lockStamp = Join-Path $Frontend 'node_modules\.package-lock.sha256'
if (Test-NeedsInstall $lockFile $lockStamp) {
    Step 'Installing frontend packages (takes a minute the first time)'
    Push-Location $Frontend
    npm.cmd ci --no-audit --no-fund
    $code = $LASTEXITCODE
    Pop-Location
    if ($code -ne 0) { Fail 'npm ci failed. Read the error above.' }
    Set-Content -Path $lockStamp -Value (Get-Hash $lockFile)
    Ok 'Frontend packages installed'
} else {
    Step 'Frontend packages'
    Ok 'Up to date'
}

Step 'Starting the frontend'
if (Test-Url $WebUrl) {
    Ok "Already running at $WebUrl"
} else {
    Start-Window 'CampusBite frontend' $Frontend 'npm.cmd run dev'
    Ok 'Started in the "CampusBite frontend" window'
}

# ---------- 5. Wait until both answer ----------
Step 'Waiting for the app to come up'
if (Wait-Url $ApiUrl 90) { Ok "Backend ready:  $ApiUrl  (API docs: $ApiUrl/docs)" }
else { Fail 'The backend did not start within 90 seconds. Check its window for the error.' }
if (Wait-Url $WebUrl 60) { Ok "Frontend ready: $WebUrl" }
else { Fail 'The frontend did not start within 60 seconds. Check its window for the error.' }

if (-not $NoBrowser) { Start-Process $WebUrl }

Write-Host ''
Write-Host 'CampusBite is running.' -ForegroundColor Green
Write-Host '  Demo logins (password for all: password123)'
Write-Host '    customer@campusbite.com   owner1@campusbite.com   delivery1@campusbite.com'
Write-Host '  Stop everything:  .\stop.ps1'
Write-Host ''
