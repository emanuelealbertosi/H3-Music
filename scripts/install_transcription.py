"""Install the transcription runtime and models (SheetSage2 + MERT-v2).

Usage: python scripts/install_transcription.py --backend cpu|cuda

Downloads everything from Hugging Face at pinned revisions; no local vendor/
folder is required. Writes models/transcription-manifest.json with the
verified SHA-256 values expected by transcription.status().
"""
import argparse, pathlib, urllib.request, zipfile, subprocess, os, json, hashlib, concurrent.futures, re, sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import execution
from scripts.transcription_models import update_files

r = pathlib.Path(__file__).resolve().parents[1]
py = r/'runtime/transcription'
tmp = r/'runtime/install-temp'
SHEET_REV='4f89269db831bdc1880124164a00d4f9385cd129'
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
 tree=json.loads((r/'scripts/mert-tree.json').read_text(encoding='utf-8'))
 files=[f for f in tree if f['type']=='file' and f['path'] in ['config.json','configuration_mert2.py','modeling_mert2.py','model.safetensors','LICENSE']]
 update_files(r,parent,'m-a-p/MERT-v2-FullSong',MERT_REV,files,get)
 sheet=r/'models/SheetSage2';sheet.mkdir(exist_ok=True,parents=True)
 meta=json.loads((r/'scripts/sheetsage2-revision.json').read_text(encoding='utf-8'))
 assert meta['revision']==SHEET_REV
 update_files(r,sheet,'m-a-p/SheetSage2',SHEET_REV,meta['files'],get)
 print('MODELS READY',flush=True)

def runtime(backend):
 if not (py/'Lib/site-packages/pip').exists():
  archive=tmp/'python311.zip';get('https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip',archive)
  with zipfile.ZipFile(archive) as z:z.extractall(py)
  (py/'python311._pth').write_text('python311.zip\n.\nLib/site-packages\nimport site\n',encoding='utf-8')
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
 subprocess.run([str(py/'python.exe'),'-m','pip','install','--no-cache-dir',str(wheel),f'torchaudio==2.8.0+{tag}','--index-url',index],check=True)
 wheel.unlink()
 # requirements.txt arriva dal repository SheetSage2: lo scarichiamo qui, in una
 # copia separata, perche' models() gira in parallelo e potrebbe non averlo ancora
 # scritto (una volta pip e' partito prima del download e l'installazione e' fallita)
 req=tmp/'sheetsage2-requirements.txt'
 get('https://huggingface.co/m-a-p/SheetSage2/resolve/'+SHEET_REV+'/requirements.txt',req)
 subprocess.run([str(py/'python.exe'),'-m','pip','install','--no-cache-dir','-r',str(req)],check=True)
 # Make the runtime independent of a machine-wide VC++ redistributable.
 with zipfile.ZipFile(r/'dist/h3-engine-cpu-win64.zip') as archive:
  for entry in archive.infolist():
   name=pathlib.PurePosixPath(entry.filename).name
   if '140' in name and name.endswith('.dll'):
    for folder in (py,py/'Lib/site-packages/torch/lib'):
     folder.mkdir(parents=True,exist_ok=True)
     target=folder/name
     if not target.exists():target.write_bytes(archive.read(entry))
 (py/'installed.json').write_text(json.dumps({'torch':f'2.8.0+{tag}','python':'3.11.9','revision':SHEET_REV}),encoding='utf-8')
 print('RUNTIME READY',flush=True)

def manifest():
 def sha(rel):return hashlib.file_digest(open(r/rel,'rb'),'sha256').hexdigest()
 m={'sheet_revision':SHEET_REV,'mert_revision':MERT_REV,
    'sha256':{'models/SheetSage2/model.safetensors':sha('models/SheetSage2/model.safetensors'),
              'models/MERT-v2-FullSong/model.safetensors':sha('models/MERT-v2-FullSong/model.safetensors'),
              'models/MERT-v2-FullSong/modeling_mert2.py':sha('models/MERT-v2-FullSong/modeling_mert2.py'),
              'models/MERT-v2-FullSong/configuration_mert2.py':sha('models/MERT-v2-FullSong/configuration_mert2.py')}}
 for p in (r/'models/SheetSage2').glob('*.py'):m['sha256'][p.relative_to(r).as_posix()]=sha(p.relative_to(r))
 path=r/'models/transcription-manifest.json';staged=path.with_suffix('.tmp')
 staged.write_text(json.dumps(m,indent=1),encoding='utf-8');staged.replace(path)

def installed_revision():
 try:return json.loads((r/'models/transcription-manifest.json').read_text(encoding='utf-8')).get('sheet_revision')
 except (OSError,ValueError):return None

def check_idle():
 # Never replace model code underneath a queued or running transcription.
 import sqlite3
 database=r/'data/music.sqlite'
 if database.exists():
  with sqlite3.connect(database) as connection:
   if connection.execute("SELECT 1 FROM jobs WHERE kind='transcribe' AND status IN ('queued','running','cancelling') LIMIT 1").fetchone():
    raise RuntimeError('Attendi la fine delle trascrizioni in coda prima di aggiornare.')

def main():
 global py
 p=argparse.ArgumentParser()
 p.add_argument('--backend',choices=['cpu','cuda'],required=True)
 p.add_argument('--runtime-only',action='store_true',help='Do not download model weights again.')
 p.add_argument('--models-only',action='store_true',help='Update model files without changing Python, torch or CPU/GPU settings.')
 p.add_argument('--preserve-existing',action='store_true',help='Keep a working CPU or CUDA installation on repair.')
 a=p.parse_args()
 os.environ.update(TEMP=str(tmp),TMP=str(tmp),PYTHONUTF8='1',PIP_DISABLE_PIP_VERSION_CHECK='1')
 tmp.mkdir(exist_ok=True,parents=True)
 if a.models_only:
  if a.runtime_only:p.error('--models-only and --runtime-only cannot be combined')
  check_idle();models();manifest();print('TRANSCRIPTION MODELS UPDATED',flush=True);return
 base=r/'runtime/transcription'
 existing=execution.transcription_python(r,a.backend)
 reusable=False
 if existing.is_file():
  try:
   found=execution.check_torch(existing,cuda=a.backend=='cuda')
   reusable=a.preserve_existing or (found['torch']=='2.8.0+'+('cu128' if a.backend=='cuda' else 'cpu') and found['torchaudio']=='2.8.0+'+('cu128' if a.backend=='cuda' else 'cpu'))
  except (OSError,ValueError,subprocess.SubprocessError):pass
 if not reusable:
  # A GPU upgrade is isolated: a failed pip install cannot damage CPU transcription.
  py=r/'runtime/transcription-cuda' if a.backend=='cuda' else base
  py.mkdir(exist_ok=True,parents=True)
  runtime(a.backend)
  execution.check_torch(py/'python.exe',cuda=a.backend=='cuda')
 else:
  print('EXISTING RUNTIME READY',existing,flush=True)
 if not a.runtime_only:
  # Existing validated weights do not need a new network request on repair.
  import transcription
  if not transcription.status(r,a.backend)['ready'] or installed_revision()!=SHEET_REV:
   check_idle();models();manifest()
  else:print('EXISTING MODELS READY',flush=True)
 print('TRANSCRIPTION INSTALL COMPLETE',flush=True)

if __name__=='__main__':main()
