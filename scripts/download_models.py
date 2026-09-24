import json, pathlib, urllib.request, hashlib, concurrent.futures, time
root = pathlib.Path(__file__).resolve().parents[1]
files = json.loads((root/'models/manifest.json').read_text(encoding='utf-8-sig'))
def get(f):
    target = root/'models/yue2'/f['path']
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size == f['size']: return
    print('Downloading '+f['path'], flush=True)
    temp = target.with_suffix(target.suffix+'.partial')
    url = 'https://huggingface.co/audio-cpp/Yue2-3B-GGUF/resolve/main/'+f['path']+'?download=true'
    for retry in range(4):
        try:
            with urllib.request.urlopen(url, timeout=120) as src, temp.open('wb') as out:
                while block := src.read(4*1024*1024): out.write(block)
            if temp.stat().st_size != f['size']: raise ValueError('size mismatch')
            if f.get('lfs'):
                h=hashlib.sha256()
                with temp.open('rb') as inp:
                    while b:=inp.read(4*1024*1024): h.update(b)
                if h.hexdigest()!=f['lfs']['oid']: raise ValueError('hash mismatch')
            temp.replace(target)
            print('Verified '+f['path'],flush=True)
            return
        except Exception as e:
            print(str(e),flush=True)
            if retry==3: raise
            time.sleep(2)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool: list(pool.map(get,files))
