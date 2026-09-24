import urllib.request,pathlib,json,concurrent.futures,hashlib,time
root=pathlib.Path('F:/H3-Music');rev='eab522a8168e8b8b8c4856bf8609cd86198f01fe';p=root/'static/score-assets'
base='https://huggingface.co/m-a-p/SheetSage2/resolve/'+rev+'/render_assets/'
meta=json.loads((p/'manifest.json').read_text())
def get(item):
 name,sha=item;dest=p/name
 if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest()==sha:return
 dest.parent.mkdir(exist_ok=True,parents=True)
 for attempt in range(5):
  try:
   b=urllib.request.urlopen(base+name+'?h3asset=1',timeout=90).read();assert hashlib.sha256(b).hexdigest()==sha;dest.write_bytes(b);return
  except Exception:
   if attempt==4:raise
   time.sleep(1)
with concurrent.futures.ThreadPoolExecutor(4) as e:list(e.map(get,meta['files'].items()))
print('All score assets verified:',len(meta['files']),flush=True)
