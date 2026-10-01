"""H3-Music. Local, dependency-free studio and persistent single-GPU queue."""
from __future__ import annotations
import array, base64, copy, hashlib, http.server, json, math, mimetypes, os, re, secrets, shutil, sqlite3, struct, subprocess, sys, threading, time, traceback, urllib.parse, urllib.request, uuid, wave, zipfile
from pathlib import Path
from contextlib import contextmanager
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import transcription, execution, cloning, mixing, remote_access, library_cleanup, platform_runtime, model_store, resinging
APP=sys.modules[__name__]
DATA=Path(os.environ.get('H3_MUSIC_DATA',str(ROOT/'data')))
OUT=DATA/'outputs'
PORT=int(os.environ.get('H3_MUSIC_PORT','8776'))
HIDDEN=0x08000000 if os.name=='nt' else 0
LOCK=threading.RLock()
ACTIVE={}
WAKE=threading.Event()
MODEL=model_store.location(ROOT)/'yue2'
MODEL_OPERATION={'status':'idle'}
ENGINE=platform_runtime.binary(ROOT,'audiocpp_cli',engine=True)
FFMPEG=platform_runtime.binary(ROOT,'ffmpeg')
DEFAULTS={'backend':'cpu','threads':8,'llm_url':'http://127.0.0.1:1234/v1','llm_model':'','paused':False,'model':'q8'}
MUSIC_MODELS={'q4':('yue2-3b-q4_0.gguf',2665632320,'Q4'), 'q8':('yue2-3b-q8_0.gguf',4264186432,'Q8'), 'bf16':('yue2-3b-bf16.gguf',7261475392,'BF16')}
NUMBERS={'cfg_scale':(0,20,1.0),'num_inference_steps':(1,128,32),'abc_temperature':(0,5,.7),'abc_top_p':(0,1,.9),'abc_top_k':(1,1000,30),'abc_repetition_penalty':(.01,10,1.005),'abc_penalty_window':(1,10000,100),'abc_min_tokens':(0,4096,32),'abc_max_tokens':(32,8192,4096),'semantic_temperature':(0,5,1),'semantic_top_p':(0,1,.95),'semantic_top_k':(1,1000,100),'semantic_repetition_penalty':(.01,10,1.2),'semantic_penalty_window':(1,10000,50),'semantic_min_tokens':(0,9000,200),'semantic_max_tokens':(200,12000,9000)}
INTEGER={'num_inference_steps'}|{k for k in NUMBERS if any(s in k for s in ('top_k','window','tokens'))}

def now(): return time.time()
def uid(): return uuid.uuid4().hex

def normalize_abc(text):
 # Older Windows saves translated CRLF to CRCRLF. Repair before universal
 # newline decoding loses that distinction; keep genuine blank lines intact.
 return text.replace('\r\r\n','\n').replace('\r\n','\n').replace('\r','\n')

def read_abc(path):
 return normalize_abc(path.read_bytes().decode('utf-8'))

@contextmanager
def conn():
 c=sqlite3.connect(DATA/'music.sqlite',timeout=20); c.row_factory=sqlite3.Row
 try:
  with c: yield c
 finally: c.close()

def db(sql, args=(), one=False):
 with LOCK,conn() as c:
  cur=c.execute(sql,args)
  rows=[dict(x) for x in cur.fetchall()] if cur.description else []
  return (rows[0] if rows else None) if one else rows

def jdump(x): return json.dumps(x,ensure_ascii=False,allow_nan=False)
def write_json(p,x):
 p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
 t=p.with_suffix(p.suffix+'.tmp'); t.write_text(jdump(x),encoding='utf-8'); t.replace(p)
def settings():
 r=db('SELECT value FROM settings WHERE key=?',('main',),True)
 return DEFAULTS| (json.loads(r['value']) if r else {})
def save_settings(s): db('INSERT OR REPLACE INTO settings VALUES (?,?)',('main',jdump(s)))
def validate(req):
 if not isinstance(req,dict): raise ValueError('Progetto non valido.')
 r={k:str(req.get(k,'')).strip() for k in ('title','style','lyrics','abc','notes')}
 r['abc']=normalize_abc(r['abc'])
 r['title']=r['title'][:120] or 'Senza titolo'
 for k,limit in [('style',4000),('lyrics',16000),('abc',50000),('notes',20000)]:
  if len(r[k])>limit: raise ValueError(k+': testo troppo lungo.')
 r['cot']='full' if req.get('base_enabled') is True else req.get('cot','full')
 if r['cot'] not in ('full','melody','off'): raise ValueError('Modalità spartito non valida.')
 if r['abc'] and r['cot']=='off': raise ValueError('Per usare lo spartito seleziona Melodia o Melodia e accordi.')
 seed=req.get('seed',831001)
 if seed in ('',None,-1,'-1'): seed=secrets.randbelow(2**31)
 r['seed']=int(seed)
 if not 0<=r['seed']<2**53: raise ValueError('Seed fuori intervallo (0–2^53).')
 opt=req.get('options',{})
 if not isinstance(opt,dict) or set(opt)-set(NUMBERS): raise ValueError('Parametri avanzati non riconosciuti.')
 r['clone_enabled']=req.get('clone_enabled',False)
 if not isinstance(r['clone_enabled'],bool):raise ValueError('Scelta della voce non valida.')
 r['clone_voice']=req.get('clone_voice','')
 if not isinstance(r['clone_voice'],str) or len(r['clone_voice'])>200:raise ValueError('Voce non valida.')
 r['options']={}
 r['mix']=mixing.validate(req.get('mix'))
 r['voice_steps']=cloning.voice_steps(req.get('voice_steps',30))
 r.update(resinging.validate_fields(req))
 for k,v in opt.items():
  lo,hi,_=NUMBERS[k]; v=float(v)
  if not math.isfinite(v) or not lo<=v<=hi or k in INTEGER and int(v)!=v: raise ValueError('Valore non valido: '+k)
  r['options'][k]=int(v) if k in INTEGER else v
 for prefix in ('abc','semantic'):
  if r['options'].get(prefix+'_min_tokens',NUMBERS[prefix+'_min_tokens'][2])>r['options'].get(prefix+'_max_tokens',NUMBERS[prefix+'_max_tokens'][2]): raise ValueError('Il limite massimo deve essere maggiore del minimo.')
 return r

