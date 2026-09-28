"""Run both transcription modes in an isolated archive with installed models."""
import json,pathlib,sys,subprocess,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import app,transcription,execution

run=ROOT/'logs'/('transcription-update-'+app.uid()[:8]);run.mkdir(parents=True)
app.DATA=run/'data';app.OUT=app.DATA/'outputs';app.init()
backend=sys.argv[1] if len(sys.argv)>1 else 'cuda'
app.save_settings(app.DEFAULTS|{'backend':backend})
source_id=app.uid();source=app.DATA/'imports'/source_id;source.mkdir(parents=True)
import shutil
shutil.copy2(ROOT/'tests/Prima-luce-trascrizione.mp3',source/'source.mp3')
meta={'id':source_id,'name':'Test.mp3','file':'source.mp3','created':app.now(),**app.audio_info(source/'source.mp3')}
app.write_json(source/'metadata.json',meta)
report={'revision':transcription.installed_revision(ROOT),'backend':backend,'results':[]}
for melody in (False,True):
 ident=app.enqueue({'kind':'transcribe','request':{'source_id':source_id,'start':5,'end':17,'melody_only':melody}})['ids'][0]
 job=app.get_job(ident);d=app.OUT/ident;d.mkdir();args=transcription.command(app,job,d)
 started=time.monotonic()
 with (d/'engine.log').open('wb') as log:
  done=subprocess.run(args,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,creationflags=app.HIDDEN,timeout=600)
 assert done.returncode==0,(d/'engine.log').read_text(encoding='utf-8',errors='replace')[-3500:]
 result=transcription.finish(app,job,d)
 assert (d/'score.abc').read_text(encoding='utf-8').strip()
 assert (d/'transcription.mid').read_bytes().startswith(b'MThd')
 assert result['melody_only']==melody and abs(result['duration']-12)<.01
 assert result['melody_notes']>0
 manifest=json.loads((d/'manifest.json').read_text(encoding='utf-8'));assert manifest['revision']==report['revision']
 record={'melody_only':melody,'elapsed':round(time.monotonic()-started,2),'folder':str(d),'result':result};report['results'].append(record)
 print(json.dumps({'passed':True,'melody_only':melody,'elapsed':record['elapsed'],'notes':result['melody_notes']}),flush=True)
app.write_json(ROOT/'logs/transcription-update-latest.json',report)
