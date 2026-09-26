"""Scarica i pesi YuE2 elencati in models/manifest.json.

Per impostazione predefinita usa una revisione fissa del repository Hugging
Face: il repository a monte cambia (il 26/09/2026 yue2-3b-q8_0.gguf e' stato
sostituito con un file di dimensione diversa) e l'app e' collaudata con quei
file. Con --latest si prende invece l'ultima revisione: in quel caso dimensioni
e hash attesi vengono letti dall'API di Hugging Face e registrati in
models/installed-models.json, che e' il file che l'app consulta per capire se i
modelli sono pronti.

I download interrotti riprendono da <file>.<revisione>.partial chiedendo al
server solo la parte mancante (Range).
"""
import argparse, json, pathlib, urllib.request, urllib.error, hashlib, concurrent.futures, time

PINNED = 'f7cb0712b9c2e5e9dcadc8b3ab23a591756c131b'
REPO = 'audio-cpp/Yue2-3B-GGUF'
# Varianti del modello principale nella revisione fissata: dimensioni e SHA-256
# (LFS) sono quelli dichiarati da Hugging Face per quella revisione.
MANIFEST_MODEL = 'yue2-3b-q8_0.gguf'
MODELS = {
    'q8': {'path': 'yue2-3b-q8_0.gguf', 'size': 4264186432,
           'lfs': 'f3a9e3b197bfd05aa4ae6ab2d4b93f6d57c8cc0ea39a4af7d151f58697c7cfb6'},
    'q4': {'path': 'yue2-3b-q4_0.gguf', 'size': 2665632320,
           'lfs': '97af67d7f800b362faee6e6bec806bddfcccb93f25fd3f9a1012724d95af6f4a'},
}
UA = {'User-Agent': 'H3-Music-Installer'}
BLOCK = 4 * 1024 * 1024
REPORT = 256 * 1024 * 1024


def api(path):
    request = urllib.request.Request('https://huggingface.co/api/models/%s%s' % (REPO, path), headers=UA)
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read())


def tree(revision):
    """{percorso: {size, lfs_oid}} per i file presenti in quella revisione."""
    out = {}
    for e in api('/tree/%s?recursive=true' % revision):
        if e.get('type') == 'file':
            out[e['path']] = {'size': e.get('size'), 'lfs': (e.get('lfs') or {}).get('oid')}
    return out


def lfs_oid(f):
    """L'hash LFS e' un oggetto nel manifest e una stringa nella tabella MODELS."""
    lfs = f.get('lfs')
    return lfs.get('oid') if isinstance(lfs, dict) else lfs


def check(temp, want_size, want_oid):
    """Verifica dimensione e SHA-256; restituisce l'hash calcolato."""
    if temp.stat().st_size != want_size:
        raise ValueError('size mismatch (%d/%d)' % (temp.stat().st_size, want_size))
    h = hashlib.sha256()
    with temp.open('rb') as inp:
        while b := inp.read(BLOCK):
            h.update(b)
    digest = h.hexdigest()
    if want_oid and digest != want_oid:
        raise ValueError('hash mismatch')
    return digest


def drop(temp):
    try:
        temp.unlink()
    except OSError:
        pass


