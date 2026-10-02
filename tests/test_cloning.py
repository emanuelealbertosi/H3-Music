import pathlib,sys,tempfile,unittest,json,shutil,wave,array,math,subprocess,hashlib
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import app,cloning
class CloningTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=app.ROOT/'tests');self.old=app.DATA,app.OUT,app.VOCI
  app.DATA=pathlib.Path(self.temp.name);app.OUT=app.DATA/'outputs';app.VOCI=app.DATA/'voci';app.init()
  self.source_id=app.uid();folder=app.DATA/'imports'/self.source_id;folder.mkdir(parents=True)
  (folder/'source.wav').write_bytes(b'original audio')
  self.meta={'id':self.source_id,'name':'Canzone.wav','file':'source.wav','duration':12,'created':app.now()};app.write_json(folder/'metadata.json',self.meta)
  self.voice=cloning.import_voice(app,{'source_id':self.source_id,'name':'La mia voce'})
 def tearDown(self):
  app.DATA,app.OUT,app.VOCI=self.old
  assert pathlib.Path(self.temp.name).resolve().is_relative_to((app.ROOT/'tests').resolve());self.temp.cleanup()
 def queued(self):
  with patch.object(cloning,'preflight',return_value=app.voice_sample(self.voice['name'])):
   ident=app.enqueue({'kind':'clone','request':{'import_id':self.source_id,'clone_voice':self.voice['name'],'title':'Prova'}})['ids'][0]
  d=app.OUT/ident;d.mkdir();return app.get_job(ident),d
 def test_import_reuse_unique_and_validation(self):
  second=cloning.import_voice(app,{'source_id':self.source_id,'name':'La mia voce'})
  self.assertNotEqual(second['name'],self.voice['name']);self.assertEqual(self.voice['label'],'La mia voce')
  self.assertEqual(app.voice_sample(second['name']).read_bytes(),b'original audio')
  with self.assertRaises(ValueError):cloning.import_voice(app,{'source_id':'../outside'})
  app.write_json(app.DATA/'imports'/self.source_id/'metadata.json',self.meta|{'duration':61})
  with self.assertRaises(ValueError):cloning.import_voice(app,{'source_id':self.source_id})
 def test_old_projects_and_clone_validation(self):
  self.assertFalse(app.validate({})['clone_enabled']);self.assertEqual(app.validate({'clone_enabled':True,'clone_voice':'x'})['clone_voice'],'x')
  with self.assertRaises(ValueError):app.validate({'clone_enabled':'yes'})
  with self.assertRaises(ValueError):cloning.preflight(app,'missing voice')
 def test_voice_quality_validation_and_snapshots(self):
  self.assertEqual(app.validate({})['voice_steps'],30)
  for steps in (30,50,100):
   self.assertEqual(app.validate({'voice_steps':steps,'options':{'num_inference_steps':8}})['voice_steps'],steps)
   with patch.object(cloning,'preflight',return_value=app.voice_sample(self.voice['name'])):
    request={'import_id':self.source_id,'clone_voice':self.voice['name'],'voice_steps':steps}
    ident=app.enqueue({'kind':'clone','request':request})['ids'][0]
    saved=app.get_job(ident)['request'];request['voice_steps']=30
    self.assertEqual(saved['voice_steps'],steps)
    retried=app.enqueue({'kind':'clone','request':saved})['ids'][0]
    self.assertEqual(app.get_job(retried)['request'],saved)
  for bad in (None,True,30.0,'50',0,31,101,[],{}):
   with self.assertRaises(ValueError):app.validate({'voice_steps':bad})
 def test_voice_quality_commands_cpu_and_gpu(self):
  for backend in ('cpu','cuda'):
   for steps in (30,50,100):
    args=cloning.voice_command(app,'a','b','c',{'backend':backend,'threads':2},steps)
    self.assertIn(f'num_inference_steps={steps}',args)
    self.assertIn('inference_guidance_scale=0.4',args)
    self.assertIn('seed=831001',args)
    self.assertEqual(args[args.index('--backend')+1],backend)
 def test_voice_quality_all_long_segments(self):
  job,d=self.queued();job['request']['voice_steps']=100;source=d/'source.wav';calls=[]
  parts=cloning.voice_segments(60*cloning.VOICE_RATE)
  def info(path):
   if path==source:return {'duration':60}
   index=int(path.name.split('-')[0]);a,b=parts[index];return {'duration':(b-a)/cloning.VOICE_RATE}
  with patch.object(cloning,'prepare_reference',return_value=d/'ref.wav'),patch.object(cloning,'prepare_voice_input',return_value=source),patch.object(app,'audio_info',side_effect=info),patch.object(app,'run_job_process',side_effect=lambda j,d,args,**kw:calls.append(args)),patch.object(cloning,'quiet_voice_segment',return_value=False),patch.object(cloning,'join_voice_segments'):
   cloning.convert_voice(app,job,d,source,d/'ref.wav',d/'voice.wav',{'backend':'cpu','threads':2})
  svc=[args for args in calls if '--task' in args]
  self.assertEqual(len(svc),len(parts));self.assertTrue(all('num_inference_steps=100' in args for args in svc))
  self.assertEqual(json.loads((d/'voice-segments.json').read_text())['voice_steps'],100)
 def test_import_independent_from_yue2_and_cancel_before_launch(self):
  with patch.object(app,'ready',side_effect=AssertionError('YuE2 must not be queried')):job,d=self.queued()
  app.cancel(job['id'])
  with patch.object(app.subprocess,'Popen') as launch,self.assertRaises(app.JobCancelled):app.run_job_process(job,d,['unused'])
  launch.assert_not_called()
  with patch.object(cloning,'preflight',return_value=app.voice_sample(self.voice['name'])):
   retry=app.enqueue({'kind':'clone','request':job['request']})
  self.assertEqual(app.get_job(retry['ids'][0])['request'],job['request'])
 def exercise(self,missing=False,cancel=False,generated=False):
  job,d=self.queued();calls=[]
  if generated:job['kind']='generate';(d/'audio.wav').write_bytes(b'generated original')
  def run(j,folder,args,**kw):
   app.check_cancel(j['id']);calls.append(args)
   if '--task' in args:
    task=args[args.index('--task')+1]
    if task=='sep':
     for name in ('vocals','drums','bass','other'):
      if not(missing and name=='other'):(d/'stems'/(name+'.wav')).write_bytes(name.encode())
     if cancel:app.cancel(j['id'])
    elif task=='svc':(d/'voce.wav').write_bytes(b'converted')
    else:raise AssertionError('Unexpected music generation')
   else:pathlib.Path(args[-1]).write_bytes(b'normalized')
  def mix(*args,**kw):
   self.assertEqual(kw['source'],d/'stems');kw['runner'](['fake mix',str(d/'audio.wav')]);return d/'audio.wav'
  def convert(a,j,folder,source,reference,output,settings):a.run_job_process(j,folder,cloning.voice_command(a,source,reference,output,settings))
  with patch.object(cloning,'convert_voice',side_effect=convert),patch.object(cloning,'preflight',return_value=app.voice_sample(self.voice['name'])),patch.object(app,'run_job_process',side_effect=run),patch.object(app,'mix_voice',side_effect=mix),patch.object(app,'audio_info',return_value={'duration':12}):
   if missing:
    with self.assertRaisesRegex(RuntimeError,'incompleta'):cloning.process(app,job,d)
   elif cancel:
    with self.assertRaises(app.JobCancelled):cloning.process(app,job,d)
   else:
    result=cloning.process(app,job,d);self.assertTrue(result['cloned']);self.assertEqual(result['source_kind'],'generated' if generated else 'import')
    self.assertTrue((d/'voice-manifest.json').exists())
    if generated:self.assertEqual((d/'original.wav').read_bytes(),b'generated original')
  tasks=[a[a.index('--task')+1] for a in calls if '--task' in a];self.assertEqual(tasks,['sep'] if missing or cancel else ['sep','svc'])
  self.assertEqual((app.DATA/'imports'/self.source_id/'source.wav').read_bytes(),b'original audio')
 def test_singing_commands_preserve_pitch(self):
  args=cloning.voice_command(app,'singing.wav','reference.wav','out.wav',{'backend':'cpu','threads':2})
  self.assertIn('f0_condition=true',args);self.assertIn('auto_f0_adjust=false',args);self.assertIn('semitone_shift=0',args)
  self.assertEqual(args[args.index('--task-route')+1],'v1_svc')
  job={'kind':'voice','request':{'source_id':'abc','voice':self.voice['name']}}
  self.assertIn('f0_condition=true',app.command_for(job,app.OUT))
 def test_instrumental_requires_no_reference_or_voice_model(self):
  with patch.object(app,'voice_model',side_effect=AssertionError('Voice model must not be needed')),patch.object(app,'ready',side_effect=AssertionError('YuE2 must not be needed')):
   result=app.enqueue({'kind':'instrumental','request':{'import_id':self.source_id}})
  job=app.get_job(result['ids'][0]);self.assertEqual(job['kind'],'instrumental');self.assertFalse(job['request']['clone_enabled'])
 def test_instrumental_mix_excludes_vocals(self):
  job,d=self.queued();job['kind']='instrumental';job['request']['clone_voice']='';calls=[]
  def run(j,folder,args,**kw):
   calls.append(args)
   if '--task' in args:
    self.assertEqual(args[args.index('--task')+1],'sep')
    for name in ('vocals','drums','bass','other'):(d/'stems'/(name+'.wav')).write_bytes(name.encode())
   else:pathlib.Path(args[-1]).write_bytes(b'normalized')
  with patch.object(app,'run_job_process',side_effect=run),patch.object(app,'audio_info',return_value={'duration':12}),patch.object(app,'voice_model',side_effect=AssertionError('No conversion')):
   result=cloning.process(app,job,d)
  self.assertTrue(result['instrumental']);self.assertEqual(result['import_id'],self.source_id)
  self.assertNotIn(str(d/'stems/vocals.wav'),calls[-1]);self.assertIn(str(d/'stems/other.wav'),calls[-1])
  self.assertTrue((d/'manifest.json').exists());self.assertFalse((d/'voce.wav').exists())
 def test_long_voice_segments_cover_every_sample(self):
  for seconds in (1,18,18.001,25,25.001,49.6,60,149.999,150,150.001,173.662,240,1800):
   frames=round(seconds*cloning.VOICE_RATE);parts=cloning.voice_segments(frames)
   self.assertEqual(parts[0][0],0);self.assertEqual(parts[-1][1],frames)
   self.assertTrue(all(0<b-a<=cloning.VOICE_WINDOW for a,b in parts))
   for previous,current in zip(parts,parts[1:]):self.assertEqual(previous[1]-current[0],cloning.VOICE_OVERLAP)
   self.assertEqual(sum(b-a for a,b in parts)-(len(parts)-1)*cloning.VOICE_OVERLAP,frames)
   self.assertTrue(all((b-a)/cloning.VOICE_RATE+cloning.REFERENCE_SECONDS<30 for a,b in parts))
 def test_reference_selection_avoids_leading_silence_and_leaves_context(self):
  rate=cloning.VOICE_RATE;values=array.array('h',[0])*(4*rate)
  values.extend(round(6000*math.sin(2*math.pi*160*i/rate)) for i in range(8*rate));values.extend(array.array('h',[0])*(8*rate))
  path=app.DATA/'spoken.wav'
  with wave.open(str(path),'wb') as f:f.setparams((1,2,rate,0,'NONE','not compressed'));f.writeframes(values.tobytes())
  selected=cloning.reference_window(path)
  self.assertGreaterEqual(selected['start_sample']/rate,3.8)
  self.assertLessEqual(selected['end_sample']/rate,12.2)
  self.assertLessEqual(selected['duration'],10)
  self.assertLessEqual(selected['peak']*10**(selected['gain_db']/20),.75)
  self.assertLess(cloning.VOICE_WINDOW/rate+selected['duration'],30)
 def test_reference_selection_rejects_silence_and_preserves_short_samples(self):
  rate=cloning.VOICE_RATE;path=app.DATA/'short.wav'
  for level in (0,1000):
   values=array.array('h',(round(level*math.sin(2*math.pi*140*i/rate)) for i in range(rate)))
   with wave.open(str(path),'wb') as f:f.setparams((1,2,rate,0,'NONE','not compressed'));f.writeframes(values.tobytes())
   if level:self.assertAlmostEqual(cloning.reference_window(path)['duration'],1)
   else:
    with self.assertRaisesRegex(ValueError,'silenzioso'):cloning.reference_window(path)
 def prepared_conversion(self,silent=False):
  job,d=self.queued();rate=cloning.VOICE_RATE;source=d/'source.wav';reference=d/'sample.wav'
  for path,seconds,level in ((source,4,0 if silent else 8000),(reference,12,3000)):
   values=array.array('h',(round(level*math.sin(2*math.pi*150*i/rate)) for i in range(seconds*rate)))
   with wave.open(str(path),'wb') as f:f.setparams((1,2,rate,0,'NONE','not compressed'));f.writeframes(values.tobytes())
  hashes=[hashlib.sha256(p.read_bytes()).hexdigest() for p in (source,reference)];commands=[]
  def run(j,folder,args,**kw):
   app.check_cancel(j['id'])
   if '--task' in args:
    commands.append(args);shutil.copy2(args[args.index('--audio')+1],args[args.index('--out')+1])
   else:
    with (folder/'engine.log').open('ab') as log:subprocess.run(args,stdout=log,stderr=log,check=True,creationflags=app.HIDDEN)
  with patch.object(app,'run_job_process',side_effect=run):cloning.convert_voice(app,job,d,source,reference,d/'converted.wav',{'backend':'cpu','threads':2})
  self.assertEqual(len(commands),0 if silent else 1)
  with wave.open(str(d/'converted.wav'),'rb') as f:
   self.assertEqual(f.getnframes(),4*rate)
   if silent:self.assertEqual(set(f.readframes(f.getnframes())),{0})
  with wave.open(str(d/'voice-reference.wav'),'rb') as f:self.assertLessEqual(f.getnframes(),10*rate)
  self.assertEqual(hashes,[hashlib.sha256(p.read_bytes()).hexdigest() for p in (source,reference)])
  manifest=json.loads((d/'voice-segments.json').read_text())
  self.assertEqual(manifest['quiet_passthrough'],[0] if silent else [])
  if commands:self.assertIn('seed=0',commands[0])
 def test_short_conversion_prepares_reference_without_modifying_uploads(self):self.prepared_conversion()
 def test_short_silence_bypasses_native_conversion(self):self.prepared_conversion(silent=True)
 def test_source_preparation_retains_headroom_for_float_audio(self):
  job,d=self.queued();source=d/'hot.wav'
  subprocess.run([str(app.FFMPEG),'-y','-v','error','-f','lavfi','-i','sine=frequency=440:duration=1','-af','volume=12','-c:a','pcm_f32le',str(source)],check=True,creationflags=app.HIDDEN)
  digest=hashlib.sha256(source.read_bytes()).hexdigest()
  def run(j,folder,args,**kw):
   with (folder/'engine.log').open('ab') as log:subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,check=True,creationflags=app.HIDDEN)
  with patch.object(app,'run_job_process',side_effect=run):
   out=cloning.prepare_voice_input(app,job,d,source)
  with wave.open(str(out),'rb') as f:
   self.assertEqual(f.getnframes(),cloning.VOICE_RATE);values=array.array('h');values.frombytes(f.readframes(f.getnframes()))
  self.assertLess(max(abs(x) for x in values)/32768,.72)
  self.assertLess(json.loads((d/'voice-input.json').read_text())['gain_db'],0)
  self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),digest)
 def test_crossfade_preserves_timing_and_late_content(self):
  paths=[];n=cloning.VOICE_OVERLAP
  for i,level in enumerate((1000,2000,3000)):
   path=app.DATA/f'part{i}.wav';paths.append(path)
   with wave.open(str(path),'wb') as f:f.setparams((1,2,cloning.VOICE_RATE,0,'NONE','not compressed'));f.writeframes(array.array('h',[level]*(n*3)).tobytes())
  out=app.DATA/'joined.wav';cloning.join_voice_segments(paths,out,lambda:None)
  with wave.open(str(out),'rb') as f:
   self.assertEqual(f.getnframes(),n*7);samples=array.array('h');samples.frombytes(f.readframes(f.getnframes()))
  self.assertEqual(samples[0],1000);self.assertEqual(samples[-1],3000);self.assertLessEqual(max(abs(b-a) for a,b in zip(samples,samples[1:])),1)
 def test_near_silent_tail_is_not_synthesized(self):
  path=app.DATA/'silence.wav'
  with wave.open(str(path),'wb') as f:f.setparams((1,2,44100,0,'NONE','not compressed'));f.writeframes(array.array('h',[2,-2]*1000).tobytes())
  self.assertTrue(cloning.quiet_voice_segment(path))
  with wave.open(str(path),'wb') as f:f.setparams((1,2,44100,0,'NONE','not compressed'));f.writeframes(array.array('h',[500,-500]*1000).tobytes())
  self.assertFalse(cloning.quiet_voice_segment(path))
 def test_crossfade_cancel_does_not_continue(self):
  with self.assertRaises(app.JobCancelled):cloning.join_voice_segments([app.DATA/'unused'],app.DATA/'cancelled.wav',lambda:(_ for _ in ()).throw(app.JobCancelled()))
 def test_import_pipeline_preserves_original(self):self.exercise()
 def test_generation_pipeline_preserves_original(self):self.exercise(generated=True)
 def test_incomplete_stems_abort_conversion(self):self.exercise(missing=True)
 def test_cancel_between_stages_stops_pipeline(self):self.exercise(cancel=True)
if __name__=='__main__':unittest.main(verbosity=2)
