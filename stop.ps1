<#
CampusBite: stop everything started by run.ps1.

  .\stop.ps1    Closes the backend and frontend windows, frees ports 8000 and 5173,
                and stops the Docker container if it is running. Your data is kept.
#>
$ErrorActionPreference = 'Continue'
$Root = $PSScriptRoot

function Ok($msg) { Write-Host "    $msg" -ForegroundColor Green }

Write-Host ''
Write-Host '==> Stopping CampusBite' -ForegroundColor Cyan

# 1. Close the windows run.ps1 opened, together with everything running inside them
$windows = Get-CimInstance Win32_Process -Filter "Name='powershell.exe' OR Name='pwsh.exe'" |
    Where-Object { $_.CommandLine -like "*WindowTitle = 'CampusBite*" }
foreach ($w in $windows) {
    taskkill /PID $w.ProcessId /T /F *> $null
}
if ($windows) { Ok "Closed $(@($windows).Count) CampusBite window(s)" } else { Ok 'No CampusBite windows were open' }

# 2. Anything still holding the ports (for example a server started by hand)
foreach ($port in 8000, 5173) {
    $owners = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($procId in $owners) {
        # Docker Desktop owns port 8000 while the container runs; the container is stopped below instead
        $name = (Get-Process -Id $procId -ErrorAction SilentlyContinue).ProcessName
        if ($name -and $name -notmatch 'docker|com\.docker|wslrelay|vpnkit') {
            taskkill /PID $procId /T /F *> $null
            Ok "Freed port $port (stopped $name)"
        }
    }
}

# 3. Docker container, if Docker is installed and running
if (Get-Command docker -ErrorAction SilentlyContinue) {
    docker info *> $null
    if ($LASTEXITCODE -eq 0) {
        Push-Location $Root
        $running = docker compose ps -q 2>$null
        if ($running) {
            docker compose down
            Ok 'Stopped the backend container (database volume kept)'
        }
        Pop-Location
    }
}

Write-Host ''
Write-Host 'CampusBite stopped.' -ForegroundColor Green
Write-Host ''
