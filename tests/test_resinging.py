import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import app
import resinging


class ResingingTests(unittest.TestCase):
 def setUp(self):
  self.temp = tempfile.TemporaryDirectory(prefix='tmp-resinging-', dir=app.ROOT/'tests')
  self.old = app.DATA, app.OUT, app.VOCI
  app.DATA = pathlib.Path(self.temp.name); app.OUT = app.DATA/'outputs'; app.VOCI = app.DATA/'voci'; app.init()
  self.source = app.uid(); folder = app.DATA/'imports'/self.source; folder.mkdir(parents=True)
  (folder/'source.wav').write_bytes(b'original untouched')
  app.write_json(folder/'metadata.json', {'id': self.source, 'name': 'Original.wav', 'file': 'source.wav', 'duration': 200})
  self.req = {'title': 'New words', 'style': '', 'lyrics': '[Verse]\nNew words', 'base_enabled': True,
              'base_import_id': self.source, 'base_start': 20, 'base_end': 45}
 def tearDown(self):
  app.DATA, app.OUT, app.VOCI = self.old; self.temp.cleanup()
 def preflight(self):
  return patch.multiple(resinging, preflight=lambda a,r:(app.DATA/'imports'/self.source/'source.wav', {}, r['base_start'], r['base_end']))
 def test_old_projects_and_fields(self):
  self.assertFalse(app.validate({})['base_enabled'])
  for key, value in [('base_enabled', 'yes'), ('base_start', True), ('base_end', float('nan')), ('base_start', -1), ('base_import_id', [])]:
   with self.subTest(key=key), self.assertRaises(ValueError): app.validate(self.req | {key: value})
  req = app.validate(self.req | {'cot': 'off', 'abc': 'X:1\nK:C\nC'})
  self.assertEqual(req['cot'], 'full')
 def test_queue_keeps_project_and_request_snapshot_without_style_or_clone(self):
  project = app.project_save({'request': self.req})
  with self.preflight(), patch.object(app, 'ready', return_value={'ready': True}):
   ident = app.enqueue({'project_id': project['id'], 'request': self.req})['ids'][0]
   with self.assertRaisesRegex(ValueError, 'Genera'): app.enqueue({'project_id': project['id'], 'request': self.req, 'kind': 'plan'})
  self.req['lyrics'] = 'changed'; saved = app.get_job(ident)
  self.assertEqual(saved['request']['lyrics'], '[Verse]\nNew words'); self.assertEqual(saved['project_id'], project['id'])
  self.assertEqual(saved['kind'], 'generate'); self.assertFalse(saved['request']['clone_enabled'])
 def test_preflight_range_and_dependencies(self):
  with patch.object(app,'ready',return_value={'ready': True}), patch.object(resinging.cloning,'preflight'), patch.object(resinging.transcription,'status',return_value={'ready': True}):
   self.assertEqual(resinging.preflight(app,app.validate(self.req))[2:], (20.,45.))
   for changes in ({'base_end': 0}, {'base_start': 50}, {'base_end': 201}, {'base_end': 21}, {'lyrics': ''}):
    with self.subTest(changes=changes), self.assertRaises(ValueError): resinging.preflight(app,app.validate(self.req | changes))
 def test_alignment_accepts_constant_positive_and_negative_delays_and_repeated_notes(self):
  original = [(i*.4,i*.4+.3,60+i%5) for i in range(30)]
  for delay in (.12, -.1):
   generated = [(a+delay+(.005 if i%2 else 0),b+delay,p) for i,(a,b,p) in enumerate(original)]
   report=resinging.alignment(original,generated)
   self.assertEqual(report['matching_notes'],30);self.assertAlmostEqual(report['vocal_delay_seconds'],delay,delta=.005)
  generated=original[:8]+[(3.1,3.15,62)]+original[8:]
  self.assertEqual(resinging.alignment(original,generated)['matching_notes'],30)
 def test_alignment_rejects_wrong_melody_and_tempo_drift(self):
  original = [(i*.4,i*.4+.3,60+i%5) for i in range(30)]
  for generated in ([],[(a,b,p+12) for a,b,p in original],[(a*1.1,b*1.1,p) for a,b,p in original],[(a+3,b+3,p) for a,b,p in original]):
   with self.subTest(generated=len(generated)), self.assertRaises(ValueError): resinging.alignment(original,generated)
 def test_note_validation_rejects_bad_or_unordered_input(self):
  path=app.DATA/'notes.lab'
  for contents in ('0 1 nan','2 1 60','0 1 60.5','1 2 60\n0 1 61'):
   path.write_text(contents)
   with self.assertRaises(ValueError):resinging.read_notes(path)
 def exercise_pipeline(self, clone=False, cancelled=False, drift=False, truncated=False, backend='cpu', automatic=True):
  req=app.validate(self.req | {'clone_enabled': clone, 'clone_voice': 'sample' if clone else '', 'voice_steps': 50, 'mix': {'automatic': automatic}})
  project=app.project_save({'request':req})
  with self.preflight(),patch.object(app,'ready',return_value={'ready':True}),patch.object(resinging.cloning,'preflight'):
   ident=app.enqueue({'project_id':project['id'],'request':req})['ids'][0]
  job=app.get_job(ident);d=app.OUT/ident;d.mkdir();calls=[]
  ref=app.DATA/'reference.wav';ref.write_bytes(b'reference')
  note_text='\n'.join(f'{i*.4} {i*.4+.3} {60+i%5}' for i in range(20))
  def run(j, folder, args, **kwargs):
   app.check_cancel(ident);calls.append(args)
   if '--output' in args:
    output=pathlib.Path(args[args.index('--output')+1]);(output/'melody_vocal.lab').write_text(note_text if not drift or output.name=='source-score' else '\n'.join(f'{i*.5} {i*.5+.3} {60+i%5}' for i in range(20)))
    (output/'score.abc').write_text('X:1\nM:4/4\nL:1/8\nQ:1/4=120\nK:C\nCDEF|')
   elif '--task' in args:
    self.assertEqual(args[args.index('--backend')+1],backend)
    if args[args.index('--task')+1]=='sep':
     output=pathlib.Path(args[args.index('--out-dir')+1])
     for name in ('vocals','drums','bass','other'):(output/(name+'.wav')).write_bytes(name.encode())
    else:
     output=pathlib.Path(args[args.index('--out-dir')+1]);(output/'audio.wav').write_bytes(b'new song')
     app.write_json(output/'generation_flags.json',{'audio_truncated':truncated})
   else:pathlib.Path(args[-1]).write_bytes(b'processed')
   if cancelled:app.cancel(ident)
  def command(job, folder):
   self.assertFalse(job['request']['base_enabled']);self.assertFalse(job['request']['clone_enabled']);self.assertEqual(job['request']['cot'],'full')
   return ['engine','--task','gen','--backend',backend,'--out-dir',str(folder)]
  def convert(a,j,folder,source,reference,out,settings):out.write_bytes(b'converted')
  def mix(j,folder,voice,**kwargs):
   self.assertEqual(kwargs['source'],d/'stems');(folder/'audio.wav').write_bytes(b'final mix');return folder/'audio.wav'
  def info(path):return {'duration':200 if pathlib.Path(path).name in ('original.wav','audio.wav') and pathlib.Path(path).parent==d else 25}
  def loudness(a,path,folder,runner):return {'lufs':-14 if path.name=='reference-singing.wav' else -19,'peak_db':-3}
  with self.preflight(),patch.object(app,'run_job_process',side_effect=run),patch.object(app,'command_for',side_effect=command),patch.object(app,'settings',return_value={'backend':backend,'threads':2}),patch.object(app,'audio_info',side_effect=info),patch.object(app,'voice_sample',return_value=ref),patch.object(resinging.cloning,'convert_voice',side_effect=convert) as vc,patch.object(app,'mix_voice',side_effect=mix),patch.object(resinging.mixing,'measure',side_effect=loudness) as measured:
   if cancelled:
    with self.assertRaises(app.JobCancelled):resinging.process(app,job,d)
   elif drift or truncated:
    with self.assertRaises(ValueError):resinging.process(app,job,d)
    self.assertFalse((d/'audio.wav').exists());vc.assert_not_called()
   else:
    result=resinging.process(app,job,d);self.assertTrue(result['regenerated_vocals']);self.assertEqual(result['cloned'],clone)
    if clone:vc.assert_called_once();self.assertEqual(result['voice_steps'],50)
    else:vc.assert_not_called()
    manifest=json.loads((d/'manifest.json').read_text());self.assertIn('voce.wav',manifest['sha256'])
    placement=next(a for a in calls if str(d/'voce.wav')==a[-1]);filters=placement[placement.index('-filter_complex')+1]
    self.assertIn('start=0.00000000:end=20.00000000',filters);self.assertIn('start=45.00000000:end=200.00000000',filters)
    self.assertNotIn('rubberband',filters);self.assertNotIn('atempo',filters)
    if automatic:self.assertEqual(result['alignment']['excerpt_voice_gain_db'],5);self.assertEqual(measured.call_count,2)
    else:measured.assert_not_called();self.assertNotIn('excerpt_voice_gain_db',result['alignment'])
  self.assertEqual((app.DATA/'imports'/self.source/'source.wav').read_bytes(),b'original untouched')
 def test_cpu_pipeline_preserves_music_and_outside_vocals(self):self.exercise_pipeline()
 def test_cuda_pipeline_optional_clone(self):self.exercise_pipeline(clone=True,backend='cuda')
 def test_manual_mix_does_not_force_new_voice_level(self):self.exercise_pipeline(automatic=False)
 def test_cancel_stops_next_stage(self):self.exercise_pipeline(cancelled=True)
 def test_bad_timing_never_publishes_mix(self):self.exercise_pipeline(drift=True)
 def test_truncation_never_publishes_mix(self):self.exercise_pipeline(truncated=True)


if __name__=='__main__':unittest.main(verbosity=2)
