#!/bin/bash
cd "$(dirname "$0")"
if [ ! -x runtime/python/bin/python ]; then
  echo "Apri prima Installa-Mac.command."
  read -r -p "Premi Invio per chiudere…"
  exit 1
fi
runtime/python/bin/python scripts/install_transcription.py --backend cpu --models-only
result=$?
read -r -p "Premi Invio per chiudere…"
exit "$result"
