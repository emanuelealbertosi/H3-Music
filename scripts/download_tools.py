"""Scarica i pesi dei modelli ausiliari elencati in models/tools-manifest.json.

Sono i modelli che servono per la voce su misura, non per la generazione
musicale: separazione del brano (HTDemucs) e conversione della voce cantata
(SeedVC). I pesi arrivano da una revisione fissa del repository Hugging Face.

Uso: python scripts/download_tools.py [--tool sep|voice|all]

I file vengono messi in models/tools/<cartella>/<file>, che e' la cartella da
passare al motore con --model. I download interrotti riprendono da
<file>.<revisione>.partial e alla fine si verifica dimensione e SHA-256.
"""
import argparse, json, pathlib, urllib.request, urllib.error, hashlib, time

BLOCK = 4 * 1024 * 1024
REPORT = 256 * 1024 * 1024


def load(root):
    return json.loads((root/'models/tools-manifest.json').read_text(encoding='utf-8'))


def check(temp, size, sha):
    if temp.stat().st_size != size:
        raise ValueError('size mismatch (%d/%d)' % (temp.stat().st_size, size))
    h = hashlib.sha256()
    with temp.open('rb') as inp:
        while b := inp.read(BLOCK):
            h.update(b)
    digest = h.hexdigest()
    if digest != sha:
        raise ValueError('hash mismatch')
    return digest


def drop(temp):
    try:
        temp.unlink()
    except OSError:
        pass


def download(root, meta, tool, known):
    target = root/'models/tools'/tool['directory']/tool['file']
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.stat().st_size == tool['size'] and known.get('sha256'):
            print('Gia presente ' + tool['file'], flush=True)
            return known['sha256']
        try:
            return check(target, tool['size'], tool['sha256'])
        except ValueError as e:
            print('%s: %s (lo riscarico)' % (tool['file'], e), flush=True)
            target.unlink()
    temp = target.with_name(target.name + '.' + meta['revision'][:8] + '.partial')
    url = 'https://huggingface.co/%s/resolve/%s/%s/%s' % (meta['repo'], meta['revision'], tool['directory'], tool['file'])
    print('Downloading %s (%.1f MB)' % (tool['file'], tool['size'] / 2**20), flush=True)
    for attempt in range(4):
        try:
            done = temp.stat().st_size if temp.exists() else 0
            if done == tool['size']:
                digest = check(temp, tool['size'], tool['sha256'])
            else:
                if done > tool['size']:
                    done = 0
                request = urllib.request.Request(url, headers={'User-Agent': 'H3-Music-Installer'})
                if done:
                    request.add_header('Range', 'bytes=%d-' % done)
                with urllib.request.urlopen(request, timeout=120) as src:
                    if done and getattr(src, 'status', 200) != 206:
                        done = 0
                    if done:
                        print('  ripreso da %d MB' % (done // (1024 * 1024)), flush=True)
                    nxt = done + REPORT
                    with temp.open('ab' if done else 'wb') as out:
                        while True:
                            block = src.read(BLOCK)
                            if not block:
                                break
                            out.write(block)
                            done += len(block)
                            if done >= nxt:
                                print('  %d%%' % (done * 100 // max(1, tool['size'])), flush=True)
                                nxt = done + REPORT
                digest = check(temp, tool['size'], tool['sha256'])
            temp.replace(target)
            print('Verified ' + tool['file'], flush=True)
            return digest
        except urllib.error.HTTPError as e:
            print('HTTP %d' % e.code, flush=True)
            if e.code in (400, 403, 404, 416):
                drop(temp)
            if attempt == 3:
                raise
            time.sleep(3)
        except Exception as e:
            print(str(e), flush=True)
            if 'hash mismatch' in str(e):
                drop(temp)
            if attempt == 3:
                raise
            time.sleep(2)


def main():
    parser = argparse.ArgumentParser(description='Scarica i modelli ausiliari.')
    parser.add_argument('--tool', choices=['sep', 'voice', 'all'], default='all')
    args = parser.parse_args()

    root = pathlib.Path(__file__).resolve().parents[1]
    meta = load(root)
    record_path = root/'models/tools-installed.json'
    known = {}
    if record_path.exists():
        try:
            known = json.loads(record_path.read_text(encoding='utf-8')).get('tools') or {}
        except Exception:
            known = {}

    wanted = [t for t in meta['tools'] if args.tool == 'all' or t['id'] == args.tool]
    if not wanted:
        raise SystemExit('nessuno strumento da scaricare per --tool %s' % args.tool)

    record = {'repo': meta['repo'], 'revision': meta['revision'], 'tools': dict(known)}
    for tool in wanted:
        digest = download(root, meta, tool, known.get(tool['file'], {}))
        record['tools'][tool['file']] = {'id': tool['id'], 'directory': tool['directory'], 'size': tool['size'], 'sha256': digest}
        print('  %s: pronto in models/tools/%s' % (tool['id'], tool['directory']), flush=True)
    record_path.write_text(json.dumps(record, indent=1), encoding='utf-8')
    print('Strumenti pronti (registrati in models/tools-installed.json)', flush=True)


if __name__ == '__main__':
    main()
