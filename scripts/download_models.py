"""Scarica i pesi YuE2 elencati in models/manifest.json.

Riprende i download interrotti: il file parziale resta in <file>.partial e alla
ripartenza si chiede a Hugging Face solo la parte mancante (Range). Alla fine
verifica dimensione e, per i file LFS, lo SHA-256 dichiarato nel manifest.
"""
import json, pathlib, urllib.request, hashlib, concurrent.futures, time

root = pathlib.Path(__file__).resolve().parents[1]
files = json.loads((root/'models/manifest.json').read_text(encoding='utf-8-sig'))
BLOCK = 4 * 1024 * 1024
REPORT = 256 * 1024 * 1024


def check(temp, f):
    """Verifica il file scaricato: dimensione esatta e, se LFS, SHA-256."""
    if temp.stat().st_size != f['size']:
        raise ValueError('size mismatch (%d/%d)' % (temp.stat().st_size, f['size']))
    if f.get('lfs'):
        h = hashlib.sha256()
        with temp.open('rb') as inp:
            while b := inp.read(BLOCK):
                h.update(b)
        if h.hexdigest() != f['lfs']['oid']:
            raise ValueError('hash mismatch')


def get(f):
    target = root/'models/yue2'/f['path']
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size == f['size']:
        return
    temp = target.with_suffix(target.suffix + '.partial')
    url = 'https://huggingface.co/audio-cpp/Yue2-3B-GGUF/resolve/main/' + f['path'] + '?download=true'
    print('Downloading ' + f['path'], flush=True)
    for retry in range(4):
        try:
            done = temp.stat().st_size if temp.exists() else 0
            if done == f['size']:
                check(temp, f)
            else:
                if done > f['size']:
                    done = 0
                request = urllib.request.Request(url)
                if done:
                    request.add_header('Range', 'bytes=%d-' % done)
                with urllib.request.urlopen(request, timeout=120) as src:
                    if done and getattr(src, 'status', 200) != 206:
                        # il server ignora la Range: si riparte da capo
                        done = 0
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
                check(temp, f)
            temp.replace(target)
            print('Verified ' + f['path'], flush=True)
            return
        except Exception as e:
            print(str(e), flush=True)
            if 'hash mismatch' in str(e):
                # file parziale inutilizzabile: alla prossima si riscarica da zero
                try:
                    temp.unlink()
                except OSError:
                    pass
            if retry == 3:
                raise
            time.sleep(2)


with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    list(pool.map(get, files))
