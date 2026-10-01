"""Pinned CNZN adapters; lossless fused projection split, stdlib only."""
import hashlib, json, os, struct, urllib.request
from pathlib import Path
import model_store

REVISION = '89508af770d21ea26215603fdd777f182ba4ecee'
REPO = 'becausereasons/yue2-cnzn-canzone-italiana'
CATALOG = {
 'teatro': ('Teatro · canto espressivo', 1.0, '6faef04d10c20a28b311815421e12676b3abfa5c650bfbd1fff1a0c01d48f31d'),
 'notte': ('Notte · timbro morbido', 0.5, '93b87d31bbce1dfb4e83be9d1f55e155b71f3572e640eda5351e7a34f0f32527'),
 'coro': ('Coro · voce energica', 1.0, 'c0708785f63a7f6d582d172120aa64e8085a3f578ac5b722cb36a2c2b1e347ed'),
 'sussurro': ('Sussurro · parlato sussurrato', 1.0, '2ec3fc4eab4413623c600015ba3f5b7ce59f5604668344912cd2eb495b0bbd63'),
}
SIZE = 117500808

def validate(value):
 if value in ('', None): return ''
 if not isinstance(value,str) or value not in CATALOG: raise ValueError('LoRA italiano non valido.')
 return value

def directory(root): return model_store.location(root)/'loras/cnzn'

def digest(path):
 with Path(path).open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()

def read_tensors(path):
 with Path(path).open('rb') as f:
  length=struct.unpack('<Q',f.read(8))[0]
  if not 0 < length < 2**20: raise ValueError('Intestazione LoRA non valida.')
  header=json.loads(f.read(length)); data=f.read()
 out={}
 for name,meta in header.items():
  if name=='__metadata__':continue
  if meta['dtype']!='BF16' or len(meta['shape'])!=2:raise ValueError('Formato CNZN inatteso: '+name)
  start,end=meta['data_offsets']; shape=meta['shape']
  if not 0<=start<end<=len(data) or end-start!=shape[0]*shape[1]*2:raise ValueError('Tensore CNZN incompleto.')
  out[name]=(shape,data[start:end])
 return out

def write_tensors(path,tensors):
 header={'__metadata__':{'source':REPO,'revision':REVISION,'conversion':'H3 lossless split v1'}}; blobs=[];offset=0
 for name,(shape,blob) in sorted(tensors.items()):
  header[name]={'dtype':'BF16','shape':shape,'data_offsets':[offset,offset+len(blob)]};offset+=len(blob);blobs.append(blob)
 raw=json.dumps(header,separators=(',',':')).encode();raw+=b' '*((-len(raw))%8)
 staged=Path(path).with_suffix('.partial')
 with staged.open('wb') as f:
  f.write(struct.pack('<Q',len(raw)));f.write(raw)
  for blob in blobs:f.write(blob)
 staged.replace(path)

def split_adapter(path):
 tensors=read_tensors(path);output={'ar':{},'nar':{}}; consumed=set()
 groups={'self_attn.qkv_proj':(('self_attn.q_proj',2048),('self_attn.k_proj',1024),('self_attn.v_proj',1024)),
         'mlp.gate_up_proj':(('mlp.gate_proj',6144),('mlp.up_proj',6144)),
         'self_attn.o_proj':(('self_attn.o_proj',2048),),'mlp.down_proj':(('mlp.down_proj',2048),)}
 for branch in output:
  for layer in range(28):
   for source,targets in groups.items():
    prefix=f'layers.{layer}.'+('nar_' if branch=='nar' else '')
    key=('diffusion_model' if branch=='nar' else 'text_encoders')+f'.model.layers.{layer}.'+source
    a,b=key+'.lora_A.weight',key+'.lora_B.weight'
    ash,abytes=tensors[a];bsh,bbytes=tensors[b]
    expected_in=6144 if source=='mlp.down_proj' else 2048
    if ash!=[32,expected_in] or bsh!=[sum(size for _,size in targets),32]:raise ValueError('Dimensioni CNZN inattese: '+key)
    offset=0
    # Share the FULL A matrix and slice B by output rows. This preserves B@A
    # even for cross-coupled/shared ranks; never assume block-diagonal ranks.
    for target,size in targets:
     output[branch][prefix+target+'.lora_A']=(ash,abytes)
     output[branch][prefix+target+'.lora_B']=([size,32],bbytes[offset*64:(offset+size)*64]);offset+=size
    consumed.update((a,b))
 if consumed!=set(tensors):raise ValueError('Tensori CNZN non riconosciuti.')
 return output

