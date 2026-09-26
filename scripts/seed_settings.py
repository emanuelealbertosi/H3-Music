"""Pre-seed app settings for CPU-only installs.

Creates data/music.sqlite with the standard schema and a 'main' settings row
(backend=cpu) ONLY when the database does not exist yet, so an existing user
database is never touched.
"""
import json, sqlite3, pathlib

r = pathlib.Path(__file__).resolve().parents[1]
d = r/'data'; d.mkdir(parents=True, exist_ok=True)
db = d/'music.sqlite'
if db.exists():
    print('DATABASE EXISTS - settings left untouched')
else:
    c = sqlite3.connect(db)
    c.executescript('''PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,title TEXT,request TEXT,created REAL,updated REAL,archived INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,project_id TEXT,kind TEXT,status TEXT,request TEXT,created REAL,started REAL,finished REAL,error TEXT DEFAULT '',favorite INTEGER DEFAULT 0,result TEXT DEFAULT '{}');
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);''')
    c.execute("INSERT OR REPLACE INTO settings VALUES ('main',?)", (json.dumps({'backend':'cpu','threads':8,'llm_url':'http://127.0.0.1:1234/v1','llm_model':'','paused':False}),))
    c.commit(); c.close()
    print('SETTINGS SEEDED (backend=cpu)')
