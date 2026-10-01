"""Activate a verified native engine, preserving the previous engine and settings."""
import argparse, json, pathlib, shutil, sqlite3, sys, time, uuid
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import execution, windows_engine
from contextlib import closing

def activate(root, candidate, backend='cuda'):
    root = pathlib.Path(root).resolve(); candidate = pathlib.Path(candidate).resolve()
    runtime = root/'runtime'; current = runtime/'engine'
    if not candidate.is_relative_to(root) or candidate == current or current in candidate.parents:
        raise ValueError('La build candidata deve essere una cartella separata dentro H3-Music.')
    windows_engine.enable_utf8(candidate/'audiocpp_cli.exe')
    if backend == 'cuda':
        report = execution.check_cuda(root, candidate/'audiocpp_cli.exe')
    else:
        report = {'engine': execution.check_engine(candidate/'audiocpp_cli.exe', 'cpu')}
    # Prepare a complete replacement before acquiring the database write lock.
    stamp = time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]
    prepared = runtime/('engine-ready-'+stamp)
    previous = runtime/('engine-backup-'+stamp)
    shutil.copytree(candidate, prepared)
    database = root/'data/music.sqlite'
    if not database.is_file():
        raise ValueError('Esegui prima install.bat per preparare il database.')
    with closing(sqlite3.connect(database, timeout=30)) as db:
        db.execute('BEGIN IMMEDIATE')
        active = db.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('queued','running','cancelling')").fetchone()[0]
        if active:
            raise ValueError('Termina o annulla i lavori in coda prima di attivare il nuovo motore. La build e stata conservata.')
        row = db.execute("SELECT value FROM settings WHERE key='main'").fetchone()
        settings = json.loads(row[0]) if row else {}
        old_moved = False; new_moved = False
        try:
            if current.exists():
                current.rename(previous); old_moved = True
            prepared.rename(current); new_moved = True
            settings['backend'] = backend
            db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('main',?)", (json.dumps(settings),))
            db.commit()
        except BaseException:
            if new_moved:
                current.rename(prepared)
            if old_moved:
                previous.rename(current)
            db.rollback()
            raise
    report.update(backend=backend, backup=str(previous) if old_moved else None, engine=str(current))
    (runtime/'engine-activation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--backend',choices=['cpu','cuda'],default='cuda')
    a=p.parse_args()
    print(json.dumps(activate(pathlib.Path(__file__).resolve().parents[1],a.candidate,a.backend),indent=2))
