"""Optional assistant install; no global Python packages or model auto-downloads."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import urllib.request
import uuid
import zipfile
from contextlib import closing

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import model_store
import platform_runtime

def download(url,dest,sha,size=None):
 if dest.is_file() and (size is None or dest.stat().st_size==size):
  with dest.open('rb') as stream:
   if hashlib.file_digest(stream,'sha256').hexdigest()==sha:return
 dest.parent.mkdir(parents=True,exist_ok=True)
 if size and shutil.disk_usage(dest.parent).free<size+512*1024**2:raise RuntimeError('Spazio insufficiente per il modello dell’assistente (circa 2,5 GB più il margine di installazione).')
 temp=dest.with_suffix(dest.suffix+'.partial')
 try:
  with urllib.request.urlopen(url,timeout=120) as response,temp.open('wb') as output:shutil.copyfileobj(response,output)
  with temp.open('rb') as stream:
   if hashlib.file_digest(stream,'sha256').hexdigest()!=sha:raise RuntimeError('Download non integro: riprova.')
  if size and temp.stat().st_size!=size:raise RuntimeError('Download incompleto: riprova.')
  temp.replace(dest)
 finally:temp.unlink(missing_ok=True)

def extract(archive,destination):
 destination.mkdir(parents=True,exist_ok=True)
 if archive.suffix=='.zip':
  with zipfile.ZipFile(archive) as package:
   for item in package.infolist():
    target=(destination/item.filename).resolve()
    if not target.is_relative_to(destination.resolve()):raise RuntimeError('Archivio del runtime non valido.')
   package.extractall(destination)
 else:
  with tarfile.open(archive) as package:
   # No paths or symlink targets may escape the extraction directory.
   for item in package.getmembers():
    target=(destination/item.name).resolve()
    if not target.is_relative_to(destination.resolve()):raise RuntimeError('Archivio del runtime non valido.')
    if item.issym() and not (target.parent/item.linkname).resolve().is_relative_to(destination.resolve()):raise RuntimeError('Collegamento del runtime non valido.')
    if item.islnk() and not (destination/item.linkname).resolve().is_relative_to(destination.resolve()):raise RuntimeError('Collegamento del runtime non valido.')
    if not (item.isfile() or item.isdir() or item.issym() or item.islnk()):raise RuntimeError('Tipo di file del runtime non valido.')
   package.extractall(destination)

def install(args):
 pinned=json.loads((ROOT/'scripts/assistant-runtime.json').read_text())
 destination=ROOT/'runtime/assistant';stage=destination.with_name('assistant-stage-'+uuid.uuid4().hex[:12])
 stage.mkdir(parents=True)
 marker={'backends':['cpu'],'source':'ggml-org/llama.cpp','release':pinned['release'],'optimized_mtp':False}
 try:
  if args.local_engine:
   source=Path(args.local_engine).resolve()
   if not (source/'llama-server.exe').is_file():raise RuntimeError('La cartella scelta non contiene llama-server.exe.')
   for item in source.iterdir():
    if item.is_file() and (item.suffix in ('.exe','.dll') or item.name.startswith('LICENSE')):shutil.copy2(item,stage/item.name)
   marker.update(source='local-optimized',backends=['cpu','cuda'],optimized_mtp=args.optimized_mtp,library_path=args.library_path or '')
   if (source/'build-manifest.json').is_file():marker['build']=json.loads((source/'build-manifest.json').read_text())
  else:
   if platform_runtime.windows():keys=['windows-cpu'] if not args.gpu else ['windows-cuda','windows-cudart']
   elif platform_runtime.macos():keys=['macos-'+platform.machine()];marker['backends']=['cpu','metal']
   else:raise RuntimeError('Installazione automatica disponibile su Windows x64 e Mac arm64/x86_64.')
   if args.gpu and platform_runtime.windows():marker['backends']=['cpu','cuda']
   for key in keys:
    asset=pinned['assets'][key];archive=stage/asset['name']
    print('Scarico il motore dell’assistente: '+asset['name'],flush=True)
    download(pinned['base_url']+asset['name'],archive,asset['sha256'])
    extracted=stage/('extract-'+key);extract(archive,extracted)
    for item in extracted.rglob('*'):
     if item.is_file() and (item.suffix in ('.dll','.dylib','.exe') or item.name=='llama-server' or item.name.startswith('LICENSE')):
      shutil.copy2(item,stage/item.name)
    archive.unlink()
  executable=stage/('llama-server.exe' if platform_runtime.windows() else 'llama-server')
  if not executable.is_file():raise RuntimeError('Il pacchetto non contiene il server atteso.')
  if not platform_runtime.windows():executable.chmod(0o755)
  env=dict(os.environ)
  if args.library_path:env['PATH']=args.library_path+os.pathsep+env.get('PATH','')
  subprocess.run([str(executable),'--version'],check=True,env=env,creationflags=0x08000000 if os.name=='nt' else 0,timeout=30)
  model=Path(args.model).resolve() if args.model else model_store.location(ROOT)/'assistant'/pinned['model']['file']
  if args.model:
   if not model.is_file() or model.suffix.lower()!='.gguf':raise RuntimeError('Seleziona un modello GGUF già presente.')
  else:
   entry=pinned['model'];print('Scarico Qwen3 4B Q4: circa 2,5 GB.',flush=True)
   download('https://huggingface.co/'+entry['repo']+'/resolve/'+entry['revision']+'/'+entry['file'],model,entry['sha256'],entry['bytes'])
  for item in list(stage.iterdir()):
   if item.is_dir():
    assert item.resolve().is_relative_to(stage.resolve());shutil.rmtree(item)
  if marker.get('optimized_mtp'):marker['optimized_model']=str(model)
  (stage/'installed.json').write_text(json.dumps(marker,indent=2),encoding='utf-8')
  with model_store.exclusive(ROOT):
   model_store.check_idle(ROOT)
   backup=destination.with_name('assistant-backup-'+uuid.uuid4().hex[:12])
   if destination.exists():destination.replace(backup)
   try:stage.replace(destination)
   except BaseException:
    if backup.exists():backup.replace(destination)
    raise
   database=ROOT/'data/music.sqlite'
   if database.exists():
    with closing(sqlite3.connect(database)) as connection, connection:
     row=connection.execute("SELECT value FROM settings WHERE key='main'").fetchone();settings=json.loads(row[0]) if row else {}
     settings.update(llm_provider='internal',llm_internal_model=str(model) if args.model else '',llm_device='cuda' if args.gpu and platform_runtime.windows() else 'cpu',llm_context=16384)
     connection.execute("INSERT OR REPLACE INTO settings VALUES ('main',?)",(json.dumps(settings),))
  print('Assistente interno pronto. Il modello si carica su richiesta e viene scaricato alla fine.',flush=True)
 finally:
  if stage.exists():
   assert stage.resolve().is_relative_to((ROOT/'runtime').resolve());shutil.rmtree(stage)

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--gpu',action='store_true');parser.add_argument('--model');parser.add_argument('--local-engine');parser.add_argument('--optimized-mtp',action='store_true');parser.add_argument('--library-path')
 args=parser.parse_args()
 with model_store.exclusive(ROOT,'assistant-runtime.lock'):
  with model_store.exclusive(ROOT):model_store.check_idle(ROOT)
  install(args)

if __name__=='__main__':main()
