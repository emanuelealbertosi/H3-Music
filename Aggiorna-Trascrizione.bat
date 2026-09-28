@echo off
setlocal
cd /d "%~dp0"
if not exist "runtime\python\python.exe" (
  echo Esegui prima install.bat.
  pause
  exit /b 1
)
"runtime\python\python.exe" -X utf8 "scripts\install_transcription.py" --backend cpu --models-only
set "result=%errorlevel%"
if not "%result%"=="0" echo Aggiornamento non completato. Leggi il motivo qui sopra.
if "%result%"=="0" echo Trascrizione aggiornata. Le impostazioni CPU/GPU sono rimaste invariate.
pause
exit /b %result%
