#!/bin/bash
cd "$(dirname "$0")" || exit 1
runtime/python/bin/python -X utf8 scripts/install_assistant.py "$@"
result=$?
read -r -p "Premi Invio per chiudere…"
exit "$result"
