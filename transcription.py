"""Local audio imports and SheetSage2 queue integration (stdlib only)."""
import hashlib,json,math,re,shutil,time,urllib.parse,uuid
from pathlib import Path
import execution
MAX_UPLOAD=256*1024*1024
EXTENSIONS={'.mp3','.wav','.flac','.m4a','.ogg','.opus','.aac','.aif','.aiff','.wma','.mp4'}

def status(root,backend="cpu"):
 files={'runtime/transcription/python.exe':None,'runtime/transcription/Lib/site-packages/torch/__init__.py':None,'runtime/transcription/Lib/site-packages/transformers/__init__.py':None,'models/SheetSage2/model.safetensors':228738564,'models/MERT-v2-FullSong/model.safetensors':2529812848,'runtime/ffmpeg.exe':None,'runtime/transcription/installed.json':None,'models/transcription-manifest.json':None}
 runtime=execution.transcription_python(root,backend).parent
 selected=runtime.relative_to(root).as_posix()+'/'
 files={n.replace('runtime/transcription/',selected):size for n,size in files.items()}
 missing=[n for n,size in files.items() if not (root/n).is_file() or size and (root/n).stat().st_size!=size]
 revision=installed_revision(root)
 try:expected=json.loads((root/'scripts/sheetsage2-revision.json').read_text(encoding='utf-8'))['revision']
 except (OSError,ValueError,KeyError):expected=None
 return {'ready':not missing,'model':'SheetSage2 + MERT-v2','missing':missing,'max_upload_mb':256,'max_duration_seconds':1800,'runtime_path':str(runtime.resolve()),'revision':revision,'update_available':bool(expected and revision!=expected)}

def installed_revision(root):
 try:return json.loads((root/'models/transcription-manifest.json').read_text(encoding='utf-8')).get('sheet_revision')
 except (OSError,ValueError):return None

def source(data,ident):
 if not re.fullmatch('[a-f0-9]{32}',str(ident)):raise ValueError('Audio importato non valido.')
 folder=(data/'imports'/ident).resolve()
 if not folder.is_relative_to((data/'imports').resolve()):raise ValueError('Percorso audio non valido.')
 try:meta=json.loads((folder/'metadata.json').read_text(encoding='utf-8'))
 except FileNotFoundError:raise ValueError('Audio importato non trovato. Carica nuovamente il file.')
 path=(folder/meta['file']).resolve()
 if path.parent!=folder or not path.is_file():raise ValueError('Audio importato non disponibile.')
 return path,meta

def list_sources(data):
 records=[]
 for p in (data/'imports').glob('*/metadata.json'):
  try:
   _,meta=source(data,p.parent.name);records.append(meta)
  except (ValueError,OSError,json.JSONDecodeError):continue
 return sorted(records,key=lambda m:m['created'],reverse=True)[:100]

