@echo off
setlocal
cd /d "%~dp0"
"%~dp0runtime\python\python.exe" "%~dp0scripts\tailscale_access.py" --disable
set "result=%errorlevel%"
pause
exit /b %result%
