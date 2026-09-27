"""Reference upload and automatic voice replacement, with no music regeneration for imports."""
import hashlib,json,shutil,math,array,sys,wave
import transcription, mixing

def preflight(app,voice, instrumental=False):
 if not app.ENGINE.is_file() or not app.FFMPEG.is_file():raise ValueError('Completa prima install.bat.')
 if not app.separation_model():raise ValueError('Manca il modello di separazione: esegui install.bat per completarlo.')
 if instrumental:return None
 if not app.voice_model():raise ValueError('Manca il modello voce: esegui install.bat per completarlo.')
 ref=app.voice_sample(voice)
 if not ref or not ref.is_file():raise ValueError('Carica o scegli un campione di voce prima di avviare.')
 return ref

def import_voice(app,data):
 source,meta=transcription.source(app.DATA,data.get('source_id'))
 if not 1<=meta['duration']<=60:raise ValueError('Per la voce usa un campione tra 1 e 60 secondi; consigliati 10–30 secondi puliti.')
 ident=app.uid();folder=app.VOCI/ident;folder.mkdir(parents=True)
 try:
  target=folder/('reference'+source.suffix);shutil.copy2(source,target)
  app.write_json(folder/'voice.json',{'label':str(data.get('name') or meta['name']).strip()[:120], 'source_id':meta['id'],'duration':meta['duration']})
 except BaseException:
  for p in folder.iterdir():p.unlink()
  folder.rmdir();raise
 return next(v for v in app.voice_list() if v['name']==ident)

def enqueue(app,data):
 req=data.get('request',data);voice=str(req.get('clone_voice') or '');instrumental=data.get('kind')=='instrumental'
 preflight(app,voice,instrumental=instrumental);_,meta=transcription.source(app.DATA,req.get('import_id'))
 request={'title':str(req.get('title') or (meta['name']+(' · solo musica' if instrumental else ' · la mia voce'))).strip()[:120], 'import_id':meta['id'],'source_name':meta['name'],'clone_voice':voice,'clone_enabled':not instrumental,'style':'Base originale','lyrics':'','abc':'','notes':'','cot':'off','seed':0,'options':{}}
 request['mix']=mixing.validate(req.get('mix'))
 ident=app.uid();app.db('INSERT INTO jobs(id,kind,status,request,created) VALUES(?,?,?,?,?)',(ident,'instrumental' if instrumental else 'clone','queued',app.jdump(request),app.now()));app.WAKE.set()
 return {'ids':[ident]}

