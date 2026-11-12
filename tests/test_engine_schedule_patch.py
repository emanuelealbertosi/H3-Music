"""Rebuild the extension from pristine pinned files, then apply it twice."""
from pathlib import Path
import hashlib
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'vendor/audio.cpp'


@unittest.skipUnless((SOURCE/'.git').exists(),'Native checkout is only present on build machines')
class NativePatchTests(unittest.TestCase):
 def test_pristine_source_and_repeated_patch_are_reproducible(self):
  files=['CMakeLists.txt','include/engine/models/yue2/types.h','src/models/yue2/request.cpp',
         'src/models/yue2/pipeline.cpp','include/engine/models/yue2/assets.h','src/models/yue2/session.cpp',
         'include/engine/models/yue2/tokenizer_text.h','src/models/yue2/tokenizer_text.cpp',
         'include/engine/models/yue2/ar_runtime.h','src/models/yue2/ar_runtime.cpp',
         'include/engine/framework/modules/transformers/qwen_causal_decode_runtime.h',
         'src/framework/modules/transformers/qwen_causal_decode_runtime.cpp']
  with tempfile.TemporaryDirectory(dir=ROOT/'tests',prefix='tmp-schedule-patch-') as temp:
   destination=Path(temp)
   for name in files:
    data=subprocess.run(['git','-C',str(SOURCE),'show','HEAD:'+name],check=True,capture_output=True).stdout
    p=destination/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
   (destination/'src/framework/assets').mkdir(parents=True,exist_ok=True)
   (destination/'include/engine/framework/assets').mkdir(parents=True,exist_ok=True)
   def apply():
    result=subprocess.run([sys.executable,str(ROOT/'scripts/patch_engine.py'),'--source',str(destination)],capture_output=True,text=True)
    self.assertEqual(result.returncode,0,result.stderr)
   def hashes():return {str(p.relative_to(destination)):hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.rglob('*') if p.is_file()}
   apply();first=hashes();apply();self.assertEqual(first,hashes())
   for name in files:
    self.assertEqual((destination/name).read_bytes(),(SOURCE/name).read_bytes())


if __name__=='__main__':unittest.main()
