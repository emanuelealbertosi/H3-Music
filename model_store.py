"""Per-installation model location and verified relocation, stdlib only."""
from contextlib import contextmanager, closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import uuid

METADATA = {'manifest.json', 'tools-manifest.json'}


def location(root):
    root = Path(root)
    config = root / 'data/model-location.json'
    if not config.exists():
        return root / 'models'
    try:
        path = Path(json.loads(config.read_text(encoding='utf-8'))['path'])
        if not path.is_absolute():
            raise ValueError()
        return path
    except (OSError, ValueError, KeyError, TypeError):
        raise ValueError('Configurazione della cartella modelli non leggibile: ' + str(config))


def save_location(root, path):
    config = Path(root) / 'data/model-location.json'
    config.parent.mkdir(parents=True, exist_ok=True)
    staged = config.with_suffix('.tmp')
    staged.write_text(json.dumps({'path': str(Path(path).resolve())}), encoding='utf-8')
    staged.replace(config)


@contextmanager
def exclusive(root, name='model-store.lock'):
    """OS lock released even after a crash; shared by the app and installers."""
    lock = Path(root) / 'data' / name
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open('a+b') as stream:
        try:
            if os.fstat(stream.fileno()).st_size == 0:
                stream.write(b'0'); stream.flush()
            stream.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise ValueError('I modelli sono in uso o in aggiornamento. Attendi la fine dell’operazione.')
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def check_idle(root):
    database = Path(os.environ.get('H3_MUSIC_DATA', str(Path(root) / 'data'))) / 'music.sqlite'
    if database.exists():
        with closing(sqlite3.connect(database)) as connection:
            if connection.execute("SELECT 1 FROM jobs WHERE status IN ('queued','running','cancelling') LIMIT 1").fetchone():
                raise ValueError('Termina o annulla i lavori in coda prima di cambiare o aggiornare i modelli.')


def linked(path):
    return path.is_symlink() or getattr(path, 'is_junction', lambda: False)()


def validate_destination(root, source, value, transfer):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Indica la cartella dei modelli.')
    target = Path(value.strip()).expanduser()
    if not target.is_absolute():
        raise ValueError('Indica un percorso completo, per esempio F:\\Modelli\\H3-Music.')
    if any(linked(p) for p in (target, *target.parents)):
        raise ValueError('Scegli una cartella senza collegamenti simbolici o junction.')
    target = target.resolve(); source = Path(source).resolve(); root = Path(root).resolve()
    if target == source:
        return target
    if target.parent == target or root.is_relative_to(target):
        raise ValueError('Scegli una cartella dedicata ai modelli, non la radice del disco o dell’app.')
    if source.is_relative_to(target) or target.is_relative_to(source):
        raise ValueError('La nuova cartella non può contenere o essere contenuta nella precedente.')
    if target.is_relative_to(root) and target != root / 'models':
        raise ValueError('Scegli una cartella fuori da H3-Music, oppure la sua cartella models.')
    if target.exists() and not target.is_dir():
        raise ValueError('Il percorso scelto non è una cartella.')
    if transfer and target.exists() and any(p.name not in METADATA for p in target.iterdir()):
        raise ValueError('Per trasferire i modelli scegli una cartella vuota. Per usare quelli già presenti disattiva il trasferimento.')
    if not transfer and (not target.is_dir() or not any((target / n).is_dir() for n in ('yue2', 'tools', 'SheetSage2', 'MERT-v2-FullSong'))):
        raise ValueError('La cartella non contiene modelli H3-Music: scegli quella che contiene yue2, tools o SheetSage2.')
    return target


