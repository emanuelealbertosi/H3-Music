import hashlib,pathlib,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from scripts.transcription_models import matches,update_files
import transcription

def entry(name,data,lfs=False):
 result={'type':'file','path':name,'size':len(data),'oid':hashlib.sha1(f'blob {len(data)}\0'.encode()+data).hexdigest()}
 if lfs:result['lfs']={'oid':hashlib.sha256(data).hexdigest()}
 return result

class UpdateTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='tmp-update-',dir=pathlib.Path(__file__).parent);self.root=pathlib.Path(self.tmp.name);self.folder=self.root/'models/SheetSage2';self.folder.mkdir(parents=True)
 def tearDown(self):self.tmp.cleanup()
 def update(self,entries,download):return update_files(self.root,self.folder,'m-a-p/SheetSage2','abc',entries,download)
 def test_unchanged_weights_are_not_downloaded(self):
  p=self.folder/'model.safetensors';p.write_bytes(b'weights');e=entry(p.name,b'weights',True)
  def fail(*args):self.fail('unchanged file must not be downloaded')
  self.assertIsNone(self.update([e],fail));self.assertTrue(matches(p,e))
 def test_corrupt_same_size_file_is_repaired_and_backed_up(self):
  p=self.folder/'module.py';p.write_bytes(b'wrong');e=entry(p.name,b'right')
  backup=self.update([e],lambda url,out:out.write_bytes(b'right'))
  self.assertEqual(p.read_bytes(),b'right');self.assertEqual((backup/p.name).read_bytes(),b'wrong')
 def test_failed_download_cannot_partially_replace_installation(self):
  (self.folder/'first.py').write_bytes(b'old')
  entries=[entry('first.py',b'new'),entry('second.py',b'expected')]
  with self.assertRaises(ValueError):self.update(entries,lambda url,out:out.write_bytes(b'new' if out.name=='first.py' else b'bad'))
  self.assertEqual((self.folder/'first.py').read_bytes(),b'old');self.assertFalse((self.folder/'second.py').exists())
 def test_activation_failure_rolls_back_previous_files(self):
  (self.folder/'first.py').write_bytes(b'old');original=pathlib.Path.replace
  def replace(path,target):
   if path.name=='second.py':raise OSError('simulated activation failure')
   return original(path,target)
  with patch.object(pathlib.Path,'replace',replace),self.assertRaises(OSError):
   self.update([entry('first.py',b'new'),entry('second.py',b'new')],lambda url,out:out.write_bytes(b'new'))
  self.assertEqual((self.folder/'first.py').read_bytes(),b'old');self.assertFalse((self.folder/'second.py').exists())
 def test_reject_unsafe_metadata_paths(self):
  for name in ('../outside','F:/outside','/outside','..\\outside'):
   with self.assertRaises(ValueError):self.update([entry(name,b'new')],lambda url,out:out.write_bytes(b'new'))
 def test_revision_is_read_from_installed_manifest(self):
  import json
  p=self.root/'models/transcription-manifest.json';p.write_text(json.dumps({'sheet_revision':'abc'}))
  self.assertEqual(transcription.installed_revision(self.root),'abc')
  p.write_text('invalid');self.assertIsNone(transcription.installed_revision(self.root))

if __name__=='__main__':unittest.main()
