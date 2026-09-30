#!/bin/bash
set -e
cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
function h3_failed() {
  h3_result=$?
  trap - ERR
  echo ""
  echo "Installazione NON completata. Leggi l'errore sopra."
  echo "Se Homebrew non riconosce macOS, esegui brew update nel Terminale e riprova."
  read -r -p "Premi Invio per chiudere…" || true
  exit "$h3_result"
}
trap h3_failed ERR
h3_macos_version="$(sw_vers -productVersion)"
if [ "${h3_macos_version%%.*}" -lt 15 ]; then
  echo "H3-Music richiede macOS 15 o successivo. Versione rilevata: $h3_macos_version"
  read -r -p "Premi Invio per chiudere…" || true
  exit 1
fi
if ! command -v brew >/dev/null 2>&1; then
  echo "Installa Homebrew da https://brew.sh e poi riapri questo file."
  open https://brew.sh
  read -r -p "Premi Invio per chiudere…"
  exit 1
fi
export HOMEBREW_NO_AUTO_UPDATE=1
echo "Aggiornamento di Homebrew per riconoscere la versione di macOS…"
brew update
export H3_MUSIC_BREW_UPDATED=1
brew install --skip-link python@3.12
"$(brew --prefix python@3.12)/bin/python3.12" scripts/install_macos.py "$@"
echo "Installazione completata. Apri Avvia-Mac.command per usare H3-Music."
read -r -p "Premi Invio per chiudere…"
