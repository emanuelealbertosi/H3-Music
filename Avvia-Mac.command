#!/bin/bash
cd "$(dirname "$0")"
if [ ! -x runtime/python/bin/python ]; then
  echo "Apri prima Installa-Mac.command."
  read -r -p "Premi Invio per chiudere…"
  exit 1
fi
runtime/python/bin/python scripts/launch_macos.py || {
  read -r -p "Premi Invio per chiudere…"
  exit 1
}
