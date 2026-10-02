"""Optional OpenAI-compatible text APIs. Credentials never enter public state."""
from contextlib import contextmanager
import copy
import json
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

_session=threading.local()
KEYS_ROW='assistant-api-keys'
_models_cache={}
_models_lock=threading.Lock()

def active(app):return getattr(_session,'root',None)==app.ROOT and getattr(_session,'config',None) is not None


def api_url(value):
 if not isinstance(value,str) or not value.strip() or len(value)>2000 or any(ord(c)<33 for c in value.strip()):
  raise ValueError('Inserisci l’indirizzo completo delle API.')
 value=value.strip().rstrip('/')
 try:
  parsed=urllib.parse.urlsplit(value);port=parsed.port
 except ValueError:raise ValueError('Indirizzo delle API non valido.')
 local=parsed.hostname in ('localhost','127.0.0.1','::1')
 if not parsed.hostname or parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment or parsed.scheme!='https' and not (parsed.scheme=='http' and local):
  raise ValueError('Usa un indirizzo HTTPS senza credenziali o parametri, per esempio https://api.openai.com/v1. HTTP è ammesso solo per un server sullo stesso PC.')
 return urllib.parse.urlunsplit((parsed.scheme,parsed.netloc.lower(),parsed.path,'',''))


def keys(app):
 row=app.db('SELECT value FROM settings WHERE key=?',(KEYS_ROW,),one=True)
 return json.loads(row['value']) if row else {}


def public_settings(app):
 settings={k:v for k,v in app.settings().items() if k not in ('llm_api_key','llm_api_clear_key')}
 settings['llm_api_key_saved']=bool(keys(app).get(settings['llm_api_url']))
 return settings


def save_preferences(app,settings,data):
 """Save validated public preferences and endpoint-bound secrets atomically."""
 settings=dict(settings)
 settings['llm_api_url']=api_url(settings['llm_api_url'])
 model=settings['llm_api_model']
 if not isinstance(model,str) or len(model)>200 or any(ord(c)<32 for c in model):raise ValueError('Nome del modello API non valido.')
 settings['llm_api_model']=model.strip()
 if settings['llm_api_format'] not in ('auto','json','text'):raise ValueError('Formato della risposta API non valido.')
 key=data.get('llm_api_key','');clear=data.get('llm_api_clear_key',False)
 if not isinstance(key,str) or len(key)>4000 or any(ord(c)<33 or ord(c)>126 for c in key.strip()):raise ValueError('Chiave API non valida.')
 if type(clear)!=bool:raise ValueError('Scelta della chiave API non valida.')
 key=key.strip()
 if key and clear:raise ValueError('Scegli se sostituire o rimuovere la chiave API.')
 settings.pop('llm_api_key',None);settings.pop('llm_api_clear_key',None);settings.pop('llm_api_key_saved',None)
 with app.LOCK,app.conn() as connection:
  credentials=keys(app)
  if clear:credentials.pop(settings['llm_api_url'],None)
  elif key:credentials[settings['llm_api_url']]=key
  connection.execute('INSERT OR REPLACE INTO settings VALUES (?,?)',(KEYS_ROW,app.jdump(credentials)))
  connection.execute('INSERT OR REPLACE INTO settings VALUES (?,?)',('main',app.jdump(settings)))


def configuration(app):
 if active(app):return _session.config
 settings=app.settings();base=api_url(settings['llm_api_url'])
 return settings,base,keys(app).get(base,'')


@contextmanager
def session(app):
 previous=(getattr(_session,'root',None),getattr(_session,'config',None))
 _session.config=configuration(app);_session.root=app.ROOT
 try:yield
 finally:_session.root,_session.config=previous


def model_id(app):
 model=configuration(app)[0]['llm_api_model']
 if not model:raise ValueError('Scegli il modello API in Sistema: usa Leggi modelli oppure inserisci il suo identificativo e salva le preferenze.')
 return model


class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):return None


