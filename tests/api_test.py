import json,urllib.request,urllib.error,subprocess,pathlib,time
root=pathlib.Path(__file__).resolve().parents[1]; base='http://127.0.0.1:8776'
def call(path,data=None,headers=None):
 h={'X-H3-Music':'1','Content-Type':'application/json'} if data is not None else {}
 h.update(headers or {})
 q=urllib.request.Request(base+path,data=json.dumps(data).encode() if data is not None else None,headers=h)
 try:
  with urllib.request.urlopen(q,timeout=20) as r:return r.status,r.read(),dict(r.headers)
 except urllib.error.HTTPError as e:return e.code,e.read(),dict(e.headers)
status,raw,_=call('/api/state');before=json.loads(raw)['projects'];assert status==200
call('/api/shutdown',{})
for _ in range(40):
 try:call('/api/health');time.sleep(.1)
 except (urllib.error.URLError,ConnectionResetError):break
subprocess.Popen([str(root/'runtime/python/pythonw.exe'),str(root/'app.py')],cwd=root,creationflags=0x08000000)
for _ in range(50):
 try:
  status,raw,_=call('/api/health')
  if status==200:break
 except (urllib.error.URLError,ConnectionResetError):pass
 time.sleep(.2)
assert json.loads(raw)['app']=='H3-Music'
_,after,_=call('/api/state');assert [p['id'] for p in json.loads(after)['projects']]==[p['id'] for p in before]
assert call('/api/projects',{}, {'Origin':'http://evil.example'})[0]==403
assert call('/api/health',headers={'Host':'evil.example'})[0]==403
status,raw,headers=call('/static/app.js',headers={'Range':'bytes=0-31'})
assert status==206 and len(raw)==32 and headers['Content-Range'].startswith('bytes 0-31/')
assert call('/static/%2e%2e/app.py')[0]==400
assert call('/api/projects',{'request':{'cot':'off','abc':'X:1'}})[0]==400
assert call('/api/settings',{'llm_url':'http://example.com'})[0]==400
(root/'logs/api-tests.json').write_text(json.dumps({'passed':True,'checks':['service restart','project persistence','origin guard','host guard','audio range protocol','path containment','invalid combination rejection','local LLM restriction']},indent=2),encoding='utf-8')
print('API integration checks passed')
