import pathlib,sys,tempfile,unittest,json
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import app
class ModelSelectionTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=ROOT/'tests');self.root=pathlib.Path(self.temp.name)
  self.models=self.root/'models/yue2';self.models.mkdir(parents=True)
  self.catalog={k:(v[0],n+1,v[2]) for n,(k,v) in enumerate(app.MUSIC_MODELS.items())}
  self.stack=[]
  for name,value in [('ROOT',self.root),('MODEL',self.models),('MUSIC_MODELS',self.catalog)]:
   p=patch.object(app,name,value);p.start();self.stack.append(p)
 def tearDown(self):
  for p in reversed(self.stack):p.stop()
  self.temp.cleanup()
 def install(self,key):
  name,size,_=self.catalog[key];(self.models/name).write_bytes(b'x'*size);return name
 def test_explicit_bf16_never_falls_back_to_q8(self):
  self.install('q8')
  with patch.object(app,'settings',return_value={'model':'bf16','backend':'cpu'}):
   self.assertEqual(app.main_model_file(),self.catalog['bf16'][0])
   state=app.ready();self.assertFalse(state['ready']);self.assertIn(self.catalog['bf16'][0],state['missing'])
 def test_bf16_only_install_detected_from_cpu_default(self):
  expected=self.install('bf16')
  with patch.object(app,'settings',return_value={'model':'q8','backend':'cpu'}):self.assertEqual(app.main_model_file(),expected)
 def test_partial_download_not_selected(self):
  (self.models/self.catalog['bf16'][0]).write_bytes(b'x')
  expected=self.install('q4')
  with patch.object(app,'settings',return_value={'model':'q8'}):self.assertEqual(app.main_model_file(),expected)
 def test_ready_uses_selected_model_and_preserves_missing_shared_files(self):
  name=self.install('bf16');self.install('q8')
  record={'files':{name:{'size':self.catalog['bf16'][1]},self.catalog['q8'][0]:{'size':2},'sidecars/test.json':{'size':1}}}
  (self.root/'models/installed-models.json').write_text(json.dumps(record))
  with patch.object(app,'settings',return_value={'model':'bf16','backend':'cpu'}):
   state=app.ready();self.assertEqual(state['model_variant'],'bf16');self.assertTrue(state['available_models']['bf16']);self.assertEqual(state['missing'],['sidecars/test.json'])
 def test_stale_manifest_cannot_select_absent_q8(self):
  (self.root/'models/installed-models.json').write_text(json.dumps({'files':{self.catalog['q8'][0]:{'size':2}}}))
  expected=self.install('q4')
  with patch.object(app,'settings',return_value={'model':'q8'}):self.assertEqual(app.main_model_file(),expected)
if __name__=='__main__':unittest.main()