def installed(root,ident,verify=False):
 ident=validate(ident)
 if not ident:return True
 folder=directory(root)/ident
 try:
  record=json.loads((folder/'installed.json').read_text(encoding='utf-8'))
  return record['revision']==REVISION and record['source_sha256']==CATALOG[ident][2] and all(
   (folder/name).is_file() and (folder/name).stat().st_size==info['size'] and (not verify or digest(folder/name)==info['sha256']) for name,info in record['files'].items()) and set(record['files'])=={'ar.safetensors','nar.safetensors'}
 except (OSError,ValueError,KeyError,TypeError):return False

def status(root):return [{'id':i,'label':v[0],'ar_scale':v[1],'nar_scale':1,'installed':installed(root,i)} for i,v in CATALOG.items()]

def install(root,progress=lambda **kwargs:None):
 root=Path(root)
 with model_store.exclusive(root):
  model_store.check_idle(root)
  base=directory(root);(base/'raw').mkdir(parents=True,exist_ok=True)
  for i,(_,scale,sha) in CATALOG.items():
   if installed(root,i,True):continue
   raw=base/'raw'/f'cnzn_{i}.safetensors';progress(file=i,status='downloading')
   if not raw.exists() or raw.stat().st_size!=SIZE or digest(raw)!=sha:
    temp=raw.with_suffix('.partial')
    req=urllib.request.Request(f'https://huggingface.co/{REPO}/resolve/{REVISION}/{raw.name}',headers={'User-Agent':'H3-Music'})
    with urllib.request.urlopen(req,timeout=90) as response,temp.open('wb') as f:
     total=0
     while blob:=response.read(2**20):
      f.write(blob);total+=len(blob);progress(file=i,status='downloading',done=total,total=SIZE)
    if temp.stat().st_size!=SIZE or digest(temp)!=sha:raise ValueError('Download CNZN non integro: '+i)
    temp.replace(raw)
   progress(file=i,status='converting');branches=split_adapter(raw);folder=base/i;folder.mkdir(exist_ok=True)
   for branch,tensors in branches.items():write_tensors(folder/(branch+'.safetensors'),tensors)
   record={'revision':REVISION,'source_sha256':sha,'ar_scale':scale,'nar_scale':1,'files':{p.name:{'size':p.stat().st_size,'sha256':digest(p)} for p in (folder/'ar.safetensors',folder/'nar.safetensors')}}
   pending=folder/'installed.tmp';pending.write_text(json.dumps(record),encoding='utf-8');pending.replace(folder/'installed.json')
  progress(status='completed',file='',done=SIZE,total=SIZE)

def session_options(root,ident):
 ident=validate(ident)
 if not ident:return {}
 if not installed(root,ident,True):raise ValueError('Installa o ripara i quattro LoRA italiani da Sistema.')
 folder=directory(root)/ident
 return {'yue2.ar_lora':str(folder/'ar.safetensors'),'yue2.nar_lora':str(folder/'nar.safetensors'),
         'yue2.ar_lora_scale':CATALOG[ident][1],'yue2.nar_lora_scale':1}

def style_prompt(style,ident):
 if not validate(ident):return style
 prefix='cnzn, Italian'
 if ident=='sussurro':prefix+=', whispered spoken vocals'
 return prefix+', '+style
