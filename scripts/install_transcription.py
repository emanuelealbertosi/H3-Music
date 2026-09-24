import pathlib,urllib.request,zipfile,subprocess,os,json,hashlib,concurrent.futures
r=pathlib.Path('F:/H3-Music');py=r/'runtime/transcription';py.mkdir(exist_ok=True)
tmp=r/'runtime/install-temp';tmp.mkdir(exist_ok=True)
os.environ.update(TEMP=str(tmp),TMP=str(tmp),PYTHONUTF8='1',PIP_DISABLE_PIP_VERSION_CHECK='1')
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
 parent=r/'models/MERT-v2-FullSong';parent.mkdir(exist_ok=True)
 rev='d8ba1c745e733b3908ce6ad16ebeb17ac7600a42'
 tree=json.loads((r/'scripts/mert-tree.json').read_text())
 for f in tree:
  if f['type']=='file' and f['path'] in ['config.json','configuration_mert2.py','modeling_mert2.py','model.safetensors','LICENSE']:
   dest=parent/f['path'];get('https://huggingface.co/m-a-p/MERT-v2-FullSong/resolve/'+rev+'/'+f['path'],dest)
   if f.get('lfs'):assert hashlib.file_digest(open(dest,'rb'),'sha256').hexdigest()==f['lfs']['oid']
   print('MODEL',dest.name,dest.stat().st_size,flush=True)
 sheet=r/'models/SheetSage2';sheet.mkdir(exist_ok=True)
 meta=json.loads((r/'vendor/SheetSage2/revision.json').read_text())
 import shutil
 for p in (r/'vendor/SheetSage2').iterdir():
  if p.is_file():shutil.copyfile(p,sheet/p.name)
 dest=sheet/'model.safetensors';get('https://huggingface.co/m-a-p/SheetSage2/resolve/'+meta['revision']+'/model.safetensors',dest)
 assert hashlib.file_digest(open(dest,'rb'),'sha256').hexdigest()=='b235f68091a5f5b644000f2b5acb57d1e70432aca2b34ab1b9cf27236e1f4274'
 print('MODELS READY',flush=True)
def runtime():
 if not (py/'Lib/site-packages/pip').exists():
  archive=tmp/'python311.zip';get('https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip',archive)
  with zipfile.ZipFile(archive) as z:z.extractall(py)
  (py/'python311._pth').write_text('python311.zip\n.\nLib/site-packages\nimport site\n')
  bootstrap=tmp/'get-pip.py';get('https://bootstrap.pypa.io/get-pip.py',bootstrap)
  subprocess.run([str(py/'python.exe'),str(bootstrap),'--no-cache-dir'],check=True)
 wheel_cache=tmp;wheel_cache.mkdir(exist_ok=True,parents=True)
 wheel=wheel_cache/'torch-2.8.0+cu128-cp311-cp311-win_amd64.whl'
 get('https://download.pytorch.org/whl/cu128/torch-2.8.0%2Bcu128-cp311-cp311-win_amd64.whl',wheel)
 import re,html
 index=urllib.request.urlopen('https://download.pytorch.org/whl/cu128/torch/').read().decode()
 expected=re.search(r'torch-2\.8\.0(?:%2B|\+)cu128-cp311-cp311-win_amd64\.whl#sha256=([a-f0-9]{64})',index).group(1)
 assert hashlib.file_digest(open(wheel,'rb'),'sha256').hexdigest()==expected
 subprocess.run([str(py/'python.exe'),'-m','pip','install','--no-cache-dir',str(wheel),'torchaudio==2.8.0','--index-url','https://download.pytorch.org/whl/cu128'],check=True)
 wheel.unlink()
 subprocess.run([str(py/'python.exe'),'-m','pip','install','--no-cache-dir','-r',str(r/'vendor/SheetSage2/requirements.txt')],check=True)
 (py/'installed.json').write_text(json.dumps({'torch':'2.8.0+cu128','python':'3.11.9','revision':'eab522a8168e8b8b8c4856bf8609cd86198f01fe'}))
 print('RUNTIME READY',flush=True)
with concurrent.futures.ThreadPoolExecutor(2) as pool:
 futures=[pool.submit(models),pool.submit(runtime)]
 for f in futures:f.result()