def remember_models(base,result):
 entries=result.get('data')
 if not isinstance(entries,list):return
 models={m['id']:{'reasoning':m.get('reasoning'),'top_provider':m.get('top_provider',{})} for m in entries if isinstance(m,dict) and isinstance(m.get('id'),str)}
 with _models_lock:_models_cache[base]=(time.monotonic(),models)


def openrouter_model(base,model):
 """Public capabilities: cache metadata only, never credentials or prompts."""
 with _models_lock:cached=_models_cache.get(base)
 if cached and time.monotonic()-cached[0]<900:return cached[1].get(model)
 try:
  with urllib.request.build_opener(NoRedirect()).open(base+'/models',timeout=15) as response:raw=response.read(8*1024*1024+1)
  if len(raw)>8*1024*1024:return None
  result=json.loads(raw)
  if not isinstance(result,dict):return None
  remember_models(base,result)
  with _models_lock:cached=_models_cache.get(base)
  return cached[1].get(model) if cached else None
 except (OSError,ValueError,UnicodeError):return None


def prepare_openrouter(body,capabilities):
 reasoning=capabilities.get('reasoning') if capabilities else None
 if isinstance(reasoning,dict):
  limit=body.get('max_tokens',6000)
  if reasoning.get('mandatory') is False:
   # Short structural answers must not spend their whole budget on thinking.
   body['reasoning']={'enabled':False,'exclude':True}
   body['max_tokens']=max(limit,1024)
  elif reasoning.get('mandatory') is True:
   config={'exclude':True}
   if reasoning.get('supports_max_tokens') is True:config['max_tokens']=1024
   else:
    efforts=reasoning.get('supported_efforts')
    lowest=next((e for e in ('minimal','low','medium','high','xhigh','max') if isinstance(efforts,list) and e in efforts),None)
    if lowest:config['effort']=lowest
   body['reasoning']=config;body['max_tokens']=max(limit+2048,4096)
 top=capabilities.get('top_provider',{}) if capabilities else {}
 maximum=top.get('max_completion_tokens') if isinstance(top,dict) else None
 if type(maximum)==int and maximum>0 and 'max_tokens' in body:body['max_tokens']=min(body['max_tokens'],maximum)
 if body.get('reasoning',{}).get('max_tokens',0)>=body.get('max_tokens',6000):
  # A constrained provider may not accept a separate thinking budget.
  body['reasoning'].pop('max_tokens',None)


