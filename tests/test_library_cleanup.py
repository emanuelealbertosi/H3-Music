import json
import http.client
import pathlib
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import app
import library_cleanup


class CleanupTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='tmp-cleanup-',dir=app.ROOT/'tests')
  self.old=app.DATA,app.OUT
  app.DATA=pathlib.Path(self.tmp.name);app.OUT=app.DATA/'outputs';app.init()
 def tearDown(self):
  app.DATA,app.OUT=self.old;self.tmp.cleanup()
 def job(self,n,kind='generate',status='completed',source=None):
  ident=f'{n:032x}';request={'title':f'Brano {n}'}
  if source:request['source_id']=source
  app.db('INSERT INTO jobs(id,kind,status,request) VALUES(?,?,?,?)',(ident,kind,status,json.dumps(request)))
  d=app.OUT/ident;d.mkdir();(d/'audio.wav').write_bytes(b'audio');(d/'stems').mkdir();(d/'stems/vocals.wav').write_bytes(b'voice')
  return ident
 def exists(self,ident):return app.db('SELECT id FROM jobs WHERE id=?',(ident,),True) is not None
 def test_single_batch_and_idempotent_delete_preserve_unselected_files(self):
  a,b,c=self.job(1),self.job(2),self.job(3)
  project=app.project_save({'request':{'title':'Saved project'}})
  for directory in ('imports','voci'):
   p=app.DATA/directory;p.mkdir();(p/'original.wav').write_bytes(b'keep')
  result=library_cleanup.delete(app,[a,b,a]);self.assertEqual(set(result['deleted']),{a,b});self.assertEqual(result['errors'],[])
  for ident in (a,b):self.assertFalse(self.exists(ident));self.assertFalse((app.OUT/ident).exists())
  self.assertTrue(self.exists(c));self.assertEqual((app.OUT/c/'audio.wav').read_bytes(),b'audio')
  self.assertTrue(app.db('SELECT id FROM projects WHERE id=?',(project['id'],),True))
  self.assertEqual((app.DATA/'imports/original.wav').read_bytes(),b'keep');self.assertEqual((app.DATA/'voci/original.wav').read_bytes(),b'keep')
  self.assertEqual(library_cleanup.delete(app,[a])['missing'],[a])
 def test_invalid_ids_and_active_job_reject_whole_selection(self):
  a=self.job(1);b=self.job(2,status='queued')
  for ids in (None,[],['../imports'],[a,False],[a]*301,[a,b]):
   with self.subTest(ids=ids),self.assertRaises(ValueError):library_cleanup.delete(app,ids)
   self.assertTrue((app.OUT/a/'audio.wav').exists())
 def test_active_dependency_chain_and_legacy_voice_are_protected(self):
  a=self.job(1);b=self.job(2,'sep',source=a);c=self.job(3,'voice',source=b);d=self.job(4,'remix',status='queued',source=c)
  for ids in ([a],[b],[c]):
   with self.subTest(ids=ids),self.assertRaises(ValueError):library_cleanup.delete(app,ids)
  app.db("UPDATE jobs SET status='completed' WHERE id=?",(d,))
  with self.assertRaises(ValueError):library_cleanup.delete(app,[b])
  result=library_cleanup.delete(app,[b,c]);self.assertEqual(result['deleted'],[c,b]);self.assertTrue(self.exists(d))
 def test_locked_file_failure_is_reported_and_other_results_can_be_removed(self):
  a=self.job(1);b=self.job(2)
  real=library_cleanup.shutil.rmtree
  def remove(path):
   if path.name==a:raise PermissionError('busy')
   return real(path)
  with patch.object(library_cleanup.shutil,'rmtree',side_effect=remove):result=library_cleanup.delete(app,[a,b])
  self.assertEqual(result['deleted'],[b]);self.assertEqual(result['errors'][0]['id'],a);self.assertTrue(self.exists(a))
 def test_failed_voice_deletion_keeps_parent_stems(self):
  a=self.job(1,'sep');b=self.job(2,'voice',source=a)
  with patch.object(library_cleanup.shutil,'rmtree',side_effect=PermissionError('busy')):
   result=library_cleanup.delete(app,[a,b])
  self.assertEqual(result['deleted'],[]);self.assertEqual(len(result['errors']),2);self.assertTrue((app.OUT/a/'stems/vocals.wav').exists())
 def test_link_outside_results_is_rejected_without_touching_target(self):
  a=self.job(1);target=app.DATA/'imports';target.mkdir();(target/'keep.wav').write_bytes(b'keep')
  link=app.OUT/a/'external'
  try:link.symlink_to(target,target_is_directory=True)
  except OSError:self.skipTest('Symlink creation unavailable on this Windows account')
  with self.assertRaises(ValueError):library_cleanup.delete(app,[a])
  self.assertEqual((target/'keep.wav').read_bytes(),b'keep');link.unlink()
 def test_missing_output_folder_still_removes_record(self):
  a=self.job(1);library_cleanup.shutil.rmtree(app.OUT/a)
  self.assertEqual(library_cleanup.delete(app,[a])['deleted'],[a])
 def test_http_delete_requires_marker_and_removes_only_requested_results(self):
  a,b,c=self.job(1),self.job(2),self.job(3)
  server=app.http.server.ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
  previous=app.PORT;app.PORT=server.server_port
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   for marked,expected in ((False,403),(True,200)):
    headers={'Content-Type':'application/json','Origin':f'http://127.0.0.1:{app.PORT}'}
    if marked:headers['X-H3-Music']='1'
    client=http.client.HTTPConnection('127.0.0.1',app.PORT,timeout=5)
    try:
     client.request('POST','/api/jobs/delete',json.dumps({'ids':[a,b]}),headers)
     response=client.getresponse();body=json.loads(response.read());self.assertEqual(response.status,expected)
     if marked:self.assertEqual(set(body['deleted']),{a,b})
     else:self.assertTrue((app.OUT/a/'audio.wav').exists())
    finally:client.close()
   self.assertTrue(self.exists(c));self.assertFalse(self.exists(a));self.assertFalse((app.OUT/b).exists())
  finally:server.shutdown();server.server_close();thread.join();app.PORT=previous


if __name__=='__main__':unittest.main()