def init():
 DATA.mkdir(parents=True,exist_ok=True); OUT.mkdir(exist_ok=True)
 with conn() as c:
  c.executescript('''PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,title TEXT,request TEXT,created REAL,updated REAL,archived INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,project_id TEXT,kind TEXT,status TEXT,request TEXT,created REAL,started REAL,finished REAL,error TEXT DEFAULT '',favorite INTEGER DEFAULT 0,result TEXT DEFAULT '{}');
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
''')
  c.execute("UPDATE jobs SET status='interrupted',error='Interrotto dalla chiusura del programma. Puoi riprovare.' WHERE status IN ('running','cancelling')")

def project_save(data):
 req=validate(data.get('request',data)); ident=data.get('id')
 if ident:
  if not re.fullmatch('[a-f0-9]{32}',str(ident)) or not db('SELECT id FROM projects WHERE id=?',(ident,),True): raise ValueError('Progetto inesistente.')
  db('UPDATE projects SET title=?,request=?,updated=? WHERE id=?',(req['title'],jdump(req),now(),ident))
 else:
  ident=uid(); t=now(); db('INSERT INTO projects(id,title,request,created,updated) VALUES(?,?,?,?,?)',(ident,req['title'],jdump(req),t,t))
 return {'id':ident,'request':req}

def files_for(ident):
 d=OUT/ident
 return [{'name':p.name,'bytes':p.stat().st_size,'url':f'/files/{ident}/{urllib.parse.quote(p.name)}'} for p in d.iterdir() if p.is_file() and not p.name.endswith('.tmp')] if d.exists() else []

def get_job(ident,detail=False):
 j=db('SELECT * FROM jobs WHERE id=?',(ident,),True)
 if not j: raise ValueError('Generazione inesistente.')
 j['request']=json.loads(j['request']); j['result']=json.loads(j['result']); j['files']=files_for(ident)
 if detail:
  log=OUT/ident/'engine.log'
  if log.exists():
   with log.open('rb') as f:
    f.seek(max(0,log.stat().st_size-16000)); j['log']=f.read().decode('utf-8',errors='replace')
  score=OUT/ident/'score.abc'; j['abc']=read_abc(score) if score.exists() else ''
  if j['kind']=='transcribe':
   j['annotations']={}
   for name in ('chord','key','structure','beat'):
    annotation=OUT/ident/(name+'.lab')
    if annotation.exists(): j['annotations'][name]=[line.split('\t') for line in annotation.read_text(encoding='utf-8').splitlines()[:300]]
  progress=OUT/ident/'progress.json'
  if progress.exists():
   try: j['progress']=json.loads(progress.read_text(encoding='utf-8'))
   except (OSError,json.JSONDecodeError): pass
 if 'progress' not in j:
  progress=OUT/ident/'progress.json'
  if progress.exists():
   try: j['progress']=json.loads(progress.read_text(encoding='utf-8'))
   except (OSError,json.JSONDecodeError): pass
 return j

def system_memory():
 """Memoria fisica e limite di commit (RAM + file di paging)."""
 try:
  if platform_runtime.macos():
   total=int(run_capture(['sysctl','-n','hw.memsize']).stdout)
   return {'total_gb':round(total/2**30,1)}
  import ctypes
  class M(ctypes.Structure):
   _fields_=[('dwLength',ctypes.c_ulong),('dwMemoryLoad',ctypes.c_ulong),('ullTotalPhys',ctypes.c_ulonglong),('ullAvailPhys',ctypes.c_ulonglong),('ullTotalPageFile',ctypes.c_ulonglong),('ullAvailPageFile',ctypes.c_ulonglong),('ullTotalVirtual',ctypes.c_ulonglong),('ullAvailVirtual',ctypes.c_ulonglong),('ullAvailExtendedVirtual',ctypes.c_ulonglong)]
  st=M(); st.dwLength=ctypes.sizeof(st)
  if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st)): return {}
  gb=lambda v: round(v/2**30,1)
  return {'total_gb':gb(st.ullTotalPhys),'avail_gb':gb(st.ullAvailPhys),'commit_limit_gb':gb(st.ullTotalPageFile),'commit_avail_gb':gb(st.ullAvailPageFile)}
 except Exception: return {}

def memory_profile():
 """Opzioni di sessione per il motore in base alla memoria disponibile.

 Il motore riserva le arene dei grafi (pesi, prefill, decode, NAR, VAE): sui PC
 con poca memoria o con un file di paging piccolo quelle prenotazioni non ci
 stanno e la generazione fallisce con 'failed to allocate'. Qui le riduciamo
 quando serve; su una macchina con memoria abbondante restano i valori del
 motore.
 """
 mem=system_memory(); free=mem.get('commit_avail_gb')
 if not free or free>=30: return {}
 if free>=20: return {'yue2.ar_prefill_graph_arena_mb':'3072','yue2.ar_decode_graph_arena_mb':'1024'}
 return {'yue2.ar_prefill_graph_arena_mb':'2048','yue2.ar_decode_graph_arena_mb':'1024','yue2.nar_graph_arena_mb':'4096','yue2.vae_graph_arena_mb':'1024','yue2.vae_weight_context_mb':'1024'}

def ready():
 required={'yue2-3b-q8_0.gguf':4264186432,'yue2-vae-f16.gguf':265218656,'sidecars/yue2-qwen.tiktoken':2561218,'sidecars/yue2-model-config.json':959,'sidecars/yue2-generation-config.json':466,'sidecars/yue2-vae-config.json':1378}
 record=model_store.location(ROOT)/'installed-models.json'
 if record.exists():
  try:
   installed=json.loads(record.read_text(encoding='utf-8')).get('files') or {}
   from_record={n:info['size'] for n,info in installed.items() if isinstance(info,dict) and info.get('size')}
   if from_record: required=from_record
  except Exception: pass
 chosen=main_model_file()
 variant=next((k for k,v in MUSIC_MODELS.items() if v[0]==chosen),'q8')
 expected=required.get(chosen,MUSIC_MODELS[variant][1])
 required={n:size for n,size in required.items() if not n.startswith('yue2-3b-')}
 required[chosen]=expected
 missing=[n for n,size in required.items() if not (MODEL/n).is_file() or (MODEL/n).stat().st_size!=size]
 available={k:(MODEL/v[0]).is_file() and (MODEL/v[0]).stat().st_size==installed_model_sizes().get(v[0],v[1]) for k,v in MUSIC_MODELS.items()}
 return {'ready':ENGINE.exists() and not missing,'engine':ENGINE.exists(),'missing':missing,'ffmpeg':FFMPEG.exists(),'sep':bool(separation_model()),'voice':bool(voice_model()),'voices':len(voice_list()),'model':'YuE2-3B · %s / VAE F16' % MUSIC_MODELS[variant][2],'model_variant':variant,'available_models':available,'root':str(ROOT),'transcription':transcription.status(ROOT,settings()['backend']),'platform':sys.platform,'backends':platform_runtime.backends(),'setup_name':platform_runtime.setup_name()}