def process(app,job,d):
 req=job['request'];instrumental=job['kind']=='instrumental';ref=preflight(app,req.get('clone_voice',''),instrumental=instrumental);app.check_cancel(job['id'])
 original=d/'original.wav';app.write_json(d/'request.json',req)
 if job['kind'] in ('clone','instrumental'):
  source,meta=transcription.source(app.DATA,req['import_id']);app.write_json(d/'source.json',meta)
  app.run_job_process(job,d,[str(app.FFMPEG),'-y','-v','error','-nostdin','-protocol_whitelist','file,pipe','-i',str(source),'-ar','48000','-ac','2',str(original)],append=True,phase=('Preparazione della canzone',5))
 else:shutil.copy2(d/'audio.wav',original)
 stems=d/'stems';stems.mkdir(exist_ok=True);normalized=stems/'input.wav';s=app.settings()
 app.run_job_process(job,d,[str(app.FFMPEG),'-y','-v','error','-nostdin','-i',str(original),'-ar','44100','-ac','2',str(normalized)],append=True,phase=('Preparazione della separazione',10))
 app.run_job_process(job,d,[str(app.ENGINE),'--task','sep','--family','htdemucs','--model',str(app.separation_model()),'--backend',s['backend'],'--threads',str(s['threads']),'--audio',str(normalized),'--out-dir',str(stems),'--log','--metrics'],append=True,phase=('Separazione voce e base',25))
 if not all((stems/n).is_file() for n in ('vocals.wav','drums.wav','bass.wav','other.wav')):raise RuntimeError('Separazione incompleta: il cambio voce non è stato avviato.')
 if instrumental:
  final=d/'audio.wav'
  args=[str(app.FFMPEG),'-y','-v','error','-nostdin']
  for name in ('drums.wav','bass.wav','other.wav'):args+=['-i',str(stems/name)]
  args+=['-filter_complex','[0:a][1:a][2:a]amix=inputs=3:duration=longest:normalize=0','-ar','48000','-ac','2','-c:a','pcm_s24le',str(final)]
  app.run_job_process(job,d,args,append=True,phase=('Salvataggio della sola musica',95));app.check_cancel(job['id'])
  result=app.audio_info(final)|{'instrumental':True,'original_preserved':True,'source_kind':'import','import_id':req['import_id']}
  app.write_json(d/'manifest.json',{'result':result,'sha256':{name:hashlib.sha256((d/name).read_bytes()).hexdigest() for name in ('audio.wav','original.wav')}})
  return result
 reference_source=d/('reference-source'+ref.suffix);shutil.copy2(ref,reference_source)
 reference=d/'reference.wav'
 app.run_job_process(job,d,[str(app.FFMPEG),'-y','-v','error','-nostdin','-protocol_whitelist','file,pipe','-i',str(reference_source),'-ar','44100','-ac','1',str(reference)],append=True,phase=('Preparazione del campione vocale',55))
 converted=d/'voce.wav'
 convert_voice(app,job,d,stems/'vocals.wav',reference,converted,s)
 app.check_cancel(job['id'])
 final=app.mix_voice(job,d,converted,source=stems,runner=lambda args:app.run_job_process(job,d,args,append=True,phase=('Rimix con la base',95)))
 app.check_cancel(job['id']);result=app.audio_info(final)|{'voice':req['clone_voice'],'cloned':True,'pitch_conditioning':True,'voice_pipeline':'segmented-v1','original_preserved':True,'source_kind':'import' if job['kind']=='clone' else 'generated'}
 if job['kind'] in ('clone','instrumental'):result['import_id']=req['import_id']
 def digest(p):
  with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
 app.write_json(d/'voice-manifest.json',{'result':result,'sha256':{name:digest(d/name) for name in ('audio.wav','original.wav','voce.wav',reference.name)}})
 return result


def voice_command(app,source,reference,output,settings=None):
 s=settings or app.settings()
 # The singing checkpoint needs pitch conditioning; the native default is false.
 return [str(app.ENGINE),'--task','svc','--family','seed_vc','--model',str(app.voice_model()),'--backend',s['backend'],'--threads',str(s['threads']),'--task-route','v1_svc','--request-option','f0_condition=true','--request-option','auto_f0_adjust=false','--request-option','semitone_shift=0','--audio',str(source),'--voice-ref',str(reference),'--out',str(output),'--log','--metrics']


VOICE_RATE=44100
VOICE_WINDOW=25*VOICE_RATE
VOICE_OVERLAP=int(.4*VOICE_RATE)

def voice_segments(frames):
 # Bundled native Whisper content extraction truncates at 30 seconds.
 if frames<=0:raise ValueError('La traccia vocale è vuota.')
 result=[];start=0
 while start<frames:
  end=min(start+VOICE_WINDOW,frames);result.append((start,end))
  if end==frames:break
  start=end-VOICE_OVERLAP
 return result

