import pathlib, shutil, time, subprocess, json, urllib.request, os
root=pathlib.Path(__file__).resolve().parents[1]
bin=root/'vendor/audio.cpp/build/windows-cuda-release/bin'
log=root/'logs/build2.log'
for _ in range(540):
 if (bin/'audiocpp_cli.exe').exists(): break
 text=log.read_text(encoding='utf-8',errors='replace')[-5000:]
 if 'ninja: build stopped' in text: raise RuntimeError('Engine build failed. See build2.log')
 time.sleep(5)
else: raise RuntimeError('Build timeout')
for p in bin.iterdir():
 if p.suffix.lower() in ('.exe','.dll'): shutil.copy2(p,root/'runtime/engine'/p.name)
cuda=pathlib.Path(r'C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.8\bin')
for pattern in ['cudart64*.dll','cublas64*.dll','cublasLt64*.dll']:
 for p in cuda.glob(pattern): shutil.copy2(p,root/'runtime/engine'/p.name)
vc=pathlib.Path(r'F:\visualstudiobuild\VC\Redist\MSVC')
for name in ['msvcp140.dll','vcruntime140.dll','vcruntime140_1.dll','vcomp140.dll']:
 candidates=list(vc.glob('**/x64/**/'+name))
 if candidates: shutil.copy2(sorted(candidates)[-1],root/'runtime/engine'/name)
print('Native runtime packaged',flush=True)
r=subprocess.run([str(root/'runtime/engine/audiocpp_cli.exe'),'--list-devices'],capture_output=True,text=True,encoding='utf-8',errors='replace',creationflags=0x08000000,cwd=root)
(root/'logs/devices.txt').write_text(r.stdout+'\n'+r.stderr,encoding='utf-8')
print(r.stdout,flush=True)
if r.returncode: raise RuntimeError('Native startup failed: '+str(r.returncode))
base='http://127.0.0.1:8776/api/'
def call(path,data=None):
 req=urllib.request.Request(base+path,data=json.dumps(data,ensure_ascii=False).encode('utf-8') if data else None,headers={'Content-Type':'application/json','X-H3-Music':'1'})
 with urllib.request.urlopen(req,timeout=30) as res:return json.load(res)
try:call('health')
except Exception:
 subprocess.Popen([str(root/'runtime/python/pythonw.exe'),str(root/'app.py')],cwd=root,creationflags=0x08000000)
 for _ in range(40):
  try:call('health');break
  except Exception:time.sleep(.5)
request={'title':'Prima luce · prova YuE2','style':'English, indie pop, warm clear lead vocal, acoustic guitar, soft drums, gentle uplifting chorus, 100 BPM','lyrics':'[Verse]\nMorning light across the floor\nI can hear the ocean call\n[Chorus]\nLet the music take us home\nWe are never on our own','cot':'full','seed':831001,'options':{'num_inference_steps':8,'semantic_max_tokens':3000}}
p=call('projects',{'request':request})
jobs=[]
for kind in ['generate','plan']:
 j=call('jobs',{'project_id':p['id'],'kind':kind});jobs+=j['ids']
(root/'logs/smoke-jobs.json').write_text(json.dumps({'project_id':p['id'],'jobs':jobs}),encoding='utf-8')
print('Queued GPU smoke tests: '+str(jobs),flush=True)
