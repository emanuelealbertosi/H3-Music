import json, math, sys, unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import app, lyric_meter

class MeterTests(unittest.TestCase):
 def setUp(self):
  self.settings=patch.object(app,'settings',return_value=app.DEFAULTS);self.settings.start();self.addCleanup(self.settings.stop)
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
 def test_source_sections_keep_order_and_numbered_verses(self):
  lyrics='[Verse 1]\nOne line\n[Pre-Chorus]\nAnother\n[Chorus]\nRefrain\n[Verse 2]\nOne more\n[Chorus]\nRefrain'
  self.assertEqual(lyric_meter.source_sections(lyrics),['Verse 1','Pre-Chorus','Chorus','Verse 2','Chorus'])
 def test_section_plan_rejects_changed_order_or_empty_sections(self):
  phrases=[{'id':n} for n in range(1,5)]
  good={'sections':[{'start':1,'section':'Verse'},{'start':3,'section':'Chorus'}]}
  self.assertEqual(lyric_meter.parse_section_plan(json.dumps(good),phrases,['Verse','Chorus'])[0],['Verse','Verse','Chorus','Chorus'])
  for sections in ([{'start':2,'section':'Verse'}],[{'start':1,'section':'Verse'},{'start':0,'section':'Chorus'}],[{'start':1,'section':'Chorus'},{'start':3,'section':'Verse'}],[{'start':1,'section':'Verse'},{'start':6,'section':'Chorus'}]):
   with self.assertRaises(ValueError):lyric_meter.parse_section_plan(json.dumps({'sections':sections}),phrases,['Verse','Chorus'])
  empty={'sections':[{'start':1,'section':'Intro'},{'start':1,'section':'Verse 1'},{'start':5,'section':'Outro'}]}
  plan,headings=lyric_meter.parse_section_plan(json.dumps(empty),phrases,['Intro','Verse 1','Outro'])
  self.assertEqual(plan,['Verse 1']*4);self.assertEqual([r['section'] for r in headings],['Intro','Verse 1','Outro'])
 def test_existing_structure_controls_phrase_tags(self):
  phrases=[{'notes':[{'start':n*.5,'duration':.25},{'start':n*.5+.25,'duration':.25}]} for n in range(4)]
  def reply(value):return {'choices':[{'message':{'content':json.dumps(value)}}]}
  plan=reply({'sections':[{'start':1,'section':'Verse'},{'start':3,'section':'Chorus'}]})
  wrong=reply({'lines':[{'id':n,'section':'Spoken','text':'Canto'} for n in range(1,5)]})
  correct=reply({'lines':[{'id':n,'section':'Verse' if n<3 else 'Chorus','text':'Canto'} for n in range(1,5)]})
  with patch.object(app,'settings',return_value=app.DEFAULTS|{'llm_model':'test'}),patch.object(app,'llm',side_effect=[plan,wrong,correct]) as call:
   result=lyric_meter.adapt(app,{'request':{'lyrics':'[Verse]\nForeign words\n[Chorus]\nThe refrain'},'mode':'translate','phrases':phrases})
   self.assertEqual(call.call_count,3)
   self.assertEqual(result['request']['lyrics'],'[Verse]\nCanto\nCanto\n\n[Chorus]\nCanto\nCanto')
   sent=json.loads(call.call_args_list[1].args[1]['messages'][1]['content'])
   self.assertEqual([p['section'] for p in sent['phrases']],['Verse','Verse','Chorus','Chorus'])
   self.assertIn('title',sent);self.assertIn('style',sent)
 def test_section_continues_across_chunk_boundary(self):
  phrases=[{'notes':[{'start':n*.5,'duration':.25},{'start':n*.5+.25,'duration':.25}]} for n in range(13)]
  def respond(path,payload,**kwargs):
   data=json.loads(payload['messages'][1]['content'])
   if data['phrases'][0]['id']==13:self.assertEqual(data['previous_lines'][-1]['section'],'Pre-Chorus')
   rows=[{'id':p['id'],'section':p['section'],'text':'Canto'} for p in data['phrases']]
   return {'choices':[{'message':{'content':json.dumps({'lines':rows})}}]}
  with patch.object(app,'settings',return_value=app.DEFAULTS|{'llm_model':'test'}),patch.object(app,'llm',side_effect=respond):
   result=lyric_meter.adapt(app,{'request':{'lyrics':'[Pre-Chorus]\nWords'},'phrases':phrases})
   self.assertEqual(result['request']['lyrics'].count('[Pre-Chorus]'),1)
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
 def test_repeated_refrain_receives_completed_reference_across_chunks(self):
  phrases=[{'notes':[{'start':n*.5,'duration':.25},{'start':n*.5+.25,'duration':.25}]} for n in range(13)]
  def respond(path,payload,**kwargs):
   data=json.loads(payload['messages'][1]['content'])
   if 'required_section_order' in data:
    result={'sections':[{'start':1,'section':'Chorus'},{'start':3,'section':'Verse'},{'start':13,'section':'Chorus'}]}
   else:
    if data['phrases'][0]['id']==13:
     self.assertEqual(data['chorus_reference'],[{'section':'Chorus','text':'Canto'}]*2)
     self.assertEqual([h['section'] for h in data['song_structure']],['Chorus','Verse','Chorus'])
     self.assertEqual(data['previous_lines'][-1]['section'],'Verse')
    result={'lines':[{'id':p['id'],'section':p['section'],'text':'Canto'} for p in data['phrases']]}
   return {'choices':[{'message':{'content':json.dumps(result)}}]}
  with patch.object(app,'settings',return_value=app.DEFAULTS|{'llm_model':'test'}),patch.object(app,'llm',side_effect=respond) as call:
   result=lyric_meter.adapt(app,{'request':{'lyrics':'[Chorus]\nCanto\n[Verse]\nWords\n[Chorus]\nCanto'},'phrases':phrases})
   self.assertEqual(lyric_meter.lyric_tags(result['request']['lyrics']),['Chorus','Verse','Chorus'])
   self.assertEqual(call.call_count,5)
 def test_incomplete_or_empty_refrain_is_not_a_completed_reference(self):
  headings=[{'start':1,'section':'Intro'},{'start':1,'section':'Chorus'},{'start':4,'section':'Verse'}]
  self.assertEqual(lyric_meter.chorus_reference([{'section':'Chorus','text':'Canto'}],headings,4),[])
  self.assertEqual(lyric_meter.chorus_reference([],[{'start':1,'section':'Chorus'},{'start':1,'section':'Verse'}],4),[])
 def test_final_refrain_is_not_reused_before_it_has_finished(self):
  lines=[{'section':'Chorus','text':'Un verso'}]
  self.assertEqual(lyric_meter.chorus_reference(lines,[{'start':1,'section':'Chorus'}],3),[])
 def test_section_order_recovers_on_third_attempt_with_error_feedback(self):
  phrases=lyric_meter.validate_phrases([{'notes':[{'start':n,'duration':.25}]} for n in range(4)])
  req=app.validate({'lyrics':'[Verse]\nWords\n[Chorus]\nRefrain'})
  wrong=json.dumps({'sections':[{'start':1,'section':'Chorus'},{'start':3,'section':'Verse'}]})
  correct=json.dumps({'sections':[{'start':1,'section':'Verse'},{'start':3,'section':'Chorus'}]})
  with patch.object(lyric_meter,'complete',side_effect=[wrong,wrong,correct]) as call:
   plan,_=lyric_meter.section_plan(app,'test',phrases,req,'adapt','',False,2)
  self.assertEqual(plan,['Verse','Verse','Chorus','Chorus']);self.assertEqual(call.call_count,3)
  messages=call.call_args.args[2]
  self.assertEqual(len(messages),4);self.assertIn('ordine delle sezioni',messages[-1]['content']);self.assertIn(app.jdump(['Verse','Chorus']),messages[-1]['content'])
 def test_default_retry_budget_is_three_repairs_and_zero_disables_them(self):
  phrases=lyric_meter.validate_phrases([{'notes':[{'start':n,'duration':.25}]} for n in range(2)])
  req=app.validate({'lyrics':'[Verse]\nWords\n[Chorus]\nRefrain'})
  wrong=json.dumps({'sections':[{'start':1,'section':'Chorus'},{'start':2,'section':'Verse'}]})
  for selected,count in ((None,4),(0,1),(1,2)):
   with self.subTest(retries=selected),patch.object(lyric_meter,'complete',return_value=wrong) as call:
    with self.assertRaisesRegex(ValueError,r'Tentativi esauriti \('+str(count)+r'\)'):lyric_meter.section_plan(app,'test',phrases,req,'adapt','',False,selected)
    self.assertEqual(call.call_count,count)
 def test_invalid_retry_selection_and_service_failures_do_not_call_again(self):
  for value in (-1,11,True,2.5,'3',None):
   with self.subTest(value=value),patch.object(app,'llm') as call,self.assertRaisesRegex(ValueError,'ripetizioni automatiche'):
    lyric_meter.adapt(app,{'request':{'lyrics':'Words'},'phrases':self.phrases(),'retries':value})
   call.assert_not_called()
  with patch.object(app,'settings',return_value=app.DEFAULTS|{'llm_model':'test'}),patch.object(app,'llm',side_effect=ValueError('Chiave API non valida')) as call:
   with self.assertRaisesRegex(ValueError,'Chiave API'):lyric_meter.adapt(app,{'request':{'lyrics':'Words'},'phrases':self.phrases(),'retries':3})
   self.assertEqual(call.call_count,1)
 def test_later_chunk_repairs_do_not_regenerate_successful_earlier_chunk(self):
  phrases=[{'notes':[{'start':n*.5,'duration':.25},{'start':n*.5+.25,'duration':.25}]} for n in range(13)]
  visits=[]
  def respond(path,payload,**kwargs):
   data=json.loads(payload['messages'][1]['content']);first=data['phrases'][0]['id'];visits.append(first)
   rows=[{'id':p['id'],'section':p['section'],'text':'Canto'} for p in data['phrases']]
   if first==13 and visits.count(13)==1:rows[0]['section']='Chorus'
   return {'choices':[{'message':{'content':json.dumps({'lines':rows})}}]}
  with patch.object(app,'settings',return_value=app.DEFAULTS|{'llm_model':'test'}),patch.object(app,'llm',side_effect=respond):
   result=lyric_meter.adapt(app,{'request':{'lyrics':'[Verse]\nWords'},'phrases':phrases,'retries':3})
  self.assertEqual(visits,[1,1,13,13]);self.assertEqual(len(result['lines']),13)
 def test_context_does_not_fabricate_transcription(self):
  with self.assertRaisesRegex(ValueError,'spartito'):app.lyric_context({'request':{}})
  self.assertEqual(app.lyric_context({'request':{'abc':'K:C\nC |'}})['abc'],'K:C\nC |')
  with patch.object(app.transcription,'source',return_value=(None,{'duration':30})),patch.object(app,'db',return_value=[]),self.assertRaisesRegex(ValueError,'Trascrivi prima'):app.lyric_context({'request':{'base_enabled':True,'base_import_id':'a'*32,'abc':'stale'}})
 def test_original_context_prepares_only_the_selected_range(self):
  req={'title':'Brano','base_enabled':True,'base_import_id':'a'*32,'base_start':5,'base_end':20,'abc':'stale'}
  from contextlib import nullcontext
  with patch.object(app.transcription,'source',return_value=(None,{'duration':30})),patch.object(app,'db',return_value=[]),patch.object(app.model_store,'exclusive',return_value=nullcontext()),patch.object(app.transcription,'enqueue',return_value={'ids':['new']}) as enqueue:
   result=app.lyric_context({'request':req,'prepare':True})
   self.assertEqual(result['job_id'],'new');args=enqueue.call_args.args[1]['request']
   self.assertEqual((args['source_id'],args['start'],args['end'],args['melody_only']),('a'*32,5,20,True))
 def test_original_context_reuses_an_existing_transcription_in_queue(self):
  from contextlib import nullcontext
  pending={'id':'existing','request':json.dumps({'source_id':'a'*32,'start':5,'end':20})}
  with patch.object(app.transcription,'source',return_value=(None,{'duration':30})),patch.object(app,'db',side_effect=[[],[pending]]),patch.object(app.model_store,'exclusive',return_value=nullcontext()),patch.object(app.transcription,'enqueue') as enqueue:
   result=app.lyric_context({'request':{'base_enabled':True,'base_import_id':'a'*32,'base_start':5,'base_end':20},'prepare':True})
   self.assertEqual(result['job_id'],'existing');enqueue.assert_not_called()

if __name__=='__main__':unittest.main()
