import json, math, sys, unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import app, lyric_meter

class MeterTests(unittest.TestCase):
 def setUp(self):
  self.reasoning=patch.object(lyric_meter,'reasoning_off_available',return_value=False);self.reasoning.start();self.addCleanup(self.reasoning.stop)
 def phrases(self):return [{'notes':[{'start':0,'duration':.25,'strong':True},{'start':.25,'duration':.25,'strong':False}]}]
 def response(self,text='Canto',ident=1):return {'choices':[{'message':{'content':json.dumps({'lines':[{'id':ident,'section':'Verse','text':text}]})}}]}
 def test_bounds_order_and_nonfinite(self):
  for value in (None,[],[{'notes':[]}],[{'notes':[{'start':math.nan,'duration':1}]}],[{'notes':[{'start':2,'duration':1},{'start':1,'duration':1}]}]):
   with self.assertRaises((ValueError,TypeError)):lyric_meter.validate_phrases(value)
  self.assertEqual(lyric_meter.validate_phrases(self.phrases())[0]['max_syllables'],2)
 def test_automatic_selection_only_uses_a_loaded_instance(self):
  models={'models':[{'type':'llm','key':'unloaded','loaded_instances':[]},{'type':'llm','key':'chosen-on-cpu','loaded_instances':[{'id':'cpu-instance'}]}]}
  with patch.object(app,'llm',return_value=models):self.assertEqual(lyric_meter.loaded_model(app),'cpu-instance')
  models['models'][1]['loaded_instances']=[]
  with patch.object(app,'llm',return_value=models):self.assertIsNone(lyric_meter.loaded_model(app))
 def test_native_reasoning_toggle_only_reads_final_messages(self):
  result={'output':[{'type':'reasoning','content':'private internal analysis'},{'type':'message','content':'final JSON'}]}
  with patch.object(app,'llm',return_value=result) as call:
   self.assertEqual(lyric_meter.complete(app,'cpu',[{'role':'system','content':'rules'},{'role':'user','content':'theme'}],360,{},True),'final JSON')
   payload=call.call_args.args[1];self.assertEqual(payload['reasoning'],'off');self.assertFalse(payload['store']);self.assertNotIn('integrations',payload)
 def test_syllables_range_and_common_words(self):
  self.assertEqual(lyric_meter.syllables('sedia'),(2,2));self.assertEqual(lyric_meter.syllables('canto'),(2,2))
  self.assertEqual(lyric_meter.syllables('cuore aperto'),(4,5))
  self.assertEqual(lyric_meter.syllables("Vedo l'alba sorgere"),(7,7))
  self.assertEqual(lyric_meter.syllables('d’amore'),(3,3))
 def test_preserve_all_fields_except_lyrics(self):
  req=app.validate({'title':'Originale','lyrics':'Source','style':'rock','abc':'K:C\nC D |','seed':12,'lora':'notte','options':{'num_inference_steps':48},'base_enabled':True,'base_import_id':'a'*32})
  with patch.object(app,'settings',return_value=app.DEFAULTS|{'llm_model':'test'}),patch.object(app,'llm',return_value=self.response()):
   result=lyric_meter.adapt(app,{'request':req,'mode':'translate','phrases':self.phrases()})
  self.assertEqual(result['request']|{'lyrics':req['lyrics']},req)
  self.assertEqual(result['request']['lyrics'],'[Verse]\nCanto');self.assertTrue(result['lines'][0]['fits'])
 def test_repair_once_then_report_remaining_mismatch(self):
  with patch.object(app,'settings',return_value=app.DEFAULTS|{'llm_model':'test'}),patch.object(app,'llm',side_effect=[self.response('La meravigliosa avventura'),self.response('Canto')]) as call:
   result=lyric_meter.adapt(app,{'request':{'lyrics':'source'},'phrases':self.phrases()})
   self.assertEqual(call.call_count,2);self.assertTrue(result['lines'][0]['fits'])
  with patch.object(app,'settings',return_value=app.DEFAULTS|{'llm_model':'test'}),patch.object(app,'llm',return_value=self.response('La meravigliosa avventura')) as call:
   result=lyric_meter.adapt(app,{'request':{'lyrics':'source'},'phrases':self.phrases()})
   self.assertEqual(call.call_count,2);self.assertFalse(result['lines'][0]['fits']);self.assertEqual(len(result['warnings']),2)
 def test_malformed_output_or_missing_model_never_applies(self):
  with patch.object(app,'settings',return_value=app.DEFAULTS),patch.object(app,'llm',return_value={'data':[]}),self.assertRaisesRegex(ValueError,'Carica'):lyric_meter.adapt(app,{'request':{'lyrics':'source'},'phrases':self.phrases()})
  with patch.object(app,'settings',return_value=app.DEFAULTS|{'llm_model':'test'}),patch.object(app,'llm',return_value=self.response(ident=2)),self.assertRaisesRegex(ValueError,'ordine'):lyric_meter.adapt(app,{'request':{'lyrics':'source'},'phrases':self.phrases()})
 def test_context_does_not_fabricate_transcription(self):
  with self.assertRaisesRegex(ValueError,'spartito'):app.lyric_context({'request':{}})
  self.assertEqual(app.lyric_context({'request':{'abc':'K:C\nC |'}})['abc'],'K:C\nC |')
  with patch.object(app.transcription,'source',return_value=(None,{'duration':30})),patch.object(app,'db',return_value=[]),self.assertRaisesRegex(ValueError,'Trascrivi prima'):app.lyric_context({'request':{'base_enabled':True,'base_import_id':'a'*32,'abc':'stale'}})

if __name__=='__main__':unittest.main()
