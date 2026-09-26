"""Imposta il backend del motore ('cpu' o 'cuda') nel database dell'app.

Uso: python scripts/set_backend.py cpu|cuda

Conserva tutte le altre impostazioni; l'app rilegge il backend a ogni richiesta,
quindi non serve riavviare il server.
"""
import json
import pathlib
import sqlite3
import sys

root = pathlib.Path(__file__).resolve().parents[1]
db = root / 'data/music.sqlite'
wanted = (sys.argv[1] if len(sys.argv) > 1 else '').strip().lower()
if wanted not in ('cpu', 'cuda'):
    raise SystemExit('Uso: set_backend.py cpu|cuda')
if not db.exists():
    raise SystemExit('Database assente: esegui prima install.bat')

conn = sqlite3.connect(db)
try:
    row = conn.execute("SELECT value FROM settings WHERE key='main'").fetchone()
    settings = json.loads(row[0]) if row else {}
    settings['backend'] = wanted
    conn.execute("INSERT OR REPLACE INTO settings VALUES ('main',?)", (json.dumps(settings),))
    conn.commit()
finally:
    conn.close()
print('backend =', wanted)
