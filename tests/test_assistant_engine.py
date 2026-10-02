import json
from pathlib import Path
import sys
import threading
import unittest
import tempfile
import base64
import subprocess
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app,assistant_engine

class AssistantTests(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory(dir=app.ROOT/'tests')
 def tearDown(self):assistant_engine._busy=False;self.temp.cleanup()
 def test_cpu_command_never_offloads_or_enables_mtp(self):
  args=assistant_engine.command(Path('llama-server'),Path('voice.gguf'),'cpu',8192,1234,'private',6,{'optimized_mtp':True})
  self.assertEqual(args[args.index('-ngl')+1],'0');self.assertNotIn('--spec-type',args)
  self.assertEqual(args[args.index('--host')+1],'127.0.0.1')
 def test_gpu_retains_verified_optimized_profile(self):
  args=assistant_engine.command(Path('llama-server'),Path('voice.gguf'),'cuda',16384,1234,'private',6,{'optimized_mtp':True,'optimized_model':'voice.gguf'})
  self.assertIn('--backend-sampling',args);self.assertIn('draft-mtp',args)
  self.assertEqual(args[args.index('--spec-draft-n-max')+1],'2');self.assertIn('q4_0',args)
 def test_switching_model_does_not_apply_other_models_mtp_profile(self):
  args=assistant_engine.command(Path('llama-server'),Path('other.gguf'),'cuda',16384,1234,'private',6,{'optimized_mtp':True,'optimized_model':'voice.gguf'})
  self.assertNotIn('--spec-type',args)
 def test_model_picker_cancellation_and_file_validation(self):
  fake=Mock();fake.platform_runtime.windows.return_value=True
  fake.run_capture.return_value=Mock(returncode=0,stdout='',stderr='')
  self.assertEqual(assistant_engine.choose_model(fake),{'path':''})
  with tempfile.TemporaryDirectory(dir=app.ROOT/'tests') as folder:
   model=Path(folder)/'Modello è.gguf';model.write_bytes(b'GGUF')
   fake.run_capture.return_value.stdout=str(model)
   self.assertEqual(assistant_engine.choose_model(fake),{'path':str(model.resolve())})
   fake.run_capture.return_value.stdout=str(model.with_suffix('.txt'))
   with self.assertRaisesRegex(ValueError,'gguf'):assistant_engine.choose_model(fake)
 @unittest.skipUnless(app.platform_runtime.windows(),'Windows PowerShell parser required')
 def test_windows_picker_script_parses_with_real_powershell(self):
  fake=Mock();fake.platform_runtime.windows.return_value=True
  fake.run_capture.return_value=Mock(returncode=0,stdout='',stderr='')
  assistant_engine.choose_model(fake)
  script=fake.run_capture.call_args.args[0][-1]
  encoded=base64.b64encode(script.encode('utf-16le')).decode()
  probe="$source=[Text.Encoding]::Unicode.GetString([Convert]::FromBase64String('"+encoded+"')); $tokens=$null; $parseErrors=$null; [void][System.Management.Automation.Language.Parser]::ParseInput($source,[ref]$tokens,[ref]$parseErrors); $parseErrors | ForEach-Object {$_.Message}; if($parseErrors.Count){exit 1}"
  response=subprocess.run(['powershell','-NoProfile','-Command',probe],capture_output=True,text=True,timeout=15,creationflags=app.HIDDEN)
  self.assertEqual(response.returncode,0,response.stdout+response.stderr)
 def test_macos_model_picker_cancellation_is_not_an_error(self):
  fake=Mock();fake.platform_runtime.windows.return_value=False;fake.platform_runtime.macos.return_value=True
  fake.run_capture.return_value=Mock(returncode=1,stdout='',stderr='User canceled. (-128)')
  self.assertEqual(assistant_engine.choose_model(fake),{'path':''})
 def fake(self):
  return Mock(ROOT=Path(self.temp.name),settings=lambda:{'llm_provider':'internal'},LOCK=threading.RLock(),db=Mock(return_value=None),WAKE=threading.Event())
 def test_runtime_install_and_assistant_load_are_mutually_exclusive(self):
  fake=self.fake()
  with assistant_engine.model_store.exclusive(fake.ROOT,'assistant-runtime.lock'),patch.object(assistant_engine,'start') as start:
   with self.assertRaisesRegex(ValueError,'in uso'),assistant_engine.session(fake):pass
   start.assert_not_called();self.assertFalse(assistant_engine.busy())
 def test_session_unloads_after_success_and_error(self):
  fake=self.fake()
  for fail in (False,True):
   with patch.object(assistant_engine,'start'),patch.object(assistant_engine,'stop') as stop:
    try:
     with assistant_engine.session(fake):
      self.assertTrue(assistant_engine.busy())
      if fail:raise ValueError('model response failed')
    except ValueError:pass
    stop.assert_called_once();self.assertFalse(assistant_engine.busy());self.assertTrue(fake.WAKE.is_set())
 def test_model_load_failure_releases_queue(self):
  fake=self.fake()
  with patch.object(assistant_engine,'start',side_effect=ValueError('missing model')),patch.object(assistant_engine,'stop') as stop:
   with self.assertRaises(ValueError),assistant_engine.session(fake):pass
   stop.assert_called_once();self.assertFalse(assistant_engine.busy());self.assertTrue(fake.WAKE.is_set())
 def test_active_audio_cannot_start_assistant(self):
  fake=self.fake();fake.db.return_value={'id':'active'}
  with patch.object(assistant_engine,'start') as start:
   with self.assertRaisesRegex(ValueError,'Attendi'),assistant_engine.session(fake):pass
   start.assert_not_called();self.assertFalse(assistant_engine.busy())
 def test_external_assistant_is_unchanged(self):
  fake=self.fake();fake.settings=lambda:{'llm_provider':'lmstudio'}
  with patch.object(assistant_engine,'start') as start:
   with assistant_engine.session(fake):self.assertFalse(assistant_engine.busy())
   start.assert_not_called()
 def test_general_assistant_rejects_removed_original_tags(self):
  req={'lyrics':'[Intro]\n[Verse 1]\nVedo il cielo\n[Pre-Chorus]\nCanto ancora\n[Chorus]\nVedo il cielo'}
  response={'choices':[{'message':{'content':json.dumps({'lyrics':'[Verse]\nCanto ancora'})}}]}
  with patch.object(app,'settings',return_value=app.DEFAULTS|{'llm_model':'test'}),patch.object(app,'llm',return_value=response):
   with self.assertRaisesRegex(ValueError,'TAG originali'):app.assist({'request':req,'instruction':'Migliora il testo'})

if __name__=='__main__':unittest.main()
