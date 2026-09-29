import http.client
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app
import remote_access
from scripts.tailscale_access import endpoint_available


class RemoteAccessTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='tmp-remote-',dir=app.ROOT/'tests')
  self.old=(app.DATA,app.OUT,app.PORT)
  app.DATA=Path(self.tmp.name);app.OUT=app.DATA/'outputs';app.init()
  self.server=app.http.server.ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
  app.PORT=self.server.server_port
  self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
  self.origin='https://studio.example-tailnet.ts.net:8776'
 def tearDown(self):
  self.server.shutdown();self.server.server_close();self.thread.join()
  app.DATA,app.OUT,app.PORT=self.old;self.tmp.cleanup()
 def configure(self,value=None):
  (app.DATA/'remote-access.json').write_text(json.dumps({'origin':value or self.origin}),encoding='utf-8')
 def request(self,method='GET',host=None,origin=None,marker=True):
  headers={'Host':host or f'127.0.0.1:{app.PORT}'}
  if origin is not None:headers['Origin']=origin
  if marker:headers['X-H3-Music']='1'
  c=http.client.HTTPConnection('127.0.0.1',app.PORT,timeout=5)
  try:
   c.request(method,'/api/health' if method=='GET' else '/api/projects',body=None if method=='GET' else '{"request":{"title":"Remote test"}}',headers=headers)
   r=c.getresponse();return r.status,json.loads(r.read())
  finally:c.close()
 def test_local_default_and_remote_opt_in(self):
  self.assertEqual(self.request()[0],200)
  self.assertEqual(self.request(host=self.origin[8:])[0],403)
  self.assertEqual(self.request('POST',origin=self.origin)[0],403)
  self.configure()
  self.assertEqual(self.request(host=self.origin[8:])[0],200)
  self.assertEqual(self.request('POST',origin=self.origin)[0],200)
  self.assertEqual(self.request('POST',host=self.origin[8:],origin=self.origin)[0],200)
  self.assertEqual(self.request('POST',origin=f'http://localhost:{app.PORT}')[0],200)
  (app.DATA/'remote-access.json').unlink()
  self.assertEqual(self.request('POST',origin=self.origin)[0],403)
 def test_reject_other_origins_hosts_and_missing_csrf_marker(self):
  self.configure()
  for origin in ('https://evil.example','null','https://other.example-tailnet.ts.net:8776',self.origin+'/',self.origin.replace('https:','http:'),self.origin.replace('8776','443')):
   with self.subTest(origin=origin):self.assertEqual(self.request('POST',origin=origin)[0],403)
  self.assertEqual(self.request('POST',origin=self.origin,marker=False)[0],403)
  self.assertEqual(self.request(host='evil.example')[0],403)
 def test_invalid_configuration_fails_closed(self):
  for origin in ('https://*.ts.net','https://example.com','http://studio.example-tailnet.ts.net:8776',self.origin+'/path',self.origin+'?x=1',self.origin+'#x',self.origin.replace('8776','99999'),'https://user@studio.example-tailnet.ts.net'):
   with self.subTest(origin=origin):
    self.configure(origin);self.assertIsNone(remote_access.configured_origin(app.DATA));self.assertEqual(self.request()[0],200)
  (app.DATA/'remote-access.json').write_text('broken',encoding='utf-8')
  self.assertIsNone(remote_access.configured_origin(app.DATA))
 def test_serve_preserves_other_services_and_rejects_conflicts(self):
  authority=self.origin[8:];target='http://127.0.0.1:8776'
  config={'TCP':{'443':{'HTTPS':True}},'Web':{'studio.example-tailnet.ts.net:443':{'Handlers':{'/':{'Proxy':'http://127.0.0.1:3000'}}}}}
  before=json.dumps(config);endpoint_available(config,authority,target);self.assertEqual(json.dumps(config),before)
  config['TCP']['8776']={'HTTPS':True};config['Web'][authority]={'Handlers':{'/':{'Proxy':target}}}
  endpoint_available(config,authority,target)
  config['Web'][authority]['Handlers']['/other']={'Proxy':'http://127.0.0.1:3000'}
  with self.assertRaises(ValueError):endpoint_available(config,authority,target)
  del config['Web'][authority]['Handlers']['/other'];config['AllowFunnel']={authority:True}
  with self.assertRaises(ValueError):endpoint_available(config,authority,target)


if __name__=='__main__':unittest.main()