def files_to_move(source):
    source = Path(source)
    if any(linked(p) for p in (source, *source.parents)):
        raise ValueError('La cartella modelli contiene un collegamento.')
    if not source.exists():
        return []
    files = []
    for folder, dirs, names in os.walk(source, followlinks=False):
        parent = Path(folder)
        for name in dirs + names:
            path = parent / name
            if linked(path):
                raise ValueError('La cartella modelli contiene un collegamento: ' + str(path))
        for name in names:
            path = parent / name
            if parent == source and name in METADATA:
                continue  # Repository metadata stays with the application.
            files.append((path, path.relative_to(source), path.stat().st_size))
    return files


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def relocate(root, value, transfer=True, progress=lambda **_: None):
    """Caller holds exclusive(). Keep all source files until config commits."""
    source = location(root).resolve()
    target = validate_destination(root, source, value, transfer)
    if os.name == 'nt' and not str(target).isascii():
        import windows_engine
        windows_engine.prepare(root)
    if source == target:
        return {'path': str(target), 'warning': ''}
    if not transfer:
        files_to_move(target)  # Reject nested links before activating an existing store.
        save_location(root, target)
        return {'path': str(target), 'warning': ''}
    if not source.exists() and (Path(root) / 'data/model-location.json').exists():
        raise ValueError('La cartella modelli attuale non è disponibile. Collega il disco prima di trasferirla.')
    files = files_to_move(source)
    snapshots = {p: (p.stat().st_size, p.stat().st_mtime_ns) for p, _, _ in files}
    total = sum(size for _, _, size in files)
    ancestor = target
    while not ancestor.exists():
        if ancestor.parent == ancestor:
            raise ValueError('Il disco di destinazione non è disponibile.')
        ancestor = ancestor.parent
    if shutil.disk_usage(ancestor).free < total + 64 * 1024**2:
        raise ValueError('Spazio insufficiente sul disco di destinazione: servono circa %.1f GB liberi.' % (total / 1e9))
    target.mkdir(parents=True, exist_ok=True)
    staging = target / ('.h3-transfer-' + uuid.uuid4().hex)
    staging.mkdir()
    published = []
    created_dirs = set()
    committed = False
    try:
        done = 0
        for original, relative, size in files:
            candidate = staging / relative
            candidate.parent.mkdir(parents=True, exist_ok=True)
            h = hashlib.sha256()
            with original.open('rb') as inp, candidate.open('xb') as out:
                while block := inp.read(4 * 1024**2):
                    out.write(block); h.update(block); done += len(block)
                    progress(status='copying', file=relative.as_posix(), done=done, total=total)
            progress(status='verifying', file=relative.as_posix(), done=done, total=total)
            if candidate.stat().st_size != size or digest(candidate) != h.hexdigest():
                raise ValueError('Verifica del trasferimento fallita: ' + relative.as_posix())
            if (original.stat().st_size, original.stat().st_mtime_ns) != snapshots[original]:
                raise ValueError('Il file originale è stato modificato durante la copia: ' + relative.as_posix())
            shutil.copystat(original, candidate)
        for _, relative, _ in files:
            dest = target / relative
            parent = dest.parent
            while parent != target and not parent.exists():
                created_dirs.add(parent); parent = parent.parent
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                raise ValueError('La destinazione è stata modificata durante il trasferimento.')
            (staging / relative).replace(dest)
            published.append(dest)
        save_location(root, target)
        committed = True
    finally:
        if not committed:
            for path in published:
                path.unlink(missing_ok=True)
        if staging.resolve().parent != target.resolve():
            raise ValueError('Cartella temporanea esterna alla destinazione.')
        shutil.rmtree(staging)
        if not committed:
            for folder in sorted(created_dirs, key=lambda p: len(p.parts), reverse=True):
                try:
                    folder.rmdir()
                except OSError:
                    pass
    # Never delete a tree. Delete only the exact regular files we copied.
    failures = []
    progress(status='cleaning', done=total, total=total, file='')
    for original, _, _ in files:
        try:
            if (original.stat().st_size, original.stat().st_mtime_ns) != snapshots[original]:
                raise OSError('File originale modificato dopo la copia')
            original.unlink()
        except OSError:
            failures.append(str(original))
    for folder, _, _ in os.walk(source, topdown=False):
        try:
            Path(folder).rmdir()
        except OSError:
            pass
    warning = 'Modelli trasferiti; alcuni file nella vecchia cartella non si sono potuti eliminare.' if failures else ''
    return {'path': str(target), 'warning': warning}
