@echo off
cd /d "%~dp0"
runtime\python\python.exe -X utf8 scripts\install_assistant.py %*
if errorlevel 1 echo Installazione dell'assistente interrotta. Puoi riprovare.
pause
