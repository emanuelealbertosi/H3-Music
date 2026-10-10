"""Optional duration is a native generation budget, never prompt text or a crop."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app


class MusicDurationTests(unittest.TestCase):
 def setUp(self):
  self.temp = tempfile.TemporaryDirectory(dir=app.ROOT/'tests', prefix='tmp-duration-')
  self.folder = Path(self.temp.name)
  self.old = app.DATA, app.OUT
  app.DATA = self.folder/'data'; app.OUT = app.DATA/'outputs'; app.init()
  self.request = {'title':'Durata', 'style':'Italian pop, piano',
                  'lyrics':'[Verse]\nLe parole del brano', 'cot':'off', 'seed':42}
 def tearDown(self):
  app.DATA, app.OUT = self.old; self.temp.cleanup()
 def engine_options(self, req, backend='cpu', kind='generate'):
  with patch.object(app,'settings',return_value=app.DEFAULTS|{'backend':backend}), patch.object(app,'memory_profile',return_value={}):
   cmd=app.command_for({'kind':kind, 'request':req}, self.folder)
  return cmd, json.loads((self.folder/'engine-request.json').read_text(encoding='utf-8'))[0]
 def test_optional_legacy_request_unchanged(self):
  for opts in ({}, {'semantic_max_tokens':4000,'num_inference_steps':48}):
   req=app.validate(self.request|{'options':opts}); _, native=self.engine_options(req)
   self.assertEqual(app.music_options(opts),opts)
   self.assertEqual(req['options'],opts)
   self.assertNotIn('max_duration',native['options'])
   self.assertNotIn('semantic_min_tokens',native['options'])
   self.assertEqual(native['options'].get('semantic_max_tokens'),opts.get('semantic_max_tokens'))
 def test_seconds_converted_to_frames_on_both_backends_without_changing_prompts(self):
  for backend in ('cpu','cuda'):
   for seconds, tokens in ((.04,1),(4,100),(60,1500),(240,6000),(360,9000),(900,22500)):
    with self.subTest(backend=backend,seconds=seconds):
     req=app.validate(self.request|{'options':{'max_duration':seconds}}); before=copy.deepcopy(req)
     cmd,native=self.engine_options(req,backend)
     self.assertEqual(cmd[cmd.index('--backend')+1],backend)
     self.assertEqual(native['options']['max_duration'],seconds)
     self.assertEqual(native['options']['semantic_max_tokens'],tokens)
     self.assertEqual(native['options']['semantic_min_tokens'],min(200,tokens))
     self.assertEqual(native['options']['style'],self.request['style'])
     self.assertEqual(native['text'],self.request['lyrics'])
     self.assertEqual(req,before)
     self.assertEqual(json.loads((self.folder/'request.json').read_text(encoding='utf-8')),before)
 def test_explicit_token_cap_remains_stricter(self):
  opts={'max_duration':240,'semantic_max_tokens':1000,'semantic_min_tokens':500}
  native=app.music_options(app.validate(self.request|{'options':opts})['options'])
  self.assertEqual(native['semantic_max_tokens'],1000)
  self.assertEqual(native['semantic_min_tokens'],500)
 def test_impossible_minimum_rejected_before_enqueue(self):
  with self.assertRaisesRegex(ValueError,'durata massima'):
   app.validate(self.request|{'options':{'max_duration':4,'semantic_min_tokens':200}})
 def test_invalid_duration_rejected(self):
  for value in (0,-1,.01,900.04,float('nan'),float('inf'),'invalid',None):
   with self.subTest(value=value),self.assertRaises((ValueError,TypeError)):
    app.validate(self.request|{'options':{'max_duration':value}})
 def test_saved_project_and_queue_keep_optional_value(self):
  req=self.request|{'options':{'max_duration':180,'num_inference_steps':48}}
  saved=app.project_save({'request':req})
  with patch.object(app,'ready',return_value={'ready':True}):
   ident=app.enqueue({'project_id':saved['id'],'request':saved['request']})['ids'][0]
  self.assertEqual(app.get_job(ident)['request']['options'],req['options'])
  row=app.db('SELECT request FROM projects WHERE id=?',(saved['id'],),True)
  self.assertEqual(json.loads(row['request'])['options'],req['options'])
 def test_external_score_and_plan_stay_unchanged(self):
  req=app.validate(self.request|{'cot':'full','abc':'X:1\nK:C\nCDEF|',
                 'options':{'max_duration':60,'abc_max_tokens':5000}})
  _,native=self.engine_options(req,kind='plan')
  self.assertEqual(native['options']['abc_max_tokens'],5000)
  self.assertEqual(native['options']['h3_plan_only'],'true')
  self.assertEqual((self.folder/'input.abc').read_text(),req['abc'])
 def test_original_base_and_clone_fields_preserved(self):
  req=app.validate(self.request|{'base_enabled':True,'base_import_id':'a'*32,
       'base_start':0,'base_end':217.3,'clone_enabled':True,'clone_voice':'mia',
       'options':{'max_duration':240}})
  _,native=self.engine_options(req)
  self.assertEqual(native['options']['semantic_max_tokens'],6000)
  self.assertEqual(req['base_end'],217.3)
  self.assertTrue(req['clone_enabled'])


if __name__=='__main__': unittest.main()
