import sys,pathlib,tempfile,threading,unittest,urllib.request,urllib.error,json,hashlib
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import app,transcription
class TranscriptionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory(dir=app.ROOT/'tests');cls.old=app.DATA,app.OUT,app.PORT
  app.DATA=pathlib.Path(cls.temp.name);app.OUT=app.DATA/'outputs';app.init()
  cls.server=app.http.server.ThreadingHTTPServer(('127.0.0.1',0),app.Handler);app.PORT=cls.server.server_port
  cls.thread=threading.Thread(target=cls.server.serve_forever);cls.thread.start();cls.base=f'http://127.0.0.1:{app.PORT}'
  cls.mp3=(app.ROOT/'tests/Prima-luce-trascrizione.mp3').read_bytes()
 @classmethod
 def tearDownClass(cls):
  cls.server.shutdown();cls.server.server_close();cls.thread.join();app.DATA,app.OUT,app.PORT=cls.old
  assert pathlib.Path(cls.temp.name).resolve().is_relative_to((app.ROOT/'tests').resolve());cls.temp.cleanup()
 def call(self,path,data=None,headers=None):
  h={'X-H3-Music':'1',**(headers or {})};body=json.dumps(data).encode() if isinstance(data,dict) else data
  return urllib.request.urlopen(urllib.request.Request(self.base+path,data=body,headers=h),timeout=30)
 def upload(self,name='Una melodia.mp3',data=None,headers=None):
  with self.call('/api/audio/upload',self.mp3 if data is None else data,{'X-Filename':urllib.parse.quote(name),**(headers or {})}) as response:return json.load(response)
 def test_real_mp3_import_and_range(self):
  m=self.upload('È una melodia.mp3');self.assertEqual(m['name'],'È una melodia.mp3');self.assertGreater(m['duration'],6);self.assertEqual(m['sha256'],hashlib.sha256(self.mp3).hexdigest())
  with self.call(m['url'],headers={'Range':'bytes=10-99'}) as r:self.assertEqual(r.status,206);self.assertEqual(r.read(),self.mp3[10:100])
 def test_invalid_upload_and_cleanup(self):
  for name,data in [('bad.exe',b'x'),('fake.mp3',b'not audio'),('playlist.m3u',b'#EXTM3U')]:
   before=len(transcription.list_sources(app.DATA))
   with self.assertRaises(urllib.error.HTTPError) as cm:self.upload(name,data)
   self.assertEqual(cm.exception.code,400);self.assertEqual(len(transcription.list_sources(app.DATA)),before)
 def test_origin_guard(self):
  with self.assertRaises(urllib.error.HTTPError) as cm:self.upload(headers={'Origin':'https://example.com'})
  self.assertEqual(cm.exception.code,403)
 def test_queue_snapshot_cancel_retry_and_intervals(self):
  m=self.upload();req={'source_id':m['id'],'title':'Trascrizione prova','start':1,'end':5,'melody_only':True}
  with patch.object(transcription,'status',return_value={'ready':True}):
   j=app.enqueue({'kind':'transcribe','request':req});ident=j['ids'][0];req['title']='changed'
   self.assertEqual(app.get_job(ident)['request']['title'],'Trascrizione prova')
   app.cancel(ident);self.assertEqual(app.get_job(ident)['status'],'cancelled')
   with self.call('/api/jobs/retry',{'id':ident}) as response:retry=json.load(response)
   self.assertEqual(app.get_job(retry['ids'][0])['kind'],'transcribe')
   for changes in [{'start':-1},{'end':100},{'end':.01},{'start':float('nan')},{'source_id':'../outside'},{'melody_only':'yes'}]:
    with self.assertRaises(ValueError):app.enqueue({'kind':'transcribe','request':req|changes})
 def test_bundle_includes_original_and_nested_annotations(self):
  import zipfile
  m=self.upload()
  with patch.object(transcription,'status',return_value={'ready':True}):ident=app.enqueue({'kind':'transcribe','request':{'source_id':m['id']}})['ids'][0]
  d=app.OUT/ident;(d/'notation').mkdir(parents=True);(d/'score.abc').write_text('X:1\nK:C\nCDEF|');(d/'notation/song_beats.txt').write_text('0 1')
  app.bundle({'id':ident})
  with zipfile.ZipFile(d/'project.zip') as z:
   self.assertIn('notation/song_beats.txt',z.namelist());self.assertEqual(z.read('original.mp3'),self.mp3)
 def test_preflight_not_ready(self):
  with patch.object(transcription,'status',return_value={'ready':False}),self.assertRaises(ValueError):app.enqueue({'kind':'transcribe','request':{}})
if __name__=='__main__':unittest.main(verbosity=2)
