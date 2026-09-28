"""Verify installed weights, record provenance, restart idle app and transcribe the test MP3."""
from pathlib import Path
import urllib.request,json,hashlib,subprocess,time,sys
r=Path(__file__).resolve().parents[1]
expected={'models/SheetSage2/model.safetensors':'b235f68091a5f5b644000f2b5acb57d1e70432aca2b34ab1b9cf27236e1f4274','models/MERT-v2-FullSong/model.safetensors':'e6dd2ab187d6dd62b6521cd7d8f932e237acf0c5757745a7232082e28391350d','models/MERT-v2-FullSong/modeling_mert2.py':'b1a3174e5649c4b26b0c90d8626f0adacfbbba111a58ed3bb72ad651945a2f5c','models/MERT-v2-FullSong/configuration_mert2.py':'77b53ec9d7ee31a599d744fb006e812c7eeaf7390deb46e2f460cf8c17b00bd6'}
for name,sha in expected.items():
 with (r/name).open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
 assert actual==sha,(name,actual)
 print('Verified',name,flush=True)
installed=json.loads((r/'models/transcription-manifest.json').read_text(encoding='utf-8'))
assert installed['sheet_revision']==json.loads((r/'scripts/sheetsage2-revision.json').read_text(encoding='utf-8'))['revision']
check=subprocess.run([str(r/'runtime/transcription/python.exe'),'-c',"import torch,json; assert torch.cuda.is_available(); x=torch.ones((256,256),device='cuda'); y=x@x; assert y[0,0].item()==256; print(json.dumps({'torch':torch.__version__,'gpu':torch.cuda.get_device_name(0),'cuda':torch.version.cuda,'architectures':torch.cuda.get_arch_list()}))"],capture_output=True,text=True,timeout=120)
print(check.stdout,check.stderr,flush=True);assert check.returncode==0
(r/'logs/transcription-cuda.json').write_text(check.stdout,encoding='utf-8')
base='http://127.0.0.1:8776'
def api(path,data=None):
 req=urllib.request.Request(base+'/api/'+path,data=json.dumps(data).encode() if data is not None else None,headers={'X-H3-Music':'1','Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=30) as resp:return json.load(resp)
state=api('state');assert not [j for j in state['jobs'] if j['status'] in ('queued','running','cancelling')]
api('shutdown',{})
for _ in range(30):
 try:api('health');time.sleep(.25)
 except Exception:break
subprocess.Popen([str(r/'runtime/python/pythonw.exe'),str(r/'app.py')],creationflags=0x08000000)
for _ in range(60):
 try:
  if api('health')['status']=='ok':break
 except Exception:pass
 time.sleep(.25)
assert api('state')['runtime']['transcription']['ready']
source=json.loads((r/'logs/transcription-ui-tests.json').read_text())['source_id']
ident=api('jobs',{'kind':'transcribe','request':{'source_id':source,'title':'Prima luce · trascrizione MP3','start':0,'end':0,'melody_only':False}})['ids'][0]
(r/'logs/transcription-smoke-id.txt').write_text(ident)
print('TRANSCRIPTION JOB',ident,flush=True)
for _ in range(900):
 j=api('jobs/'+ident)
 if j['status'] in ['completed','failed','cancelled','interrupted']:break
 time.sleep(2)
(r/'logs/transcription-smoke.json').write_text(json.dumps(j,indent=2,ensure_ascii=False),encoding='utf-8')
assert j['status']=='completed',j['error']
assert j['abc'] and j['result']['melody_notes']>0,j['result']
print(json.dumps({'id':ident,'result':j['result']},ensure_ascii=False),flush=True)