def request(app,path,payload=None,timeout=None):
 if path not in ('/models','/chat/completions'):raise ValueError('Questa operazione richiede LM Studio locale.')
 settings,base,key=configuration(app);host=urllib.parse.urlsplit(base).hostname
 if host in ('api.openai.com','api.deepseek.com','openrouter.ai') and not key:raise ValueError('Inserisci e salva la chiave API del servizio scelto in Sistema.')
 headers={'Content-Type':'application/json','Accept':'application/json'}
 if key:headers['Authorization']='Bearer '+key
 body=copy.deepcopy(payload) if payload is not None else None
 if body is not None:
  body['model']=model_id(app)
  schema=body.get('response_format',{}).get('json_schema',{}).get('schema')
  if schema:
   # Keep the exact structure in the prompt for providers with JSON mode only.
   body['messages'].append({'role':'system','content':'Return ONLY JSON conforming to this schema: '+app.jdump(schema)})
  mode=settings['llm_api_format']
  if mode=='text':body.pop('response_format',None)
  elif mode=='json' or host=='api.deepseek.com' or 'response_format' not in body:body['response_format']={'type':'json_object'}
  if host=='api.openai.com' and 'max_tokens' in body:
   body['max_completion_tokens']=body.pop('max_tokens')
   # Reasoning models may reject sampling controls. Keep the provider default.
   body.pop('temperature',None)
  if host=='openrouter.ai':prepare_openrouter(body,openrouter_model(base,body['model']))
 opener=urllib.request.build_opener(NoRedirect())
 for attempt in range(3):
  req=urllib.request.Request(base+path,data=app.jdump(body).encode('utf-8') if body is not None else None,headers=headers)
  try:
   with opener.open(req,timeout=timeout or (600 if body is not None else 20)) as response:
    raw=response.read(8*1024*1024+1)
   if len(raw)>8*1024*1024:raise ValueError('La risposta del servizio API è troppo grande.')
   try:result=json.loads(raw)
   except (ValueError,UnicodeError):raise ValueError('Il servizio API non ha restituito JSON. Controlla l’indirizzo in Sistema.')
   if not isinstance(result,dict) or result.get('error'):raise ValueError('Il servizio API ha restituito una risposta non valida.')
   if path=='/models':
    if host=='openrouter.ai':remember_models(base,result)
    entries=result.get('data')
    if not isinstance(entries,list):raise ValueError('Il servizio non espone una lista di modelli compatibile. Inserisci il modello manualmente in Sistema.')
    return {'data':[{'id':m['id']} for m in entries if isinstance(m,dict) and isinstance(m.get('id'),str)]}
   choices=result.get('choices');choice=choices[0] if isinstance(choices,list) and choices and isinstance(choices[0],dict) else {}
   message=choice.get('message',{});message=message if isinstance(message,dict) else {}
   if message.get('refusal'):raise ValueError('Il servizio API ha rifiutato questa richiesta. Modifica le indicazioni e riprova.')
   if choice.get('finish_reason')=='length':
    usage=result.get('usage',{});details=usage.get('completion_tokens_details',{}) if isinstance(usage,dict) else {}
    thought=details.get('reasoning_tokens',0) if isinstance(details,dict) else 0
    total=usage.get('completion_tokens',0) if isinstance(usage,dict) else 0
    if not message.get('content') and isinstance(thought,int) and thought>0:
     raise ValueError(f'Il modello ha raggiunto il limite prima di restituire il testo: {thought} token di ragionamento su {total} token di risposta. La bozza è conservata.')
    raise ValueError('La risposta API è stata troncata. Riduci la richiesta o scegli un altro modello; la bozza è conservata.')
   if not isinstance(message.get('content'),str) or not message['content'].strip():raise ValueError('Il modello API non ha restituito testo. Prova un modello per chat senza ragionamento prolungato.')
   return result
  except urllib.error.HTTPError as error:
   try:
    detail=json.loads(error.read(16000)).get('error',{})
    detail=detail.get('message','') if isinstance(detail,dict) else str(detail)
   except (ValueError,UnicodeError):detail=''
   finally:error.close()
   if key:detail=detail.replace(key,'[chiave nascosta]')
   detail=detail[:800];lower=detail.lower()
   # Retry only an explicitly rejected format, never network failures or quotas.
   unsupported=any(word in lower for word in ('unsupported','not support','not available','invalid','not permitted','not allowed'))
   if error.code in (400,422) and body is not None and settings['llm_api_format']=='auto' and unsupported and ('response_format' in lower or 'json_schema' in lower):
    kind=body.get('response_format',{}).get('type')
    if attempt<2 and kind=='json_schema':body['response_format']={'type':'json_object'};continue
    if attempt<2 and kind=='json_object':body.pop('response_format',None);continue
   cause={401:'Chiave API non valida o scaduta.',403:'Il servizio API non autorizza questa chiave o questo modello.',404:'Indirizzo API o modello non trovato.',429:'Il servizio API ha raggiunto il limite di richieste o il credito disponibile.'}.get(error.code,'Il servizio API non ha completato la richiesta (HTTP '+str(error.code)+').')
   if 300<=error.code<400:cause='Il servizio API rimanda a un altro indirizzo. Inserisci direttamente l’indirizzo corretto in Sistema.'
   raise ValueError(cause+(' '+detail if detail else '')) from None
  except (urllib.error.URLError,TimeoutError,socket.timeout):raise ValueError('Il servizio API non risponde. Controlla connessione e indirizzo in Sistema, poi riprova.') from None
