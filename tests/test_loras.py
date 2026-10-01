import json, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import app, loras, model_store

class LoraTests(unittest.TestCase):
 def test_optional_default_does_not_change_style_or_engine_options(self):
  self.assertEqual(app.validate({})['lora'],'')
  self.assertEqual(loras.style_prompt('Italian, pop',''),'Italian, pop')
  self.assertEqual(loras.session_options(ROOT,''),{})
  for bad in ('sanremo','../teatro',True,[],{}):
   with self.assertRaises(ValueError):app.validate({'lora':bad})

 def test_defaults_and_trigger(self):
  self.assertEqual({i:v[1] for i,v in loras.CATALOG.items()},{'teatro':1,'notte':.5,'coro':1,'sussurro':1})
  self.assertEqual(loras.style_prompt('pop','notte'),'cnzn, Italian, pop')
  self.assertIn('whispered spoken',loras.style_prompt('pop','sussurro'))

 def test_missing_and_corrupt_installation_are_not_accepted(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'tests',prefix='tmp-lora-') as temp:
   root=Path(temp);folder=loras.directory(root)/'teatro';folder.mkdir(parents=True)
   self.assertFalse(loras.installed(root,'teatro'))
   record={'revision':loras.REVISION,'source_sha256':loras.CATALOG['teatro'][2],'files':{}}
   for name in ('ar.safetensors','nar.safetensors'):
    p=folder/name;p.write_bytes(b'adapter');record['files'][name]={'size':7,'sha256':loras.digest(p)}
   (folder/'installed.json').write_text(json.dumps(record))
   self.assertTrue(loras.installed(root,'teatro',True))
   opts=loras.session_options(root,'teatro');self.assertEqual(opts['yue2.nar_lora_scale'],1)
   self.assertTrue(opts['yue2.ar_lora'].startswith(str(folder)))
   (folder/'nar.safetensors').write_bytes(b'corrupt')
   self.assertFalse(loras.installed(root,'teatro',True))
   with self.assertRaises(ValueError):loras.session_options(root,'teatro')

 def test_safe_tensor_roundtrip(self):
  with tempfile.TemporaryDirectory(dir=ROOT/'tests',prefix='tmp-lora-') as temp:
   path=Path(temp)/'adapter.safetensors';tensors={'a':([2,3],bytes(range(12))),'b':([3,2],bytes(range(12,24)))}
   loras.write_tensors(path,tensors);self.assertEqual(loras.read_tensors(path),tensors)
   with path.open('r+b') as f:f.truncate(path.stat().st_size-1)
   with self.assertRaises(ValueError):loras.read_tensors(path)

 def test_fused_shared_ranks_preserve_all_a_columns_and_b_rows(self):
  # Non-block-diagonal A/B: any rank can affect every q/k/v output.
  tensors={};groups={'self_attn.qkv_proj':(2048,4096),'self_attn.o_proj':(2048,2048),'mlp.gate_up_proj':(2048,12288),'mlp.down_proj':(6144,2048)}
  for branch in ('diffusion_model','text_encoders'):
   for layer in range(28):
    for name,(inp,out) in groups.items():
     key=f'{branch}.model.layers.{layer}.{name}'
     tensors[key+'.lora_A.weight']=([32,inp],b'\x01\x3f'*(32*inp))
     tensors[key+'.lora_B.weight']=([out,32],bytes(range(256))*(out*64//256))
  with patch.object(loras,'read_tensors',return_value=tensors):result=loras.split_adapter('unused')
  for branch,prefix in [('ar',''),('nar','nar_')]:
   target=result[branch];self.assertEqual(len(target),28*7*2)
   fused=tensors[('diffusion_model' if branch=='nar' else 'text_encoders')+'.model.layers.0.self_attn.qkv_proj.lora_B.weight'][1]
   self.assertEqual(b''.join(target['layers.0.'+prefix+'self_attn.'+p+'.lora_B'][1] for p in ('q_proj','k_proj','v_proj')),fused)
   for p in ('q_proj','k_proj','v_proj'):self.assertEqual(target['layers.0.'+prefix+'self_attn.'+p+'.lora_A'][0],[32,2048])
  tensors['unrecognized']=([1,1],b'xx')
  with patch.object(loras,'read_tensors',return_value=tensors),self.assertRaises(ValueError):loras.split_adapter('unused')

 def test_old_engine_cannot_silently_ignore_adapter(self):
  class Result:stdout='old engine options'
  with patch.object(app,'run_capture',return_value=Result()),self.assertRaisesRegex(ValueError,'non supporta'):app.check_lora_engine()

if __name__=='__main__':unittest.main()
