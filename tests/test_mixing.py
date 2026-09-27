import array, hashlib, json, math, pathlib, shutil, sys, tempfile, unittest, wave
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import app, mixing

class MixingTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='tmp-mixing-',dir=app.ROOT/'tests');self.d=pathlib.Path(self.tmp.name)
  self.old=app.DATA,app.OUT;app.DATA=self.d;app.OUT=self.d/'outputs';app.init()
 def tearDown(self):
  app.DATA,app.OUT=self.old;self.tmp.cleanup()
 def tone(self,path,amplitude,frequency=440):
  path.parent.mkdir(parents=True,exist_ok=True)
  with wave.open(str(path),'wb') as w:
   w.setparams((1,2,48000,0,'NONE','not compressed'))
   w.writeframes(array.array('h',(int(amplitude*32767*math.sin(2*math.pi*frequency*i/48000)) for i in range(48000*4))).tobytes())
 def runner(self,d):
  def run(args):
   r=app.run_capture(args,60)
   with (d/'engine.log').open('a',encoding='utf-8') as log:log.write(r.stdout or '');log.write(r.stderr or '')
   self.assertEqual(r.returncode,0,r.stderr)
  return run
 def fixture(self):
  stems=self.d/'stems';self.tone(stems/'vocals.wav',.08);self.tone(self.d/'voce.wav',.32)
  for name,hz in [('drums',160),('bass',220),('other',880)]:self.tone(stems/(name+'.wav'),.05,hz)
  return stems
 def test_reject_invalid_settings_and_keep_old_projects(self):
  self.assertEqual(app.validate({})['mix'],mixing.DEFAULTS)
  for v in [[],{'unknown':1},{'automatic':'yes'},{'compression':1},{'voice_db':float('nan')},{'voice_db':13},{'ambience':-1}]:
   with self.assertRaises(ValueError):mixing.validate(v)
 def test_silence_and_gain_limits(self):
  for level in (None,-70):self.assertEqual(mixing.matching_gain({'lufs':level},{'lufs':-20}),0)
  self.assertEqual(mixing.matching_gain({'lufs':-10},{'lufs':-50}),12)
  self.assertEqual(mixing.matching_gain({'lufs':-50},{'lufs':-10}),-18)
 @unittest.skipUnless(app.FFMPEG.exists(),'Bundled FFmpeg required')
 def test_loud_voice_matches_reference_and_slider_changes_only_voice(self):
  stems=self.fixture();run=self.runner(self.d)
  job={'request':{'mix':{'compression':False}}}
  out=mixing.render(app,job,self.d,self.d/'voce.wav',stems,run)
  report=json.loads((self.d/'mix-report.json').read_text(encoding='utf-8'))
  self.assertAlmostEqual(report['automatic_voice_gain_db'],-12.04,delta=.2)
  self.assertAlmostEqual(app.audio_info(out)['duration'],4,delta=.001)
  self.assertLessEqual(mixing.measure(app,out,self.d,run)['peak_db'],-1.8)
  digest=hashlib.sha256((self.d/'mix-before.wav').read_bytes()).hexdigest()
  job['request']['mix']['voice_db']=-6
  mixing.render(app,job,self.d,self.d/'voce.wav',stems,run)
  newer=json.loads((self.d/'mix-report.json').read_text(encoding='utf-8'))
  self.assertAlmostEqual(newer['voice_gain_db'],report['voice_gain_db']-6)
  self.assertEqual(digest,hashlib.sha256((self.d/'mix-before.wav').read_bytes()).hexdigest())
 @unittest.skipUnless(app.FFMPEG.exists(),'Bundled FFmpeg required')
 def test_compression_room_and_clipping_protection(self):
  stems=self.fixture();self.tone(self.d/'voce.wav',.95)
  for name in ('vocals','drums','bass','other'):self.tone(stems/(name+'.wav'),.95)
  out=mixing.render(app,{'request':{'mix':{'ambience':100,'voice_db':12}}},self.d,self.d/'voce.wav',stems,self.runner(self.d))
  stats=mixing.measure(app,out,self.d,self.runner(self.d))
  self.assertLessEqual(stats['peak_db'],-1.8)
  self.assertAlmostEqual(app.audio_info(out)['duration'],4,delta=.001)
 @unittest.skipUnless(app.FFMPEG.exists(),'Bundled FFmpeg required')
 def test_silent_mix_is_finite(self):
  stems=self.d/'stems';self.tone(stems/'vocals.wav',0);self.tone(self.d/'voce.wav',0)
  out=mixing.render(app,{'request':{}},self.d,self.d/'voce.wav',stems,self.runner(self.d))
  report=json.loads((self.d/'mix-report.json').read_text(encoding='utf-8'))
  self.assertEqual(report['automatic_voice_gain_db'],0);self.assertIsNone(mixing.measure(app,out,self.d,self.runner(self.d))['lufs'])
 def test_remix_is_independent_and_cancellable(self):
  ident=app.uid();folder=app.OUT/ident;folder.mkdir()
  for name in ('vocals','drums','bass','other'):
   p=folder/'stems'/(name+'.wav');p.parent.mkdir(exist_ok=True);p.write_bytes(name.encode())
  for name in ('voce.wav','audio.wav','original.wav'):(folder/name).write_bytes(name.encode())
  app.db('INSERT INTO jobs(id,kind,status,request,created) VALUES(?,?,?,?,?)',(ident,'clone','completed',app.jdump({'title':'Song'}),app.now()))
  with patch.object(app,'ready',side_effect=AssertionError('No model needed')):
   new=app.enqueue({'kind':'remix','request':{'source_id':ident,'mix':{'voice_db':-3}}})['ids'][0]
  job=app.get_job(new);dest=app.OUT/new;dest.mkdir()
  def render(*args):
   (dest/'audio.wav').write_bytes(b'new mix');return dest/'audio.wav'
  with patch.object(mixing,'render',side_effect=render),patch.object(app,'audio_info',return_value={'duration':4}):
   result=mixing.process(app,job,dest)
  self.assertTrue(result['remixed']);self.assertEqual((dest/'mix-before.wav').read_bytes(),b'audio.wav');self.assertEqual((folder/'audio.wav').read_bytes(),b'audio.wav')
  self.assertEqual(mixing.source_files(app,ident)[0]['id'],ident)
  app.cancel(new)
  with self.assertRaises(app.JobCancelled):mixing.process(app,job,dest)
  for source in ('../x',None):
   with self.assertRaises(ValueError):mixing.source_files(app,source)

if __name__=='__main__':unittest.main()
