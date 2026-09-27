@echo off
setlocal
cd /d "%~dp0"
"%~dp0runtime\python\python.exe" -X utf8 "%~dp0scripts\set_backend.py" cpu
set "result=%errorlevel%"
pause
exit /b %result%
