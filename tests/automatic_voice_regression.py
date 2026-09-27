"""Real, isolated HTTP upload -> replacement and generation -> replacement checks."""
import pathlib,sys,threading,time,json,urllib.request,urllib.parse,hashlib,array,math
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));import app
run=ROOT/'logs'/('automatic-voice-'+app.uid()[:8]);run.mkdir();app.DATA=run/'data';app.OUT=app.DATA/'outputs';app.VOCI=app.DATA/'voci';app.init();app.save_settings(app.settings()|{'backend':'cuda','model':'q4','threads':6})
server=app.http.server.ThreadingHTTPServer(('127.0.0.1',0),app.Handler);app.PORT=server.server_port
threading.Thread(target=server.serve_forever,daemon=True).start();threading.Thread(target=app.worker,daemon=True).start();base=f'http://127.0.0.1:{app.PORT}'
def call(path,data=None,headers=None):
 body=json.dumps(data).encode() if isinstance(data,dict) else data
 with urllib.request.urlopen(urllib.request.Request(base+path,data=body,headers={'X-H3-Music':'1',**(headers or {})}),timeout=120) as r:return json.load(r)
def upload(p):return call('/api/audio/upload',p.read_bytes(),{'X-Filename':urllib.parse.quote(p.name)})
def wait(ident):
 start=time.monotonic()
 while time.monotonic()-start<900:
  job=app.get_job(ident)
  if job['status'] in ('completed','failed','cancelled'):break
  time.sleep(1)
 assert job['status']=='completed',job
 d=app.OUT/ident;audio=d/'audio.wav'
 import subprocess
 samples=array.array('f',subprocess.check_output([str(app.FFMPEG),'-v','error','-i',str(audio),'-f','f32le','-ac','1','-'],creationflags=app.HIDDEN));assert samples and all(math.isfinite(x) for x in samples)
 rms=math.sqrt(sum(x*x for x in samples)/len(samples));assert rms>1e-7
 manifest=json.loads((d/'voice-manifest.json').read_text(encoding='utf-8'));assert manifest['sha256']['audio.wav']==hashlib.sha256(audio.read_bytes()).hexdigest()
 assert job['result']['cloned'];assert job['result']['sample_rate']==48000;assert job['result']['channels']==2
 print('PASS',job['kind'],round(time.monotonic()-start,2),job['result'],flush=True)
 return {'id':ident,'kind':job['kind'],'elapsed':round(time.monotonic()-start,2),'result':job['result'],'rms':rms,'folder':str(d)}
report={'folder':str(run)}
try:
 song=run/'song.wav';ref=run/'reference.m4a'
 for source,out in [(ROOT/'tests/Prima-luce-trascrizione.mp3',song),(ROOT/'tests/Prima-luce-trascrizione.mp3',ref)]:
  result=app.run_capture([str(app.FFMPEG),'-y','-v','error','-i',str(source),'-t','6','-ar','48000',str(out)],60);assert result.returncode==0,result.stderr
 imported=upload(song);reference=upload(ref);voice=call('/api/voices/import',{'source_id':reference['id'],'name':'Campione sintetico di collaudo'})
 original_digest=hashlib.sha256(song.read_bytes()).hexdigest()
 ident=call('/api/jobs',{'kind':'clone','request':{'import_id':imported['id'],'clone_voice':voice['name'],'title':'Originale con nuova voce'}})['ids'][0]
 report['import']=wait(ident)
 source,_=app.transcription.source(app.DATA,imported['id']);assert hashlib.sha256(source.read_bytes()).hexdigest()==original_digest
 log=(app.OUT/ident/'engine.log').read_text(encoding='utf-8',errors='replace');assert 'yue2.' not in log
 req={'title':'Generazione con voce automatica','style':'Italian pop, solo female vocals, acoustic guitar','lyrics':'[Verse]\nSotto il cielo della sera\nCanto piano una canzone','cot':'off','clone_enabled':True,'clone_voice':voice['name'],'seed':831001,'options':{'num_inference_steps':8,'semantic_min_tokens':200,'semantic_max_tokens':500}}
 project=call('/api/projects',{'request':req})
 ident=call('/api/jobs',{'kind':'generate','project_id':project['id'],'request':req})['ids'][0];report['generate']=wait(ident)
 d=app.OUT/ident;manifest=json.loads((d/'manifest.json').read_text(encoding='utf-8'));assert manifest['sha256']['audio.wav']==hashlib.sha256((d/'audio.wav').read_bytes()).hexdigest();assert (d/'original.wav').read_bytes()!=(d/'audio.wav').read_bytes()
 report['passed']=True
finally:
 server.shutdown();server.server_close();app.write_json(run/'report.json',report);app.write_json(ROOT/'logs/automatic-voice-latest.json',report)
print(json.dumps(report,ensure_ascii=False),flush=True)
