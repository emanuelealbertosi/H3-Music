"""Generate an isolated Italian Q8/BF16 sample and observe total GPU memory."""
import argparse,array,json,math,pathlib,subprocess,sys,threading,time,uuid
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import app
p=argparse.ArgumentParser();p.add_argument('--model',choices=['q8','bf16'],required=True);a=p.parse_args()
run=ROOT/'logs'/('italian-'+a.model+'-'+uuid.uuid4().hex[:8]);run.mkdir()
app.DATA=run/'data';app.OUT=app.DATA/'outputs';app.VOCI=app.DATA/'voci';app.init()
app.save_settings(app.settings()|{'backend':'cuda','model':a.model,'threads':6})
assert app.ready()['ready']
request={'title':'Ancora una canzone · '+a.model.upper(),'style':'Italian acoustic pop ballad, solo clear female vocals, natural Italian pronunciation, expressive phrasing, piano and acoustic guitar, 90 BPM','lyrics':'[Verse]\nLa città si sveglia piano\nmentre il sole torna su\nCerco ancora la tua mano\ne una strada che sai tu\n[Chorus]\nPerché la musica rimane\nanche quando te ne vai\nPorta il cuore verso il mare\nquesta notte canterai','cot':'full','seed':831001,'options':{'num_inference_steps':32,'abc_max_tokens':1024,'semantic_min_tokens':200,'semantic_max_tokens':1500}}
report={'model':a.model,'model_file':app.main_model_file(),'request':request,'folder':str(run),'gpu_memory_samples':[]};stop=threading.Event()
def monitor():
 while not stop.is_set():
  try:
   output=subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,memory.total','--format=csv,noheader,nounits','--id=0'],creationflags=app.HIDDEN,text=True,timeout=5)
   used,total=[int(v.strip()) for v in output.strip().split(',')];report['gpu_memory_samples'].append({'time':time.time(),'used_mib':used,'total_mib':total})
  except Exception:pass
  stop.wait(1)
mon=threading.Thread(target=monitor,daemon=True);mon.start()
threading.Thread(target=app.worker,daemon=True).start()
ident=None
try:
 project=app.project_save({'request':request})
 ident=app.enqueue({'kind':'generate','project_id':project['id'],'request':request})['ids'][0];print('START',a.model,ident,flush=True);start=time.monotonic()
 while time.monotonic()-start<1800:
  job=app.get_job(ident)
  if job['status'] in ('completed','failed','cancelled','interrupted'):break
  time.sleep(1)
 report['job']=job;report['elapsed_seconds']=round(time.monotonic()-start,2)
 assert job['status']=='completed',job.get('error') or job['status']
 audio=app.OUT/ident/'audio.wav';report['audio']=str(audio);report['audio_info']=app.audio_info(audio)
 raw=subprocess.check_output([str(app.FFMPEG),'-v','error','-i',str(audio),'-f','f32le','-ac','1','-'],creationflags=app.HIDDEN)
 samples=array.array('f',raw);assert samples and all(math.isfinite(x) for x in samples)
 report['rms']=math.sqrt(sum(x*x for x in samples)/len(samples));assert report['rms']>1e-7
 report['passed']=True
finally:
 stop.set();mon.join(timeout=10)
 if ident and app.get_job(ident)['status'] in ('queued','running'):app.cancel(ident)
 report['observed_peak_gpu_mib']=max((x['used_mib'] for x in report['gpu_memory_samples']),default=None)
 report['gpu_memory_note']='Total GPU memory observed by nvidia-smi, including desktop and other processes; not an exact allocation profile.'
 (run/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 (ROOT/'logs'/('italian-'+a.model+'-latest.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ('job','gpu_memory_samples','request')},ensure_ascii=False),flush=True)
