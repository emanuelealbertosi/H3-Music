import sys, tempfile, unittest, json, pathlib, math, array, base64, os
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import app
class StudioTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=app.ROOT/'tests')
  self.old=(app.DATA,app.OUT,app.MODEL)
  app.DATA=pathlib.Path(self.tmp.name);app.OUT=app.DATA/'outputs';app.init()
 def tearDown(self):
  assert pathlib.Path(self.tmp.name).resolve().is_relative_to((app.ROOT/'tests').resolve())
  app.DATA,app.OUT,app.MODEL=self.old;self.tmp.cleanup()
 def test_snapshot_and_unicode_roundtrip(self):
  r=app.validate({'title':'È già musica ♬','lyrics':'[Verse]\nPerché l’estate è qui','style':'Italian, pop','options':{'num_inference_steps':8}})
  p=app.project_save({'request':r})
  job={'request':r,'kind':'generate'};d=app.OUT/'a';d.mkdir();args=app.command_for(job,d)
  decoded=json.loads((d/'engine-request.json').read_text(encoding='utf-8'))[0]
  self.assertEqual(decoded['text'],r['lyrics']);self.assertEqual(decoded['options']['num_inference_steps'],8)
  self.assertIn('--request-sequence',args);self.assertNotIn(r['lyrics'],args)
  app.project_save({'id':p['id'],'request':r|{'lyrics':'new'}})
  self.assertEqual(json.loads((d/'request.json').read_text(encoding='utf-8'))['lyrics'],r['lyrics'])
 def test_invalid_modes_and_ranges(self):
  for r in [{'cot':'unknown'},{'cot':'off','abc':'X:1'},{'seed':-8},{'options':{'semantic_max_tokens':100}},{'options':{'abc_min_tokens':4000,'abc_max_tokens':300}},{'options':{'cfg_scale':float('nan')}},{'options':{'shell':'x'}}]:
   with self.subTest(r=r),self.assertRaises((ValueError,TypeError)):app.validate(r)
 def test_blank_optional_values(self):
  r=app.validate({'seed':-1});self.assertGreaterEqual(r['seed'],0);self.assertEqual(r['options'],{})
 def test_restart_marks_interruption_not_success(self):
  for status in ('running','cancelling','queued','completed'):
   app.db('INSERT INTO jobs(id,status) VALUES(?,?)',(status,status))
  app.init()
  self.assertEqual(app.db('SELECT status FROM jobs WHERE id=?',('running',),True)['status'],'interrupted')
  self.assertEqual(app.db('SELECT status FROM jobs WHERE id=?',('queued',),True)['status'],'queued')
 def test_cancel_queued_job(self):
  app.db('INSERT INTO jobs(id,status,request) VALUES(?,?,?)',('a','queued','{}'));app.cancel('a')
  self.assertEqual(app.get_job('a')['status'],'cancelled')
 def test_decode_original_token_bytes(self):
  app.MODEL=app.DATA/'model';(app.MODEL/'sidecars').mkdir(parents=True)
  (app.MODEL/'sidecars/yue2-qwen.tiktoken').write_text(base64.b64encode('X:1\nT:È luce\n'.encode()).decode()+' 10\n')
  d=app.OUT/'sample';d.mkdir();a=array.array('i',[10,151848]);(d/'abc_tokens.i32').write_bytes(a.tobytes())
  self.assertEqual(app.decode_score(d),'X:1\nT:È luce\n')
 def test_abc_newlines_survive_generation_and_reopen(self):
  expected='X:1\nT:È luce\n\nK:C\nCDEF |\n'
  app.MODEL=app.DATA/'model';(app.MODEL/'sidecars').mkdir(parents=True)
  d=app.OUT/'score-roundtrip';d.mkdir()
  app.db('INSERT INTO jobs(id,kind,status,request,result) VALUES(?,?,?,?,?)',('score-roundtrip','plan','completed','{}','{}'))
  for ending in ('\n','\r\n','\r'):
   with self.subTest(ending=repr(ending)):
    raw=expected.replace('\n',ending).encode('utf-8')
    (app.MODEL/'sidecars/yue2-qwen.tiktoken').write_text(base64.b64encode(raw).decode()+' 10\n')
    tokens=array.array('i',[10])
    if sys.byteorder!='little': tokens.byteswap()
    (d/'abc_tokens.i32').write_bytes(tokens.tobytes())
    self.assertEqual(app.decode_score(d),expected)
    self.assertEqual((d/'score.abc').read_bytes(),expected.encode('utf-8'))
    reopened=app.get_job('score-roundtrip',detail=True)['abc']
    self.assertEqual(reopened,expected)
    for _ in range(3):
     request=app.project_save({'request':{'abc':reopened,'cot':'full'}})['request']
     app.command_for({'kind':'plan','request':request},d)
     self.assertEqual((d/'input.abc').read_bytes(),expected.strip().encode('utf-8'))
     reopened=request['abc']
 def test_legacy_abc_repairs_only_doubled_windows_endings(self):
  expected='X:1\n\nK:C\nCDEF |\n'
  d=app.OUT/'legacy';d.mkdir();p=d/'score.abc'
  for ending in ('\n','\r\n','\r\r\n'):
   raw=expected.replace('\n',ending).encode('utf-8');p.write_bytes(raw)
   self.assertEqual(app.read_abc(p),expected)
   self.assertEqual(p.read_bytes(),raw)
 def test_abc_fallback_write_preserves_blank_lines(self):
  d=app.OUT/'fallback';d.mkdir()
  expected='X:1\n\nK:C\nCDEF |'
  app.finish_artifacts({'kind':'plan','request':{'abc':expected.replace('\n','\r\n')}},d)
  self.assertEqual((d/'score.abc').read_bytes(),expected.encode('utf-8'))
 def test_llm_is_local_only(self):
  for url in ['https://example.com','http://127.0.0.1.evil.org','file:///etc/passwd','http://user:pass@localhost:1234']:
   with self.assertRaises(ValueError):app.local_llm_url(url)
  self.assertEqual(app.local_llm_url('http://127.0.0.1:1234/v1/'),'http://127.0.0.1:1234/v1')
if __name__=='__main__':unittest.main(verbosity=2)