TOOLS=model_store.location(ROOT)/'tools'

def model_location_status():
 with LOCK:
  return {'path':str(model_store.location(ROOT)), 'operation':dict(MODEL_OPERATION)}

def change_model_location(data):
 global MODEL_OPERATION
 transfer=data.get('transfer',True)
 if not isinstance(transfer,bool):raise ValueError('Scelta del trasferimento non valida.')
 with LOCK:
  if MODEL_OPERATION['status'] in ('starting','copying','verifying','cleaning'):raise ValueError('Un trasferimento è già in corso.')
  guard=model_store.exclusive(ROOT);guard.__enter__()
  try:
   if ACTIVE or db("SELECT id FROM jobs WHERE status IN ('queued','running','cancelling') LIMIT 1",one=True):raise ValueError('Termina o annulla i lavori in coda prima di cambiare cartella.')
   target=model_store.validate_destination(ROOT,model_store.location(ROOT),data.get('path'),transfer)
   MODEL_OPERATION={'status':'starting','done':0,'total':0,'target':str(target)}
   def run():
    global MODEL,TOOLS
    def update(**values):
     with LOCK:MODEL_OPERATION.update(values)
    try:
     result=model_store.relocate(ROOT,str(target),transfer,update)
     terminal={'status':'completed',**result}
    except Exception as e: terminal={'status':'failed','error':str(e)}
    finally:
     with LOCK:
      try:
       MODEL=model_store.location(ROOT)/'yue2';TOOLS=model_store.location(ROOT)/'tools'
      finally:
       guard.__exit__(None,None,None)
       MODEL_OPERATION.update(terminal)
     WAKE.set()
   threading.Thread(target=run,daemon=True).start()
  except BaseException:
   guard.__exit__(None,None,None);raise
 return {'ok':True}
def normalize_audio(src,dst,rate=44100,channels=2):
 """Ricampiona un audio col formato atteso dai modelli ausiliari.

 I brani generati sono a 48 kHz, mentre HTDemucs e SeedVC lavorano a 44,1 kHz:
 senza questo passaggio la separazione si ferma con 'sample rate mismatch'.
 """
 r=run_capture([str(FFMPEG),'-y','-v','error','-i',str(src),'-ar',str(rate),'-ac',str(channels),str(dst)],600)
 if r.returncode or not dst.exists(): raise RuntimeError('Preparazione audio non riuscita: '+(r.stderr or '')[-300:])
 return dst

def separation_model():
 """Cartella del modello di separazione (HTDemucs), se installato."""
 d=TOOLS/'HTDemucs-GGUF'
 return d if d.exists() and any(d.glob('*.gguf')) else None

def source_audio(ident):
 return OUT/str(ident or '')/'audio.wav'

def enqueue_separation(data):
 """Accoda la separazione di un brano gia generato (voce, batteria, basso, altro)."""
 if not ENGINE.exists(): raise ValueError('Il motore non è installato.')
 if not separation_model(): raise ValueError('Il modello di separazione non è installato: esegui scripts/download_tools.py --tool sep.')
 ident=data.get('source_id') or ''
 src=source_audio(ident)
 if not src.exists(): raise ValueError('Scegli un brano completato da separare.')
 title='Brano'
 pid=''
 try:
  j=get_job(ident); title=j['request'].get('title') or title; pid=j.get('project_id') or ''
 except ValueError: pass
 req={'title':title+' · voce e base','style':'','lyrics':'','abc':'','notes':'','seed':0,'options':{},'source_id':ident}
 new=uid()
 db('INSERT INTO jobs(id,project_id,kind,status,request,created) VALUES(?,?,?,?,?,?)',(new,pid,'sep','queued',jdump(req),now()))
 WAKE.set(); return {'ids':[new]}

VOCI=DATA/'voci'
def voice_model():
 """Cartella del modello di conversione vocale (SeedVC), se installato."""
 d=TOOLS/'SeedVC-MLX-GGUF'
 return d if d.exists() and any(d.glob('*.gguf')) else None

def voice_list():
 """Voci di riferimento disponibili: data/voci/<nome>/<campione audio>."""
 out=[]
 if VOCI.exists():
  for d in sorted(VOCI.iterdir()):
   if not d.is_dir(): continue
   samples=[p for p in sorted(d.iterdir()) if p.is_file() and p.suffix.lower() in transcription.EXTENSIONS]
   if samples:
    label=d.name
    try:label=json.loads((d/'voice.json').read_text(encoding='utf-8')).get('label') or label
    except (OSError,ValueError):pass
    out.append({'name':d.name,'label':label,'file':samples[0].name,'bytes':samples[0].stat().st_size})
 return out

def voice_sample(name):
 for v in voice_list():
  if v['name']==name: return VOCI/v['name']/v['file']
 return None

def enqueue_voice(data):
 """Accoda la conversione della voce cantata verso una voce di riferimento."""
 data=data.get('request',data)
 if not ENGINE.exists(): raise ValueError('Il motore non è installato.')
 if not voice_model(): raise ValueError('Il modello di conversione vocale non è installato: esegui scripts/download_tools.py --tool voice.')
 ref=voice_sample(str(data.get('voice') or ''))
 if not ref: raise ValueError('Scegli una voce: metti un campione parlato in data/voci/<nome>/ (wav, mp3 o flac).')
 ident=str(data.get('source_id') or '')
 if not (OUT/ident/'vocals.wav').exists(): raise ValueError('Prima separa il brano: serve la traccia voce.')
 title='Brano'
 try: title=get_job(ident)['request'].get('title') or title
 except ValueError: pass
 req={'title':title+' · voce '+ref.parent.name,'style':'','lyrics':'','abc':'','notes':'','seed':0,'options':{},'source_id':ident,'voice':ref.parent.name}
 req['voice_steps']=cloning.voice_steps(data.get('voice_steps',30))
 new=uid()
 db('INSERT INTO jobs(id,project_id,kind,status,request,created) VALUES(?,?,?,?,?,?)',(new,'','voice','queued',jdump(req),now()))
 WAKE.set(); return {'ids':[new]}

