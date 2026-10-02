import json
from pathlib import Path
import sys
import threading
import unittest
import tempfile
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
 def test_in_app_picker_lists_only_folders_and_gguf_including_unicode(self):
  folder=Path(self.temp.name);(folder/'Sotto cartella').mkdir()
  model=folder/"Modello d'Italia è.GGUF";model.write_bytes(b'GGUF')
  (folder/'ignored.txt').write_text('not a model')
  fake=self.fake();fake.MODEL=folder/'yue2'
  result=assistant_engine.model_files(fake,{'path':str(folder)})
  self.assertEqual([e['name'] for e in result['entries']],['Sotto cartella',model.name])
  self.assertEqual(result['entries'][1]['bytes'],4)
  self.assertEqual(result['entries'][1]['path'],str(model))
  self.assertEqual(result['parent'],str(folder.parent));fake.run_capture.assert_not_called()
 def test_in_app_picker_starts_in_configured_model_folder(self):
  fake=self.fake();fake.MODEL=Path(self.temp.name)/'yue2'
  model=Path(self.temp.name)/'Qwen.gguf';model.write_bytes(b'GGUF')
  fake.settings=lambda:{'llm_internal_model':str(model)}
  self.assertEqual(assistant_engine.model_files(fake,{'initial':True})['path'],str(model.parent))
 def test_in_app_picker_rejects_missing_relative_and_non_directory_paths(self):
  fake=self.fake();fake.MODEL=Path(self.temp.name)/'yue2'
  file=Path(self.temp.name)/'Qwen.gguf';file.write_bytes(b'GGUF')
  for path in ('relative-folder',str(file.parent/'missing'),str(file)):
   with self.subTest(path=path),self.assertRaises(ValueError):assistant_engine.model_files(fake,{'path':path})
 def test_in_app_picker_reports_unreadable_folder(self):
  fake=self.fake();fake.MODEL=Path(self.temp.name)/'yue2'
  with patch.object(assistant_engine.os,'scandir',side_effect=PermissionError),self.assertRaisesRegex(ValueError,'leggere'):
   assistant_engine.model_files(fake,{'path':self.temp.name})
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
