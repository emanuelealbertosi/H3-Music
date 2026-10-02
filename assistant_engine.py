"""Optional private llama.cpp process, alive only during an assistant operation."""
import atexit
from contextlib import contextmanager
import json
import os
from pathlib import Path
import socket
import subprocess
import threading
import time
import urllib.request
import urllib.error
import model_store

LOCK=threading.RLock()
_busy=False
_process=None
_url=None
_key=None
_log=None
_job=None

def attach_windows_job(process):
 """Windows closes our server if the H3 process disappears unexpectedly."""
 if os.name!='nt':return None
 import ctypes
 from ctypes import wintypes
 class Basic(ctypes.Structure):
  _fields_=[('PerProcessUserTimeLimit',ctypes.c_int64),('PerJobUserTimeLimit',ctypes.c_int64),('LimitFlags',wintypes.DWORD),('MinimumWorkingSetSize',ctypes.c_size_t),('MaximumWorkingSetSize',ctypes.c_size_t),('ActiveProcessLimit',wintypes.DWORD),('Affinity',ctypes.c_size_t),('PriorityClass',wintypes.DWORD),('SchedulingClass',wintypes.DWORD)]
 class IO(ctypes.Structure):
  _fields_=[(name,ctypes.c_uint64) for name in ('ReadOperationCount','WriteOperationCount','OtherOperationCount','ReadTransferCount','WriteTransferCount','OtherTransferCount')]
 class Extended(ctypes.Structure):
  _fields_=[('BasicLimitInformation',Basic),('IoInfo',IO),('ProcessMemoryLimit',ctypes.c_size_t),('JobMemoryLimit',ctypes.c_size_t),('PeakProcessMemoryUsed',ctypes.c_size_t),('PeakJobMemoryUsed',ctypes.c_size_t)]
 kernel=ctypes.WinDLL('kernel32',use_last_error=True)
 kernel.CreateJobObjectW.argtypes=[ctypes.c_void_p,wintypes.LPCWSTR];kernel.CreateJobObjectW.restype=wintypes.HANDLE
 kernel.SetInformationJobObject.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
 kernel.AssignProcessToJobObject.argtypes=[wintypes.HANDLE,wintypes.HANDLE]
 kernel.CloseHandle.argtypes=[wintypes.HANDLE]
 job=kernel.CreateJobObjectW(None,None)
 limits=Extended();limits.BasicLimitInformation.LimitFlags=0x2000
 if not job or not kernel.SetInformationJobObject(job,9,ctypes.byref(limits),ctypes.sizeof(limits)) or not kernel.AssignProcessToJobObject(job,wintypes.HANDLE(int(process._handle))):
  error=ctypes.get_last_error()
  if job:kernel.CloseHandle(job)
  raise OSError(error,'Impossibile controllare lo scaricamento del processo dell’assistente.')
 return job

def busy():return _busy
def internal(app):return app.settings().get('llm_provider','lmstudio')=='internal'
def model_id(app):return 'h3-assistant'

def choose_model(app):
 """Choose an existing file on the computer running H3, without copying it."""
 if app.platform_runtime.windows():
  script="Add-Type -AssemblyName System.Windows.Forms; $picker=New-Object System.Windows.Forms.OpenFileDialog; $picker.Title='Scegli un modello GGUF per H3-Music'; $picker.Filter='Modelli GGUF (*.gguf)|*.gguf'; $picker.CheckFileExists=$true; $picker.Multiselect=$false; $picker.RestoreDirectory=$true; if($picker.ShowDialog() -eq 'OK'){[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; [Console]::Write($picker.FileName)}"
  response=app.run_capture(['powershell','-NoProfile','-STA','-Command',script],300)
 elif app.platform_runtime.macos():
  response=app.run_capture(['osascript','-e','POSIX path of (choose file with prompt "Scegli un modello GGUF per l’assistente H3-Music")'],300)
  if response.returncode and '(-128)' in response.stderr:return {'path':''}
 else:raise ValueError('Inserisci il percorso completo del modello GGUF.')
 if response.returncode:raise ValueError('Non è stato possibile aprire il selettore del modello. Puoi inserire il percorso nel campo.')
 selected=response.stdout.strip()
 if not selected:return {'path':''}
 model=Path(selected)
 if model.suffix.lower()!='.gguf' or not model.is_file():raise ValueError('Scegli un file modello con estensione .gguf.')
 return {'path':str(model.resolve())}

def manifest(app):
 try:return json.loads((app.ROOT/'runtime/assistant/installed.json').read_text(encoding='utf-8'))
 except (OSError,ValueError):return {}

def configuration(app):
 cfg=manifest(app);settings=app.settings()
 engine=app.ROOT/'runtime/assistant'/('llama-server.exe' if os.name=='nt' else 'llama-server')
 configured=settings.get('llm_internal_model','')
 model=Path(configured) if configured else app.MODEL.parent/'assistant/Qwen3-4B-Q4_K_M.gguf'
 if not model.is_absolute():model=app.MODEL.parent/model
 device=settings.get('llm_device','cpu')
 if device not in ('cpu','cuda','metal'):raise ValueError('Dispositivo dell’assistente non valido.')
 if device!='cpu' and device not in cfg.get('backends',[]):raise ValueError('Il motore dell’assistente non include questa GPU. Installa il componente GPU dell’assistente.')
 context=int(settings.get('llm_context',16384))
 if not 4096<=context<=65536:raise ValueError('Contesto dell’assistente fuori intervallo (4096–65536).')
 return engine,model,device,context,cfg

