@echo off
REM Runs stop.ps1 without needing to change the PowerShell execution policy.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop.ps1" %*
