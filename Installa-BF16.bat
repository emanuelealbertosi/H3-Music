@echo off
setlocal
cd /d "%~dp0"
if not exist "runtime\python\python.exe" (
 echo Esegui prima install.bat per preparare H3-Music.
 pause
 exit /b 1
)
"runtime\python\python.exe" -X utf8 "scripts\download_models.py" --quant bf16
set "result=%errorlevel%"
if "%result%"=="0" echo BF16 pronto. Apri Sistema, seleziona BF16 e salva le preferenze.
pause
exit /b %result%
