import importlib.util,json,pathlib,sqlite3,sys,tempfile,unittest,zipfile
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
import install_cpu_engine
from unittest.mock import patch
from contextlib import closing
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import execution,app
spec=importlib.util.spec_from_file_location('activate',ROOT/'scripts/activate_engine.py');activate=importlib.util.module_from_spec(spec);spec.loader.exec_module(activate)

class ExecutionTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='tmp-execution-',dir=ROOT/'tests');self.r=pathlib.Path(self.tmp.name)
  (self.r/'runtime/engine').mkdir(parents=True);(self.r/'runtime/engine/audiocpp_cli.exe').write_bytes(b'OLD')
  (self.r/'candidate').mkdir();(self.r/'candidate/audiocpp_cli.exe').write_bytes(b'NEW')
  (self.r/'data').mkdir()
  self.db=self.r/'data/music.sqlite'
  with closing(sqlite3.connect(self.db)) as c,c:
   c.executescript('CREATE TABLE jobs(status TEXT);CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT);')
   c.execute('INSERT INTO settings VALUES (?,?)',('main',json.dumps({'backend':'cpu','threads':3,'paused':True,'model':'q4'})))
 def tearDown(self):self.tmp.cleanup()
 def settings(self):
  with closing(sqlite3.connect(self.db)) as c,c:return json.loads(c.execute('SELECT value FROM settings').fetchone()[0])
 def test_default_cpu_and_saved_cuda_preserved(self):
  previous=app.DATA,app.OUT;app.DATA=self.r/'fresh';app.OUT=app.DATA/'outputs'
  try:
   app.init();self.assertEqual(app.settings()['backend'],'cpu')
   app.save_settings(app.settings()|{'backend':'cuda','threads':3});app.init()
   self.assertEqual(app.settings()['backend'],'cuda');self.assertEqual(app.settings()['threads'],3)
  finally:app.DATA,app.OUT=previous
 def test_runtime_selection_preserves_cpu(self):
  cpu=self.r/'runtime/transcription/python.exe';cuda=self.r/'runtime/transcription-cuda/python.exe'
  cpu.parent.mkdir();cpu.touch()
  self.assertEqual(execution.transcription_python(self.r,'cuda'),cpu)
  cuda.parent.mkdir();cuda.touch()
  self.assertEqual(execution.transcription_python(self.r,'cuda'),cuda)
  self.assertEqual(execution.transcription_python(self.r,'cpu'),cpu)
 def test_rejects_old_engine_missing_voice_families(self):
  with patch.object(execution,'capture',return_value=json.dumps({'loaders':{'yue2':{}}})):
   with self.assertRaisesRegex(ValueError,'htdemucs'):execution.check_engine(self.r/'candidate/audiocpp_cli.exe')
 def test_cuda_not_inferred_from_any_cuda_log_message(self):
  outputs=[json.dumps({'loaders':dict.fromkeys(execution.REQUIRED_FAMILIES,{})}),'CUDA initialization failed\nCPU:0 "CPU"']
  with patch.object(execution,'capture',side_effect=outputs):
   with self.assertRaisesRegex(ValueError,'non rileva'):execution.check_engine(self.r/'candidate/audiocpp_cli.exe')
 def test_activation_preserves_previous_and_preferences(self):
  with patch.object(execution,'check_cuda',return_value={'checked':True}):result=activate.activate(self.r,self.r/'candidate')
  self.assertEqual((self.r/'runtime/engine/audiocpp_cli.exe').read_bytes(),b'NEW')
  self.assertEqual((pathlib.Path(result['backup'])/'audiocpp_cli.exe').read_bytes(),b'OLD')
  self.assertEqual(self.settings(),{'backend':'cuda','threads':3,'paused':True,'model':'q4'})
 def test_failed_preflight_leaves_engine_and_settings(self):
  with patch.object(execution,'check_cuda',side_effect=ValueError('Torch CUDA assente')):
   with self.assertRaises(ValueError):activate.activate(self.r,self.r/'candidate')
  self.assertEqual((self.r/'runtime/engine/audiocpp_cli.exe').read_bytes(),b'OLD');self.assertEqual(self.settings()['backend'],'cpu')
 def test_busy_queue_prevents_swap(self):
  with closing(sqlite3.connect(self.db)) as c,c:c.execute("INSERT INTO jobs VALUES ('running')")
  with patch.object(execution,'check_cuda',return_value={}):
   with self.assertRaisesRegex(ValueError,'coda'):activate.activate(self.r,self.r/'candidate')
  self.assertEqual((self.r/'runtime/engine/audiocpp_cli.exe').read_bytes(),b'OLD')
 def test_install_preserves_complete_cuda(self):
  (self.r/'runtime/engine/cudart64_12.dll').touch()
  with patch.object(install_cpu_engine,'root',self.r),patch.object(execution,'check_engine',return_value={}),patch.object(install_cpu_engine,'activate') as activate_mock:
   install_cpu_engine.main()
  activate_mock.assert_not_called()
  self.assertEqual((self.r/'runtime/engine/audiocpp_cli.exe').read_bytes(),b'OLD')
 def test_install_replaces_incomplete_cuda_with_complete_cpu(self):
  (self.r/'runtime/engine/cudart64_12.dll').touch();(self.r/'dist').mkdir()
  with zipfile.ZipFile(self.r/'dist/h3-engine-cpu-win64.zip','w') as z:z.writestr('audiocpp_cli.exe',b'NEW')
  with closing(sqlite3.connect(self.db)) as c,c:c.execute("UPDATE settings SET value=?",(json.dumps({'backend':'cuda','threads':3}),))
  with patch.object(install_cpu_engine,'root',self.r),patch.object(execution,'check_engine',side_effect=[ValueError('missing htdemucs'),{}]),patch.object(install_cpu_engine.subprocess,'run'):
   install_cpu_engine.main()
  self.assertEqual((self.r/'runtime/engine/audiocpp_cli.exe').read_bytes(),b'NEW')
  self.assertEqual(self.settings(),{'backend':'cpu','threads':3})
  self.assertEqual(len(list((self.r/'runtime').glob('engine-backup-*'))),1)
 def test_failed_swap_restores_previous(self):
  rename=pathlib.Path.rename
  def fault(path,target):
   if path.name.startswith('engine-ready-'):raise OSError('simulated locked directory')
   return rename(path,target)
  with patch.object(execution,'check_cuda',return_value={}),patch.object(pathlib.Path,'rename',fault):
   with self.assertRaises(OSError):activate.activate(self.r,self.r/'candidate')
  self.assertEqual((self.r/'runtime/engine/audiocpp_cli.exe').read_bytes(),b'OLD');self.assertEqual(self.settings()['backend'],'cpu')

if __name__=='__main__':unittest.main(verbosity=2)