def status(app):
 try:
  engine,model,device,context,cfg=configuration(app)
  return {'installed':engine.is_file(),'ready':engine.is_file() and model.is_file(),
   'busy':busy(),'loaded':bool(_process and _process.poll() is None),
   'model_path':str(model),'engine_path':str(engine),'device':device,
   'backends':cfg.get('backends',['cpu']),'context':context,'error':''}
 except (ValueError,TypeError) as e:return {'installed':False,'ready':False,'busy':busy(),'loaded':False,'error':str(e),'backends':['cpu']}

def command(engine,model,device,context,port,key,threads,cfg):
 args=[str(engine),'-m',str(model),'--alias','h3-assistant','--host','127.0.0.1',
  '--port',str(port),'--api-key',key,'-c',str(context),'-np','1','-ngl','0' if device=='cpu' else 'all',
  '-fit','off','-fa','on','-ctk','q4_0','-ctv','q4_0','-t',str(threads),'-tb',str(threads),
  '-b','2048','-ub','512','--jinja','--reasoning','off','--reasoning-format','deepseek',
  '--no-context-shift','--log-timestamps']
 if device=='cuda' and cfg.get('optimized_mtp') and str(model)==cfg.get('optimized_model'):
  args+=['--backend-sampling','--spec-type','draft-mtp','--spec-draft-n-max','2',
   '--spec-draft-p-min','0','--spec-draft-ngl','all','-ctkd','q4_0','-ctvd','q4_0']
 return args

def stop():
 global _process,_url,_key,_log,_job
 if _process is not None:
  if _process.poll() is None:
   _process.terminate()
   try:_process.wait(timeout=15)
   except subprocess.TimeoutExpired:_process.kill();_process.wait(timeout=15)
  _process=None
 if _job:
  import ctypes
  kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.CloseHandle.argtypes=[ctypes.c_void_p]
  kernel.CloseHandle(_job);_job=None
 if _log is not None:_log.close();_log=None
 _url=_key=None

atexit.register(stop)

def start(app):
 global _process,_url,_key,_log,_job
 if _process is not None and _process.poll() is None:return
 engine,model,device,context,cfg=configuration(app)
 if not engine.is_file() or not model.is_file():raise ValueError('Assistente interno non installato: esegui Installa-Assistente dalla cartella dell’app oppure seleziona un modello GGUF già presente.')
 with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
 _url='http://127.0.0.1:'+str(port);_key=app.secrets.token_urlsafe(32)
 folder=app.DATA/'assistant';folder.mkdir(parents=True,exist_ok=True)
 log_path=folder/'engine.log';_log=log_path.open('w',encoding='utf-8')
 env=dict(os.environ,GGML_CUDA_GRAPH_OPT='0')
 extra=cfg.get('library_path','')
 if extra:env['PATH']=extra+os.pathsep+env.get('PATH','')
 try:
  _process=subprocess.Popen(command(engine,model,device,context,port,_key,min(app.settings()['threads'],8),cfg),
   cwd=engine.parent,env=env,stdout=_log,stderr=_log,
   creationflags=app.HIDDEN)
  _job=attach_windows_job(_process)
  deadline=time.monotonic()+240
  while time.monotonic()<deadline:
   if _process.poll() is not None:
    _log.flush();detail=log_path.read_text(encoding='utf-8',errors='replace')[-1600:]
    raise ValueError('Caricamento dell’assistente non riuscito. '+detail)
   try:
    req=urllib.request.Request(_url+'/health',headers={'Authorization':'Bearer '+_key})
    with urllib.request.urlopen(req,timeout=2) as response:
     if json.load(response).get('status')=='ok':return
   except (OSError,ValueError):pass
   time.sleep(.2)
  raise ValueError('Il caricamento dell’assistente ha impiegato troppo tempo. Controlla modello e memoria disponibili.')
 except BaseException:stop();raise

@contextmanager
def session(app):
 global _busy
 if not internal(app):yield;return
 with LOCK,model_store.exclusive(app.ROOT,'assistant-runtime.lock'):
  with app.LOCK:
   if app.db("SELECT 1 FROM jobs WHERE status IN ('running','cancelling') LIMIT 1",one=True):raise ValueError('Attendi la fine del lavoro audio: poi l’assistente potrà usare la memoria e liberarla prima della generazione successiva.')
   _busy=True
  try:
   start(app)
   yield
  finally:
   stop()
   with app.LOCK:_busy=False;app.WAKE.set()

def request(app,path,payload=None,timeout=None):
 if path=='/models':return {'data':[{'id':model_id(app)}] if status(app).get('ready') else []}
 if path.startswith('/api/'):
  # The embedded server speaks OpenAI, not LM Studio's native model API.
  raise urllib.error.HTTPError(path,404,'API LM Studio non disponibile nel motore interno',None,None)
 if not busy() or _url is None:raise ValueError('Il motore interno può essere usato soltanto durante una richiesta all’assistente.')
 if payload:
  payload=dict(payload,model=model_id(app))
  payload['chat_template_kwargs']={'enable_thinking':False}
 headers={'Content-Type':'application/json','Authorization':'Bearer '+_key}
 req=urllib.request.Request(_url+'/v1'+path,data=app.jdump(payload).encode() if payload else None,headers=headers)
 with urllib.request.urlopen(req,timeout=timeout or 600) as response:return json.load(response)
