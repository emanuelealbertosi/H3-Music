"""Real isolated queue checks. Does not modify the user's library or settings."""
import argparse,array,json,math,pathlib,shutil,sys,threading,time,urllib.request,uuid
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import app,execution
p=argparse.ArgumentParser();p.add_argument('--engine',required=True);p.add_argument('--backend',choices=['cpu','cuda'],required=True);p.add_argument('--transcribe',action='store_true');p.add_argument('--model',choices=['q4','q8','bf16'],default='q4');args=p.parse_args()
run=ROOT/'logs'/('hardware-'+args.backend+'-'+uuid.uuid4().hex[:8]);run.mkdir()
app.DATA=run/'data';app.OUT=app.DATA/'outputs';app.VOCI=app.DATA/'voci';app.ENGINE=pathlib.Path(args.engine).resolve();app.init()
assert app.settings()['backend']=='cpu'
app.save_settings(app.settings()|{'backend':args.backend,'model':args.model,'threads':6})
server=app.http.server.ThreadingHTTPServer(('127.0.0.1',0),app.Handler);app.PORT=server.server_address[1]
threading.Thread(target=server.serve_forever,daemon=True).start();threading.Thread(target=app.worker,daemon=True).start()
base='http://127.0.0.1:'+str(app.PORT)+'/api/'
results={'backend':args.backend,'model':args.model,'engine':execution.check_engine(app.ENGINE,args.backend),'checks':[],'folder':str(run)}
def api(path,data=None,headers=None):
 raw=json.dumps(data).encode() if isinstance(data,dict) else data
 req=urllib.request.Request(base+path,data=raw,headers={'X-H3-Music':'1','Content-Type':'application/json',**(headers or {})})
 return json.load(urllib.request.urlopen(req,timeout=120))
def job(payload):
 ident=api('jobs',payload)['ids'][0];start=time.monotonic();print('START',payload['kind'],ident,flush=True)
 while time.monotonic()-start<1200:
  j=api('jobs/'+ident)
  if j['status'] in ('completed','failed','cancelled','interrupted'):break
  time.sleep(1)
 assert j['status']=='completed',json.dumps(j,ensure_ascii=False)
 results['checks'].append({'kind':payload['kind'],'id':ident,'elapsed_seconds':round(time.monotonic()-start,2),'result':j['result']})
 print('PASS',payload['kind'],j['result'],flush=True);return ident

def audio(path):
 info=app.audio_info(path);assert info['duration']>0
 # run_capture is text-oriented; decode PCM through a binary subprocess instead.
 import subprocess
 raw=subprocess.check_output([str(app.FFMPEG),'-v','error','-i',str(path),'-t','6','-f','f32le','-ac','1','-'],creationflags=app.HIDDEN)
 samples=array.array('f',raw);assert samples and all(math.isfinite(x) for x in samples)
 rms=math.sqrt(sum(x*x for x in samples)/len(samples));assert rms>1e-7,(path,rms)
 return dict(info,rms=rms)
try:
 request={'title':'Hardware regression','style':'English acoustic pop, warm female vocal, piano, 100 BPM','lyrics':'[Verse]\nMorning light across the floor\nLet the music take us home','cot':'full','seed':831001,'options':{'num_inference_steps':8,'abc_max_tokens':128,'semantic_min_tokens':200,'semantic_max_tokens':500}}
 project=api('projects',{'request':request})
 native=job({'kind':'generate','project_id':project['id'],'request':request})
 results['generation_audio']=audio(app.OUT/native/'audio.wav')
 source=uuid.uuid4().hex;folder=app.OUT/source;folder.mkdir()
 import subprocess
 subprocess.run([str(app.FFMPEG),'-y','-v','error','-ss','5','-i',str(ROOT/'tests/Prima-luce-trascrizione.mp3'),'-t','6','-ar','48000','-ac','2',str(folder/'audio.wav')],check=True,creationflags=app.HIDDEN)
 app.db('INSERT INTO jobs(id,kind,status,request,created,result) VALUES(?,?,?,?,?,?)',(source,'generate','completed',app.jdump({'title':'Fixture originale'}),app.now(),app.jdump({'duration':6,'sample_rate':48000,'channels':2})))
 separated=job({'kind':'sep','source_id':source})
 assert all((app.OUT/separated/name).is_file() for name in ('vocals.wav','drums.wav','bass.wav','other.wav'))
 voice=app.VOCI/'test-synthetic';voice.mkdir(parents=True);shutil.copy2(app.OUT/separated/'vocals.wav',voice/'reference.wav')
 converted=job({'kind':'voice','source_id':separated,'voice':'test-synthetic'})
 results['converted_audio']=audio(app.OUT/converted/'voce.wav');results['remix_audio']=audio(app.OUT/converted/'audio.wav')
 assert results['remix_audio']['sample_rate']==48000 and results['remix_audio']['channels']==2
 assert abs(results['remix_audio']['duration']-6)<.5
 if args.transcribe:
  imported=api('audio/upload',(ROOT/'tests/Prima-luce-trascrizione.mp3').read_bytes(),{'X-Filename':'fixture.mp3','Content-Type':'audio/mpeg'})
  transcribed=job({'kind':'transcribe','request':{'source_id':imported['id'],'title':'Hardware transcription','start':5,'end':11,'melody_only':True}})
  assert (app.OUT/transcribed/'transcription.mid').read_bytes()[:4]==b'MThd'
  assert (app.OUT/transcribed/'score.abc').stat().st_size>0
 results['passed']=True
finally:
 for ident in list(app.ACTIVE):app.cancel(ident)
 server.shutdown();server.server_close()
 (run/'report.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
 (ROOT/'logs'/('hardware-'+args.backend+'-latest.json')).write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(results,ensure_ascii=False),flush=True)
