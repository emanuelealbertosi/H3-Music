#!/bin/bash
set -e
cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
if ! command -v brew >/dev/null 2>&1; then
  echo "Installa Homebrew da https://brew.sh e poi riapri questo file."
  open https://brew.sh
  read -r -p "Premi Invio per chiudere…"
  exit 1
fi
export HOMEBREW_NO_AUTO_UPDATE=1
brew install --skip-link python@3.12
"$(brew --prefix python@3.12)/bin/python3.12" scripts/install_macos.py "$@" || {
  echo "Installazione interrotta. Puoi riaprire questo file per riprovare."
  read -r -p "Premi Invio per chiudere…"
  exit 1
}
read -r -p "Installazione completata. Premi Invio per chiudere…"