def mix_voice(job,d,converted,source=None,runner=None):
 """Unisce la voce convertita alla base strumentale del brano separato."""
 src=source if source is not None else OUT/job['request'].get('source_id','')
 return mixing.render(APP,job,d,converted,src,runner)

def enqueue(data):
 with LOCK,model_store.exclusive(ROOT):return _enqueue(data)

def _enqueue(data):
 if data.get('kind')=='remix':return mixing.enqueue(APP,data)
 if data.get('kind') in ('clone','instrumental'): return cloning.enqueue(APP,data)
 if data.get('kind')=='transcribe': return transcription.enqueue(APP,data)
 if data.get('kind')=='sep': return enqueue_separation(data)
 if data.get('kind')=='voice': return enqueue_voice(data)
 if not ready()['ready']: raise ValueError('Il motore o i modelli non sono pronti. Vedi Sistema.')
 pid=data.get('project_id'); p=db('SELECT * FROM projects WHERE id=?',(pid,),True)
 if not p: raise ValueError('Salva prima il progetto.')
 req=validate(data.get('request',json.loads(p['request'])))
 if not req['lyrics'] or not req['style'] and not req['base_enabled']: raise ValueError('Inserisci stile musicale e testo.')
 kind=data.get('kind','generate')
 if kind not in ('generate','plan'): raise ValueError('Operazione non valida.')
 if req['base_enabled']:
  if kind!='generate':raise ValueError('La base originale richiede Genera il brano.')
  resinging.preflight(APP,req)
 if kind=='generate' and req['clone_enabled']:cloning.preflight(APP,req['clone_voice'])
 if kind=='plan' and req['cot']=='off': raise ValueError('La composizione richiede Melodia o Melodia e accordi.')
 count=int(data.get('count',1))
 if not 1<=count<=8: raise ValueError('Scegli da 1 a 8 varianti.')
 ids=[]
 for n in range(count):
  ident=uid(); r=copy.deepcopy(req); r['seed']+=n
  db('INSERT INTO jobs(id,project_id,kind,status,request,created) VALUES(?,?,?,?,?,?)',(ident,pid,kind,'queued',jdump(r),now()))
  ids.append(ident)
 WAKE.set(); return {'ids':ids}

def installed_model_sizes():
 record=model_store.location(ROOT)/'installed-models.json'
 try:return {n:info['size'] for n,info in json.loads(record.read_text(encoding='utf-8')).get('files',{}).items() if isinstance(info,dict) and info.get('size')}
 except (OSError,ValueError,TypeError):return {}

def main_model_file():
 pref=settings().get('model','q8')
 wanted=MUSIC_MODELS.get(pref,MUSIC_MODELS['q8'])[0]
 # An explicit BF16 request must never silently execute a quantized model.
 if pref=='bf16':return wanted
 sizes=installed_model_sizes()
 for key in dict.fromkeys([pref,'q8','q4','bf16']):
  name,size,_=MUSIC_MODELS.get(key,MUSIC_MODELS['q8']);path=MODEL/name
  if path.is_file() and path.stat().st_size==sizes.get(name,size):return name
 return wanted

STAGES=(('seed_vc.','Conversione voce',10),('audio_out[','Separazione',60),('yue2.vae.','Finalizzazione',95),('yue2.nar.','Sintesi audio',55),('yue2.semantic.','Composizione',8),('yue2.ar.','Composizione',8),('yue2.plan.','Preparazione',2))
def engine_progress(d,started,backend):
 """Fase del motore e avanzamento stimato, ricavati dal suo registro.

 Il motore segnala solo i confini di fase: la percentuale dentro la fase e' una
 stima basata sul tempo, mentre i passaggi di fase sono esatti.
 """
 log=d/'engine.log'
 name,pct='Avvio',1
 if log.exists():
  try: tail=log.read_text(encoding='utf-8',errors='replace')[-40000:]
  except OSError: tail=''
  for marker,label,value in STAGES:
   if marker in tail: name,pct=label,value; break
 elapsed=max(0.0,time.time()-started)
 if name=='Sintesi audio': lo,hi,typical=55,95,2400 if backend=='cpu' else 60
 elif name=='Composizione': lo,hi,typical=8,55,420 if backend=='cpu' else 25
 elif name=='Separazione': lo,hi,typical=60,94,240 if backend=='cpu' else 20
 elif name=='Conversione voce': lo,hi,typical=10,94,1800 if backend=='cpu' else 120
 elif name=='Finalizzazione': lo,hi,typical=95,99,60 if backend=='cpu' else 15
 else: lo,hi,typical=pct,pct,0
 if typical: pct=min(hi,lo+int((hi-lo)*min(1.0,elapsed/typical)))
 return {'stage':name,'pct':int(pct),'elapsed_s':int(elapsed)}

def command_for(job,d):
 if job['kind']=='transcribe': return transcription.command(APP,job,d)
 if job['kind']=='voice':
  s=settings(); r=job['request']
  return cloning.voice_command(APP,OUT/r.get('source_id','')/'vocals.wav',voice_sample(r.get('voice')),d/'voce.wav',s,r.get('voice_steps',30))
 if job['kind']=='sep':
  s=settings()
  inp=normalize_audio(source_audio(job['request'].get('source_id')),d/'input.wav')
  return [str(ENGINE),'--task','sep','--family','htdemucs','--model',str(separation_model()),'--backend',s['backend'],'--threads',str(s['threads']),'--audio',str(inp),'--out-dir',str(d),'--log','--metrics']
 req=job['request']; opts=req['options']|{'style':req['style'],'cot':req['cot'],'seed':str(req['seed']),'h3_artifact_dir':str(d),'h3_plan_only':'true' if job['kind']=='plan' else 'false'}
 if req['abc']:
  (d/'input.abc').write_text(normalize_abc(req['abc']),encoding='utf-8',newline='\n'); opts['abc_file']=str(d/'input.abc')
 write_json(d/'request.json',req)
 write_json(d/'engine-request.json',[{'id':'audio','text':req['lyrics'],'options':opts}])
 s=settings()
 cmd=[str(ENGINE),'--task','gen','--family','yue2','--model',str(MODEL),'--backend',s['backend'],'--threads',str(s['threads']),'--session-option','yue2.model_gguf='+main_model_file()]
 for k,v in memory_profile().items(): cmd+=[ '--session-option','%s=%s'%(k,v)]
 return cmd+['--request-sequence',str(d/'engine-request.json'),'--out-dir',str(d),'--log','--metrics']

