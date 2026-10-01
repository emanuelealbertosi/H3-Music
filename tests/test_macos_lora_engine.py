import hashlib, io, json, sys, tempfile, unittest, zipfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import install_macos

class MacEngineUpdateTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(dir=ROOT/'tests',prefix='tmp-mac-lora-');self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name);self.engine=self.root/'runtime/engine/audiocpp_cli';self.engine.parent.mkdir(parents=True)
  self.patches=[patch.object(install_macos,'ROOT',self.root),patch.object(install_macos.platform_runtime,'binary',return_value=self.engine),patch.object(install_macos.platform,'machine',return_value='arm64')]
  for p in self.patches:p.start();self.addCleanup(p.stop)
 def archive(self):
  content=b'new native engine yue2.ar_lora yue2.nar_lora';blob=io.BytesIO()
  with zipfile.ZipFile(blob,'w') as z:z.writestr('H3-Music/runtime/engine/audiocpp_cli',content)
  package=blob.getvalue();sums=(hashlib.sha256(package).hexdigest()+'  H3-Music-Mac-arm64.zip\n').encode()
  return content,[io.BytesIO(sums),io.BytesIO(package)]
 def test_new_engine_is_preserved_without_network(self):
  self.engine.write_bytes(b'yue2.ar_lora yue2.nar_lora')
  with patch.object(install_macos.execution,'check_engine'),patch.object(install_macos.urllib.request,'urlopen') as download:install_macos.install_engine();download.assert_not_called()
 def test_existing_cpu_engine_is_updated_and_backed_up(self):
  self.engine.write_bytes(b'healthy old engine');content,responses=self.archive()
  with patch.object(install_macos.execution,'check_engine'),patch.object(install_macos.urllib.request,'urlopen',side_effect=responses):install_macos.install_engine()
  self.assertEqual(self.engine.read_bytes(),content);self.assertEqual(next(self.engine.parent.glob('*.backup-*')).read_bytes(),b'healthy old engine')
 def test_invalid_candidate_keeps_previous_engine(self):
  self.engine.write_bytes(b'healthy old engine');_,responses=self.archive()
  with patch.object(install_macos.execution,'check_engine',side_effect=[{},ValueError('bad candidate')]),patch.object(install_macos.urllib.request,'urlopen',side_effect=responses),self.assertRaises(ValueError):install_macos.install_engine()
  self.assertEqual(self.engine.read_bytes(),b'healthy old engine');self.assertFalse(list(self.engine.parent.glob('*.backup-*')))
if __name__=='__main__':unittest.main()
