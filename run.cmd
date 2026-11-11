@echo off
REM Runs run.ps1 without needing to change the PowerShell execution policy.
REM Usage: run.cmd  [-Docker] [-Reset] [-NoBrowser]
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" %*
