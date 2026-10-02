"""Exercise API transport and settings against local fake providers, without credit."""
import http.server
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
import urllib.request
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app, assistant_api, assistant_engine, lyric_meter


class ApiTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=app.ROOT/'tests',prefix='tmp-api-')
  self.old=app.DATA,app.OUT
  app.DATA=Path(self.temp.name);app.OUT=app.DATA/'outputs';app.init()
  self.calls=[];self.reply=lambda path,body:(200,{'data':[{'id':'chosen'}]} if path.endswith('/models') else {'choices':[{'message':{'content':'{"lyrics":"[Verse]\\nCanto"}'}}]})
  owner=self
  class Provider(http.server.BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def respond(self):
    body=json.loads(self.rfile.read(int(self.headers['Content-Length']))) if self.command=='POST' else None
    owner.calls.append((self.path,dict(self.headers),body))
    status,value=owner.reply(self.path,body);self.send_response(status)
    if status==302:self.send_header('Location','http://127.0.0.1:1/stolen')
    self.end_headers();self.wfile.write(json.dumps(value).encode())
   do_GET=respond;do_POST=respond
  self.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Provider)
  self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
  self.url='http://127.0.0.1:'+str(self.server.server_port)+'/v1'
  self.settings=app.DEFAULTS|{'llm_provider':'api','llm_api_url':self.url,'llm_api_model':'chosen'}
  assistant_api.save_preferences(app,self.settings,{'llm_api_key':'fake-secret'})
 def tearDown(self):
  self.server.shutdown();self.server.server_close();self.thread.join()
  app.DATA,app.OUT=self.old;self.temp.cleanup()
 def payload(self):return {'model':'old','messages':[{'role':'system','content':'Return JSON'},{'role':'user','content':'A song'}],'max_tokens':100,'temperature':.35}
 def test_url_validation_preserves_https_prefix_and_local_http(self):
  self.assertEqual(assistant_api.api_url(' HTTPS://API.OPENAI.COM/v1/ '),'https://api.openai.com/v1')
  self.assertEqual(assistant_api.api_url(self.url),self.url)
  for value in ('','file:///model','http://example.com/v1','https://user:key@example.com','https://example.com/?key=abc','https://example.com/#x','https://example.com:abc','https://example.com/\nkey'):
   with self.subTest(value=value),self.assertRaises(ValueError):assistant_api.api_url(value)
 def test_key_saved_separately_preserved_removed_and_bound_to_endpoint(self):
  public=assistant_api.public_settings(app)
  self.assertTrue(public['llm_api_key_saved']);self.assertNotIn('fake-secret',json.dumps(public));self.assertNotIn('llm_api_key',app.settings())
  assistant_api.save_preferences(app,self.settings,{'llm_api_key':''})
  self.assertEqual(assistant_api.keys(app)[self.url],'fake-secret')
  other=self.settings|{'llm_api_url':self.url+'/other'}
  assistant_api.save_preferences(app,other,{})
  self.assertFalse(assistant_api.public_settings(app)['llm_api_key_saved'])
  app.llm('/models');self.assertNotIn('Authorization',self.calls[-1][1])
  assistant_api.save_preferences(app,self.settings,{'llm_api_clear_key':True})
  self.assertFalse(assistant_api.public_settings(app)['llm_api_key_saved'])
 def test_invalid_key_does_not_change_preferences_or_existing_key(self):
  before=app.settings()
  for data in ({'llm_api_key':'abc\r\nInjected: yes'},{'llm_api_key':'new','llm_api_clear_key':True},{'llm_api_clear_key':'true'}):
   with self.subTest(data=data),self.assertRaises(ValueError):assistant_api.save_preferences(app,self.settings|{'threads':2},data)
  self.assertEqual(app.settings(),before);self.assertEqual(assistant_api.keys(app)[self.url],'fake-secret')
 def test_models_and_completion_use_authorization_without_mutating_payload(self):
  self.assertEqual(app.llm('/models'),{'data':[{'id':'chosen'}]})
  payload=self.payload();app.llm('/chat/completions',payload)
  path,headers,sent=self.calls[-1]
  self.assertEqual(path,'/v1/chat/completions');self.assertEqual(headers['Authorization'],'Bearer fake-secret')
  self.assertEqual(sent['model'],'chosen');self.assertEqual(sent['response_format'],{'type':'json_object'})
  self.assertNotIn('response_format',payload);self.assertEqual(payload['model'],'old')
 def test_remote_session_pins_model_endpoint_key_and_does_not_load_local_engine(self):
  with patch.object(assistant_engine,'start') as start,assistant_engine.session(app):
   app.save_settings(app.DEFAULTS|{'llm_provider':'internal'})
   app.llm('/chat/completions',self.payload())
   self.assertEqual(assistant_engine.selected_model(app),'chosen');self.assertFalse(assistant_engine.busy())
  start.assert_not_called();self.assertEqual(self.calls[-1][1]['Authorization'],'Bearer fake-secret')
  self.assertFalse(assistant_api.active(app))
 def test_requires_explicit_remote_model_without_native_lmstudio_probes(self):
  app.save_settings(self.settings|{'llm_api_model':''})
  with self.assertRaisesRegex(ValueError,'Scegli il modello API'):app.assist({'instruction':'Scrivi una canzone'})
  self.assertEqual(self.calls,[])
  self.assertFalse(lyric_meter.reasoning_off_available(app,'chosen'))
 def test_assistant_and_meter_use_api_and_preserve_original_fields_and_tags(self):
  result=app.assist({'request':{'lyrics':'[Verse]\nWords','abc':'K:C\nC |','style':'Italian pop','notes':'private production notes','clone_voice':'private-voice-reference'},'instruction':'Adatta il testo'})
  self.assertEqual(result['request']['lyrics'],'[Verse]\nCanto');self.assertEqual(result['request']['abc'],'K:C\nC |')
  current=json.loads(self.calls[-1][2]['messages'][1]['content'])['current']
  self.assertEqual(set(current),{'title','style','lyrics','abc'});self.assertEqual(result['request']['notes'],'private production notes')
  self.reply=lambda path,body:(200,{'choices':[{'message':{'content':json.dumps({'lines':[{'id':1,'section':'Verse','text':'Canto'}]})}}]})
  request={'title':'Originale','lyrics':'[Verse]\nWords','style':'Italian pop','abc':'K:C\nC |'}
  phrases=[{'notes':[{'start':0,'duration':.25},{'start':.25,'duration':.25}]}]
  result=lyric_meter.adapt(app,{'request':request,'phrases':phrases})
  self.assertEqual(result['request']['lyrics'],'[Verse]\nCanto');self.assertEqual(result['request']['style'],request['style'])
  self.assertTrue(all(path=='/v1/chat/completions' for path,_,_ in self.calls))
 def test_unsupported_schema_falls_back_only_after_rejection_and_keeps_schema_in_prompt(self):
  self.reply=lambda path,body:(400,{'error':{'message':'response_format json_schema is not supported'}}) if body.get('response_format',{}).get('type')=='json_schema' else (200,{'choices':[{'message':{'content':'{}'}}]})
  payload=self.payload()|{'response_format':{'type':'json_schema','json_schema':{'schema':{'type':'object'}}}}
  app.llm('/chat/completions',payload)
  self.assertEqual(len(self.calls),2);self.assertEqual(self.calls[-1][2]['response_format'],{'type':'json_object'})
  self.assertIn('schema',self.calls[-1][2]['messages'][-1]['content'])
 def test_auth_quota_and_other_failures_are_clear_redacted_and_never_retried(self):
  for code,message in ((401,'Chiave API'),(429,'credito'),(500,'non ha completato')):
   self.reply=lambda path,body:(code,{'error':{'message':'fake-secret'}})
   before=len(self.calls)
   with self.assertRaisesRegex(ValueError,message) as error:app.llm('/chat/completions',self.payload())
   self.assertNotIn('fake-secret',str(error.exception));self.assertEqual(len(self.calls),before+1)
 def test_redirect_is_rejected_without_forwarding_credentials(self):
  self.reply=lambda path,body:(302,{})
  with self.assertRaisesRegex(ValueError,'altro indirizzo'):app.llm('/models')
  self.assertEqual(len(self.calls),1)
 def test_truncated_or_empty_output_is_never_applied(self):
  for choice in ({'message':{'content':'{}'},'finish_reason':'length'},{'message':{'content':''}},{'message':{'refusal':'No'}}):
   self.reply=lambda path,body:(200,{'choices':[choice]})
   with self.subTest(choice=choice),self.assertRaises(ValueError):app.llm('/chat/completions',self.payload())
 def test_known_services_need_a_key_and_openai_uses_current_token_parameter(self):
  assistant_api.save_preferences(app,self.settings|{'llm_api_url':'https://api.openai.com/v1'},{})
  with self.assertRaisesRegex(ValueError,'chiave API'):app.llm('/models')
  assistant_api.save_preferences(app,app.settings(),{'llm_api_key':'fake-openai'})
  with patch.object(assistant_api.urllib.request,'build_opener') as factory:
   response=factory.return_value.open.return_value.__enter__.return_value
   response.read.return_value=b'{"choices":[{"message":{"content":"{}"}}]}'
   app.llm('/chat/completions',self.payload())
   sent=json.loads(factory.return_value.open.call_args.args[0].data)
   self.assertEqual(sent['max_completion_tokens'],100);self.assertNotIn('max_tokens',sent);self.assertNotIn('temperature',sent)
 def test_openrouter_disables_optional_reasoning_in_actual_request(self):
  base='https://openrouter.ai/api/v1'
  assistant_api.save_preferences(app,self.settings|{'llm_api_url':base,'llm_api_model':'kimi'},{'llm_api_key':'fake-router'})
  assistant_api.remember_models(base,{'data':[{'id':'kimi','reasoning':{'mandatory':False,'default_effort':'max','supported_efforts':['low','high','max']}}]})
  with patch.object(assistant_api.urllib.request,'build_opener') as factory:
   factory.return_value.open.return_value.__enter__.return_value.read.return_value=b'{"choices":[{"message":{"content":"{}"}}]}'
   payload=self.payload();app.llm('/chat/completions',payload)
   factory.return_value.open.assert_called_once()
   sent=json.loads(factory.return_value.open.call_args.args[0].data)
   self.assertEqual(sent['reasoning'],{'enabled':False,'exclude':True});self.assertGreaterEqual(sent['max_tokens'],1024)
   self.assertNotIn('reasoning',payload);self.assertEqual(payload['max_tokens'],100)
 def test_mandatory_reasoning_uses_only_supported_controls_and_reserves_output(self):
  for metadata,expected in (({'mandatory':True,'supported_efforts':['max','high','low']},{'exclude':True,'effort':'low'}),({'mandatory':True},{'exclude':True}),({'mandatory':True,'supports_max_tokens':True},{'exclude':True,'max_tokens':1024})):
   with self.subTest(metadata=metadata):
    body=self.payload();assistant_api.prepare_openrouter(body,{'reasoning':metadata})
    self.assertEqual(body['reasoning'],expected);self.assertGreaterEqual(body['max_tokens'],4096)
  body=self.payload();assistant_api.prepare_openrouter(body,{'reasoning':{'mandatory':True,'supports_max_tokens':True},'top_provider':{'max_completion_tokens':512}})
  self.assertEqual(body['max_tokens'],512);self.assertNotIn('max_tokens',body['reasoning'])
 def test_unknown_metadata_and_other_providers_preserve_payload(self):
  body=self.payload();before=dict(body);assistant_api.prepare_openrouter(body,None);self.assertEqual(body,before)
  app.llm('/chat/completions',body);self.assertNotIn('reasoning',self.calls[-1][2]);self.assertEqual(self.calls[-1][2]['max_tokens'],100)
 def test_reasoning_exhaustion_and_malformed_choices_are_safe_errors(self):
  self.reply=lambda path,body:(200,{'choices':[{'finish_reason':'length','message':{'content':'','reasoning':'private thinking'}}],'usage':{'completion_tokens':360,'completion_tokens_details':{'reasoning_tokens':360}}})
  with self.assertRaisesRegex(ValueError,'360 token di ragionamento') as error:app.llm('/chat/completions',self.payload())
  self.assertNotIn('private thinking',str(error.exception))
  for choices in ({'unexpected':'value'},[None],[{'message':None}]):
   self.reply=lambda path,body:(200,{'choices':choices})
   with self.subTest(choices=choices),self.assertRaises(ValueError):app.llm('/chat/completions',self.payload())
 def test_capabilities_lookup_is_public_cached_and_failure_is_optional(self):
  base='https://openrouter.ai/api/v1/cache-test'
  with patch.object(assistant_api.urllib.request,'build_opener') as factory:
   factory.return_value.open.return_value.__enter__.return_value.read.return_value=b'{"data":[{"id":"kimi","reasoning":{"mandatory":false}}]}'
   self.assertEqual(assistant_api.openrouter_model(base,'kimi')['reasoning'],{'mandatory':False})
   self.assertIsNotNone(assistant_api.openrouter_model(base,'kimi'));factory.return_value.open.assert_called_once_with(base+'/models',timeout=15)
  with patch.object(assistant_api.urllib.request,'build_opener') as factory:
   factory.return_value.open.side_effect=OSError('Offline')
   self.assertIsNone(assistant_api.openrouter_model(base+'/offline','kimi'))
 def test_failed_adaptation_records_error_without_prompt_or_key(self):
  with patch.object(lyric_meter,'adapt',side_effect=ValueError('API rejected fake-secret')):
   with self.assertRaises(ValueError):app.assistant_operation('lyrics/adapt',{'request':{'lyrics':'private words'}})
  record=json.loads((app.DATA/'assistant/last-error.json').read_text(encoding='utf-8'))
  self.assertEqual(record['operation'],'lyrics/adapt');self.assertEqual(record['model'],'chosen')
  log=(app.DATA/'assistant/request-errors.log').read_text(encoding='utf-8')
  self.assertNotIn('fake-secret',log);self.assertNotIn('private words',log);self.assertIn('[chiave nascosta]',log)
 def test_success_does_not_write_error_log_or_change_preferences(self):
  before=app.settings()
  result=app.assistant_operation('assist',{'instruction':'Cambia le parole'})
  self.assertEqual(result['request']['lyrics'],'[Verse]\nCanto')
  self.assertFalse((app.DATA/'assistant/last-error.json').exists());self.assertEqual(app.settings(),before)
 def test_error_log_rotates_and_preserves_the_latest_reason(self):
  folder=app.DATA/'assistant';folder.mkdir();(folder/'request-errors.log').write_text('old'*24000)
  with patch.object(lyric_meter,'adapt',side_effect=ValueError('Latest reason')):
   with self.assertRaises(ValueError):app.assistant_operation('lyrics/adapt',{})
  self.assertTrue((folder/'request-errors.previous.log').exists())
  self.assertEqual(json.loads((folder/'last-error.json').read_text())['error'],'Latest reason')


if __name__=='__main__':unittest.main()