def join_voice_segments(paths,output,check_cancel):
 # Crossfade only the shared samples; never stretch a chunk or shift the base.
 pending=array.array('h')
 with wave.open(str(output),'wb') as out:
  out.setparams((1,2,VOICE_RATE,0,'NONE','not compressed'))
  for index,path in enumerate(paths):
   check_cancel()
   with wave.open(str(path),'rb') as inp:
    if (inp.getnchannels(),inp.getsampwidth(),inp.getframerate())!=(1,2,VOICE_RATE):raise ValueError('Formato segmento vocale non valido.')
    samples=array.array('h');samples.frombytes(inp.readframes(inp.getnframes()))
   if sys.byteorder!='little':samples.byteswap()
   if pending:
    n=len(pending)
    if len(samples)<n:raise ValueError('Segmento vocale troppo corto.')
    blended=array.array('h',(round(pending[i]*(1-i/(n-1))+samples[i]*i/(n-1)) for i in range(n)))
    if sys.byteorder!='little':blended.byteswap()
    out.writeframes(blended.tobytes());samples=samples[n:]
   pending=samples[-VOICE_OVERLAP:] if index<len(paths)-1 else array.array('h')
   body=samples[:-VOICE_OVERLAP] if pending else samples
   if sys.byteorder!='little':body.byteswap()
   out.writeframes(body.tobytes())

def quiet_voice_segment(path):
 with wave.open(str(path),'rb') as inp:
  if (inp.getnchannels(),inp.getsampwidth())!=(1,2):return False
  values=array.array('h');values.frombytes(inp.readframes(inp.getnframes()))
 if sys.byteorder!='little':values.byteswap()
 return bool(values) and max(abs(x) for x in values)<328 and sum(x*x for x in values)/len(values)<(32768*.001)**2

def convert_voice(app,job,d,source,reference,output,settings=None):
 settings=settings or app.settings()
 duration=app.audio_info(source)['duration']
 if not math.isfinite(duration) or duration<=0:raise ValueError('La traccia vocale è vuota.')
 segments=voice_segments(round(duration*VOICE_RATE))
 if len(segments)==1:
  app.run_job_process(job,d,voice_command(app,source,reference,output,settings),append=True,phase=('Applicazione della tua voce',65));return
 folder=d/'voice-segments';folder.mkdir(exist_ok=True);paths=[];quiet=[]
 for index,(start,end) in enumerate(segments):
  app.check_cancel(job['id']);src=folder/f'{index:03d}-source.wav';raw=folder/f'{index:03d}-raw.wav';aligned=folder/f'{index:03d}.wav'
  phase=(f'Applicazione della tua voce · {index+1}/{len(segments)}',65+int(27*index/len(segments)))
  app.run_job_process(job,d,[str(app.FFMPEG),'-y','-v','error','-nostdin','-i',str(source),'-af',f'aresample={VOICE_RATE},atrim=start_sample={start}:end_sample={end},asetpts=PTS-STARTPTS','-ar',str(VOICE_RATE),'-ac','1',str(src)],append=True,phase=phase)
  if quiet_voice_segment(src):
   shutil.copy2(src,aligned);paths.append(aligned);quiet.append(index);continue
  app.run_job_process(job,d,voice_command(app,src,reference,raw,settings),append=True,phase=phase)
  # The vocoder rounds to mel hops; only pad/trim the tiny rounding difference.
  produced=app.audio_info(raw)['duration']
  if abs(produced-(end-start)/VOICE_RATE)>.25:raise RuntimeError('Durata della voce convertita incoerente: il rimix è stato fermato.')
  app.run_job_process(job,d,[str(app.FFMPEG),'-y','-v','error','-nostdin','-i',str(raw),'-af',f'apad=whole_len={end-start},atrim=end_sample={end-start}','-ar',str(VOICE_RATE),'-ac','1','-c:a','pcm_s16le',str(aligned)],append=True,phase=phase)
  paths.append(aligned)
 join_voice_segments(paths,output,lambda:app.check_cancel(job['id']))
 app.write_json(d/'voice-segments.json',{'sample_rate':VOICE_RATE,'overlap_samples':VOICE_OVERLAP,'quiet_passthrough':quiet,'segments':[{'start_sample':a,'end_sample':b} for a,b in segments]})
