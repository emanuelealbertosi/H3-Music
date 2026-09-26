"""Install the transcription runtime and models (SheetSage2 + MERT-v2).

Usage: python scripts/install_transcription.py --backend cpu|cuda

Downloads everything from Hugging Face at pinned revisions; no local vendor/
folder is required. Writes models/transcription-manifest.json with the
verified SHA-256 values expected by transcription.status().
"""
import argparse, pathlib, urllib.request, zipfile, subprocess, os, json, hashlib, concurrent.futures, re

r = pathlib.Path(__file__).resolve().parents[1]
py = r/'runtime/transcription'
tmp = r/'runtime/install-temp'
SHEET_REV='eab522a8168e8b8b8c4856bf8609cd86198f01fe'
MERT_REV='d8ba1c745e733b3908ce6ad16ebeb17ac7600a42'

def get(url,p):
 import time
 with urllib.request.urlopen(urllib.request.Request(url,headers={'Range':'bytes=0-0'}),timeout=60) as a:
  cr=a.headers.get('Content-Range')
  if not cr:
   with open(p,'wb') as b:
    while chunk:=a.read(1024*1024):b.write(chunk)
   return
  size=int(cr.split('/')[-1])
 if size<16000000:
  with urllib.request.urlopen(url,timeout=90) as a,open(p,'wb') as b:
   while chunk:=a.read(1024*1024):b.write(chunk)
  return
 complete=set()
 if p.exists() and p.stat().st_size==size:
  with open(p,'rb') as f:
   for start in range(0,size,1024*1024):
    f.seek(start);first=f.read(256);f.seek(min(size,start+1024*1024)-256);last=f.read(256)
    if any(first) and any(last):complete.add(start//(1024*1024))
 else:
  with open(p,'wb') as f:f.truncate(size)
 print('RESUME',p.name,len(complete),'blocks',flush=True)
 chunk_size=1024*1024
 def part(start):
  if start//(1024*1024) in complete:return
  end=min(size,start+chunk_size)-1
  for attempt in range(4):
   try:
    request=urllib.request.Request(url+('?h3part=' if '?' not in url else '&h3part=')+str(start)+'s1m',headers={'Range':f'bytes={start}-{end}'})
    with urllib.request.urlopen(request,timeout=90) as a:
     assert a.status==206 and a.headers['Content-Range']==f'bytes {start}-{end}/{size}'
     data=a.read();assert len(data)==end-start+1
    with open(p,'r+b') as f:f.seek(start);f.write(data)
    if start%(128*1024*1024)==0:print('DOWNLOAD',p.name,round(start/size*100),'%',flush=True)
    return
   except Exception:
    if attempt==3:raise
    time.sleep(2)
 with concurrent.futures.ThreadPoolExecutor(12) as pool:list(pool.map(part,range(0,size,chunk_size)))

def models():
 parent=r/'models/MERT-v2-FullSong';parent.mkdir(exist_ok=True,parents=True)
 tree=json.loads((r/'scripts/mert-tree.json').read_text())
 for f in tree:
  if f['type']=='file' and f['path'] in ['config.json','configuration_mert2.py','modeling_mert2.py','model.safetensors','LICENSE']:
   dest=parent/f['path'];get('https://huggingface.co/m-a-p/MERT-v2-FullSong/resolve/'+MERT_REV+'/'+f['path'],dest)
   if f.get('lfs'):assert hashlib.file_digest(open(dest,'rb'),'sha256').hexdigest()==f['lfs']['oid']
   print('MODEL',dest.name,dest.stat().st_size,flush=True)
 sheet=r/'models/SheetSage2';sheet.mkdir(exist_ok=True,parents=True)
 meta=json.loads((r/'scripts/sheetsage2-revision.json').read_text())
 assert meta['revision']==SHEET_REV
 for f in meta['files']:
  if f['type']!='file':continue
  dest=sheet/f['path'];get('https://huggingface.co/m-a-p/SheetSage2/resolve/'+SHEET_REV+'/'+f['path'],dest)
  assert dest.stat().st_size==f['size'],f['path']
 model=sheet/'model.safetensors'
 assert hashlib.file_digest(open(model,'rb'),'sha256').hexdigest()=='b235f68091a5f5b644000f2b5acb57d1e70432aca2b34ab1b9cf27236e1f4274'
 print('MODELS READY',flush=True)

def runtime(backend):
 if not (py/'Lib/site-packages/pip').exists():
  archive=tmp/'python311.zip';get('https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip',archive)
  with zipfile.ZipFile(archive) as z:z.extractall(py)
  (py/'python311._pth').write_text('python311.zip\n.\nLib/site-packages\nimport site\n')
  bootstrap=tmp/'get-pip.py';get('https://bootstrap.pypa.io/get-pip.py',bootstrap)
  subprocess.run([str(py/'python.exe'),str(bootstrap),'--no-cache-dir'],check=True)
 wheel_cache=tmp;wheel_cache.mkdir(exist_ok=True,parents=True)
 if backend=='cpu':index='https://download.pytorch.org/whl/cpu';tag='cpu'
 else:index='https://download.pytorch.org/whl/cu128';tag='cu128'
 wheel=wheel_cache/f'torch-2.8.0+{tag}-cp311-cp311-win_amd64.whl'
 get(index+f'/torch-2.8.0%2B{tag}-cp311-cp311-win_amd64.whl',wheel)
 page=urllib.request.urlopen(index+'/torch/').read().decode()
 expected=re.search(r'torch-2\.8\.0(?:%2B|\+)' + re.escape(tag) + r'-cp311-cp311-win_amd64\.whl#sha256=([a-f0-9]{64})', page).group(1)
 assert hashlib.file_digest(open(wheel,'rb'),'sha256').hexdigest()==expected
 subprocess.run([str(py/'python.exe'),'-m','pip','install','--no-cache-dir',str(wheel),'torchaudio==2.8.0','--index-url',index],check=True)
 wheel.unlink()
 subprocess.run([str(py/'python.exe'),'-m','pip','install','--no-cache-dir','-r',str(r/'models/SheetSage2/requirements.txt')],check=True)
 (py/'installed.json').write_text(json.dumps({'torch':f'2.8.0+{tag}','python':'3.11.9','revision':SHEET_REV}))
 print('RUNTIME READY',flush=True)

def manifest():
 def sha(rel):return hashlib.file_digest(open(r/rel,'rb'),'sha256').hexdigest()
 m={'sheet_revision':SHEET_REV,'mert_revision':MERT_REV,
    'sha256':{'models/SheetSage2/model.safetensors':sha('models/SheetSage2/model.safetensors'),
              'models/MERT-v2-FullSong/model.safetensors':sha('models/MERT-v2-FullSong/model.safetensors'),
              'models/MERT-v2-FullSong/modeling_mert2.py':sha('models/MERT-v2-FullSong/modeling_mert2.py'),
              'models/MERT-v2-FullSong/configuration_mert2.py':sha('models/MERT-v2-FullSong/configuration_mert2.py')}}
 (r/'models/transcription-manifest.json').write_text(json.dumps(m,indent=1))

p=argparse.ArgumentParser()
p.add_argument('--backend',choices=['cpu','cuda'],required=True)
a=p.parse_args()
os.environ.update(TEMP=str(tmp),TMP=str(tmp),PYTHONUTF8='1',PIP_DISABLE_PIP_VERSION_CHECK='1')
tmp.mkdir(exist_ok=True,parents=True);py.mkdir(exist_ok=True,parents=True)
with concurrent.futures.ThreadPoolExecutor(2) as pool:
 futures=[pool.submit(models),pool.submit(runtime,a.backend)]
 for f in futures:f.result()
manifest()
print('TRANSCRIPTION INSTALL COMPLETE',flush=True)