def upload(handler,app,size):
 if handler.headers.get('Transfer-Encoding'):raise ValueError('Invio chunked non supportato.')
 if not 0<size<=MAX_UPLOAD:raise ValueError('Scegli un file fino a 256 MB.')
 name=urllib.parse.unquote(handler.headers.get('X-Filename','audio'))
 name=re.split(r'[/\\]',name)[-1]
 ext=Path(name).suffix.lower()
 if ext not in EXTENSIONS:raise ValueError('Formato non supportato. Usa MP3, WAV, FLAC, M4A, OGG o un altro formato audio indicato.')
 if shutil.disk_usage(app.DATA).free<size+512*1024*1024:raise ValueError('Spazio su disco insufficiente per importare il file.')
 ident=uuid.uuid4().hex;folder=app.DATA/'imports'/ident;folder.mkdir(parents=True)
 path=folder/('source'+ext);temp=folder/'upload.tmp';digest=hashlib.sha256()
 handler.connection.settimeout(120)
 try:
  with temp.open('xb') as f:
   remaining=size
   while remaining:
    block=handler.rfile.read(min(1024*1024,remaining))
    if not block:raise ValueError('Caricamento interrotto.')
    f.write(block);digest.update(block);remaining-=len(block)
  # Decode one sample as well as probing: media is never interpreted as a playlist/network URL.
  probe=app.run_capture([str(app.ROOT/'runtime/ffprobe.exe'),'-v','error','-protocol_whitelist','file,pipe','-show_entries','format=format_name,duration:stream=codec_type','-of','json',str(temp)],30)
  if probe.returncode:raise ValueError('Il file non contiene audio leggibile.')
  parsed=json.loads(probe.stdout);fmt=parsed.get('format',{}).get('format_name','')
  if not set(fmt.split(',')).intersection({'mp3','wav','flac','ogg','mov','mp4','m4a','3gp','3g2','mj2','aac','aiff','asf'}):raise ValueError('Contenitore audio non supportato.')
  if not any(s.get('codec_type')=='audio' for s in parsed.get('streams',[])):raise ValueError('Il file non contiene una traccia audio.')
  duration=float(parsed.get('format',{}).get('duration',0))
  if not math.isfinite(duration) or not .1<=duration<=1800:raise ValueError('Scegli una registrazione tra 0,1 secondi e 30 minuti.')
  temp.replace(path)
  info=app.audio_info(path)
  meta={'id':ident,'name':name[:200],'file':path.name,'bytes':size,'sha256':digest.hexdigest(),'created':time.time(),**info,'url':f'/imports/{ident}/audio'}
  app.write_json(folder/'metadata.json',meta)
  return meta
 except Exception:
  for p in (temp,path):p.unlink(missing_ok=True)
  if not any(folder.iterdir()):folder.rmdir()
  raise

def enqueue(app,data):
 if not status(app.ROOT,app.settings()['backend'])['ready']:raise ValueError('Il motore di trascrizione non è ancora pronto. Vedi Sistema.')
 req=data.get('request',data)
 path,meta=source(app.DATA,req.get('source_id'))
 start=float(req.get('start',0));end=float(req.get('end',0)) or meta['duration']
 if not all(math.isfinite(v) for v in (start,end)) or not 0<=start<end<=meta['duration']+.05 or end-start<.1:raise ValueError('Intervallo audio non valido.')
 melody=req.get('melody_only',False)
 if not isinstance(melody,bool):raise ValueError('Modalità melodia non valida.')
 r={'title':str(req.get('title','')).strip()[:120] or Path(meta['name']).stem,'source_id':meta['id'],'source_name':meta['name'],'start':start,'end':end,'melody_only':melody,'style':'','lyrics':'','abc':'','notes':'','cot':'melody' if melody else 'full','seed':0,'options':{}}
 ident=app.uid()
 app.db('INSERT INTO jobs(id,project_id,kind,status,request,created) VALUES(?,?,?,?,?,?)',(ident,None,'transcribe','queued',app.jdump(r),app.now()))
 app.WAKE.set();return {'ids':[ident]}

def command(app,job,d):
 req=job['request'];path,meta=source(app.DATA,req['source_id'])
 app.write_json(d/'request.json',req)
 app.write_json(d/'source.json',meta)
 app.write_json(d/'transcription-version.json',{'sheet_revision':installed_revision(app.ROOT)})
 # Relative source id is validated above; the child receives paths controlled by the app.
 return [str(execution.transcription_python(app.ROOT,app.settings()['backend'])),'-u',str(app.ROOT/'scripts/transcribe_worker.py'),'--input',str(path),'--output',str(d),'--root',str(app.ROOT),'--backend',app.settings()['backend'],'--threads',str(app.settings()['threads'])]

def finish(app,job,d):
 p=d/'result.json'
 if not p.exists():raise RuntimeError('Il trascrittore non ha prodotto un risultato.')
 result=json.loads(p.read_text(encoding='utf-8'))
 if not (d/'transcription.mid').is_file():raise RuntimeError('Il trascrittore non ha prodotto MIDI utilizzabile.')
 result['duration']=result['duration_seconds'];result['source_id']=job['request']['source_id']
 manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in d.iterdir() if p.is_file() and p.name not in ('engine.log','manifest.json','progress.json')}
 version=d/'transcription-version.json'
 revision=json.loads(version.read_text(encoding='utf-8')).get('sheet_revision') if version.exists() else installed_revision(app.ROOT)
 app.write_json(d/'manifest.json',{'sha256':manifest,'engine':'SheetSage2','revision':revision,'result':result})
 return result
