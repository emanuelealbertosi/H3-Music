@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\build_engine_cuda.ps1" %*
set "result=%errorlevel%"
if not "%result%"=="0" echo Attivazione GPU non completata. Leggi il motivo qui sopra.
pause
exit /b %result%