def decode_score(d):
 p=d/'abc_tokens.i32'
 if not p.exists() or not p.stat().st_size: return ''
 tokens=array.array('i'); tokens.frombytes(p.read_bytes())
 if sys.byteorder!='little': tokens.byteswap()
 vocab={}
 with (MODEL/'sidecars/yue2-qwen.tiktoken').open('r',encoding='utf-8') as f:
  for line in f:
   b,n=line.strip().split(); vocab[int(n)]=base64.b64decode(b)
 result=normalize_abc(b''.join(vocab.get(i,b'') for i in tokens).decode('utf-8',errors='replace'))
 (d/'score.abc').write_text(result,encoding='utf-8',newline='\n'); return result

def run_capture(args,timeout=30):
 return subprocess.run(args,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout,creationflags=HIDDEN)

def audio_info(path):
 probe=platform_runtime.binary(ROOT,'ffprobe')
 if probe.exists():
  r=run_capture([str(probe),'-v','error','-select_streams','a:0','-show_entries','stream=sample_rate,channels,duration:format=duration','-of','json',str(path)])
  if r.returncode==0:
   info=json.loads(r.stdout); st=info['streams'][0]
   return {'duration':float(info.get('format',{}).get('duration',st.get('duration',0))),'sample_rate':int(st['sample_rate']),'channels':int(st['channels'])}
 with wave.open(str(path)) as w: return {'duration':w.getnframes()/w.getframerate(),'sample_rate':w.getframerate(),'channels':w.getnchannels()}

def finish_artifacts(job,d):
 if job['kind']=='transcribe': return transcription.finish(APP,job,d)
 if job['kind']=='voice':
  converted=d/'voce.wav'
  if not converted.exists() or converted.stat().st_size<100: raise RuntimeError('La conversione non ha prodotto audio utilizzabile.')
  final=mix_voice(job,d,converted)
  try: dur=audio_info(final).get('duration',0)
  except Exception: dur=0
  return {'voice':job['request'].get('voice',''),'source_id':job['request'].get('source_id',''),'duration':dur,'voice_steps':cloning.voice_steps(job['request'].get('voice_steps',30))}
 if job['kind']=='sep':
  stems=[n for n in ('vocals.wav','drums.wav','bass.wav','other.wav') if (d/n).exists()]
  if not stems: raise RuntimeError('La separazione non ha prodotto file utilizzabili.')
  try: dur=audio_info(d/stems[0]).get('duration',0)
  except Exception: dur=0
  return {'stems':stems,'duration':dur,'source_id':job['request'].get('source_id','')}
 score=decode_score(d)
 if not score and job['request']['abc']: (d/'score.abc').write_text(normalize_abc(job['request']['abc']),encoding='utf-8',newline='\n')
 flags=d/'generation_flags.json'; result=json.loads(flags.read_text()) if flags.exists() else {}
 if job['kind']=='generate':
  audio=d/'audio.wav'
  if not audio.exists() or audio.stat().st_size<100: raise RuntimeError('Il motore non ha prodotto audio utilizzabile.')
  result.update(audio_info(audio))
  if result['duration']<=0: raise RuntimeError('Audio vuoto.')
 else:
  if not (d/'score.abc').exists() or not (d/'score.abc').stat().st_size: raise RuntimeError('Spartito non prodotto dal motore.')
  # Empty audio is a transport artifact for the native plan-only mode.
  empty=d/'audio.wav'
  if empty.exists() and empty.stat().st_size<100: empty.unlink()
 manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in d.iterdir() if p.is_file() and p.name not in ('engine.log','manifest.json')}
 write_json(d/'manifest.json',{'sha256':manifest,'engine':'audio.cpp dev + H3 artifact extension','model':'audio-cpp/Yue2-3B-GGUF','result':result})
 return result

class JobCancelled(Exception):pass

def check_cancel(ident):
 row=db('SELECT status FROM jobs WHERE id=?',(ident,),True)
 if not row or row['status'] in ('cancelled','cancelling'):raise JobCancelled()

def run_job_process(job,d,args,append=False,phase=None):
 ident=job['id']
 started=time.time()
 with (d/'engine.log').open('ab' if append else 'wb') as log:
  with LOCK:
   check_cancel(ident)
   p=subprocess.Popen(args,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,creationflags=HIDDEN)
   ACTIVE[ident]=p
  # Avanzamento: per la trascrizione lo scrive il suo worker, per la
  # generazione lo ricaviamo qui dal registro del motore.
  if job['kind']!='transcribe':
   backend=settings()['backend']; progress_file=d/'progress.json'
   while p.poll() is None:
    time.sleep(1)
    try: write_json(progress_file,{'stage':phase[0],'pct':phase[1],'elapsed_s':int(time.time()-started)} if phase else engine_progress(d,started,backend))
    except Exception: pass
  rc=p.wait()
 if job['kind']!='transcribe':
  try: (d/'progress.json').unlink()
  except OSError: pass
 with LOCK:
  ACTIVE.pop(ident,None)
  status=db('SELECT status FROM jobs WHERE id=?',(ident,),True)['status']
 if status in ('cancelling','cancelled'):
  raise JobCancelled()
 if rc:
  progress=d/'progress.json'
  reason=json.loads(progress.read_text(encoding='utf-8')).get('message','') if job['kind']=='transcribe' and progress.exists() else ''
  if not reason:
   tail=(d/'engine.log').read_text(encoding='utf-8',errors='replace')[-4000:] if (d/'engine.log').exists() else ''
   if 'unsupported model family hint' in tail:
    reason='Il motore installato non include il modello richiesto (per esempio la separazione). Il motore CPU distribuito lo include; su un PC con GPU ricompila con scripts/build_engine_cuda.ps1.'
   elif 'failed to allocate' in tail or 'GGML_ASSERT' in tail:
    mem=system_memory()
    if 'cudaMalloc' in tail or 'CUDA0 buffer' in tail or 'device 0' in tail:
     reason='Memoria video insufficiente: la scheda non ha spazio per il grafo del motore. Chiudi le altre applicazioni che usano la GPU (o scegli backend CPU in Preferenze) e riprova.'
    else:
     reason='Memoria insufficiente: il motore non ha potuto prenotare la memoria che gli serve%s. Chiudi le altre applicazioni, aumenta il file di paging di Windows (Impostazioni di sistema > Prestazioni > Avanzate > Memoria virtuale) oppure scegli il modello Q4 in Preferenze: occupa 2,5 GB invece di 4.'%(' (limite attuale %.0f GB)'%mem['commit_limit_gb'] if mem.get('commit_limit_gb') else '')
  raise RuntimeError(reason or f'Il motore si è fermato (codice {rc}). Apri il registro per i dettagli.')

