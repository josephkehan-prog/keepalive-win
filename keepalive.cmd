@echo off
REM Launcher for keepalive.ps1 — double-click or run "keepalive" from a prompt.
REM Passes through any args, e.g.:  keepalive -Minutes 90 -Quiet
pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0keepalive.ps1" %*
