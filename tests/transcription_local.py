from pathlib import Path
import json,time,urllib.request,subprocess,os,shutil
root=Path('F:/H3-Music');runtime=root/'runtime/transcription'
assert runtime.resolve()==runtime,'Il runtime non è una cartella locale'
removed=json.loads((root/'logs/external-runtime-removed.json').read_text(encoding='utf-8-sig'))
assert all(not x['exists'] and not Path(x['path']).exists() for x in removed)
code="""import sys,json,torch,torchaudio,numpy
from pathlib import Path
root=Path('F:/H3-Music/runtime/transcription')
assert Path(sys.executable).resolve()==root/'python.exe'
assert all(Path(m.__file__).resolve().is_relative_to(root) for m in (torch,torchaudio,numpy))
assert torch.cuda.is_available()
x=torch.ones((256,256),device='cuda');y=x@x;assert y[0,0].item()==256;torch.cuda.synchronize()
print(json.dumps({'python':sys.executable,'torch_path':torch.__file__,'torchaudio_path':torchaudio.__file__,'numpy_path':numpy.__file__,'torch':torch.__version__,'cuda':torch.version.cuda,'device':torch.cuda.get_device_name(0),'matmul_passed':True}))
"""
env=os.environ.copy();tmp=root/'data/tmp';tmp.mkdir(exist_ok=True);env.update(TEMP=str(tmp),TMP=str(tmp),PYTHONUTF8='1')
r=subprocess.run([str(runtime/'python.exe'),'-c',code],capture_output=True,text=True,encoding='utf-8',env=env,timeout=300,creationflags=0x08000000)
assert r.returncode==0,r.stderr
cuda=json.loads(r.stdout.strip().splitlines()[-1]);print('GPU LOCALE',json.dumps(cuda),flush=True)
base='http://127.0.0.1:8776/api/'
def api(path,data=None):
 req=urllib.request.Request(base+path,data=json.dumps(data).encode() if data is not None else None,headers={'X-H3-Music':'1','Content-Type':'application/json'})
 return json.load(urllib.request.urlopen(req,timeout=45))
system=api('system');assert system['transcription']['ready'];assert Path(system['transcription']['runtime_path'])==runtime
state=json.loads((root/'logs/migration-queue-state.json').read_text(encoding='utf-8-sig'))
api('settings',{'paused':False})
source=json.loads((root/'logs/transcription-ui-tests.json').read_text())['source_id']
ident=api('jobs',{'kind':'transcribe','request':{'source_id':source,'title':'Prima luce · verifica locale F','start':5,'end':17,'melody_only':True}})['ids'][0]
print('TRASCRIZIONE LOCALE',ident,flush=True)
try:
 for _ in range(450):
  job=api('jobs/'+ident)
  if job['status'] in ('completed','failed','cancelled','interrupted'):break
  time.sleep(2)
 assert job['status']=='completed',job.get('error')
 assert abs(job['result']['duration']-12)<.05 and job['result']['melody_only'] and job['abc']
 midi=root/'data/outputs'/ident/'transcription.mid';assert midi.read_bytes()[:4]==b'MThd'
 result={'passed':True,'runtime':str(runtime.resolve()),'external_copies_removed':removed,'cuda':cuda,'transcription_id':ident,'result':job['result'],'free_bytes':shutil.disk_usage(root).free,'queue_restored':state}
 (root/'logs/transcription-F-only.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False),flush=True)
finally:api('settings',state)