def worker():
 while True:
  WAKE.wait(1); WAKE.clear()
  if settings()['paused']: continue
  with LOCK:
   try:
    with model_store.exclusive(ROOT):
     row=db("SELECT id FROM jobs WHERE status='queued' ORDER BY created LIMIT 1",one=True)
     if not row: continue
     job=get_job(row['id']); ident=job['id']; d=OUT/ident; d.mkdir(exist_ok=True)
     db("UPDATE jobs SET status='running',started=? WHERE id=?",(now(),ident))
   except ValueError:continue
  try:
   if job['kind']=='remix':result=mixing.process(APP,job,d)
   elif job['kind'] in ('clone','instrumental'):result=cloning.process(APP,job,d)
   elif job['kind']=='generate' and job['request'].get('base_enabled'):result=resinging.process(APP,job,d)
   elif job['kind']=='voice':
    cloning.convert_voice(APP,job,d,OUT/job['request']['source_id']/'vocals.wav',voice_sample(job['request']['voice']),d/'voce.wav')
    result=finish_artifacts(job,d)
   else:
    run_job_process(job,d,command_for(job,d))
    result=finish_artifacts(job,d)
    if job['kind']=='generate' and job['request'].get('clone_enabled'):
     result.update(cloning.process(APP,job,d))
     manifest=json.loads((d/'manifest.json').read_text(encoding='utf-8'))
     manifest['sha256']['audio.wav']=json.loads((d/'voice-manifest.json').read_text(encoding='utf-8'))['sha256']['audio.wav'];manifest['result']=result;write_json(d/'manifest.json',manifest)
   with LOCK:
    check_cancel(ident)
    db("UPDATE jobs SET status='completed',finished=?,result=? WHERE id=?",(now(),jdump(result),ident))
  except JobCancelled:
   with LOCK:ACTIVE.pop(ident,None)
   db("UPDATE jobs SET status='cancelled',finished=? WHERE id=?",(now(),ident))
  except Exception as e:
   with LOCK: ACTIVE.pop(ident,None)
   db("UPDATE jobs SET status='failed',finished=?,error=? WHERE id=?",(now(),str(e),ident))
   traceback.print_exc()

def cancel(ident):
 with LOCK:
  j=get_job(ident)
  if j['status'] in ('queued','running','cancelling'):
   p=ACTIVE.get(ident)
   db('UPDATE jobs SET status=?,finished=? WHERE id=?',('cancelling' if p else 'cancelled',now(),ident))
   if p:
    if os.name=='nt': run_capture(['taskkill','/PID',str(p.pid),'/T','/F'],15)
    else: p.terminate()
 return {'ok':True}

def local_llm_url(value):
 u=urllib.parse.urlparse(str(value).rstrip('/'))
 if u.scheme!='http' or u.hostname not in ('127.0.0.1','localhost','::1') or u.username or u.password or u.query or u.fragment: raise ValueError('L’assistente richiede un indirizzo HTTP locale, per esempio http://127.0.0.1:1234/v1.')
 return str(value).rstrip('/')

def llm(path,payload=None):
 s=settings(); url=local_llm_url(s['llm_url'])+path
 req=urllib.request.Request(url,data=jdump(payload).encode() if payload else None,headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=180 if payload else 5) as response: return json.load(response)

def assist(data):
 req=validate(data.get('request',{})); instruction=str(data.get('instruction','')).strip()[:8000]
 if not instruction: raise ValueError('Descrivi la modifica desiderata.')
 model=settings()['llm_model']
 if not model:
  models=llm('/models').get('data',[])
  if not models: raise ValueError('Nessun modello caricato in LM Studio.')
  model=models[0]['id']
 system='You are a music composer assisting H3-Music. Return ONLY a valid JSON object with title, style, lyrics, abc. Write the style prompt in English. Follow the user language for lyrics and use [Verse], [Chorus] section labels. Preserve fields the user did not ask to change. ABC is optional; do not invent an audio transcription. For score edits preserve notes and lyric order unless the user requests changing them. Never claim you generated audio.'
 res=llm('/chat/completions',{'model':model,'messages':[{'role':'system','content':system},{'role':'user','content':jdump({'current':req,'instruction':instruction})}],'temperature':.7,'max_tokens':6000,'stream':False})
 text=res['choices'][0]['message']['content']; text=re.sub(r'<think>.*?</think>','',text,flags=re.S).strip(); text=re.sub(r'^```(?:json)?\s*|\s*```$','',text)
 try: suggestion=json.loads(text)
 except json.JSONDecodeError: raise ValueError('L’assistente non ha restituito JSON valido. Riprova con una richiesta più breve.')
 merged=req|{k:suggestion[k] for k in ('title','style','lyrics','abc') if k in suggestion}
 return {'request':validate(merged)}

