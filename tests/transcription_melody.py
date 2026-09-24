import urllib.request,json,time,pathlib
r=pathlib.Path('F:/H3-Music');base='http://127.0.0.1:8776/api/'
def api(path,data=None):
 req=urllib.request.Request(base+path,data=json.dumps(data).encode() if data else None,headers={'X-H3-Music':'1','Content-Type':'application/json'})
 return json.load(urllib.request.urlopen(req,timeout=30))
source=json.loads((r/'logs/transcription-ui-tests.json').read_text())['source_id']
ident=api('jobs',{'kind':'transcribe','request':{'source_id':source,'title':'Prima luce · melodia del ritornello','start':5,'end':17,'melody_only':True}})['ids'][0]
print('MELODY JOB',ident,flush=True)
for _ in range(450):
 j=api('jobs/'+ident)
 if j['status'] in ('completed','failed','cancelled','interrupted'):break
 time.sleep(2)
(r/'logs/transcription-melody.json').write_text(json.dumps(j,ensure_ascii=False,indent=2),encoding='utf-8')
assert j['status']=='completed',j['error']
assert abs(j['result']['duration']-12)<.05
assert j['result']['melody_only'] and j['abc']
preview=json.loads((r/'data/outputs'/ident/'preview-notes.json').read_text())
assert not any('chord' in t['name'].lower() and t['notes'] for t in preview['tracks'])
print(json.dumps({'passed':True,'id':ident,'result':j['result']},ensure_ascii=False),flush=True)
