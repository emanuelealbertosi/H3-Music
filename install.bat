@echo off
rem H3-Music — avvia l'installatore (PowerShell 5.1 o superiore)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
if errorlevel 1 (
  echo.
  echo INSTALLAZIONE INTERROTTO — controlla i messaggi sopra.
)