def export_audio(data):
 job=get_job(data.get('id')); ident=job['id']; d=OUT/ident
 if job['status']!='completed' or not (d/'audio.wav').exists(): raise ValueError('Seleziona una generazione audio completata.')
 fmt=data.get('format','flac')
 if fmt not in ('wav','flac','mp3','ogg'): raise ValueError('Formato non valido.')
 start=float(data.get('start',0)); end=float(data.get('end',0)); gain=float(data.get('gain',0)); fade=float(data.get('fade',0))
 dur=job['result']['duration']
 if not all(math.isfinite(x) for x in (start,end,gain,fade)) or not 0<=start<dur or end and not start<end<=dur+.1 or not -24<=gain<=24 or not 0<=fade<=30: raise ValueError('Taglio o volume non valido.')
 name='export-'+uid()[:8]+'.'+fmt; dest=d/name
 args=[str(FFMPEG),'-hide_banner','-loglevel','error','-nostdin','-i',str(d/'audio.wav'),'-ss',str(start)]
 length=(end or dur)-start
 if end: args+=['-t',str(length)]
 filters=[]
 if gain: filters.append(f'volume={gain}dB')
 if data.get('normalize'): filters.append('loudnorm=I=-16:TP=-1.5:LRA=11')
 if fade:
  f=min(fade,length/2); filters+= [f'afade=t=in:d={f}',f'afade=t=out:st={max(0,length-f)}:d={f}']
 if filters: args+=['-af',','.join(filters)]
 args+=['-ar','48000']
 args+= {'mp3':['-codec:a','libmp3lame','-b:a','320k'],'wav':['-codec:a','pcm_s24le'],'flac':['-codec:a','flac'],'ogg':['-codec:a','libvorbis','-q:a','7']}[fmt]
 args+=[str(dest)]
 r=run_capture(args,300)
 if r.returncode: raise ValueError('Esportazione fallita: '+r.stderr[-1500:])
 write_json(d/(name+'.json'),{'source':'audio.wav','settings':data})
 return {'url':f'/files/{ident}/{name}','name':name}

def bundle(data):
 job=get_job(data.get('id')); d=OUT/job['id']; target=d/'project.zip'
 with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
  for p in d.rglob('*'):
   if p.is_file() and p.name!='project.zip' and not p.is_symlink() and p.resolve().is_relative_to(d.resolve()): z.write(p,p.relative_to(d).as_posix())
  if job['kind']=='transcribe':
   original,_=transcription.source(DATA,job['request']['source_id']); z.write(original,'original'+original.suffix)
 return {'url':f'/files/{job["id"]}/project.zip','name':'project.zip'}