def download(root, f, revision, known):
    target = root/'models/yue2'/f['path']
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():                                   # gia' presente e inutile riscaricarlo
        if target.stat().st_size == f['size'] and known.get('size') == f['size'] and known.get('sha256'):
            print('Gia presente ' + f['path'], flush=True)
            return known['sha256']
        try:
            return check(target, f['size'], lfs_oid(f))
        except ValueError as e:
            print('%s: %s (lo riscarico)' % (f['path'], e), flush=True)
            target.unlink()
    temp = target.with_name(target.name + '.' + revision[:8] + '.partial')
    url = 'https://huggingface.co/%s/resolve/%s/%s' % (REPO, revision, f['path'])
    print('Downloading ' + f['path'], flush=True)
    for retry in range(4):
        try:
            done = temp.stat().st_size if temp.exists() else 0
            if done == f['size']:
                digest = check(temp, f['size'], lfs_oid(f))
            else:
                if done > f['size']:
                    done = 0
                request = urllib.request.Request(url)
                if done:
                    request.add_header('Range', 'bytes=%d-' % done)
                with urllib.request.urlopen(request, timeout=120) as src:
                    if done and getattr(src, 'status', 200) != 206:
                        done = 0                          # il server ignora la Range
                    if done:
                        print('  %s: riprendo da %d MB' % (f['path'], done // (1024 * 1024)), flush=True)
                    next_report = done + REPORT
                    with temp.open('ab' if done else 'wb') as out:
                        while True:
                            block = src.read(BLOCK)
                            if not block:
                                break
                            out.write(block)
                            done += len(block)
                            if done >= next_report:
                                print('  %s %d%%' % (f['path'], done * 100 // max(1, f['size'])), flush=True)
                                next_report = done + REPORT
                digest = check(temp, f['size'], lfs_oid(f))
            temp.replace(target)
            print('Verified ' + f['path'], flush=True)
            return digest
        except urllib.error.HTTPError as e:
            print('HTTP %d su %s' % (e.code, f['path']), flush=True)
            if e.code in (400, 403, 404, 416):            # 416: parziale non allineato
                drop(temp)
            if retry == 3:
                raise
            time.sleep(3)
        except Exception as e:
            print(str(e), flush=True)
            if 'hash mismatch' in str(e):
                drop(temp)
            if retry == 3:
                raise
            time.sleep(2)


def main():
    parser = argparse.ArgumentParser(description='Scarica i pesi YuE2.')
    parser.add_argument('--latest', action='store_true', help="usa l'ultima revisione del repository invece di quella fissata")
    parser.add_argument('--quant', choices=['both', 'q8', 'q4'], default='both',
                        help='quali modelli scaricare: both (default) = Q8 e Q4, cosi si sceglie dall app')
    args = parser.parse_args()

    root = pathlib.Path(__file__).resolve().parents[1]
    manifest = json.loads((root/'models/manifest.json').read_text(encoding='utf-8-sig'))
    wanted = []
    for f in manifest:
        if f['path'] == MANIFEST_MODEL:
            for key in (['q8', 'q4'] if args.quant == 'both' else [args.quant]):
                wanted.append(dict(MODELS[key]))
        else:
            wanted.append(dict(f))
    record_path = root/'models/installed-models.json'
    known = {}
    if record_path.exists():
        try:
            known = json.loads(record_path.read_text(encoding='utf-8')).get('files') or {}
        except Exception:
            known = {}

    if args.latest:
        info = api('')
        revision = info['sha']
        available = tree(revision)
        files = []
        for f in wanted:
            e = available.get(f['path'])
            if not e:
                raise SystemExit('file assente nella revisione %s: %s' % (revision, f['path']))
            files.append({'path': f['path'], 'size': e['size'], 'lfs': e['lfs']})
        print('Ultima revisione: %s' % revision)
    else:
        # dimensioni e hash sono quelli della revisione fissata: nessuna chiamata all'API
        revision = PINNED
        files = wanted
        print('Revisione fissata: %s' % revision)
    print('Modelli: %s' % ', '.join('%s (%.2f GB)' % (MODELS[k]['path'], MODELS[k]['size'] / 2**30)
                                    for k in (['q8', 'q4'] if args.quant == 'both' else [args.quant])), flush=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        digests = list(pool.map(lambda f: download(root, f, revision, known.get(f['path'], {})), files))

    record = {'repo': REPO, 'revision': revision,
              'files': {f['path']: {'size': f['size'], 'sha256': d} for f, d in zip(files, digests)}}
    record_path.write_text(json.dumps(record, indent=1), encoding='utf-8')
    print('Modelli pronti (registrati in models/installed-models.json)', flush=True)


if __name__ == '__main__':
    main()