class Handler(http.server.BaseHTTPRequestHandler):
 server_version='H3Music/1.1'
 def log_message(self,fmt,*args): pass
 def json_response(self,data,status=200):
  b=jdump(data).encode('utf-8'); self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(b))); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(b)
 def check_host(self):
  if self.headers.get('Host') not in remote_access.allowed_hosts(DATA,PORT): raise PermissionError('Host non consentito.')
 def file_response(self,path,download=False):
  if not path.is_file(): return self.json_response({'error':'File inesistente.'},404)
  size=path.stat().st_size; start=0; end=size-1
  range_header=self.headers.get('Range',''); match=re.fullmatch(r'bytes=(\d+)-(\d*)',range_header)
  if match:
   start=int(match[1]); end=min(int(match[2]) if match[2] else end,end)
   if start>end or start>=size:
    self.send_response(416); self.send_header('Content-Range',f'bytes */{size}'); self.end_headers(); return
  self.send_response(206 if match else 200)
  self.send_header('Content-Type',mimetypes.guess_type(path.name)[0] or 'application/octet-stream')
  self.send_header('Accept-Ranges','bytes'); self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Content-Length',str(end-start+1))
  if match: self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
  if download: self.send_header('Content-Disposition',"attachment; filename*=UTF-8''"+urllib.parse.quote(path.name))
  self.end_headers()
  with path.open('rb') as f:
   f.seek(start); remaining=end-start+1
   while remaining>0:
    b=f.read(min(262144,remaining))
    if not b: break
    self.wfile.write(b); remaining-=len(b)
 def do_GET(self):
  try:
   self.check_host(); parsed=urllib.parse.urlparse(self.path); path=urllib.parse.unquote(parsed.path)
   if path=='/api/health': return self.json_response({'app':'H3-Music','status':'ok','pid':os.getpid()})
   if path=='/api/models/location':return self.json_response(model_location_status())
   if path=='/api/state':
    projects=db('SELECT * FROM projects WHERE archived=0 ORDER BY updated DESC')
    for p in projects: p['request']=json.loads(p['request'])
    jobs=[get_job(j['id']) for j in db('SELECT id FROM jobs ORDER BY created DESC LIMIT 300')]
    return self.json_response({'projects':projects,'jobs':jobs,'settings':settings(),'runtime':ready(),'options':NUMBERS})
   if path=='/api/system':
    try:
     g=run_capture(['nvidia-smi','--query-gpu=name','--format=csv,noheader'],10).stdout.strip()
    except Exception: g=''
    try:
     cuda=json.loads(run_capture([str(platform_runtime.python(ROOT)),str(ROOT/'scripts/gpu_info.py')],15).stdout or '{}') if platform_runtime.windows() else {}
    except Exception: cuda={}
    motore={'cuda':'CUDA','metal':'Metal','cpu':'CPU'}[settings()['backend']]
    return self.json_response(ready()|{'gpu':g,'cuda':cuda,'memory':system_memory(),'free_gb':round(shutil.disk_usage(ROOT).free/2**30,1),'version':'1.7.2','engine_note':'audio.cpp dev, motore %s; estensione locale per spartiti e artefatti.' % motore})
   if path=='/api/voice-audio':
    ref=voice_sample(urllib.parse.parse_qs(parsed.query).get('name',[''])[0])
    if ref is None:raise ValueError('Campione vocale non trovato.')
    return self.file_response(ref)
   if path=='/api/voices': return self.json_response({'voices':voice_list(),'model':bool(voice_model())})
   if path=='/api/imports': return self.json_response({'sources':transcription.list_sources(DATA)})
   if re.fullmatch('/imports/[a-f0-9]{32}/audio',path):
    source,_=transcription.source(DATA,path.split('/')[2]); return self.file_response(source)
   if path=='/api/llm/models': return self.json_response(llm('/models'))
   if re.fullmatch('/api/jobs/[a-f0-9]{32}',path): return self.json_response(get_job(path.rsplit('/',1)[1],True))
   if path.startswith('/files/'):
    parts=path.split('/')
    if len(parts)!=4 or not re.fullmatch('[a-f0-9]{32}',parts[2]): raise ValueError('Percorso non valido.')
    target=(OUT/parts[2]/parts[3]).resolve()
    if target.parent!=(OUT/parts[2]).resolve(): raise ValueError('Percorso non valido.')
    return self.file_response(target,'download' in urllib.parse.parse_qs(parsed.query))
   target=ROOT/'static'/('index.html' if path=='/' else path.removeprefix('/static/'))
   if not target.resolve().is_relative_to((ROOT/'static').resolve()): raise ValueError('Percorso non valido.')
   return self.file_response(target)
  except ConnectionError: pass
  except PermissionError as e: self.json_response({'error':str(e)},403)
  except Exception as e: self.json_response({'error':str(e)},400)
 def do_POST(self):
  try:
   self.check_host()
   origin=self.headers.get('Origin')
   if self.headers.get('X-H3-Music')!='1' or origin and origin not in remote_access.allowed_origins(DATA,PORT): raise PermissionError('Richiesta non autorizzata.')
   size=int(self.headers.get('Content-Length',0))
   path=urllib.parse.urlparse(self.path).path
   if path=='/api/audio/upload': return self.json_response(transcription.upload(self,APP,size))
   if not 0<size<=2*1024*1024: raise ValueError('Richiesta troppo grande o vuota.')
   data=json.loads(self.rfile.read(size)); path=urllib.parse.urlparse(self.path).path
   if path=='/api/projects': result=project_save(data)
   elif path=='/api/models/location':result=change_model_location(data)
   elif path=='/api/models/browse':
    if platform_runtime.windows():
     script="Add-Type -AssemblyName System.Windows.Forms; $picker=New-Object System.Windows.Forms.FolderBrowserDialog; $picker.Description='Scegli la cartella dei modelli H3-Music'; if($picker.ShowDialog() -eq 'OK'){[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; [Console]::Write($picker.SelectedPath)}"
     selected=run_capture(['powershell','-NoProfile','-STA','-Command',script],180).stdout.strip()
    elif platform_runtime.macos():selected=run_capture(['osascript','-e','POSIX path of (choose folder with prompt "Scegli la cartella dei modelli H3-Music")'],180).stdout.strip()
    else:raise ValueError('Inserisci il percorso completo della cartella.')
    result={'path':selected}
   elif path=='/api/projects/archive':
    if db("SELECT id FROM jobs WHERE project_id=? AND status IN ('running','queued','cancelling')",(data['id'],),True): raise ValueError('Termina o annulla prima le generazioni del progetto.')
    db('UPDATE projects SET archived=1 WHERE id=?',(data['id'],)); result={'ok':True}
   elif path=='/api/voices/import': result=cloning.import_voice(APP,data)
   elif path=='/api/jobs': result=enqueue(data)
   elif path=='/api/jobs/cancel': result=cancel(data['id'])
   elif path=='/api/jobs/delete': result=library_cleanup.delete(APP,data.get('ids'))
   elif path=='/api/jobs/favorite':
    db('UPDATE jobs SET favorite=? WHERE id=?',(int(bool(data['favorite'])),data['id'])); result={'ok':True}
   elif path=='/api/jobs/retry':
    j=get_job(data['id']); result=enqueue({'project_id':j['project_id'],'request':j['request'],'kind':j['kind']})
   elif path=='/api/settings':
    s=settings()
    for k in DEFAULTS:
     if k in data: s[k]=data[k]
    if s['backend'] not in platform_runtime.backends(): raise ValueError('Backend non valido per questo sistema.')
    if s['backend']=='cuda' and settings()['backend']!='cuda': execution.check_cuda(ROOT)
    if s['backend']=='metal' and settings()['backend']!='metal': execution.check_engine(ENGINE,'metal')
    if s['model'] not in MUSIC_MODELS: raise ValueError('Modello non valido.')
    if s['model']=='bf16' and not ((MODEL/MUSIC_MODELS['bf16'][0]).is_file() and (MODEL/MUSIC_MODELS['bf16'][0]).stat().st_size==installed_model_sizes().get(MUSIC_MODELS['bf16'][0],MUSIC_MODELS['bf16'][1])): raise ValueError('BF16 non installato o incompleto. Esegui Installa-BF16.bat dalla cartella dell’app, poi riprova.')
    s['threads']=int(s['threads'])
    if not 1<=s['threads']<=64: raise ValueError('Thread fuori intervallo.')
    s['llm_url']=local_llm_url(s['llm_url']); s['llm_model']=str(s['llm_model'])[:200]; s['paused']=bool(s['paused'])
    save_settings(s); WAKE.set(); result={'ok':True}
   elif path=='/api/assist': result=assist(data)
   elif path=='/api/export': result=export_audio(data)
   elif path=='/api/bundle': result=bundle(data)
   elif path=='/api/shutdown':
    if MODEL_OPERATION['status'] in ('starting','copying','verifying','cleaning'):raise ValueError('Attendi la fine del trasferimento dei modelli prima di chiudere.')
    threading.Thread(target=self.server.shutdown,daemon=True).start(); result={'ok':True}
   elif path=='/api/open-folder':
    target=OUT/data['id'] if data.get('id') and re.fullmatch('[a-f0-9]{32}',str(data['id'])) else ROOT
    if not target.is_dir(): raise ValueError('Cartella inesistente.')
    platform_runtime.open_folder(target); result={'ok':True}
   else: return self.json_response({'error':'API inesistente.'},404)
   return self.json_response(result)
  except ConnectionError: pass
  except PermissionError as e: self.json_response({'error':str(e)},403)
  except Exception as e: self.json_response({'error':str(e)},400)

def main():
 (ROOT/'logs').mkdir(exist_ok=True)
 log=(ROOT/'logs/server.log').open('a',encoding='utf-8',buffering=1)
 sys.stdout=log; sys.stderr=log
 init(); server=http.server.ThreadingHTTPServer(('127.0.0.1',PORT),Handler)
 threading.Thread(target=worker,daemon=True).start()
 print(f'H3-Music http://127.0.0.1:{PORT}',flush=True)
 try: server.serve_forever()
 finally:
  for ident in list(ACTIVE): cancel(ident)
  server.server_close()
if __name__=='__main__': main()
